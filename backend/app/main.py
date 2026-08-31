import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.security import SECRET_KEY
from app.routers import (
    pantry, recipes, favorites, zero_waste, scale, substitutions, auth, shelf_life,
    community, admin_dashboard, admin_tags, admin_trust_scores, admin_recipes, admin_dataset,
    profile, bookmarks, recipes_browse, recommend, tags,
)

_DEV_DEFAULT_SECRET = "dev-secret-change-me-in-production"


def _check_secret_key_is_safe_for_production() -> None:
    """Refuse to start with the known-public default JWT secret when ENV=production.

    Local dev (ENV unset or ENV=development) is left untouched -- the default
    secret is fine there, it's only a problem once real user sessions are on
    the line. This only checks whether the secret was ever overridden, not
    the "strength" of whatever value was provided.
    """
    env = os.getenv("ENV", "development")
    if env != "production":
        return
    if SECRET_KEY == _DEV_DEFAULT_SECRET:
        raise RuntimeError(
            "JWT_SECRET_KEY is unset (or still the default dev value) while ENV=production. "
            "Set JWT_SECRET_KEY to a real secret before running with ENV=production."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_secret_key_is_safe_for_production()
    yield


app = FastAPI(title="i-can-cook API", lifespan=lifespan)

# Dev-friendly CORS default so the frontend (Vite dev server on a different
# origin) can call this API from the browser without extra setup. Set
# CORS_ALLOWED_ORIGINS to a comma-separated list of real origins (e.g.
# "https://app.example.com,https://admin.example.com") before deploying
# anywhere real -- leaving it unset keeps the wide-open "*" default, which is
# fine for local dev but not for production.
_cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
CORS_ALLOWED_ORIGINS = (
    [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
    if _cors_origins_env
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(shelf_life.router)
app.include_router(pantry.router)
# zero_waste must be registered before recipes: both define paths under
# /api/recipes, and recipes.py's GET /api/recipes/{recipe_id} is a catch-all
# that would otherwise swallow /api/recipes/zero-waste-suggestions as if
# "zero-waste-suggestions" were a recipe id.
app.include_router(zero_waste.router)
# Additive: public GET /api/recipes list/search -- see recipes_browse.py docstring.
app.include_router(recipes_browse.router)
app.include_router(recipes.router)
app.include_router(favorites.router)
app.include_router(scale.router)
app.include_router(substitutions.router)
app.include_router(community.router)
app.include_router(admin_dashboard.router)
app.include_router(admin_tags.router)
app.include_router(admin_trust_scores.router)
app.include_router(admin_recipes.router)
app.include_router(admin_dataset.router)
app.include_router(profile.router)
app.include_router(bookmarks.router)
# ML-01: tiered (Gemma -> Sentence-Transformer -> rule-based) recipe recommendations.
app.include_router(recommend.router)
# Public tag vocabulary: canonical equipment list + RB-01 filter-tag extraction
# (RB-01 is deliberately NOT part of the recommend pipeline above -- see
# app/services/rb01_intent.py).
app.include_router(tags.router)


@app.get("/health")
def health():
    return {"status": "ok"}
