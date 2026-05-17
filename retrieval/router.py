"""
retrieval/router.py — Query classifier and dataset router.

route_dataset()        → 'urdu_A' | 'urdu_B' | 'both'   (keyword-based, no LLM cost)
classify_query()       → genre label for Urdu B pipelines (LLM-based, ~50 tokens)
classify_query_full()  → all intent types including Urdu A tasks (LLM-based)
"""

from __future__ import annotations

from generation.llm import _create_completion, DEFAULT_MODEL

# ---------------------------------------------------------------------------
# Dataset routing — keyword signal
# ---------------------------------------------------------------------------

_KW_B: frozenset[str] = frozenset({
    # writing genres
    "درخواست", "خط", "کہانی", "مکالمہ",
    # objective
    "ایم سی کیو", "mcq", "MCQ",
    "جملہ درست", "غلطی نکالیں",
    "ضرب المثل", "محاورہ", "کہاوت",
    "معنی لکھیں", "الفاظ کے معنی",
    # paper
    "ماڈل پیپر", "ٹیسٹ پیپر", "پرچہ",
})

_KW_A: frozenset[str] = frozenset({
    "شاعر", "شاعری", "غزل", "نظم", "نثر", "سبق", "مصنف",
    "تشریح", "حوالہ","غزل کی تشریح", "نظم کی تشریح", "شعر کی تشریح",
    "نظم کا مرکزی خیال", "سبق کا خلاصہ", "ترجمہ",
})


def route_dataset(query: str) -> str:
    """
    Return 'urdu_A', 'urdu_B', or 'both' based on keyword presence.
    'both' means the query is ambiguous or explicitly spans both datasets.
    """
    has_b = any(kw in query for kw in _KW_B)
    has_a = any(kw in query for kw in _KW_A)
    if has_b and has_a:
        return "both"
    if has_b:
        return "urdu_B"
    if has_a:
        return "urdu_A"
    return "both"   # generic query — search everywhere


# ---------------------------------------------------------------------------
# Shared intent set (used by both classifiers)
# ---------------------------------------------------------------------------

ALL_INTENTS: frozenset[str] = frozenset({
    # one-line / objective
    "mcq", "word_meanings", "sentence_correction", "zarbul_imsal",
    # short
    "short_question", "general_qa", "comprehension", "translation",
    # tashreeh
    "tashreeh_ghazal", "tashreeh_nazam", "nasar_tashreeh", "poem_explanation",
    # structured long
    "khulasa", "markazi_khyal",
    # writing genres
    "application", "letter", "story", "dialogue",
    # special
    "paper",
})

_B_ALLOWED: frozenset[str] = frozenset({
    "letter", "application", "story", "dialogue",
})

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_B_SYSTEM = """\
You are a query classifier for a Pakistani Urdu exam assistant.
Read the query and return ONLY one label from this list:
letter, application, story, dialogue

Rules:
- خط / دوست کو لکھیں / کسی کو خط        → letter
- درخواست / پرنسپل کو / اجازت مانگنا      → application
- کہانی / سبق آموز / افسانہ               → story
- مکالمہ / بات چیت                        → dialogue

Return ONLY the label. No explanation. No Urdu. Just the English label."""

_FULL_SYSTEM = """\
You are a query classifier for a Pakistani Urdu Class 9 exam assistant.
Read the query and return ONLY one label from this exact list:

mcq, word_meanings, sentence_correction, zarbul_imsal,
short_question, general_qa, comprehension, translation,
tashreeh_ghazal, tashreeh_nazam, nasar_tashreeh, poem_explanation,
khulasa, markazi_khyal,
application, letter, story, dialogue,
paper

Rules:
- MCQ / ایم سی کیو / درست جواب چنیں             → mcq
- معنی / مطلب / لفظ کا مطلب                      → word_meanings
- جملہ درست کریں / غلطی نکالیں                   → sentence_correction
- ضرب المثل / کہاوت / محاورہ                     → zarbul_imsal
- مختصر سوال / سوال جواب (short)                 → short_question
- سوالات / comprehension / اقتباس کے سوال        → comprehension
- ترجمہ / آسان اردو / اردو میں لکھیں             → translation
- غزل کی تشریح / شعر کی تشریح                   → tashreeh_ghazal
- نظم کی تشریح / نظم کا مفہوم                   → tashreeh_nazam
- نثر / سبق / عبارت کی تشریح                    → nasar_tashreeh
- نظم / شعر کی وضاحت (poem)                      → poem_explanation
- خلاصہ / سبق کا خلاصہ / نظم کا خلاصہ           → khulasa
- مرکزی خیال / سبق کا مرکزی خیال / موضوع        → markazi_khyal
- خط / دوست کو لکھیں                             → letter
- درخواست / پرنسپل کو / اجازت                   → application
- کہانی / سبق آموز / افسانہ                      → story
- مکالمہ / بات چیت                               → dialogue
- پرچہ / ماڈل پیپر / ٹیسٹ                        → paper
- anything else                                   → general_qa

Return ONLY the label. No explanation."""

# ---------------------------------------------------------------------------
# Genre classifier for Urdu B only  (original — kept for compatibility)
# ---------------------------------------------------------------------------

async def classify_query(user_query: str) -> str:
    """
    Classify user_query into one Urdu B genre label.
    Falls back to 'essay' on any error or unrecognised label.
    """
    messages = [
        {"role": "system", "content": _B_SYSTEM},
        {"role": "user",   "content": f"Query: {user_query}"},
    ]
    try:
        response = await _create_completion(
            DEFAULT_MODEL,
            messages,
            False,
            temperature=0.0,
            max_tokens=10,
        )
        label = response.choices[0].message.content.strip().lower()
        return label if label in _B_ALLOWED else "essay"
    except Exception:
        return "essay"


# ---------------------------------------------------------------------------
# Full intent classifier — covers ALL intent types including Urdu A tasks
# ---------------------------------------------------------------------------

async def classify_query_full(user_query: str) -> str:
    """
    Classify into ALL intent types including Urdu A knowledge tasks.
    Falls back to 'general_qa' on any error or unrecognised label.
    """
    messages = [
        {"role": "system", "content": _FULL_SYSTEM},
        {"role": "user",   "content": f"Query: {user_query}"},
    ]
    try:
        response = await _create_completion(
            DEFAULT_MODEL,
            messages,
            False,
            temperature=0.0,
            max_tokens=10,
        )
        label = response.choices[0].message.content.strip().lower()
        return label if label in ALL_INTENTS else "general_qa"
    except Exception:
        return "general_qa"