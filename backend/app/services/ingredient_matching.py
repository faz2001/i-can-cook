"""
Shared free-text -> canonical ingredient_id matching. Used by:
  - scripts/import_external_dataset.py, when bulk-importing recipes
  - app/routers/pantry.py, when a user types an ingredient name into their pantry

Keeping one implementation means a pantry item and a recipe ingredient get matched the
same way, which matters -- RB-02 pantry matching only works when both sides resolved to
the same canonical ingredient_id.
"""
import difflib

from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient


def load_ingredient_index(db: Session) -> dict[str, str]:
    """canonical name (lowercased) -> canonical_id."""
    return {ing.name.lower(): ing.canonical_id for ing in db.query(Ingredient).all()}


_SIZE_PREFIXES = ("extra-large ", "extra large ", "large ", "medium ", "small ")

_PREP_WORDS = {
    "chopped", "fresh", "freshly", "finely", "grated", "ground", "sliced",
    "thinly", "coarsely", "minced", "diced", "crushed", "peeled", "melted",
    "softened", "room", "temperature", "shredded", "crumbled", "torn",
    "cracked", "toasted", "roasted", "divided", "plus", "more", "of",
}


def _normalize_for_matching(text: str) -> str:
    """A leading size word ('medium onion', 'large shallot') doesn't change what the
    ingredient IS, but it lowers the SequenceMatcher ratio enough to miss an otherwise-
    good match against a plain taxonomy name ('Onion', 'Shallot'). Strip it before
    matching only -- the raw_name stored on the recipe/pantry item is untouched.

    Real ingredient lines also stack multiple leading prep words ('finely grated
    orange peel', 'chopped fresh thyme'), so after the size-prefix check, pop leading
    tokens one at a time while the next token is in _PREP_WORDS."""
    t = text.lower().strip()
    for prefix in _SIZE_PREFIXES:
        if t.startswith(prefix):
            t = t[len(prefix):]
            break

    tokens = t.split()
    while tokens and tokens[0] in _PREP_WORDS:
        tokens.pop(0)
    return " ".join(tokens) if tokens else t


_STOPWORDS_FOR_OVERLAP = _PREP_WORDS | {
    "a", "an", "the", "or", "and", "with", "without", "for", "to", "in", "into", "on",
}

# Below this length a word is too common/short to say much either way (e.g. "egg",
# "oil", "corn" is the exception that's exactly 4 -- kept in), so words shorter than
# this are dropped from the overlap check rather than penalizing genuinely short
# ingredient names.
_MIN_OVERLAP_WORD_LEN = 4

# A per-word fuzzy ratio at or above this is treated as "close enough to be the same
# word" (typos/misspellings like "tumeric" vs "turmeric"), separate from the exact
# cutoff used to generate candidates in the first place.
_WORD_TYPO_RATIO = 0.8


def _content_words(s: str) -> set[str]:
    """Real, meaningful words in a string for overlap comparison -- lowercased,
    punctuation stripped, prep/stop words and very short words dropped."""
    t = s.lower()
    for ch in "(),.;:\"'":
        t = t.replace(ch, " ")
    return {w for w in t.split() if w not in _STOPWORDS_FOR_OVERLAP and len(w) >= _MIN_OVERLAP_WORD_LEN}


def _shares_real_word(normalized: str, candidate: str) -> bool:
    """True if normalized and candidate share a real word exactly, or a near-exact
    (typo-level) match of one. Widening _normalize_for_matching's prep-word stripping
    means normalized strings are shorter, which raises the odds of a same-cutoff
    match that's pure coincidental letter overlap (e.g. normalized "orange peel"
    fuzzy-matching taxonomy entry "coriander seeds") -- this catches those before
    they're returned as a match."""
    norm_words = _content_words(normalized)
    cand_words = _content_words(candidate)
    if not norm_words or not cand_words:
        # Nothing long enough to judge (e.g. bare "egg", "soy") -- don't block a
        # match on the strength of an empty comparison, fall back to trusting cutoff.
        return True
    for w1 in norm_words:
        for w2 in cand_words:
            if w1 == w2 or difflib.SequenceMatcher(None, w1, w2).ratio() >= _WORD_TYPO_RATIO:
                return True
    return False


def match_ingredient(raw_text: str, index: dict[str, str]) -> str | None:
    """Best-effort match of free text to the canonical taxonomy. Returns None (never
    raises) when there's no good match -- callers should keep the raw text either way.

    Looks at the top few cutoff=0.6 candidates (not just the single best-ratio one)
    and returns the first that shares a real word with the normalized text -- this
    both rejects coincidental letter-overlap matches (see _shares_real_word) and
    recovers cases where the *correct* candidate wasn't the top-ratio one (e.g.
    normalized "cumin" ranks taxonomy entry "Pumpkin" above "Cumin seeds" by raw
    ratio alone, even though "Cumin seeds" is the real match)."""
    if not raw_text:
        return None
    normalized = _normalize_for_matching(raw_text)
    candidates = difflib.get_close_matches(normalized, index.keys(), n=5, cutoff=0.6)
    for candidate in candidates:
        if _shares_real_word(normalized, candidate):
            return index[candidate]
    return None