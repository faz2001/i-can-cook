from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.models.pantry import PantryItem
from app.models.recipe import Recipe, RecipeIngredient
from app.schemas.zero_waste import MatchedIngredient, ZeroWasteSuggestion

router = APIRouter(prefix="/api/recipes", tags=["zero-waste"])


@router.get("/zero-waste-suggestions", response_model=list[ZeroWasteSuggestion])
def zero_waste_suggestions(
    within_days: int = Query(default=3, ge=1, le=30, description="Treat items expiring within this many days as 'use soon'"),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Cross-references the user's "use soon" pantry items (expiry_date within
    `within_days`, predicted or label-based -- doesn't matter which for this
    query) against recipe ingredients, ranking recipes by how many of those
    expiring items they'd use up. Pure query -- no new table.

    Updated to use PantryItem.expiry_date directly now that the pantry
    model tracks real dates (via ML-02 or a user-entered label) instead of
    a cached short/long classification -- a concrete cutoff is more useful
    here than a stored label ever was, and avoids the two ever drifting out
    of sync.

    Matching is on `ingredient_id`, so pantry items added without one
    (freeform/unmatched ingredients) simply can't participate -- that's a
    data quality gap for the frontend to close by having "add to pantry"
    resolve against the same canonical ingredient list recipes use, not a
    bug here.
    """
    cutoff = date.today() + timedelta(days=within_days)
    expiring_items = (
        db.query(PantryItem)
        .filter(
            PantryItem.user_id == user_id,
            PantryItem.expiry_date.isnot(None),
            PantryItem.expiry_date <= cutoff,
            PantryItem.ingredient_id.isnot(None),
        )
        .all()
    )

    if not expiring_items:
        return []

    expiring_ids = {item.ingredient_id for item in expiring_items}
    id_to_name = {item.ingredient_id: item.raw_name for item in expiring_items}

    # Total ingredient count per recipe (for coverage %), computed once.
    total_counts = dict(
        db.query(RecipeIngredient.recipe_id, func.count(RecipeIngredient.id))
        .group_by(RecipeIngredient.recipe_id)
        .all()
    )

    # Only recipes that use at least one expiring ingredient.
    matches = (
        db.query(RecipeIngredient.recipe_id, RecipeIngredient.ingredient_id)
        .filter(RecipeIngredient.ingredient_id.in_(expiring_ids))
        .all()
    )

    matched_by_recipe: dict[str, set[str]] = {}
    for recipe_id, canonical_id in matches:
        matched_by_recipe.setdefault(recipe_id, set()).add(canonical_id)

    if not matched_by_recipe:
        return []

    recipes = {
        r.id: r for r in db.query(Recipe).filter(Recipe.id.in_(matched_by_recipe.keys())).all()
    }

    suggestions = []
    for recipe_id, matched_ids in matched_by_recipe.items():
        recipe = recipes.get(recipe_id)
        if not recipe:
            continue
        total = total_counts.get(recipe_id, 0)
        suggestions.append(ZeroWasteSuggestion(
            recipe_id=recipe.id,
            name_en=recipe.name_en,
            total_time_min=recipe.total_time_min,
            matched_ingredient_count=len(matched_ids),
            total_ingredient_count=total,
            coverage_fraction=round(len(matched_ids) / total, 3) if total else 0.0,
            matched_ingredients=[
                MatchedIngredient(canonical_id=cid, pantry_item_name=id_to_name[cid])
                for cid in sorted(matched_ids)
            ],
        ))

    # Rank by how many expiring items it uses first, then by how much of the
    # recipe that covers (a 2-ingredient recipe using both is a tighter win
    # than a 20-ingredient recipe using the same 2).
    suggestions.sort(key=lambda s: (s.matched_ingredient_count, s.coverage_fraction), reverse=True)
    return suggestions[:limit]
