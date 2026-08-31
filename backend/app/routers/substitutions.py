from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.recipe import Recipe, RecipeIngredient
from app.models.substitution import IngredientSubstitution
from app.schemas.substitution import SubstitutionCreate, SubstitutionOut

router = APIRouter(tags=["substitutions"])


@router.get("/api/recipes/{recipe_id}/substitutions", response_model=list[SubstitutionOut])
def get_substitutions_for_recipe(
    recipe_id: str,
    missing_ingredient: str = Query(..., description="canonical_id of the ingredient the user doesn't have"),
    db: Session = Depends(get_db),
):
    """
    Looks up substitutes for one ingredient in a specific recipe. Requires
    the ingredient to actually belong to the recipe -- suggesting a
    substitute for something that isn't even in the dish would be a
    confusing response.

    NOTE: ingredient_substitutions is intentionally empty right now (see
    README) -- no real substitution dataset was available when this was
    built. This will correctly return `[]` for every ingredient until rows
    are seeded via POST /api/substitutions or a bulk import.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    belongs = (
        db.query(RecipeIngredient)
        .filter(RecipeIngredient.recipe_id == recipe_id, RecipeIngredient.ingredient_id == missing_ingredient)
        .first()
    )
    if not belongs:
        raise HTTPException(
            status_code=404,
            detail=f"'{missing_ingredient}' is not an ingredient in recipe '{recipe_id}'",
        )

    return (
        db.query(IngredientSubstitution)
        .filter(IngredientSubstitution.canonical_id == missing_ingredient)
        .all()
    )


@router.post("/api/substitutions", response_model=SubstitutionOut, status_code=201)
def create_substitution(body: SubstitutionCreate, db: Session = Depends(get_db)):
    """
    Seeds one substitution row. No admin-role check yet -- there's no
    admin auth module in this session to guard it with (see Auth module
    notes). Wire an admin-only dependency here once that exists; this
    endpoint being open is a placeholder, not a design decision.
    """
    sub = IngredientSubstitution(**body.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub
