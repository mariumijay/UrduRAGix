"""
retrieval/poetry_loader.py — Direct shair loader for paper Q2.

Reads غزل and نظم shair DIRECTLY from disk files — no FAISS/BM25 needed.
This guarantees real, authentic شعر appear in Q2 (not summarized prose).

Usage (in main.py / paper generation):
    from retrieval.poetry_loader import load_shair_for_paper
    nazam_shair, ghazal_shair = load_shair_for_paper(data_dir="data/urdu_A")
"""

from __future__ import annotations

import re
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Metadata tables (same as ingest_poetry.py) ────────────────────────────────

GHAZAL_META: dict[str, dict] = {
    "mirtaqimir":       {"title": "غزل",  "author": "میر تقی میر"},
    "khawajahaider":    {"title": "غزل",  "author": "خواجہ حیدر علی آتش"},
    "nasirkazmi":       {"title": "غزل",  "author": "ناصر کاظمی"},
    "parweenfinasy":    {"title": "غزل",  "author": "پروین شاکر"},
    "parweenshakir":    {"title": "غزل",  "author": "پروین شاکر"},
    "atish":            {"title": "غزل",  "author": "خواجہ حیدر علی آتش"},
}

NAZAM_META: dict[str, dict] = {
    "naat":             {"title": "نعت",              "author": "مولانا ظفر علی خاں"},
    "hamd":             {"title": "حمد",              "author": "مولانا حالی"},
    "mehatkibarkat":    {"title": "محنت کی برکات",    "author": "مولانا حالی"},
    "javedkenaam":      {"title": "جاوید کے نام",     "author": "علامہ محمد اقبال"},
    "javedkenama":      {"title": "جاوید کے نام",     "author": "علامہ محمد اقبال"},
    "piyamelatif":      {"title": "پیام لطیف",        "author": "شیخ ایاز"},
    "piyamlatif":       {"title": "پیام لطیف",        "author": "شیخ ایاز"},
    "cricketormashi":   {"title": "کرکٹ اور مشاعرہ",  "author": "دلاور فگار"},
    "cricketaur":       {"title": "کرکٹ اور مشاعرہ",  "author": "دلاور فگار"},
    "muhammad":         {"title": "محمد",             "author": "مظفر وارثی"},
}


def _stem(filename: str) -> str:
    """Strip leading number and extension: '1. mirtaqimir.txt' → 'mirtaqimir'"""
    s = Path(filename).stem
    s = re.sub(r"^\d+\.\s*", "", s).strip()
    return s.lower().replace(" ", "").replace("_", "").replace("-", "")


def _lookup(stem: str, table: dict) -> dict:
    for key, meta in table.items():
        k = key.lower().replace(" ", "").replace("_", "").replace("-", "")
        if k in stem or stem in k:
            return meta
    return {"title": stem, "author": ""}


