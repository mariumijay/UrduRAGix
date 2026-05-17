"""
ingest_poetry.py — Ingest ghazal and nazam shair files into urdu_A index.

Reads from:
    data/urdu_A/ghazal/*.txt   → chapter="tashreeh_ghazal", is_verse=True
    data/urdu_A/nazam/*.txt    → chapter="tashreeh_nazam",  is_verse=True

Each file = one poet's shair. Each shair (couplet / band) becomes one chunk.
Appends to the existing urdu_A FAISS + BM25 index (does NOT wipe urdu_A data).

Usage:
    python ingest_poetry.py
    python ingest_poetry.py --data_dir path/to/data/urdu_A
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingestion.embedder import (
    embed_texts,
    get_dataset_paths,
    load_faiss_index,
    load_metadata,
    load_bm25_index,
    save_faiss_index,
    save_bm25_index,
)
from ingestion.cleaner import normalize_for_search

import faiss
import numpy as np
import pickle
from rank_bm25 import BM25Okapi

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Shair splitter ─────────────────────────────────────────────────────────────
# A couplet (شعر) is typically 2 lines.
# A band (بند) in nazam is 4-6 lines.
# We split on blank lines — each block = one chunk.

def _split_into_shair_blocks(text: str) -> list[str]:
    """
    Split a poetry file into individual شعر / بند blocks.
    Blocks are separated by one or more blank lines.
    Single-line blocks are merged with the next to form complete couplets.
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Split on blank lines
    raw_blocks = re.split(r"\n{2,}", text.strip())
    
    blocks: list[str] = []
    pending = ""
    
    for block in raw_blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue
        
        block_text = "\n".join(lines)
        
        # Skip header lines (title, poet name, numbering headers)
        if len(lines) == 1 and (
            re.match(r"^(شاعر|مصنف|نظم|غزل|عنوان|نام)\s*[:۔]", lines[0])
            or re.match(r"^[\d۰-۹]+\s*[.۔)]?\s*$", lines[0])
            or len(lines[0]) < 4
        ):
            continue
        
        # If pending single line + this block → merge to form couplet
        if pending:
            block_text = pending + "\n" + block_text
            pending = ""
        
        # If only one misra, hold it for next block
        if len(lines) == 1:
            pending = block_text
            continue
        
        blocks.append(block_text)
    
    # Flush any remaining pending line
    if pending:
        blocks.append(pending)
    
    return [b for b in blocks if b.strip()]


def _extract_poet_and_title(filename: str) -> tuple[str, str]:
    """
    Extract a clean title/poet name from a filename like:
        "1. mirtaqimir.txt"    → ("میر تقی میر", "غزل")
        "3. mehatkibarkat.txt" → ("محنت کی برکات", "نظم")
    Returns (book_title, raw_stem).
    """
    stem = Path(filename).stem
    # Strip leading number and dot: "1. mirtaqimir" → "mirtaqimir"
    stem = re.sub(r"^\d+\.\s*", "", stem).strip()
    return stem, stem


# ── Known filename → Urdu title + author mapping ──────────────────────────────
# Add more entries here as you add files.

GHAZAL_META: dict[str, dict] = {
    "mirtaqimir":       {"title": "غزل — میر تقی میر",       "author": "میر تقی میر"},
    "khawajahaider":    {"title": "غزل — خواجہ حیدر علی آتش","author": "خواجہ حیدر علی آتش"},
    "nasirkazmi":       {"title": "غزل — ناصر کاظمی",         "author": "ناصر کاظمی"},
    "parweenfinasy":    {"title": "غزل — پروین شاکر",         "author": "پروین شاکر"},
    "atish":            {"title": "غزل — خواجہ حیدر علی آتش","author": "خواجہ حیدر علی آتش"},
}

