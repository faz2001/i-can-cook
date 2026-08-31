"""
One-off ingestion script: loads every sl_*.json recipe file from
data_sl_cook100/ into the recipes / recipe_ingredients / recipe_steps tables.

Run once after applying db/schema.sql:

    python3 scripts/ingest_recipes.py

Idempotent: re-running it deletes and re-inserts each recipe by id, so it's
safe to re-run after the dataset changes.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.recipe import Recipe, RecipeIngredient, RecipeStep

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data_sl_cook100")

# The SL-Cook100 JSON files carry no photos at all -- these are a one-time,
# hand-picked fallback per `course` (real distribution across the 99 recipes:
# Main 52, Dessert 16, Breakfast 13, Snack 9, Condiment 7, Dinner 2).
#
# Point these at files you host yourself (e.g. the frontend's /public/images/
# categories/ folder, served at /images/categories/*.jpg by Vite) rather than
# hotlinking third-party stock URLs -- no broken links, no licensing surprises.
# Any course not listed here (or a null course, e.g. on a future community
# submission) falls back to DEFAULT_IMAGE.
COURSE_IMAGES = {
    "Main": "/images/categories/main.jpg",
    "Dessert": "/images/categories/dessert.jpg",
    "Breakfast": "/images/categories/breakfast.jpg",
    "Snack": "/images/categories/snack.jpg",
    "Condiment": "/images/categories/condiment.jpg",
    "Dinner": "/images/categories/dinner.jpg",
}
DEFAULT_IMAGE = "/images/categories/default.jpg"


def ingest():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "sl_*.json")))
    if not files:
        print(f"No recipe files found in {DATA_DIR}")
        return

    db = SessionLocal()
    inserted, skipped = 0, 0
    try:
        for path in files:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            recipe_id = data.get("id")
            if not recipe_id:
                print(f"  SKIP {os.path.basename(path)}: no 'id' field")
                skipped += 1
                continue

            # idempotent: wipe any existing row for this id first
            db.query(Recipe).filter(Recipe.id == recipe_id).delete()

            nutrition = data.get("nutrition_per_serving") or {}
            recipe = Recipe(
                id=recipe_id,
                name_en=data.get("name_en", "Untitled"),
                name_native=data.get("name_si"),
                regional_origin=data.get("regional_origin"),
                cuisine=data.get("cuisine"),
                course=data.get("course"),
                servings=data.get("servings"),
                prep_time_min=data.get("prep_time_min"),
                cook_time_min=data.get("cook_time_min"),
                total_time_min=data.get("total_time_min"),
                tags=data.get("tags", []),
                ayurvedic_balance=data.get("ayurvedic_balance"),
                image_url=COURSE_IMAGES.get(data.get("course"), DEFAULT_IMAGE),
                calories_kcal=nutrition.get("calories"),
                protein_g=nutrition.get("protein_g"),
                carbs_g=nutrition.get("carbs_g"),
                fat_g=nutrition.get("fat_g"),
                fibre_g=nutrition.get("fibre_g"),
                trust_score=data.get("trust_score") or 0.9,  # curated & hand-annotated -- high default trust
                source_type="curated",
                moderation_status="approved",
                source_url=data.get("source_url"),
                source_site=data.get("source_site"),
                collection_method=data.get("collection_method"),
                annotated_by=data.get("annotated_by"),
                annotation_date=data.get("annotation_date"),
                notes=data.get("notes"),
            )
            db.add(recipe)

            for idx, ing in enumerate(data.get("ingredients", [])):
                db.add(RecipeIngredient(
                    recipe_id=recipe_id,
                    # The curated dataset already hand-annotates canonical_id per
                    # ingredient -- no fuzzy matching needed, unlike imported recipes.
                    ingredient_id=ing.get("canonical_id"),
                    raw_name=ing.get("name", "Unknown"),
                    quantity=ing.get("quantity"),
                    unit=ing.get("unit"),
                    notes=ing.get("notes"),
                    position=idx,
                ))

            for step in data.get("steps", []):
                db.add(RecipeStep(
                    recipe_id=recipe_id,
                    step_number=step.get("step", 0),
                    instruction=step.get("instruction", ""),
                    duration_min=step.get("duration_min"),
                ))

            inserted += 1

        db.commit()
        print(f"Ingested {inserted} recipes ({skipped} skipped) from {DATA_DIR}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ingest()