def _split_shair(text: str) -> list[str]:
    """
    Split a poetry file into individual شعر / بند blocks.
    Blocks are separated by blank lines; single stray lines are merged with next.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_blocks = re.split(r"\n{2,}", text.strip())

    blocks: list[str] = []
    pending = ""

    for block in raw_blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue

        # Skip pure header / numbering lines or standalone parenthesized citations
        if len(lines) == 1 and (
            re.match(r"^(شاعر|مصنف|نظم|غزل|عنوان|نام)\s*[:۔]", lines[0])
            or re.match(r"^[\d۰-۹]+\s*[.۔)]?\s*$", lines[0])
            or (lines[0].startswith("(") and lines[0].endswith(")"))
            or len(lines[0]) < 4
        ):
            continue

        block_text = "\n".join(lines)

        if pending:
            block_text = pending + "\n" + block_text
            pending = ""

        # A single misra — hold for pairing
        if len(lines) == 1:
            pending = block_text
            continue

        blocks.append(block_text)

    if pending:
        blocks.append(pending)

    return [b for b in blocks if b.strip()]


# ── Public data structures ─────────────────────────────────────────────────────

class ShairEntry:
    """One شعر / بند with its metadata."""
    __slots__ = ("text", "title", "author", "genre", "source_file")

    def __init__(self, text: str, title: str, author: str, genre: str, source_file: str):
        self.text        = text
        self.title       = title
        self.author      = author
        self.genre       = genre        # "tashreeh_ghazal" | "tashreeh_nazam"
        self.source_file = source_file

    def to_dict(self) -> dict:
        return {
            "text":        self.text,
            "book_title":  self.title,
            "author":      self.author,
            "chapter":     self.genre,
            "genre":       self.genre,
            "is_verse":    True,
            "chunk_type":  "verse",
            "dataset":     "urdu_A",
            "source_file": self.source_file,
        }


# ── Main loader ────────────────────────────────────────────────────────────────

def load_all_shair(data_dir: str = "data/urdu_A") -> tuple[list[ShairEntry], list[ShairEntry]]:
    """
    Load ALL ghazal and nazam shair from disk.
    Returns (ghazal_list, nazam_list) — each item is a ShairEntry.
    """
    base = Path(data_dir)
    ghazal_entries: list[ShairEntry] = []
    nazam_entries:  list[ShairEntry] = []

    for folder, genre, table, target in [
        (base / "ghazal", "tashreeh_ghazal", GHAZAL_META, ghazal_entries),
        (base / "nazam",  "tashreeh_nazam",  NAZAM_META,  nazam_entries),
    ]:
        if not folder.exists():
            logger.warning("Poetry folder not found: %s", folder)
            continue

        for txt_file in sorted(folder.glob("*.txt")):
            stem   = _stem(txt_file.name)
            meta   = _lookup(stem, table)
            text   = txt_file.read_text(encoding="utf-8", errors="ignore")
            blocks = _split_shair(text)

            if not blocks:
                logger.warning("No shair found in %s", txt_file.name)
                continue

            logger.debug("%s → %d blocks", txt_file.name, len(blocks))
            for block in blocks:
                target.append(ShairEntry(
                    text        = block,
                    title       = meta["title"],
                    author      = meta["author"],
                    genre       = genre,
                    source_file = txt_file.name,
                ))

    logger.info(
        "poetry_loader: %d غزل shair + %d نظم shair loaded from disk",
        len(ghazal_entries), len(nazam_entries),
    )
    return ghazal_entries, nazam_entries


def load_shair_for_paper(
    data_dir: str = "data/urdu_A",
    nazam_count: int = 4,
    ghazal_count: int = 3,
    seed: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Pick random شعر from each pool for Q2 of the paper.

    Returns:
        nazam_chunks  — list of dicts ready to pass to build_paper_prompt (Part 2)
        ghazal_chunks — list of dicts ready to pass to build_paper_prompt (Part 2)

    Each dict has: text, book_title, author, chapter, is_verse, genre, dataset.
    """
    ghazal_all, nazam_all = load_all_shair(data_dir)

    rng = random.Random(seed)

    def _pick(pool: list[ShairEntry], n: int) -> list[dict]:
        # Group by source file so we pick from DIFFERENT poems/poets
        by_file: dict[str, list[ShairEntry]] = {}
        for e in pool:
            by_file.setdefault(e.source_file, []).append(e)

        selected: list[ShairEntry] = []
        files = list(by_file.keys())
        rng.shuffle(files)

        for f in files:
            if len(selected) >= n:
                break
            candidates = by_file[f]
            chosen = rng.choice(candidates)
            selected.append(chosen)

        # If we still need more (fewer files than n), pick extras
        remaining = n - len(selected)
        if remaining > 0:
            already = {id(e) for e in selected}
            extras = [e for e in pool if id(e) not in already]
            rng.shuffle(extras)
            selected.extend(extras[:remaining])

        return [e.to_dict() for e in selected]

    nazam_chunks  = _pick(nazam_all,  nazam_count)
    ghazal_chunks = _pick(ghazal_all, ghazal_count)

    if not nazam_chunks:
        logger.warning("No نظم shair loaded — check data/urdu_A/nazam/ folder")
    if not ghazal_chunks:
        logger.warning("No غزل shair loaded — check data/urdu_A/ghazal/ folder")

    return nazam_chunks, ghazal_chunks


# ── Quick test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    data = sys.argv[1] if len(sys.argv) > 1 else "data/urdu_A"

    logging.basicConfig(level=logging.INFO)
    nazam, ghazal = load_shair_for_paper(data)

    print(f"\n{'='*60}")
    print(f"نظم شعر ({len(nazam)} selected):")
    for i, c in enumerate(nazam, 1):
        print(f"\n[{i}] {c['book_title']} — {c['author']}")
        print(c["text"])

    print(f"\n{'='*60}")
    print(f"غزل شعر ({len(ghazal)} selected):")
    for i, c in enumerate(ghazal, 1):
        print(f"\n[{i}] {c['book_title']} — {c['author']}")
        print(c["text"])