NAZAM_META: dict[str, dict] = {
    "naat":             {"title": "نعت",                      "author": "مولانا ظفر علی خاں"},
    "hamd":             {"title": "حمد",                      "author": "مولانا حالی"},
    "mehatkibarkat":    {"title": "محنت کی برکات",            "author": "مولانا حالی"},
    "javedkenaam":      {"title": "جاوید کے نام",             "author": "علامہ محمد اقبال"},
    "javedkenama":      {"title": "جاوید کے نام",             "author": "علامہ محمد اقبال"},
    "piyamelatif":      {"title": "پیام لطیف",                "author": "شیخ ایاز"},
    "piyamlatif":       {"title": "پیام لطیف",                "author": "شیخ ایاز"},
    "cricketormashi":   {"title": "کرکٹ اور مشاعرہ",          "author": "دلاور فگار"},
    "cricketaur":       {"title": "کرکٹ اور مشاعرہ",          "author": "دلاور فگار"},
    "muhammad":         {"title": "محمد",                     "author": "مظفر وارثی"},
}


def _lookup_meta(stem_clean: str, genre: str) -> dict:
    """Fuzzy match stem against known metadata tables."""
    stem_lower = stem_clean.lower().replace(" ", "").replace("_", "").replace("-", "")
    
    table = GHAZAL_META if genre == "tashreeh_ghazal" else NAZAM_META
    
    for key, meta in table.items():
        key_clean = key.lower().replace(" ", "").replace("_", "").replace("-", "")
        if key_clean in stem_lower or stem_lower in key_clean:
            return meta
    
    # Fallback: use stem as title
    return {"title": stem_clean, "author": ""}


# ── Core ingestion ─────────────────────────────────────────────────────────────

def load_poetry_chunks(data_dir: Path) -> list[dict]:
    """
    Read all ghazal/*.txt and nazam/*.txt files and return chunk dicts.
    Each chunk has is_verse=True and proper metadata.
    """
    all_chunks: list[dict] = []
    
    genre_folders = [
        (data_dir / "ghazal", "tashreeh_ghazal"),
        (data_dir / "nazam",  "tashreeh_nazam"),
    ]
    
    for folder, genre in genre_folders:
        if not folder.exists():
            logger.warning("Folder not found, skipping: %s", folder)
            continue
        
        txt_files = sorted(folder.glob("*.txt"))
        if not txt_files:
            logger.warning("No .txt files found in: %s", folder)
            continue
        
        logger.info("Reading %d files from %s/", len(txt_files), folder.name)
        
        for txt_file in txt_files:
            raw_text = txt_file.read_text(encoding="utf-8", errors="ignore")
            stem_raw, stem_clean = _extract_poet_and_title(txt_file.name)
            meta = _lookup_meta(stem_clean, genre)
            
            blocks = _split_into_shair_blocks(raw_text)
            
            if not blocks:
                logger.warning("No shair blocks found in: %s", txt_file.name)
                continue
            
            logger.info(
                "  %s → %d شعر blocks  [%s]",
                txt_file.name, len(blocks), meta["title"]
            )
            
            for i, block in enumerate(blocks):
                chunk = {
                    "chunk_id":    str(uuid.uuid4()),
                    "faiss_index": -1,          # assigned later
                    "text":        block,
                    "token_count": len(block.split()),
                    "book_title":  meta["title"],
                    "author":      meta["author"],
                    "chapter":     genre,
                    "genre":       genre,
                    "page_start":  1,
                    "page_end":    1,
                    "position":    i,
                    "chunk_type":  "verse",
                    "is_verse":    True,
                    "dataset":     "urdu_A",
                    "source":      "urdu_A",
                    "source_file": txt_file.name,
                }
                all_chunks.append(chunk)
    
    return all_chunks


