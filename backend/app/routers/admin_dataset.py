import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_admin
from app.core.database import get_db
from app.models.pantry import PantryItem
from app.models.recipe import Recipe, RecipeIngredient
from app.models.ingredient import Ingredient
from app.schemas.admin import (
    AdminIngredientCreate, AdminIngredientUpdate, IngredientOut,
    ResolveUnmatchedIngredientIn, UnmatchedIngredientGroupOut, ValidationIssueOut,
)

router = APIRouter(prefix="/api/admin/dataset", tags=["admin"], dependencies=[Depends(require_admin)])


def _slugify_ingredient(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return f"ing_{slug}"


# ---------------------------------------------------------------------------
# Schema/quality validation for the curated SL-Cook100 corpus
# ---------------------------------------------------------------------------

@router.get("/validate", response_model=list[ValidationIssueOut])
def validate_curated_dataset(db: Session = Depends(get_db)):
    """Checks every curated (SL-Cook50/100) recipe against the expectations your schema
    implies but can't fully enforce with SQL constraints alone -- e.g. a curated recipe
    with unmatched ingredients defeats the point of hand-curation, so it's flagged even
    though the column itself is nullable."""
    issues: list[ValidationIssueOut] = []
    curated = (
        db.query(Recipe)
        .options(joinedload(Recipe.ingredients), joinedload(Recipe.steps))
        .filter(Recipe.source_type == "curated")
        .all()
    )

    seen_names: dict[str, str] = {}
    for r in curated:
        def flag(issue: str, severity: str = "warning") -> None:
            issues.append(ValidationIssueOut(recipe_id=r.id, recipe_name=r.name_en, issue=issue, severity=severity))

        if not r.ingredients:
            flag("No ingredients recorded", "error")
        if not r.steps:
            flag("No steps recorded", "error")
        if r.servings is None:
            flag("Missing servings", "warning")
        if r.calories_kcal is None:
            flag("Missing per-serving nutrition", "warning")
        if r.name_native is None:
            flag("Missing native-language name", "warning")
        if float(r.trust_score) < 0.7:
            flag(f"Trust Score ({r.trust_score}) is low for a curated recipe", "warning")

        unmatched = [ri for ri in r.ingredients if ri.ingredient_id is None]
        if unmatched:
            flag(f"{len(unmatched)} ingredient(s) not matched to canonical taxonomy: "
                 f"{', '.join(u.raw_name for u in unmatched[:3])}", "warning")

        key = r.name_en.strip().lower()
        if key in seen_names:
            flag(f"Duplicate name -- also used by recipe '{seen_names[key]}'", "warning")
        else:
            seen_names[key] = r.id

    return issues


# ---------------------------------------------------------------------------
# Unmatched ingredient triage -- mainly useful after a bulk external import
# ---------------------------------------------------------------------------

@router.get("/unmatched-ingredients", response_model=list[UnmatchedIngredientGroupOut])
def list_unmatched_ingredients(db: Session = Depends(get_db)):
    rows = (
        db.query(RecipeIngredient.raw_name, func.count(RecipeIngredient.id), func.array_agg(RecipeIngredient.recipe_id))
        .filter(RecipeIngredient.ingredient_id.is_(None))
        .group_by(RecipeIngredient.raw_name)
        .order_by(func.count(RecipeIngredient.id).desc())
        .all()
    )
    return [
        UnmatchedIngredientGroupOut(raw_name=raw_name, occurrence_count=count, sample_recipe_ids=recipe_ids[:5])
        for raw_name, count, recipe_ids in rows
    ]


@router.post("/unmatched-ingredients/resolve", status_code=status.HTTP_204_NO_CONTENT)
def resolve_unmatched_ingredient(payload: ResolveUnmatchedIngredientIn, db: Session = Depends(get_db)):
    """Bulk-assigns a canonical ingredient to every recipe_ingredients row (and matching
    pantry_items row) with this exact raw_name -- for fixing a common ETL miss in one go
    instead of editing recipes individually."""
    ingredient = db.query(Ingredient).filter(Ingredient.canonical_id == payload.ingredient_id).first()
    if ingredient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Canonical ingredient not found")

    db.query(RecipeIngredient).filter(
        RecipeIngredient.raw_name == payload.raw_name, RecipeIngredient.ingredient_id.is_(None)
    ).update({"ingredient_id": payload.ingredient_id}, synchronize_session=False)

    db.query(PantryItem).filter(
        PantryItem.raw_name == payload.raw_name, PantryItem.ingredient_id.is_(None)
    ).update({"ingredient_id": payload.ingredient_id}, synchronize_session=False)

    db.commit()


# ---------------------------------------------------------------------------
# Canonical ingredient taxonomy CRUD
# ---------------------------------------------------------------------------

@router.get("/ingredients", response_model=list[IngredientOut])
def list_ingredients(search: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Ingredient)
    if search:
        query = query.filter(Ingredient.name.ilike(f"%{search}%"))
    return query.order_by(Ingredient.name).all()


@router.post("/ingredients", response_model=IngredientOut, status_code=status.HTTP_201_CREATED)
def create_ingredient(payload: AdminIngredientCreate, db: Session = Depends(get_db)):
    ingredient_id = payload.id or _slugify_ingredient(payload.name)
    if db.query(Ingredient).filter(Ingredient.canonical_id == ingredient_id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ingredient id already exists")
    ingredient = Ingredient(canonical_id=ingredient_id, name=payload.name, category=payload.category,
                             unit_default=payload.unit_default)
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.put("/ingredients/{ingredient_id}", response_model=IngredientOut)
def update_ingredient(ingredient_id: str, payload: AdminIngredientUpdate, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).filter(Ingredient.canonical_id == ingredient_id).first()
    if ingredient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ingredient, field, value)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.delete("/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient_id: str, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).filter(Ingredient.canonical_id == ingredient_id).first()
    if ingredient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingredient not found")
    db.delete(ingredient)  # recipe_ingredients/pantry_items referencing it fall back to NULL (ON DELETE SET NULL)
    db.commit()
