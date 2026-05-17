"""
Urdu Sentence-Aware Chunker (v2)
- Detects verse blocks (بند نمبر / شعر نمبر) and keeps them atomic
- Prose falls through normal sentence-boundary chunking
"""

import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Sentence splitter (prose only) ───────────────────────────────────────────
SENTENCE_SPLITTER = re.compile(r"(?<=[۔؟!])\s+")

# ── Verse block markers ───────────────────────────────────────────────────────
# Matches:
#   "بند نمبر 1"               (nazam band)
#   "شعر نمبر 4"               (numbered shaar)
#   "شعر نمبر 4 میں شاخ تاک…"  (inline verse on marker line)
#   "شعر ۱:"  "شعر ۲:"         (colon-style, Urdu digits)
VERSE_BLOCK_START = re.compile(
    r"^(بند\s*نمبر|شعر\s*نمبر)\s*[\d۰-۹]+"   # بند/شعر نمبر N
    r"|^شعر\s*[\d۰-۹]+\s*:"                    # شعر ۱:
)

# Lines that end a verse block (prose resumes after these)
VERSE_BLOCK_END = re.compile(
    r"^(مفہوم|تشریح|خلاصہ|سوال|جواب|نوٹ)\s*[:\-۔]"
)

# Noise lines to strip before processing
NOISE_LINE = re.compile(
    r"(freeilm|FREEILM|www\.|WWW\.|---\s*Page|\[WANT TO|REPORT ANY|WEBSITE:)",
    re.IGNORECASE
)


def _token_count(text: str) -> int:
    return len(text.split())


@dataclass
class Chunk:
    chunk_id:    str
    text:        str
    token_count: int
    book_title:  str
    author:      str
    page_start:  int
    page_end:    int
    chapter:     str
    position:    int
    chunk_type:  str = "prose"   # "prose" | "verse"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_verse"] = (self.chunk_type == "verse")
        return d


# ── Pre-processing ────────────────────────────────────────────────────────────

def _clean_lines(raw_text: str) -> list[str]:
    """Strip noise/header lines from OCR text."""
    lines = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if NOISE_LINE.search(stripped):
            continue
        # Skip markdown table lines (vocab tables)
        if stripped.startswith("|") and stripped.endswith("|"):
            continue
        lines.append(stripped)
    return lines


# ── Segmentation: split raw lines into prose/verse segments ──────────────────

def _segment_lines(lines: list[str]) -> list[dict]:
    """
    Returns list of segments:
      {"type": "verse", "marker": "بند نمبر ۱", "lines": [...]}
      {"type": "prose", "lines": [...]}
    """
    segments = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if VERSE_BLOCK_START.match(line):
            # Extract marker (e.g. "شعر نمبر 4") and optional inline verse tail
            m = VERSE_BLOCK_START.match(line)
            marker = line[: m.end()].strip()          # just "شعر نمبر 4"
            inline_tail = line[m.end():].strip()       # verse text on same line

            verse_lines = []
            if inline_tail:
                verse_lines.append(inline_tail)        # first misra inline

            i += 1

            while i < len(lines):
                curr = lines[i]
                # End verse block when prose markers appear or empty line + prose
                if VERSE_BLOCK_END.match(curr):
                    break
                # Another verse block starts → close current
                if VERSE_BLOCK_START.match(curr):
                    break
                verse_lines.append(curr)
                i += 1

            if verse_lines:
                segments.append({
                    "type":   "verse",
                    "marker": marker,
                    "lines":  verse_lines,
                })
        else:
            # Accumulate prose lines until next verse block
            prose_lines = []
            while i < len(lines):
                curr = lines[i]
                if VERSE_BLOCK_START.match(curr):
                    break
                prose_lines.append(curr)
                i += 1

            text = " ".join(l for l in prose_lines if l).strip()
            if text:
                segments.append({"type": "prose", "lines": prose_lines})

    return segments


# ── Prose chunking (sentence-boundary) ───────────────────────────────────────

def _split_into_sentences(text: str) -> list[str]:
    sentences = SENTENCE_SPLITTER.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _chunk_prose(
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    sentences = _split_into_sentences(text)
    if not sentences:
        return []

    chunks = []
    i = 0
    while i < len(sentences):
        current_tokens = 0
        current_sents: list[str] = []

        while i < len(sentences):
            s_tokens = _token_count(sentences[i])
            if current_tokens + s_tokens > chunk_size and current_sents:
                break
            current_sents.append(sentences[i])
            current_tokens += s_tokens
            i += 1

        chunk_str = " ".join(current_sents).strip()
        if chunk_str:
            chunks.append(chunk_str)

        # Overlap: step back
        overlap_tokens = 0
        step_back = 0
        for s in reversed(current_sents):
            overlap_tokens += _token_count(s)
            step_back += 1
            if overlap_tokens >= overlap:
                break
        i -= step_back
        if step_back >= len(current_sents):
            i += 1

    return chunks


# ── Main public API ───────────────────────────────────────────────────────────

def chunk_text(
    clean_text: str,
    book_title: str = "",
    author: str = "",
    chapter: str = "",
    page_number: int = 1,
    chunk_size: int = 150,
    overlap: int = 30,
) -> list["Chunk"]:
    """
    Split Urdu text into chunks. Verse blocks (بند/شعر) are kept atomic.
    Prose is split on sentence boundaries with overlap.
    """
    lines = _clean_lines(clean_text)
    segments = _segment_lines(lines)

    chunks: list[Chunk] = []
    position = 0

    for seg in segments:
        if seg["type"] == "verse":
            # Keep entire verse block as ONE chunk
            verse_text = seg["marker"] + "\n" + "\n".join(seg["lines"])
            verse_text = verse_text.strip()
            if verse_text:
                chunks.append(Chunk(
                    chunk_id    = str(uuid.uuid4()),
                    text        = verse_text,
                    token_count = _token_count(verse_text),
                    book_title  = book_title,
                    author      = author,
                    page_start  = page_number,
                    page_end    = page_number,
                    chapter     = chapter,
                    position    = position,
                    chunk_type  = "verse",
                ))
                position += 1

        else:  # prose
            prose_text = " ".join(l for l in seg["lines"] if l).strip()
            if not prose_text:
                continue
            for chunk_str in _chunk_prose(prose_text, chunk_size, overlap):
                chunks.append(Chunk(
                    chunk_id    = str(uuid.uuid4()),
                    text        = chunk_str,
                    token_count = _token_count(chunk_str),
                    book_title  = book_title,
                    author      = author,
                    page_start  = page_number,
                    page_end    = page_number,
                    chapter     = chapter,
                    position    = position,
                    chunk_type  = "prose",
                ))
                position += 1

    return chunks


def chunks_from_pages(
    pages: list[dict],
    book_title: str = "",
    author: str = "",
    chapter: str = "",
    chunk_size: int = 400,
    overlap: int = 50,
) -> list[Chunk]:
    """Convenience: build chunks from a list of page dicts.
    Each page dict: {"page_number": int, "text": str}
    """
    all_chunks: list[Chunk] = []
    position_counter = 0

    for page in pages:
        page_num = page.get("page_number", 1)
        text     = page.get("text", "")
        if not text.strip():
            continue

        page_chunks = chunk_text(
            clean_text  = text,
            book_title  = book_title,
            author      = author,
            chapter     = chapter,
            page_number = page_num,
            chunk_size  = chunk_size,
            overlap     = overlap,
        )
        for c in page_chunks:
            c.position   = position_counter
            c.page_start = page_num
            c.page_end   = page_num
            position_counter += 1

        all_chunks.extend(page_chunks)

    return all_chunks