def ingest_poetry(data_dir: str = "data/urdu_A") -> dict:
    """
    Main entry point. Appends poetry chunks to the existing urdu_A index.
    If no existing index, creates a fresh one.
    """
    path = Path(data_dir)
    if not path.exists():
        raise ValueError(f"Data directory not found: {path}")
    
    logger.info("=" * 60)
    logger.info("Poetry Ingestion Pipeline — dataset: urdu_A")
    logger.info("=" * 60)
    
    # ── Step 1: Load new poetry chunks ───────────────────────────────────────
    new_chunks = load_poetry_chunks(path)
    if not new_chunks:
        raise ValueError("No poetry chunks loaded — check your ghazal/ and nazam/ folders.")
    
    logger.info("Total new poetry chunks: %d", len(new_chunks))
    
    # ── Step 2: Load existing urdu_A index (if present) ──────────────────────
    paths = get_dataset_paths("urdu_A")
    existing_meta: list[dict] = []
    existing_index = None
    
    if paths["metadata"].exists() and paths["faiss"].exists():
        logger.info("Loading existing urdu_A index…")
        existing_meta   = load_metadata("urdu_A")
        existing_index  = load_faiss_index("urdu_A")
        logger.info("  Existing chunks: %d", len(existing_meta))
    else:
        logger.info("No existing urdu_A index found — building fresh.")
    
    # ── Step 3: Remove old poetry chunks (avoid duplicates on re-run) ─────────
    non_poetry_meta = [
        m for m in existing_meta
        if not m.get("is_verse", False)
        or m.get("chapter", "") not in ("tashreeh_ghazal", "tashreeh_nazam")
    ]
    removed = len(existing_meta) - len(non_poetry_meta)
    if removed:
        logger.info("Removed %d old poetry chunks (will replace with fresh).", removed)
    
    # ── Step 4: Merge metadata ────────────────────────────────────────────────
    merged_meta = non_poetry_meta + new_chunks
    
    # Reassign faiss_index sequentially
    for i, m in enumerate(merged_meta):
        m["faiss_index"] = i
    
    logger.info("Total chunks after merge: %d", len(merged_meta))
    
    # ── Step 5: Embed ALL merged chunks ──────────────────────────────────────
    # We must re-embed everything because FAISS IndexFlatIP doesn't support
    # selective deletion — we rebuild the full index.
    logger.info("Embedding %d chunks (this may take a while)…", len(merged_meta))
    texts = [m["text"] for m in merged_meta]
    embeddings = embed_texts(texts)
    
    # ── Step 6: Build and save FAISS index ───────────────────────────────────
    dim = int(embeddings.shape[1])
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    save_faiss_index(index, "urdu_A")
    logger.info("FAISS index saved: %d vectors", index.ntotal)
    
    # ── Step 7: Build and save BM25 index ────────────────────────────────────
    tokenized = [normalize_for_search(t).split() for t in texts]
    bm25 = BM25Okapi(tokenized)
    save_bm25_index(bm25, "urdu_A")
    logger.info("BM25 index saved.")
    
    # ── Step 8: Save metadata ─────────────────────────────────────────────────
    with open(paths["metadata"], "w", encoding="utf-8") as f:
        json.dump(merged_meta, f, ensure_ascii=False, indent=2)
    logger.info("Metadata saved: %d entries → %s", len(merged_meta), paths["metadata"])
    
    # ── Summary ───────────────────────────────────────────────────────────────
    ghazal_count = sum(1 for m in new_chunks if m["chapter"] == "tashreeh_ghazal")
    nazam_count  = sum(1 for m in new_chunks if m["chapter"] == "tashreeh_nazam")
    
    stats = {
        "new_poetry_chunks": len(new_chunks),
        "ghazal_chunks":     ghazal_count,
        "nazam_chunks":      nazam_count,
        "total_chunks":      len(merged_meta),
        "faiss_vectors":     index.ntotal,
        "embedding_dim":     dim,
    }
    
    logger.info("=" * 60)
    logger.info("✓ Poetry ingestion complete!")
    logger.info("  New poetry chunks : %d (%d غزل + %d نظم)",
                len(new_chunks), ghazal_count, nazam_count)
    logger.info("  Total urdu_A      : %d chunks", len(merged_meta))
    logger.info("=" * 60)
    
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest ghazal/nazam shair files into urdu_A index"
    )
    parser.add_argument(
        "--data_dir",
        default="data/urdu_A",
        help="Path to urdu_A data folder (must contain ghazal/ and nazam/ subfolders)",
    )
    args = parser.parse_args()
    
    from dotenv import load_dotenv
    load_dotenv()
    
    stats = ingest_poetry(args.data_dir)
    
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print(f"  New poetry chunks : {stats['new_poetry_chunks']}")
    print(f"    غزل chunks      : {stats['ghazal_chunks']}")
    print(f"    نظم chunks      : {stats['nazam_chunks']}")
    print(f"  Total urdu_A      : {stats['total_chunks']}")
    print(f"  FAISS vectors     : {stats['faiss_vectors']}")
    print("=" * 60)
