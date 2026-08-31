import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_admin
from app.core.database import get_db
from app.models.recipe import Recipe, RecipeIngredient, RecipeStep
from app.models.ingredient import Ingredient
from app.models.user import User
from app.schemas.admin import (
    AdminRecipeCreate, AdminRecipeListItemOut, AdminRecipeUpdate, ModerationAction,
)
from app.services.ingredient_matching import load_ingredient_index, match_ingredient

router = APIRouter(prefix="/api/admin/recipes", tags=["admin"], dependencies=[Depends(require_admin)])


def _replace_ingredients_and_steps(db: Session, recipe_id: str, ingredients, steps) -> None:
    db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()
    db.query(RecipeStep).filter(RecipeStep.recipe_id == recipe_id).delete()

    ing_index = load_ingredient_index(db)
    for pos, line in enumerate(ingredients):
        ingredient_id = line.ingredient_id or match_ingredient(line.raw_name, ing_index)
        db.add(RecipeIngredient(
            recipe_id=recipe_id, ingredient_id=ingredient_id, raw_name=line.raw_name,
            quantity=line.quantity, unit=line.unit, notes=line.notes, position=pos,
        ))
    for step in steps:
        db.add(RecipeStep(
            recipe_id=recipe_id, step_number=step.step_number,
            instruction=step.instruction, duration_min=step.duration_min,
        ))


@router.get("", response_model=list[AdminRecipeListItemOut])
def list_recipes(
    source_type: str | None = None,
    moderation_status: str | None = None,
    cuisine: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Recipe)
    if source_type:
        query = query.filter(Recipe.source_type == source_type)
    if moderation_status:
        query = query.filter(Recipe.moderation_status == moderation_status)
    if cuisine:
        query = query.filter(Recipe.cuisine == cuisine)
    if search:
        query = query.filter(Recipe.name_en.ilike(f"%{search}%"))
    return query.order_by(Recipe.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/pending", response_model=list[AdminRecipeListItemOut])
def list_pending_recipes(db: Session = Depends(get_db)):
    """Moderation queue: community-submitted recipes awaiting approve/reject."""
    return (
        db.query(Recipe)
        .filter(Recipe.moderation_status == "pending")
        .order_by(Recipe.created_at.asc())
        .all()
    )


@router.post("", response_model=AdminRecipeListItemOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: AdminRecipeCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    recipe_id = payload.id or f"adm_{uuid.uuid4().hex[:12]}"
    if db.query(Recipe).filter(Recipe.id == recipe_id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recipe id already exists")

    recipe = Recipe(
        id=recipe_id, name_en=payload.name_en, name_native=payload.name_native,
        cuisine=payload.cuisine, regional_origin=payload.regional_origin, course=payload.course,
        servings=payload.servings, prep_time_min=payload.prep_time_min, cook_time_min=payload.cook_time_min,
        total_time_min=payload.total_time_min, tags=payload.tags, ayurvedic_balance=payload.ayurvedic_balance,
        trust_score=payload.trust_score, source_type=payload.source_type,
        moderation_status="approved",   # admin-authored recipes don't need self-moderation
        annotated_by=current_user.email, collection_method="admin authored",
    )
    db.add(recipe)
    db.flush()
    _replace_ingredients_and_steps(db, recipe_id, payload.ingredients, payload.steps)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.put("/{recipe_id}", response_model=AdminRecipeListItemOut)
def update_recipe(
    recipe_id: str,
    payload: AdminRecipeUpdate,
    db: Session = Depends(get_db),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    updates = payload.model_dump(exclude_unset=True, exclude={"ingredients", "steps"})
    for field, value in updates.items():
        setattr(recipe, field, value)

    if payload.ingredients is not None and payload.steps is not None:
        _replace_ingredients_and_steps(db, recipe_id, payload.ingredients, payload.steps)
    elif payload.ingredients is not None or payload.steps is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide both ingredients and steps together, or neither -- partial replacement isn't supported",
        )

    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: str, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    db.delete(recipe)   # cascades to recipe_ingredients/recipe_steps/reviews/etc via FK ON DELETE CASCADE
    db.commit()


@router.post("/{recipe_id}/moderate", response_model=AdminRecipeListItemOut)
def moderate_recipe(recipe_id: str, payload: ModerationAction, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    if recipe.moderation_status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipe is not pending moderation")

    recipe.moderation_status = "approved" if payload.action == "approve" else "rejected"
    if payload.action == "reject" and payload.reason:
        recipe.notes = (f"{recipe.notes}\n" if recipe.notes else "") + f"Rejected: {payload.reason}"

    db.commit()
    db.refresh(recipe)
    return recipe
