"""
Tier 3: Rule-based keyword extraction (final fallback, per proposal 4.2:
"rule-based keyword extraction retained as a final fallback"; this is also
RB-01 Context & Intent Extraction from the rule-based module list).

This tier never raises -- it's the guaranteed-available bottom of the
fallback chain. Confidence is heuristic (fraction of categories where a
keyword actually matched), not a calibrated probability like the other
two tiers might eventually produce.
"""

import re

from .vocab import INTENT_VOCAB
from .gemma_extractor import IntentResult

# Words that negate whatever keyword follows within NEGATION_WINDOW words,
# e.g. "nothing spicy", "no dairy", "not too hot", "without chilli".
NEGATION_WORDS = {"no", "not", "nothing", "without", "non", "avoid", "skip"}
NEGATION_WINDOW = 3  # how many words ahead a negation word can reach


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.lower())


def _find_keyword(normalized_query: str, keyword: str):
    """Word-boundary match -- returns the match span, or None.

    Plain substring matching would let "breakfast" false-trigger the
    "fast" keyword (-> under-30-min). \\b anchors prevent that.
    """
    norm_kw = _normalize(keyword)
    m = re.search(r"\b" + re.escape(norm_kw) + r"\b", normalized_query)
    return m


def _is_negated(normalized_query: str, match_start: int) -> bool:
    """True if a negation word appears within NEGATION_WINDOW words before
    the start of the match in `normalized_query`."""
    preceding = normalized_query[:match_start].split()
    return any(w in NEGATION_WORDS for w in preceding[-NEGATION_WINDOW:])


def extract_intent_rule_based(query: str) -> IntentResult:
    normalized = _normalize(query)

    tags_by_category = {}
    matched_categories = 0

    for category, tags in INTENT_VOCAB.items():
        # (tag, matched_keyword) pairs found in this category, before
        # resolving overlaps between them.
        raw_matches = []
        for tag, keywords in tags.items():
            for kw in keywords:
                m = _find_keyword(normalized, kw)
                if m and not _is_negated(normalized, m.start()):
                    raw_matches.append((tag, _normalize(kw), m.start(), m.end()))
                    break  # one matching keyword is enough for this tag

        # Resolve overlaps: e.g. "very spicy" matches both the "very-spicy"
        # keyword "very spicy" AND the "spicy" keyword "spicy" (which is a
        # substring of the query at an overlapping position). When one
        # match's span is nested inside another match's span, keep only the
        # longer (more specific) one -- spice levels are mutually exclusive,
        # not additive.
        keep = []
        for tag, kw, start, end in raw_matches:
            nested_inside_another = any(
                (start >= s2 and end <= e2) and (start, end) != (s2, e2)
                for (_, _, s2, e2) in raw_matches
            )
            if not nested_inside_another:
                keep.append(tag)

        # de-dupe while preserving order
        category_matches = list(dict.fromkeys(keep))

        if category_matches:
            tags_by_category[category] = category_matches
            matched_categories += 1

    # Heuristic confidence: how many of the 6 categories produced a match.
    # This tier is meant to be "good enough to keep the app functional",
    # not high-precision -- reflected honestly in a lower confidence score.
    confidence = matched_categories / len(INTENT_VOCAB)

    return IntentResult(
        tags=tags_by_category,
        confidence=confidence,
        tier="rule_based",
        raw=f"{matched_categories}/{len(INTENT_VOCAB)} categories matched",
    )
