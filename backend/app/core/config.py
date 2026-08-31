import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/icancook"
    )
    # Still defaults to the 3-feature v1 regressor, NOT
    # gradient_boosting_shelf_life_regressor_v2_prod.pkl (which adds
    # ingredient_name). v2 was evaluated with an ingredient-held-out
    # GroupShuffleSplit -- the realistic scenario, since ~50% of the app's
    # own seeded ingredient catalog isn't in the training set at all -- and
    # came out worse (lower R^2, higher MAE) than v1, not better. See the
    # provenance section of app/services/shelf_life.py for the full
    # comparison. v2 is kept on disk for reference; override this env var
    # if that changes with more training data.
    SHELF_LIFE_MODEL_PATH: str = os.getenv(
        "SHELF_LIFE_MODEL_PATH",
        os.path.join(os.path.dirname(__file__), "..", "..", "models", "gradient_boosting_shelf_life_regressor_prod.pkl"),
    )
    # ML-01 tiered intent extraction (see app/services/ml01/pipeline.py).
    # A tier's result is accepted if its confidence >= this; otherwise the
    # pipeline falls through to the next tier.
    ML01_MIN_CONFIDENCE: float = float(os.getenv("ML01_MIN_CONFIDENCE", "0.4"))
    # Set to a real local endpoint (e.g. http://localhost:11434) to activate
    # Gemma via Ollama. Left unset, Tier 1 is unavailable and the pipeline
    # falls through to Tier 2 (Sentence Transformer) -- see gemma_extractor.py.
    GEMMA_OLLAMA_URL: str | None = os.getenv("GEMMA_OLLAMA_URL")
    # Base URL used to build the link inside verification emails. Points at
    # the API's own GET /api/auth/verify route -- other things that need an
    # absolute API URL (not a frontend one) should keep using this.
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    # Base URL of the frontend app. The verification email link points here
    # (at /verify-email?token=...), not at API_BASE_URL, so clicking it from
    # an email opens the actual app UI instead of showing raw JSON.
    FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


settings = Settings()
