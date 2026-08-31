"""
ML-01 -- Recipe Recommendation (proposal 4.2).

Query -> tiered intent extraction (Gemma -> Sentence Transformer ->
rule-based, see app/services/ml01/pipeline.py) -> score every approved
recipe against the extracted tags (+ optional pantry availability) ->
top-N ranked recipes.

Public by default (works for anonymous browsing); pass use_pantry=true
with auth to also weight by the caller's own pantry contents.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.models.pantry import PantryItem
from app.schemas.recommend import RecommendationQuery, RecommendationResult, RecommendedRecipe
from app.services.ml01.pipeline import extract_intent
from app.services.ml01.recommender import load_recipes, recommend

router = APIRouter(prefix="/api/recommendations", tags=["ml01-recommendations"])


@router.post("", response_model=RecommendationResult)
def get_recommendations(
    body: RecommendationQuery,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    intent = extract_intent(body.query)

    pantry_ids = None
    if body.use_pantry and current_user is not None:
        pantry_ids = {
            row.ingredient_id
            for row in db.query(PantryItem.ingredient_id)
            .filter(PantryItem.user_id == current_user.id, PantryItem.ingredient_id.isnot(None))
            .all()
        }

    recipes = load_recipes(db)
    ranked = recommend(intent.tags, recipes, pantry_ids, top_n=body.top_n)

    return RecommendationResult(
        query=body.query,
        extracted_tags=intent.tags,
        tier_used=intent.tier,
        tier_confidence=round(intent.confidence, 3),
        results=[
            RecommendedRecipe(
                id=r.id, name_en=r.name_en, cuisine=r.cuisine,
                course=r.course, tags=list(r.tags or []), score=round(score, 2),
            )
            for score, r in ranked
        ],
    )
