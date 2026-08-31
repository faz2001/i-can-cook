"""
Tier 1: Gemma intent extraction (primary, per proposal 4.2).

Calls a local Gemma model served through Ollama (http://localhost:11434 by
default -- see app.core.config.settings.GEMMA_OLLAMA_URL). This keeps the
"no third-party AI APIs" constraint from the proposal: Ollama runs the model
entirely on-device, there's no external network call.

If GEMMA_OLLAMA_URL isn't set, or the endpoint isn't reachable, or the
model's response doesn't parse as the expected JSON shape, this raises
GemmaUnavailableError and the pipeline falls through to Tier 2 (Sentence
Transformer) -- that fallback behaviour is the point of the tiered design,
not a failure state.

To activate: install Ollama, `ollama pull gemma3:4b` (or another Gemma
size that fits your hardware -- update the model name below to match), and
set GEMMA_OLLAMA_URL=http://localhost:11434.
"""
import json
from dataclasses import dataclass

import httpx

from app.core.config import settings
from .vocab import INTENT_VOCAB


@dataclass
class IntentResult:
    tags: dict            # {category: [tag, ...]}
    confidence: float      # 0.0-1.0, extractor's own confidence in this result
    tier: str               # which tier produced this result
    raw: str = ""           # raw model output / debug info


class GemmaUnavailableError(Exception):
    """Raised when Gemma can't be reached (not configured, endpoint down,
    model not pulled, or its response didn't parse)."""
    pass


_PROMPT_TEMPLATE = """You extract structured tags from a food/recipe query.
Return ONLY a JSON object (no prose, no markdown fences) with these keys,
each mapping to a list of zero or more tags chosen ONLY from the allowed
values below. Omit a key entirely if nothing matches.

Allowed values per category:
{vocab_json}

Query: {query}

JSON:"""


def extract_intent_gemma(query: str) -> IntentResult:
    """
    Attempt intent extraction via Gemma (local, through Ollama). Raises
    GemmaUnavailableError if Gemma isn't set up or the call/parse fails --
    the pipeline catches this and falls through to Tier 2.
    """
    if not settings.GEMMA_OLLAMA_URL:
        raise GemmaUnavailableError(
            "GEMMA_OLLAMA_URL is not set -- Tier 1 not configured. "
            "Falling back to Tier 2."
        )

    vocab_for_prompt = {cat: list(tags.keys()) for cat, tags in INTENT_VOCAB.items()}
    prompt = _PROMPT_TEMPLATE.format(vocab_json=json.dumps(vocab_for_prompt), query=query)

    try:
        resp = httpx.post(
            f"{settings.GEMMA_OLLAMA_URL}/api/generate",
            json={"model": "gemma3:4b", "prompt": prompt, "stream": False, "format": "json"},
            timeout=60.0,
        )
        resp.raise_for_status()
        model_text = resp.json()["response"]
        parsed = json.loads(model_text)
    except Exception as e:
        raise GemmaUnavailableError(f"Gemma/Ollama call failed: {e}")

    # Keep only known categories/tags -- never trust the model's output blindly.
    tags_by_category = {}
    for category, tags in parsed.items():
        if category not in INTENT_VOCAB or not isinstance(tags, list):
            continue
        valid = [t for t in tags if t in INTENT_VOCAB[category]]
        if valid:
            tags_by_category[category] = valid

    if not tags_by_category:
        raise GemmaUnavailableError("Gemma returned no tags matching the controlled vocabulary.")

    # Gemma has no calibrated confidence score of its own; treat a
    # successful, vocab-matching parse as high confidence for this tier.
    confidence = 0.9
    return IntentResult(tags=tags_by_category, confidence=confidence, tier="gemma", raw=model_text)