from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.recipe import Recipe
from app.schemas.scale import RecipeScaleOut, ScaledIngredient

router = APIRouter(prefix="/api/recipes", tags=["scale"])


def _round_qty(value: Decimal) -> Decimal:
    # Round to 2 decimal places -- enough precision for cooking without
    # showing e.g. 0.333333333 cups.
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("/{recipe_id}/scale", response_model=RecipeScaleOut)
def scale_recipe(
    recipe_id: str,
    servings: int = Query(..., ge=1, le=100, description="Target number of servings"),
    db: Session = Depends(get_db),
):
    """
    Scales every ingredient quantity proportionally to a target serving
    count. Steps are returned unchanged elsewhere (via GET /api/recipes/{id})
    since instructions are prose, not quantities -- scaling them is a
    non-goal here (e.g. "simmer for 30 minutes" doesn't change with servings).
    """
    recipe = (
        db.query(Recipe)
        .options(joinedload(Recipe.ingredients))
        .filter(Recipe.id == recipe_id)
        .first()
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    if not recipe.servings or recipe.servings <= 0:
        raise HTTPException(
            status_code=422,
            detail="This recipe has no base serving size on record, so it can't be scaled.",
        )

    factor = Decimal(servings) / Decimal(recipe.servings)

    scaled_ingredients = [
        ScaledIngredient(
            canonical_id=ing.ingredient_id,
            name=ing.raw_name,
            original_quantity=ing.quantity,
            original_unit=ing.unit,
            scaled_quantity=_round_qty(ing.quantity * factor) if ing.quantity is not None else None,
            notes=ing.notes,
        )
        for ing in recipe.ingredients
    ]

    return RecipeScaleOut(
        recipe_id=recipe.id,
        name_en=recipe.name_en,
        original_servings=recipe.servings,
        requested_servings=servings,
        scale_factor=round(float(factor), 3),
        ingredients=scaled_ingredients,
    )
