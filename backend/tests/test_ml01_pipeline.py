"""
Unit tests for the ML-01 tiered intent extraction pipeline
(app/services/ml01/pipeline.py + gemma_extractor / embedding_extractor /
rule_based_extractor).

No DB / network required -- Gemma's httpx call and the Sentence Transformer
model load are mocked. Run with:

    pytest tests/test_ml01_pipeline.py -v

NOTE ON VOCAB: INTENT_VOCAB (app/services/ml01/vocab.py) has NO "ingredients"
category -- its categories are meal_type, dietary, spice_level,
cooking_constraint, occasion, cuisine. If your Gemma prompt/docs describe it
as returning "ingredients", that's a drift between the docs and the actual
controlled vocabulary; see test_gemma_ignores_out_of_vocab_category below,
which documents that an "ingredients" key in Gemma's raw output is silently
dropped (by design -- the extractor never trusts categories outside
INTENT_VOCAB), not surfaced as an error.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.ml01.gemma_extractor import (
    extract_intent_gemma,
    GemmaUnavailableError,
)
from app.services.ml01.rule_based_extractor import extract_intent_rule_based
from app.services.ml01.embedding_extractor import EmbeddingModelUnavailableError
from app.services.ml01.pipeline import extract_intent
from app.services.ml01.vocab import INTENT_VOCAB
from app.core.config import settings


# ---------------------------------------------------------------------------
# Tier 1: Gemma
# ---------------------------------------------------------------------------

class TestGemmaExtractor:
    def test_raises_when_url_not_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMMA_OLLAMA_URL", None)
        with pytest.raises(GemmaUnavailableError, match="not set"):
            extract_intent_gemma("spicy vegetarian dinner")

    def test_happy_path_filters_to_known_vocab(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMMA_OLLAMA_URL", "http://localhost:11434")
        model_response = {
            "meal_type": ["dinner"],
            "spice_level": ["spicy"],
            "dietary": ["vegetarian"],
        }
        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.return_value = {"response": json.dumps(model_response)}

        with patch("app.services.ml01.gemma_extractor.httpx.post", return_value=fake_resp):
            result = extract_intent_gemma("a spicy vegetarian dinner")

        assert result.tier == "gemma"
        assert result.confidence == 0.9
        assert result.tags == model_response

    def test_drops_categories_outside_controlled_vocab(self, monkeypatch):
        """Gemma output is never trusted blindly -- a category the app
        doesn't know about (e.g. a stray "ingredients" key) must be
        silently dropped, not passed through to the recommender."""
        monkeypatch.setattr(settings, "GEMMA_OLLAMA_URL", "http://localhost:11434")
        model_response = {
            "meal_type": ["dinner"],
            "ingredients": ["chicken", "coconut milk"],  # not a real category
        }
        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.return_value = {"response": json.dumps(model_response)}

        with patch("app.services.ml01.gemma_extractor.httpx.post", return_value=fake_resp):
            result = extract_intent_gemma("chicken curry for dinner")

        assert "ingredients" not in result.tags
        assert result.tags == {"meal_type": ["dinner"]}

    def test_drops_out_of_vocab_tag_values_within_a_known_category(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMMA_OLLAMA_URL", "http://localhost:11434")
        model_response = {"meal_type": ["dinner", "brunch"]}  # "brunch" isn't in vocab
        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.return_value = {"response": json.dumps(model_response)}

        with patch("app.services.ml01.gemma_extractor.httpx.post", return_value=fake_resp):
            result = extract_intent_gemma("brunch")

        assert result.tags == {"meal_type": ["dinner"]}

    def test_raises_when_nothing_matches_vocab_at_all(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMMA_OLLAMA_URL", "http://localhost:11434")
        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.return_value = {"response": json.dumps({"ingredients": ["chicken"]})}

        with patch("app.services.ml01.gemma_extractor.httpx.post", return_value=fake_resp):
            with pytest.raises(GemmaUnavailableError, match="no tags matching"):
                extract_intent_gemma("chicken curry")

    def test_raises_on_malformed_json_response(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMMA_OLLAMA_URL", "http://localhost:11434")
        fake_resp = MagicMock()
        fake_resp.raise_for_status.return_value = None
        fake_resp.json.return_value = {"response": "not valid json {{"}

        with patch("app.services.ml01.gemma_extractor.httpx.post", return_value=fake_resp):
            with pytest.raises(GemmaUnavailableError, match="call failed"):
                extract_intent_gemma("anything")

    def test_raises_when_ollama_unreachable(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMMA_OLLAMA_URL", "http://localhost:11434")
        with patch(
            "app.services.ml01.gemma_extractor.httpx.post",
            side_effect=ConnectionError("refused"),
        ):
            with pytest.raises(GemmaUnavailableError, match="call failed"):
                extract_intent_gemma("anything")

    def test_raises_on_non_2xx_status(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMMA_OLLAMA_URL", "http://localhost:11434")
        import httpx
        fake_resp = MagicMock()
        fake_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock(status_code=500)
        )
        with patch("app.services.ml01.gemma_extractor.httpx.post", return_value=fake_resp):
            with pytest.raises(GemmaUnavailableError):
                extract_intent_gemma("anything")


# ---------------------------------------------------------------------------
# Tier 3: rule-based (no mocking needed -- pure function, always succeeds)
# ---------------------------------------------------------------------------

class TestRuleBasedExtractor:
    def test_never_raises_on_empty_query(self):
        result = extract_intent_rule_based("")
        assert result.tier == "rule_based"
        assert result.tags == {}
        assert result.confidence == 0.0

    def test_matches_multiple_categories(self):
        result = extract_intent_rule_based("a quick spicy vegetarian dinner")
        assert result.tags["meal_type"] == ["dinner"]
        assert result.tags["dietary"] == ["vegetarian"]
        assert result.tags["spice_level"] == ["spicy"]
        assert result.tags["cooking_constraint"] == ["under-30-min"]  # "quick"

    def test_negation_suppresses_the_match(self):
        """'nothing spicy' is itself a literal phrase keyword for the
        'mild' tag (see vocab.py), so this correctly resolves to mild --
        it is not a case of the negation window suppressing 'spicy' into
        no match. Use a phrase that hits the negation-window path
        specifically: negating 'hot' (a spicy-tag keyword with no
        direct mild-phrase overlap)."""
        result = extract_intent_rule_based("not too hot please")
        # "not too hot" is itself a literal mild-tag phrase too, so assert
        # the outcome is unambiguous: mild is tagged, spicy is NOT.
        assert result.tags.get("spice_level") == ["mild"]

    def test_negation_word_suppresses_a_plain_keyword_match(self):
        """A genuine negation-window case: 'hot' alone (not the literal
        'not too hot' phrase) is a 'spicy' keyword; negating it should
        suppress the spicy match without a competing mild-phrase match
        available to explain the result instead."""
        result = extract_intent_rule_based("please avoid hot food today")
        assert "spicy" not in result.tags.get("spice_level", [])

    def test_negation_window_is_bounded(self):
        """Negation only reaches NEGATION_WINDOW=3 words ahead -- a negation
        word far earlier in the sentence should NOT suppress an unrelated
        later match."""
        result = extract_intent_rule_based(
            "no eggs but I do want something spicy for dinner"
        )
        assert result.tags.get("spice_level") == ["spicy"]

    def test_breakfast_does_not_false_trigger_fast_keyword(self):
        """Regression guard for the \\b word-boundary fix described in the
        module docstring: 'breakfast' must not match the 'fast' keyword
        that maps to under-30-min."""
        result = extract_intent_rule_based("a nice breakfast")
        assert result.tags.get("meal_type") == ["breakfast"]
        assert "under-30-min" not in result.tags.get("cooking_constraint", [])

    def test_very_spicy_wins_over_nested_spicy_match(self):
        result = extract_intent_rule_based("make it very spicy")
        assert result.tags["spice_level"] == ["very-spicy"]

    def test_confidence_is_fraction_of_categories_matched(self):
        result = extract_intent_rule_based("dinner")
        assert result.confidence == pytest.approx(1 / len(INTENT_VOCAB))

    @pytest.mark.parametrize("query", [
        "asdkjaslkdj random gibberish text",
        "   ",
        "12345",
    ])
    def test_no_match_returns_empty_tags_not_an_error(self, query):
        result = extract_intent_rule_based(query)
        assert result.tags == {}
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Pipeline fallthrough (Gemma -> embedding -> rule-based)
# ---------------------------------------------------------------------------

class TestPipelineFallthrough:
    def test_uses_gemma_when_confident(self, monkeypatch):
        monkeypatch.setattr(settings, "ML01_MIN_CONFIDENCE", 0.4)
        fake_gemma = MagicMock(tags={"meal_type": ["dinner"]}, confidence=0.9, tier="gemma")
        with patch("app.services.ml01.pipeline.extract_intent_gemma", return_value=fake_gemma):
            result = extract_intent("dinner")
        assert result.tier == "gemma"

    def test_falls_through_to_embedding_when_gemma_unavailable(self, monkeypatch):
        monkeypatch.setattr(settings, "ML01_MIN_CONFIDENCE", 0.4)
        fake_embed = MagicMock(tags={"meal_type": ["dinner"]}, confidence=0.6, tier="sentence_transformer")
        with patch(
            "app.services.ml01.pipeline.extract_intent_gemma",
            side_effect=GemmaUnavailableError("not configured"),
        ), patch(
            "app.services.ml01.pipeline.extract_intent_embedding", return_value=fake_embed
        ):
            result = extract_intent("dinner")
        assert result.tier == "sentence_transformer"

    def test_falls_through_to_embedding_when_gemma_below_confidence(self, monkeypatch):
        monkeypatch.setattr(settings, "ML01_MIN_CONFIDENCE", 0.8)
        fake_gemma = MagicMock(tags={"meal_type": ["dinner"]}, confidence=0.5, tier="gemma")
        fake_embed = MagicMock(tags={"meal_type": ["dinner"]}, confidence=0.9, tier="sentence_transformer")
        with patch(
            "app.services.ml01.pipeline.extract_intent_gemma", return_value=fake_gemma
        ), patch(
            "app.services.ml01.pipeline.extract_intent_embedding", return_value=fake_embed
        ):
            result = extract_intent("dinner")
        assert result.tier == "sentence_transformer"

    def test_falls_through_to_rule_based_when_both_tiers_unavailable(self, monkeypatch):
        """This is the exact fallback chain exercised in the live sandbox:
        GEMMA_OLLAMA_URL unset + sentence-transformers not installed ->
        rule_based, and the pipeline never raises."""
        monkeypatch.setattr(settings, "ML01_MIN_CONFIDENCE", 0.4)
        with patch(
            "app.services.ml01.pipeline.extract_intent_gemma",
            side_effect=GemmaUnavailableError("not configured"),
        ), patch(
            "app.services.ml01.pipeline.extract_intent_embedding",
            side_effect=EmbeddingModelUnavailableError("no internet"),
        ):
            result = extract_intent("a quick spicy vegetarian dinner")
        assert result.tier == "rule_based"
        assert result.tags["meal_type"] == ["dinner"]

    def test_rule_based_used_even_when_it_finds_nothing(self, monkeypatch):
        """Rule-based is the guaranteed-available bottom of the chain --
        confirm the pipeline still returns tier='rule_based' (with empty
        tags) rather than raising, for an unmatchable query."""
        monkeypatch.setattr(settings, "ML01_MIN_CONFIDENCE", 0.4)
        with patch(
            "app.services.ml01.pipeline.extract_intent_gemma",
            side_effect=GemmaUnavailableError("not configured"),
        ), patch(
            "app.services.ml01.pipeline.extract_intent_embedding",
            side_effect=EmbeddingModelUnavailableError("no internet"),
        ):
            result = extract_intent("zzz nonsense zzz")
        assert result.tier == "rule_based"
        assert result.tags == {}

    def test_embedding_low_confidence_still_falls_through_to_rule_based(self, monkeypatch):
        monkeypatch.setattr(settings, "ML01_MIN_CONFIDENCE", 0.8)
        fake_gemma = MagicMock(tags={}, confidence=0.1, tier="gemma")
        fake_embed = MagicMock(tags={}, confidence=0.2, tier="sentence_transformer")
        with patch(
            "app.services.ml01.pipeline.extract_intent_gemma", return_value=fake_gemma
        ), patch(
            "app.services.ml01.pipeline.extract_intent_embedding", return_value=fake_embed
        ):
            result = extract_intent("dinner")
        assert result.tier == "rule_based"
