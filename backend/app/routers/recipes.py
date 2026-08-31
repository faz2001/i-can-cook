import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.favorite import Favorite
from app.models.recipe import Recipe, RecipeIngredient, RecipeStep
from app.models.user import User
from app.schemas.recipe import (
    RecipeDetailOut, IngredientLineOut, StepOut, NutritionOut,
    CookSessionOut, ChecklistItemOut, CookStepOut,
    RecipeSubmissionIn, RecipeSubmissionOut,
)
from app.services import rb02_pantry, rb03_scaling, rb04_nutrition
from app.services.ingredient_matching import load_ingredient_index, match_ingredient

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.post("", response_model=RecipeSubmissionOut, status_code=status.HTTP_201_CREATED)
def submit_recipe(
    payload: RecipeSubmissionIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Community recipe submission -- feeds the /admin/recipes moderation queue. Starts
    at moderation_status='pending' and stays invisible to everyone but the submitter and
    admins (see the visibility check in get_recipe_detail) until an admin approves it."""
    recipe_id = f"com_{uuid.uuid4().hex[:12]}"
    recipe = Recipe(
        id=recipe_id, name_en=payload.name_en, cuisine=payload.cuisine, course=payload.course,
        servings=payload.servings, prep_time_min=payload.prep_time_min, cook_time_min=payload.cook_time_min,
        tags=payload.tags, trust_score=0.3, source_type="community",
        moderation_status="pending", submitted_by=current_user.id,
        collection_method="community submission",
    )
    db.add(recipe)
    db.flush()

    ing_index = load_ingredient_index(db)
    for pos, ing in enumerate(payload.ingredients):
        db.add(RecipeIngredient(
            recipe_id=recipe_id, ingredient_id=match_ingredient(ing.raw_name, ing_index),
            raw_name=ing.raw_name, quantity=ing.quantity, unit=ing.unit, notes=ing.notes, position=pos,
        ))
    for step in payload.steps:
        db.add(RecipeStep(recipe_id=recipe_id, step_number=step.step_number,
                           instruction=step.instruction, duration_min=step.duration_min))

    db.commit()
    db.refresh(recipe)
    return RecipeSubmissionOut(id=recipe.id, name_en=recipe.name_en, moderation_status=recipe.moderation_status)


@router.get("/{recipe_id}", response_model=RecipeDetailOut)
def get_recipe_detail(
    recipe_id: str,
    servings: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = (
        db.query(Recipe)
        .options(joinedload(Recipe.ingredients), joinedload(Recipe.steps))
        .filter(Recipe.id == recipe_id)
        .first()
    )
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    if recipe.moderation_status != "approved" and current_user.role != "admin" \
            and recipe.submitted_by != current_user.id:
        # Pending/rejected community submissions are only visible to their own submitter
        # and to admins reviewing the moderation queue -- not to the public.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    requested_servings = servings or recipe.servings or 1
    factor = rb03_scaling.scale_factor(recipe, requested_servings)
    scaled_quantities = rb03_scaling.scale_ingredients(recipe.ingredients, factor)

    availabilities = rb02_pantry.match_pantry(db, current_user.id, recipe.ingredients)
    availability_by_ri_id = {a.recipe_ingredient.id: a for a in availabilities}

    ingredients_out = []
    for ri in sorted(recipe.ingredients, key=lambda x: x.position):
        avail = availability_by_ri_id[ri.id]
        ingredients_out.append(IngredientLineOut(
            ingredient_id=ri.ingredient_id,
            name=ri.raw_name,
            quantity=scaled_quantities[ri.id],
            unit=ri.unit,
            notes=ri.notes,
            pantry_status=avail.status,
            pantry_quantity_available=avail.pantry_quantity_available,
        ))

    steps_out = [
        StepOut(step_number=s.step_number, instruction=s.instruction, duration_min=s.duration_min)
        for s in sorted(recipe.steps, key=lambda x: x.step_number)
    ]

    nutrition = NutritionOut(**rb04_nutrition.get_nutrition(recipe))
    health_score = rb04_nutrition.compute_health_score(recipe)

    is_favorited = (
        db.query(Favorite.id)
        .filter(Favorite.user_id == current_user.id, Favorite.recipe_id == recipe.id)
        .first()
        is not None
    )

    return RecipeDetailOut(
        id=recipe.id,
        name_en=recipe.name_en,
        name_native=recipe.name_native,
        cuisine=recipe.cuisine,
        regional_origin=recipe.regional_origin,
        course=recipe.course,
        ayurvedic_balance=recipe.ayurvedic_balance,
        image_url=recipe.image_url,
        tags=recipe.tags,
        base_servings=recipe.servings,
        requested_servings=requested_servings,
        scale_factor=round(factor, 3),
        ingredients=ingredients_out,
        steps=steps_out,
        nutrition=nutrition,
        trust_score=float(recipe.trust_score),
        health_score=health_score,
        source_type=recipe.source_type,
        source_url=recipe.source_url,
        average_rating=float(recipe.average_rating) if recipe.average_rating is not None else None,
        review_count=recipe.review_count,
        is_favorited=is_favorited,
    )


@router.get("/{recipe_id}/cook", response_model=CookSessionOut)
def get_cook_session(
    recipe_id: str,
    servings: int | None = None,
    db: Session = Depends(get_db),
    # No current_user dependency here on purpose: Kitchen Mode doesn't need pantry status
    # (you've already committed to cooking), so it doesn't need to be behind login the way
    # the pantry-aware /results and /recipes/{id} endpoints do. Add Depends(get_current_user)
    # back if you later want to log completed cook sessions per user.
):
    recipe = (
        db.query(Recipe)
        .options(joinedload(Recipe.ingredients), joinedload(Recipe.steps))
        .filter(Recipe.id == recipe_id)
        .first()
    )
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    requested_servings = servings or recipe.servings or 1
    factor = rb03_scaling.scale_factor(recipe, requested_servings)
    scaled_quantities = rb03_scaling.scale_ingredients(recipe.ingredients, factor)

    checklist = [
        ChecklistItemOut(
            name=ri.raw_name,
            quantity=scaled_quantities[ri.id],
            unit=ri.unit,
            notes=ri.notes,
        )
        for ri in sorted(recipe.ingredients, key=lambda x: x.position)
    ]

    steps = [
        CookStepOut(
            step_number=s.step_number,
            instruction=s.instruction,
            duration_min=s.duration_min,
            timer_seconds=(s.duration_min * 60) if s.duration_min else None,
        )
        for s in sorted(recipe.steps, key=lambda x: x.step_number)
    ]
    total_active_time_min = sum(s.duration_min for s in recipe.steps if s.duration_min)

    return CookSessionOut(
        recipe_id=recipe.id,
        name_en=recipe.name_en,
        requested_servings=requested_servings,
        scale_factor=round(factor, 3),
        total_active_time_min=total_active_time_min,
        prep_checklist=checklist,
        steps=steps,
    )
