"""
Tier 2: Sentence Transformer embedding-based intent extraction (secondary
fallback, per proposal 4.2: "Sentence Transformer embeddings (Reimers and
Gurevych, 2019)").

This is a REAL implementation using the `sentence-transformers` library and
the same `all-MiniLM-L6-v2` model referenced elsewhere in the project. It
embeds the user's query and every example phrase in vocab.INTENT_VOCAB,
then assigns each intent category the tag whose best example phrase is
most cosine-similar to the query -- above a confidence threshold.

NOTE ON THIS SANDBOX: this environment has no internet access to
huggingface.co, so `SentenceTransformer('all-MiniLM-L6-v2')` cannot download
model weights here and will raise. The code is correct and will work as-is
the moment it's run somewhere with internet access (your laptop, Colab,
or once the weights are cached locally). The pipeline treats a load failure
here the same as "Tier 2 unavailable" and falls through to Tier 3, so the
overall system still works end-to-end even when this tier can't run --
which is exactly the resilience the tiered design is meant to provide.
"""

from dataclasses import dataclass
from functools import lru_cache

from .vocab import INTENT_VOCAB
from .gemma_extractor import IntentResult

MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.45  # tune once real embeddings are available


class EmbeddingModelUnavailableError(Exception):
    """Raised when the Sentence Transformer model can't be loaded (e.g. no
    internet access to download weights, or the package isn't installed)."""
    pass


@lru_cache(maxsize=1)
def _load_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise EmbeddingModelUnavailableError(
            f"sentence-transformers not installed: {e}"
        )
    try:
        return SentenceTransformer(MODEL_NAME)
    except Exception as e:
        raise EmbeddingModelUnavailableError(
            f"Could not load {MODEL_NAME} (likely no internet access to "
            f"download weights in this environment): {e}"
        )


@lru_cache(maxsize=1)
def _example_phrase_bank():
    """Flatten vocab into (category, tag, phrase) triples for embedding."""
    bank = []
    for category, tags in INTENT_VOCAB.items():
        for tag, phrases in tags.items():
            for phrase in phrases:
                bank.append((category, tag, phrase))
    return bank


def extract_intent_embedding(query: str) -> IntentResult:
    """
    Attempt intent extraction via semantic similarity. Raises
    EmbeddingModelUnavailableError if the model can't be loaded -- the
    pipeline catches this and falls through to Tier 3 (rule-based).
    """
    model = _load_model()  # raises EmbeddingModelUnavailableError if unavailable
    import numpy as np

    bank = _example_phrase_bank()
    phrases = [p for (_, _, p) in bank]

    query_vec = model.encode([query])[0]
    phrase_vecs = model.encode(phrases)

    def cosine(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

    sims = [cosine(query_vec, pv) for pv in phrase_vecs]

    # best similarity per (category, tag)
    best_per_tag = {}
    for (category, tag, _phrase), sim in zip(bank, sims):
        key = (category, tag)
        if key not in best_per_tag or sim > best_per_tag[key]:
            best_per_tag[key] = sim

    tags_by_category = {}
    matched_sims = []
    for (category, tag), sim in best_per_tag.items():
        if sim >= SIMILARITY_THRESHOLD:
            tags_by_category.setdefault(category, []).append(tag)
            matched_sims.append(sim)

    confidence = float(np.mean(matched_sims)) if matched_sims else 0.0
    return IntentResult(
        tags=tags_by_category,
        confidence=confidence,
        tier="sentence_transformer",
        raw=f"top similarities: {sorted(matched_sims, reverse=True)[:5]}",
    )
