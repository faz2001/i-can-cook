"""
ML-01 tiered intent extraction pipeline (proposal 4.2).

Tier 1: Gemma (primary)
Tier 2: Sentence Transformer embeddings (secondary, if Gemma underperforms
        or is unavailable)
Tier 3: Rule-based keyword extraction (final fallback, always succeeds)

Each tier is tried in order. A tier is skipped if it raises an
"unavailable" error (not configured / can't load) OR if it returns a
result below MIN_CONFIDENCE -- matching the proposal's "If Gemma intent
extraction performs below the Precision target ... Sentence Transformer
embeddings will be applied" language.
"""

from app.core.config import settings
from .gemma_extractor import extract_intent_gemma, GemmaUnavailableError
from .embedding_extractor import extract_intent_embedding, EmbeddingModelUnavailableError
from .rule_based_extractor import extract_intent_rule_based


def extract_intent(query: str, verbose: bool = False) -> "IntentResult":
    MIN_CONFIDENCE = settings.ML01_MIN_CONFIDENCE
    attempts = []

    # --- Tier 1: Gemma ---
    try:
        result = extract_intent_gemma(query)
        attempts.append(("gemma", "attempted", result.confidence))
        if result.confidence >= MIN_CONFIDENCE:
            if verbose:
                _log(query, attempts, used="gemma")
            return result
        attempts[-1] = ("gemma", "below confidence threshold", result.confidence)
    except GemmaUnavailableError as e:
        attempts.append(("gemma", f"unavailable: {e}", None))

    # --- Tier 2: Sentence Transformer ---
    try:
        result = extract_intent_embedding(query)
        attempts.append(("sentence_transformer", "attempted", result.confidence))
        if result.confidence >= MIN_CONFIDENCE:
            if verbose:
                _log(query, attempts, used="sentence_transformer")
            return result
        attempts[-1] = ("sentence_transformer", "below confidence threshold", result.confidence)
    except EmbeddingModelUnavailableError as e:
        attempts.append(("sentence_transformer", f"unavailable: {e}", None))

    # --- Tier 3: Rule-based (always succeeds) ---
    result = extract_intent_rule_based(query)
    attempts.append(("rule_based", "used (final fallback)", result.confidence))
    if verbose:
        _log(query, attempts, used="rule_based")
    return result


def _log(query, attempts, used):
    print(f"Query: {query!r}")
    for tier, status, conf in attempts:
        conf_str = f"{conf:.2f}" if conf is not None else "n/a"
        marker = " <-- USED" if tier == used else ""
        print(f"  [{tier:20s}] {status:38s} confidence={conf_str}{marker}")
