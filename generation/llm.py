"""
LLM Interface — Groq API wrapper for Qwen model with API key rotation + token guard
"""

import os
import re
import logging
from groq import AsyncGroq, RateLimitError, AuthenticationError, APIStatusError, BadRequestError
from generation.prompt import build_citations
from generation.prompt_b import get_prompt
from config.config import RAG_MODES, GENRE_TO_MODE

logger = logging.getLogger(__name__)

from config.config import GENRE_TO_MODEL, DEFAULT_MODEL as _DEFAULT_MODEL
DEFAULT_MODEL = os.getenv("LLM_MODEL", _DEFAULT_MODEL)

def get_model_for_genre(genre: str) -> str:
    return GENRE_TO_MODEL.get(genre, DEFAULT_MODEL)
    
# ── Token safety settings ────────────────────────────────────────────────────
def _get_mode_limits(mode: str = "short") -> tuple[int, int, int]:
    cfg = RAG_MODES.get(mode, RAG_MODES["short"])
    return (
        cfg["MAX_CONTEXT_CHUNKS"],
        cfg["MAX_TOKENS_PER_CHUNK"],
        cfg["MAX_OUTPUT_TOKENS"],
    )
# ── Key rotation setup ───────────────────────────────────────────────────────

def _load_api_keys() -> list[str]:
    keys = []
    for i in range(1, 10):
        key = os.environ.get(f"GROQ_API_KEY_{i}")
        if key:
            keys.append(key)
    plain = os.environ.get("GROQ_API_KEY")
    if plain and plain not in keys:
        keys.append(plain)
    if not keys:
        raise RuntimeError("No GROQ_API_KEY_* environment variables found.")
    logger.info(f"Loaded {len(keys)} Groq API key(s).")
    return keys


API_KEYS = _load_api_keys()
_current_key_index = 0


def _get_client(key_index: int) -> AsyncGroq:
    return AsyncGroq(api_key=API_KEYS[key_index])


ROTATABLE_ERRORS = (
    RateLimitError,       # rate limit hit — try next key
    AuthenticationError,  # invalid/expired key — try next key
)


# ── Think stripper ───────────────────────────────────────────────────────────

def _strip_thinking(text: str) -> str:
    """Remove Qwen3 chain-of-thought <think>...</think> blocks from output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


# ── Token guard ──────────────────────────────────────────────────────────────

def _trim_chunks(context_chunks: list[dict], mode: str = "short") -> list[dict]:
    max_chunks, max_tokens, _ = _get_mode_limits(mode)
    trimmed = context_chunks[:max_chunks]
    result = []
    for chunk in trimmed:
        text  = chunk.get("text", "")
        words = text.split()
        if len(words) > max_tokens:
            text = " ".join(words[:max_tokens]) + "..."
        result.append({**chunk, "text": text})
    return result


# ── Core completion helper ───────────────────────────────────────────────────

async def _create_completion(model: str, messages: list, stream: bool, **kwargs):
    global _current_key_index
    num_keys = len(API_KEYS)
    tried    = 0

    while tried < num_keys:
        key_index = (_current_key_index + tried) % num_keys
        client    = _get_client(key_index)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                stream=stream,
                **kwargs,
            )
            _current_key_index = key_index
            return response
        except ROTATABLE_ERRORS as e:
            logger.warning(
                f"Key index {key_index} failed ({type(e).__name__}: {e}). "
                f"Rotating to next key..."
            )
            tried += 1
        except Exception:
            raise

    raise RuntimeError(
        f"All {num_keys} Groq API key(s) exhausted. "
        "Check your keys or usage limits."
    )


# ── Public API ───────────────────────────────────────────────────────────────

async def stream_answer(query, context_chunks, model=None, mode=None, genre="general_qa"):
    if mode is None:
        mode = GENRE_TO_MODE.get(genre, "short")
    _, _, max_output = _get_mode_limits(mode) 
    safe_chunks = _trim_chunks(context_chunks, mode=mode)
    messages    = get_prompt(genre, safe_chunks, query)

    full_response = []  # buffer to strip <think> after stream ends

    try:
        stream = await _create_completion(
        model=model or DEFAULT_MODEL,
        messages=messages,
        stream=True,
        temperature=0.2,
        max_tokens=max_output,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                full_response.append(delta)

        # Strip <think> from complete buffered response then yield
        clean = _strip_thinking("".join(full_response))
        for char in clean:
            yield char

    except Exception as e:
        logger.error(f"LLM streaming error: {e}")
        yield f"\n\nخرابی: {str(e)}"


async def generate_answer(query, context_chunks, model=None, mode=None, genre="general_qa") -> dict:
    """Non-streaming: return full answer + citations."""
    model       = model or DEFAULT_MODEL
    if mode is None:
        mode = GENRE_TO_MODE.get(genre, "short")
    safe_chunks = _trim_chunks(context_chunks, mode=mode)
    _, _, max_output = _get_mode_limits(mode)
    messages    = get_prompt(genre, safe_chunks, query)

    try:
        response = await _create_completion(
            model=model or DEFAULT_MODEL,
            messages=messages,
            stream=False,
            temperature=0.2,
            max_tokens=max_output,
        )

        answer    = _strip_thinking(response.choices[0].message.content)  # ← stripped
        citations = build_citations(safe_chunks)

        return {
            "answer": answer,
            "citations": citations,
            "model": model,
            "usage": {
                "input_tokens":  response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
        }

    except Exception as e:
        logger.error(f"LLM generation error: {e}")
        return {
            "answer":    f"خرابی: {str(e)}",
            "citations": [],
            "model":     model,
            "usage":     {},
        }