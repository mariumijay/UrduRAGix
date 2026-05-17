from __future__ import annotations

"""
file
main.py  — Unified Urdu RAG CLI
================================
Run after building both index sets:
    python preprocess.py --book data/ocr.txt          # Urdu A → embeddings/urdu_A/
    python -m ingestion.ingest_b data/                # Urdu B → embeddings/urdu_B/
    ollama serve                                       # Qwen model must be running
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

# Reconfigure stdout and stderr for UTF-8 on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from utils.urdu_render import format_for_console as format_urdu
from dotenv import load_dotenv
from config.config import GENRE_TO_MODE
from retrieval.poetry_loader import load_shair_for_paper

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from generation.llm import _create_completion, DEFAULT_MODEL, generate_answer, get_model_for_genre
from generation.prompt_b import get_prompt, detect_intent, build_paper_prompt
from ingestion.embedder import get_dataset_paths
from retrieval.bm25_retriever import BM25Retriever
from retrieval.faiss_retriever import FAISSRetriever
from retrieval.hybrid import reciprocal_rank_fusion
from retrieval.query_normalizer import normalize_query
from retrieval.reranker import rerank
from retrieval.router import classify_query, classify_query_full, route_dataset

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

TOP_K_DENSE  = int(os.getenv("TOP_K_DENSE",  "20"))
TOP_K_SPARSE = int(os.getenv("TOP_K_SPARSE", "20"))
TOP_K_FINAL  = int(os.getenv("TOP_K_FINAL",  "5"))

RETRIEVAL_CONFIG: dict[str, dict] = {
    # writing genres — faiss-heavy (semantic similarity matters most)
    "application":      {"faiss_k": 1, "bm25_w": 0.4, "faiss_w": 0.6, "do_rerank": True},
    "letter":           {"faiss_k": 1, "bm25_w": 0.4, "faiss_w": 0.6, "do_rerank": True},
    "story":            {"faiss_k": 1, "bm25_w": 0.2, "faiss_w": 0.8, "do_rerank": True},
    "dialogue":         {"faiss_k": 1, "bm25_w": 0.3, "faiss_w": 0.7, "do_rerank": True},
    # tashreeh genres — balanced (need exact verse + semantic context)
    "tashreeh_ghazal":  {"faiss_k": 3, "bm25_w": 0.5, "faiss_w": 0.5, "do_rerank": True},
    "tashreeh_nazam":   {"faiss_k": 4, "bm25_w": 0.5, "faiss_w": 0.5, "do_rerank": True},
    "nasar_tashreeh":   {"faiss_k": 2, "bm25_w": 0.5, "faiss_w": 0.5, "do_rerank": True},
    "poem_explanation": {"faiss_k": 3, "bm25_w": 0.5, "faiss_w": 0.5, "do_rerank": True},
    # structured long — need more context chunks
    "khulasa":          {"faiss_k": 2, "bm25_w": 0.4, "faiss_w": 0.6, "do_rerank": True},
    "markazi_khyal":    {"faiss_k": 1, "bm25_w": 0.4, "faiss_w": 0.6, "do_rerank": True},
    # objective / one-line — bm25-heavy (keyword exact match matters)
    "mcq":              {"faiss_k": 3, "bm25_w": 0.6, "faiss_w": 0.4, "do_rerank": False},
    "word_meanings":    {"faiss_k": 2, "bm25_w": 0.7, "faiss_w": 0.3, "do_rerank": False},
    "sentence_correction": {"faiss_k": 2, "bm25_w": 0.7, "faiss_w": 0.3, "do_rerank": False},
    "zarbul_imsal":     {"faiss_k": 2, "bm25_w": 0.7, "faiss_w": 0.3, "do_rerank": False},
    # short responses — balanced
    "short_question":   {"faiss_k": 3, "bm25_w": 0.5, "faiss_w": 0.5, "do_rerank": True},
    "comprehension":    {"faiss_k": 3, "bm25_w": 0.5, "faiss_w": 0.5, "do_rerank": True},
    "translation":      {"faiss_k": 3, "bm25_w": 0.5, "faiss_w": 0.5, "do_rerank": True},
}

# Default config for genres not explicitly listed above
_DEFAULT_RETRIEVAL = {"faiss_k": 3, "bm25_w": 0.5, "faiss_w": 0.5, "do_rerank": True}

def _genre_to_mode(genre: str) -> str:
    return GENRE_TO_MODE.get(genre, "short")

WORD_RANGES: dict[str, tuple[int | None, int | None]] = {
    # one-line / objective — no length check
    "mcq":                 (None, None),
    "word_meanings":       (None, None),
    "sentence_correction": (None, None),
    "zarbul_imsal":        (None, None),
    # short responses — no length check
    "short_question":      (None, None),
    "general_qa":          (None, None),
    "comprehension":       (None, None),
    "translation":         (None, None),
    # tashreeh — soft length targets
    "tashreeh_ghazal":     (120, 150),
    "tashreeh_nazam":      (120, 150),
    "nasar_tashreeh":      (130, 160),
    "poem_explanation":    (100, 130),
    # structured long
    "khulasa":             (250, 350),
    "markazi_khyal":       (80,  120),
    # writing genres — strict length enforced
    "application":         (150, 180),
    "letter":              (150, 200),
    "story":               (180, 220),
    "dialogue":            (150, 200),
}

_B_GENRES = frozenset({
    # one-line / objective
    "mcq", "word_meanings", "sentence_correction", "zarbul_imsal",
    # short
    "short_question", "general_qa", "comprehension", "translation",
    # tashreeh
    "tashreeh_ghazal", "tashreeh_nazam", "nasar_tashreeh", "poem_explanation",
    # structured long
    "khulasa", "markazi_khyal",
    # writing
    "application", "letter", "story", "dialogue",
})


# ── Global state ──────────────────────────────────────────────────────────────

class _State:
    faiss_a:  FAISSRetriever | None = None
    bm25_a:   BM25Retriever  | None = None
    manifest: dict = {}
    ready_a:  bool = False

    faiss_b:  FAISSRetriever | None = None
    bm25_b:   BM25Retriever  | None = None
    ready_b:  bool = False

state = _State()


# ── Urdu formatter ────────────────────────────────────────────────────────────
# The format_urdu function is now imported from utils.urdu_render

def _dedupe_chunks(chunks: list[dict], similarity_threshold: float = 0.85) -> list[dict]:
    """Remove near-duplicate chunks based on text overlap.
    Uses a simple token-set Jaccard similarity to filter semantic duplicates.
    """
    if not chunks:
        return chunks
    
    seen_texts: list[set[str]] = []
    unique: list[dict] = []
    
    for c in chunks:
        text = c.get("text", "").strip()
        if not text:
            continue
        tokens = set(text.split())
        if not tokens:
            continue
        
        is_dup = False
        for prev_tokens in seen_texts:
            overlap = len(tokens & prev_tokens) / max(len(tokens | prev_tokens), 1)
            if overlap >= similarity_threshold:
                is_dup = True
                break
        
        if not is_dup:
            seen_texts.append(tokens)
            unique.append(c)
    
    return unique

# ── Index loading ─────────────────────────────────────────────────────────────

def _load_indexes_a() -> bool:
    paths = get_dataset_paths("urdu_A")
    missing = [k for k in ("faiss", "bm25", "metadata") if not paths[k].exists()]
    if missing:
        print(f"[WARN] Urdu A index files missing: {missing}  (غزل/نظم/نثر/سبق unavailable)")
        return False
    try:
        state.faiss_a = FAISSRetriever("urdu_A")
        state.faiss_a.load()
        state.bm25_a = BM25Retriever("urdu_A")
        state.bm25_a.load()

        manifest_path = paths["faiss"].parent / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                state.manifest = json.load(f)

        state.ready_a = True
        print(
            f"[OK] Urdu A loaded — "
            f"{state.manifest.get('total_chunks', '?')} chunks | "
            f"Book: {state.manifest.get('book_title', 'Unknown')}"
        )
        return True
    except Exception as exc:
        logger.error("Failed to load Urdu A indexes: %s", exc, exc_info=True)
        return False


def _load_indexes_b() -> bool:
    paths = get_dataset_paths("urdu_B")
    if not any(paths[k].exists() for k in ("faiss", "bm25", "metadata")):
        print("[WARN] Urdu B index files not found.  (درخواست/خط/مضمون/کہانی unavailable)")
        return False
    try:
        state.faiss_b = FAISSRetriever("urdu_B")
        ok_faiss = state.faiss_b.load()
        state.bm25_b = BM25Retriever("urdu_B")
        ok_bm25 = state.bm25_b.load()
        state.ready_b = ok_faiss and ok_bm25
        if state.ready_b:
            print(f"[OK] Urdu B loaded — {state.faiss_b.index.ntotal} vectors")
        return state.ready_b
    except Exception as exc:
        logger.error("Failed to load Urdu B indexes: %s", exc, exc_info=True)
        return False


def load_all_indexes() -> bool:
    ok_a = _load_indexes_a()
    ok_b = _load_indexes_b()
    if not ok_a and not ok_b:
        print(
            "\n[ERROR] No indexes loaded.\n"
            "        Run  python preprocess.py --book data/ocr.txt    for Urdu A\n"
            "        Run  python -m ingestion.ingest_b data/          for Urdu B\n"
        )
        return False
    return True


# ── Urdu A pipeline ───────────────────────────────────────────────────────────

def _retrieve_a(urdu_query: str, top_k: int, mode: str = "short") -> tuple[list[dict], list[dict]]:
    dense  = state.faiss_a.search(urdu_query, top_k=TOP_K_DENSE)
    sparse = state.bm25_a.search(urdu_query,  top_k=TOP_K_SPARSE)
    fused  = reciprocal_rank_fusion([dense, sparse], mode=mode)
    ranked = rerank(urdu_query, fused, top_k=top_k)
    ranked = _dedupe_chunks(ranked)
    citations = [
        {
            "chunk_id":   c["chunk_id"],
            "text":       c["text"],
            "chapter":    c.get("chapter"),
            "page_start": c.get("page_start"),
            "score":      round(c.get("rerank_score", c.get("score", 0.0)), 4),
        }
        for c in ranked
    ]
    return ranked, citations


def _print_result_a(result: dict) -> None:
    if "error" in result:
        print(f"\n[خرابی] {result['error']}\n")
        return
    answer = re.sub(r"<think>.*?</think>", "", result["answer"], flags=re.DOTALL)
    answer = re.sub(r"جواب:\s*", "", answer).strip()
    print(format_urdu(answer))


# ── Urdu B pipeline ───────────────────────────────────────────────────────────

def _retrieve_b(urdu_query: str, genre: str, mode: str = "short") -> list[dict]:
    if genre == "short_question":
        cfg = {**RETRIEVAL_CONFIG.get(genre, _DEFAULT_RETRIEVAL), "faiss_k": 8}
    else:
        cfg = RETRIEVAL_CONFIG.get(genre, _DEFAULT_RETRIEVAL)
    faiss_n = max(10, int(cfg["faiss_w"] * 20))
    bm25_n  = max(10, int(cfg["bm25_w"]  * 20))
    dense  = state.faiss_b.search(urdu_query, top_k=faiss_n)
    sparse = state.bm25_b.search(urdu_query,  top_k=bm25_n)
    fused  = reciprocal_rank_fusion([dense, sparse], mode=mode, genre=genre)
    if cfg["do_rerank"]:
        return _dedupe_chunks(rerank(urdu_query, fused, top_k=cfg["faiss_k"]))
    return _dedupe_chunks(fused[:cfg["faiss_k"]])


async def _generate_b(genre: str, chunks: list[dict], query: str) -> str:
    messages = get_prompt(genre, chunks, query)
    model = get_model_for_genre(genre)
    response = await _create_completion(
        model, messages, False, temperature=0.3, max_tokens=2048,
    )
    raw = response.choices[0].message.content
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()


async def _validate(genre: str, output: str) -> list[str]:
    min_w, max_w = WORD_RANGES.get(genre, (None, None))
    skip_length  = min_w is None
    length_line  = "3. (length check skipped — always Y for this genre)" if skip_length \
                   else f"3. Is word count between {min_w} and {max_w}? YES/NO"
    length_fmt   = "length:Y" if skip_length else "length:{Y/N}"

    prompt = (
        f"Given this {genre} output, check ONLY:\n"
        f"1. Does it have correct opening structure? YES/NO\n"
        f"2. Does it have correct closing structure? YES/NO\n"
        f"{length_line}\n"
        f"Output format: opening:{{Y/N}} closing:{{Y/N}} {length_fmt}\n"
        f"Text:\n{output}"
    )
    try:
        resp = await _create_completion(
            DEFAULT_MODEL, [{"role": "user", "content": prompt}],
            False, temperature=0.0, max_tokens=30,
        )
        result = resp.choices[0].message.content.strip()
        failing = []
        if "opening:N" in result: failing.append("opening")
        if "closing:N" in result: failing.append("closing")
        if not skip_length and "length:N" in result: failing.append("length")
        sentences = [s.strip() for s in re.split(r'[۔!؟]', output) if len(s.strip()) > 15]
        if len(sentences) != len(set(sentences)):
            failing.append("repetition")
        return failing
    except Exception:
        return []


async def _fix(genre: str, output: str, failing_parts: list[str]) -> str:
    parts_str = " and ".join(failing_parts)
    fix_prompt = (
        f"Fix ONLY the {parts_str} of this {genre}. "
        f"Keep everything else unchanged.\nOriginal:\n{output}"
    )
    try:
        resp = await _create_completion(
            DEFAULT_MODEL, [{"role": "user", "content": fix_prompt}],
            False, temperature=0.2, max_tokens=2048,
        )
        fixed = resp.choices[0].message.content
        return re.sub(r"<think>.*?</think>", "", fixed, flags=re.DOTALL).strip()
    except Exception:
        return output


def _print_result_b(result: dict) -> None:
    if "error" in result:
        print(f"\n[خرابی] {result['error']}\n")
        return
    genre     = result.get("genre", "")
    validated = result.get("validated", True)
    print(f"\n[صنف: {genre}]  {'✓' if validated else '~fixed'}")
    print("-" * 60)
    print(format_urdu(result["answer"]))
    print()


# ── Both-dataset pipeline (merged retrieval) ──────────────────────────────────

def _retrieve_both(urdu_query: str) -> list[dict]:
    result_lists = []
    
    if state.ready_a:
        result_lists += [
            state.faiss_a.search(urdu_query, top_k=3),
            state.bm25_a.search(urdu_query,  top_k=3),
        ]

    if state.ready_b:
        result_lists += [
            state.faiss_b.search(urdu_query, top_k=3),
            state.bm25_b.search(urdu_query,  top_k=3),
        ]
    fused = reciprocal_rank_fusion(result_lists)
    fused = fused[:20]
    fused = _dedupe_chunks(fused)
    return rerank(urdu_query, fused, top_k=4)


# ── Paper Retrieval Mode ────────────────────────────────────────────────────────
def retrieve_for_paper(current_state) -> tuple[list[dict], list[dict]]:
    SUBQUERIES = [
        "MCQ سوالات نثر نظم غزل",
        "اشعار کی تشریح نظم غزل",
        "مختصر سوالات نثر",
        "خلاصہ مرکزی خیال",
        "خط درخواست",
        "جملہ درستی ضرب الامثال قواعد",
    ]
    
    # Dedicated poetry subquery with higher top_k for better verse retrieval
    POETRY_SUBQUERIES = [
        "اشعار بند نمبر نظم غزل حمد نعت شعر",
        "شعر تشریح مصرع بند",
    ]
    
    all_fused = []
    
    for subq in SUBQUERIES:
        result_lists = []
        if current_state.ready_a:
            result_lists.append(current_state.faiss_a.search(subq, top_k=10))
            result_lists.append(current_state.bm25_a.search(subq, top_k=10))
        if current_state.ready_b:
            result_lists.append(current_state.faiss_b.search(subq, top_k=10))
            result_lists.append(current_state.bm25_b.search(subq, top_k=10))
            
        if result_lists:
            subq_fused = reciprocal_rank_fusion(result_lists)
            all_fused.extend(subq_fused)
    
    # Poetry-specific retrieval with higher top_k
    for subq in POETRY_SUBQUERIES:
        result_lists = []
        if current_state.ready_a:
            result_lists.append(current_state.faiss_a.search(subq, top_k=15))
            result_lists.append(current_state.bm25_a.search(subq, top_k=15))
        if result_lists:
            subq_fused = reciprocal_rank_fusion(result_lists)
            all_fused.extend(subq_fused)

    # Global deduplication across all subquery results
    unique_chunks = _dedupe_chunks(all_fused, similarity_threshold=0.85)
    
    # Keep top 50 unique chunks (increased from 40 for better poetry coverage)
    unique_chunks = unique_chunks[:50]
    
    meta_a = [c for c in unique_chunks if c.get("dataset") == "urdu_A"]
    meta_b = [c for c in unique_chunks if c.get("dataset") == "urdu_B"]
    
    # Log verse chunk availability
    verse_a = sum(1 for c in meta_a if c.get("is_verse") is True)
    logger.info(f"Paper retrieval: {len(meta_a)} urdu_A chunks ({verse_a} verse), {len(meta_b)} urdu_B chunks")
    if verse_a == 0:
        print("[WARN] No is_verse=True chunks found in retrieval — poetry quality may be poor")
    
    return meta_a, meta_b

# ── Paper helper (shared between fast-path and LLM-path) ──────────────────────
from typing import AsyncGenerator

def _extract_couplets_from_file(file_path: Path) -> list[str]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # Exclude parenthesized citation at the end (e.g. starts with '(' and ends with ')')
    if lines and lines[-1].startswith("(") and lines[-1].endswith(")"):
        lines.pop()
        
    couplets = []
    # Group remaining lines by pairs of 2
    for i in range(0, len(lines) - 1, 2):
        couplet = f"{lines[i]}\n{lines[i+1]}"
        couplets.append(couplet)
    return couplets

def _load_direct_couplets() -> tuple[list[dict], list[dict]]:
    nazam_chunks = []
    ghazal_chunks = []
    
    # Load ghazal couplets
    ghazal_dir = Path("data/urdu_A/ghazal")
    if ghazal_dir.exists():
        for f in sorted(ghazal_dir.glob("*.txt")):
            if f.stat().st_size == 0:
                continue
            couplets = _extract_couplets_from_file(f)
            poet_name = f.stem.split(".")[1].strip() if "." in f.stem else f.stem
            for idx, c in enumerate(couplets):
                ghazal_chunks.append({
                    "chunk_id": f"ghazal_file_{f.stem}_{idx}",
                    "text": c,
                    "is_verse": True,
                    "genre": "ghazal",
                    "chapter": poet_name,
                    "book_title": "Urdu A",
                    "author": poet_name,
                    "dataset": "urdu_A"
                })
                
    # Load nazam couplets
    nazam_dir = Path("data/urdu_A/nazam")
    if nazam_dir.exists():
        for f in sorted(nazam_dir.glob("*.txt")):
            if f.stat().st_size == 0:
                continue
            couplets = _extract_couplets_from_file(f)
            nazam_name = f.stem.split(".")[1].strip() if "." in f.stem else f.stem
            for idx, c in enumerate(couplets):
                nazam_chunks.append({
                    "chunk_id": f"nazam_file_{f.stem}_{idx}",
                    "text": c,
                    "is_verse": True,
                    "genre": "nazam",
                    "chapter": nazam_name,
                    "book_title": "Urdu A",
                    "author": "",
                    "dataset": "urdu_A"
                })
    return nazam_chunks, ghazal_chunks

async def _run_paper(urdu_query: str, meta_a: list[dict], meta_b: list[dict]) -> AsyncGenerator[str, None]:
    """
    Generate a complete Class 9 Punjab Board Urdu paper.
    Hissa-e-Awal (MCQs, 15 marks) = NOT generated (not available online).
    Hissa-e-Dom (60 marks, Q2-Q9) = generated in 7 parts.
    
    Part 0 → سرورق (header)
    Part 1 → Q2: Tashreeh-e-Ashaar (nazam + ghazal)
    Part 2 → Q3: Nasr Tashreeh (2 sabaq passages)
    Part 3 → Q4: Mukhtasar Sawalat (8 questions, answer 5)
    Part 4 → Q5+Q6: Khulasa + Markazi Khyal
    Part 5 → Q7: Khat ya Darkhwast
    Part 6 → Q8+Q9: Story/Mukalma + Qawaid (jumlay + zarb ul amsal)
    """
    print("\n[پرچہ ساز] جاری ہے… (حصہ دوم — Q2 تا Q9 — تقریباً 2.5 منٹ)")
    print("نوٹ: حصہ اول (MCQs) الگ پرچے پر ہے — یہاں نہیں بنایا جاتا۔\n")
 
    import random
 
    # ── Genre pools ────────────────────────────────────────────────────────
    def by_genre(pool, genres, must_be_verse=False):
        hits = [c for c in pool if c.get("genre", "") in genres]
        if not hits:
            hits = pool
            
        if must_be_verse:
            verse_hits = [c for c in hits if c.get("is_verse") is True]
            return verse_hits if verse_hits else hits
        return hits
 
    mcqs_pool = by_genre(meta_a, {"mcqs", "MCQ", "mcq"})
    
    # Try loading direct couplets first, fall back to RAG meta_a otherwise
    direct_nazam, direct_ghazal = _load_direct_couplets()
    if direct_nazam:
        nazam_pool = direct_nazam
    else:
        print("[WARN] No direct nazam couplets loaded from folders, falling back to RAG index")
        nazam_pool = by_genre(meta_a, {"نظم", "تشریح_نظم", "tashreeh_nazam", "حمد", "نعت", "محنت کی برکات", "جاوید کے نام", "پیام لطیف", "محمد", "کرکٹ اور مشاعرہ"}, must_be_verse=True)

    if direct_ghazal:
        ghazal_pool = direct_ghazal
    else:
        print("[WARN] No direct ghazal couplets loaded from folders, falling back to RAG index")
        ghazal_pool = by_genre(meta_a, {"غزل", "تشریح_غزل", "tashreeh_ghazal"}, must_be_verse=True)
        
    sabaq_pool   = by_genre(meta_a, {"نثر", "سبق", "nasar_tashreeh", "khulasa", "short_question"})
    khat_pool    = by_genre(meta_b, {"خط", "letter"})
    darkhwast_pool = by_genre(meta_b, {"درخواست", "application"})
    story_pool   = by_genre(meta_b, {"کہانی","story"})
    dialogue_pool = by_genre(meta_b, {"مکالمہ","dialogue"})
    qawaid_pool  = by_genre(meta_b, {"قواعد", "zarbul_imsal", "sentence_correction"})
    
    # Log verse availability for debugging
    nazam_verses = sum(1 for c in nazam_pool if c.get("is_verse") is True)
    ghazal_verses = sum(1 for c in ghazal_pool if c.get("is_verse") is True)
    print(f"  📊 Verse pools: nazam={len(nazam_pool)} ({nazam_verses} verse), ghazal={len(ghazal_pool)} ({ghazal_verses} verse)")
 
    used_ids: set = set()
 
    def pick(pool, n, prioritize_verse=False):
        available = [c for c in pool if c.get("chunk_id") not in used_ids]
        if prioritize_verse:
            verses = [c for c in available if c.get("is_verse") is True]
            others = [c for c in available if c.get("is_verse") is not True]
            available = verses + others # prioritized order
        else:
            verses = []
            
        n = min(n, len(available))
        # For verses, strongly prefer verse-only chunks
        if prioritize_verse and len(verses) >= n:
            chosen = random.sample(verses, n)
        elif prioritize_verse and verses:
            # Take all available verses + supplement with others
            chosen = list(verses)
            remaining = n - len(chosen)
            if remaining > 0 and others:
                chosen.extend(random.sample(others, min(remaining, len(others))))
        else:
            chosen = random.sample(available, n) if n > 0 else []
            
        used_ids.update(c.get("chunk_id") for c in chosen if c.get("chunk_id"))
        return chosen
 
    def cap(chunks, max_chars=200):
        return [{**c, "text": c.get("text", "")[:max_chars]} for c in chunks]
 
    # ── Per-part context chunks ────────────────────────────────────────────
    # Part 0: header — no chunks
    p0 = []
    
    # Part 1 (Q1): MCQs
    p1 = cap(pick(mcqs_pool, 15), max_chars=400)
    # Part 2 (Q2): nazam ashaar + ghazal ashaar for tashreeh
    # Increased pool sizes for better verse coverage; higher max_chars to avoid truncating verses
    # Part 2 (Q2): Load شعر DIRECTLY from disk files for authentic verse
    _nazam_shair, _ghazal_shair = load_shair_for_paper(
        data_dir="data/urdu_A",
        nazam_count=4,
        ghazal_count=3,
    )
    if _nazam_shair or _ghazal_shair:
        p2 = _nazam_shair + _ghazal_shair
        used_ids.update(c.get("chunk_id", "") for c in p2 if c.get("chunk_id"))
        print(f"  📜 Q2: {len(_nazam_shair)} نظم + {len(_ghazal_shair)} غزل shair loaded from files")
    else:
        p2 = cap(
            pick(nazam_pool, 8, prioritize_verse=True) +
            pick(ghazal_pool, 6, prioritize_verse=True),
            max_chars=800,
        )
        print("  ⚠️ Q2: falling back to embedding search")
    # Part 3 (Q3): sabaq passages for nasr tashreeh
    p3 = cap(pick(sabaq_pool, 4), max_chars=300)
 
    # Part 4 (Q4): mixed urdu_A for mukhtasar sawalat
    p4 = cap(pick(sabaq_pool, 4) + pick(nazam_pool, 2) + pick(ghazal_pool, 2))

    # Part 5 (Q5): sabaq for khulasa
    p5 = cap(pick(sabaq_pool, 2), max_chars=400)

    # Part 6 (Q6): nazam for markazi khyal
    p6 = cap(pick(nazam_pool, 1), max_chars=400)

    # Part 7 (Q7): khat + darkhwast samples
    p7 = cap(pick(khat_pool, 2) + pick(darkhwast_pool, 2), max_chars=250)

    # Part 8 (Q8): dialogue/story
    dialogue_pool = by_genre(meta_b, {"مکالمہ", "dialogue"})
    story_pool    = by_genre(meta_b, {"کہانی", "story"})
    p8 = cap(pick(dialogue_pool, 2) + pick(story_pool, 2), max_chars=400)

    # Part 9 (Q9): qawaid
    p9 = cap(pick(qawaid_pool, 3), max_chars=400)

    # Fallback
    fallback = cap(pick(meta_a, 4) + pick(meta_b, 2))

    part_configs = [
        (0, p0,             200),   # سرورق
        (1, p1 or fallback, 1200),  # Q1 MCQs (increased to 1200 tokens to fit 15 questions)
        (2, p2 or fallback, 900),   # Q2 تشریح اشعار
        (3, p3 or fallback, 900),   # Q3 نثر تشریح
        (4, p4 or fallback, 800),   # Q4 مختصر سوالات
        (5, p5 or fallback, 500),   # Q5 خلاصہ
        (6, p6 or fallback, 500),   # Q6 مرکزی خیال
        (7, p7 or fallback, 700),   # Q7 خط یا درخواست
        (8, p8 or fallback, 600),   # Q8 مضمون/کہانی یا مکالمہ
        (9, p9 or fallback, 350),   # Q9 قواعد
    ]

    part_labels = {
        0: "سرورق",
        1: "سوال ۱: معروضی (MCQs)",
        2: "سوال ۲: تشریح اشعار",
        3: "سوال ۳: نثر تشریح",
        4: "سوال ۴: مختصر سوالات",
        5: "سوال ۵: خلاصہ",
        6: "سوال ۶: مرکزی خیال + شاعر کا حال",
        7: "سوال ۷: خط یا درخواست",
        8: "سوال ۸: کہانی یا مکالمہ",
        9: "سوال ۹: قواعد",
    }

    for i, (part, p_chunks, max_tok) in enumerate(part_configs):
        label = part_labels.get(part, f"حصہ {part}")
        print(f"  ⏳ {label} تیار ہو رہا ہے…")
        messages = build_paper_prompt(urdu_query, p_chunks, part=part)

        for attempt in range(2):
            response = await _create_completion(
                get_model_for_genre("paper"), messages, False,
                temperature=0.2,
                max_tokens=max_tok,
            )

            raw = response.choices[0].message.content
            paper_text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

            # Validation: Ensure expected question number appears in output
            if part > 0 and str(part) not in paper_text and _urdu_numeral(part) not in paper_text:
                if attempt == 0:
                    print(f"  ⚠️ حصہ {part} کی فارمیٹنگ درست نہیں نکلی۔ دوبارہ کوشش…")
                    continue
                else:
                    # Inject fallback header so numbering stays intact
                    header = (
                        "━" * 38 + "\n"
                        + f"سوال نمبر {part}\n"
                        + "━" * 38 + "\n"
                    )
                    paper_text = header + paper_text
            break

        print(format_urdu(paper_text))
        print("\n" + "─" * 50 + "\n")

        yield paper_text + "\n\n" + "─" * 50 + "\n\n"

        # Rate limit guard between parts (skip after last)
        if i < len(part_configs) - 1:
            await asyncio.sleep(65)

    print()
    print(format_urdu("═" * 50))
    print(format_urdu("پرچہ مکمل ہوا"))
    print(format_urdu("═" * 50))

    print("Done.")

    yield "\n" + "═" * 50 + "\n" + "پرچہ مکمل ہوا" + "\n" + "═" * 50 + "\n"


def _urdu_numeral(n: int) -> str:
    urdu_nums = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"]
    return "".join(urdu_nums[int(digit)] for digit in str(n))
