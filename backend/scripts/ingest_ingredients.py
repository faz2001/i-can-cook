"""
One-off ingestion: loads ingredient_taxonomy.json into the ingredients
table. Idempotent (upserts by canonical_id).

Run once after applying db/schema.sql:

    python3 scripts/ingest_ingredients.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.ingredient import Ingredient

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data_sl_cook100", "ingredient_taxonomy.json")


def ingest():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    ingredients = data.get("ingredients", [])
    db = SessionLocal()
    try:
        for ing in ingredients:
            db.merge(Ingredient(
                canonical_id=ing["id"],
                name=ing["name"],
                category=ing["category"],
                unit_default=ing.get("unit_default"),
                source="sl_cook100",
            ))
        db.commit()
        print(f"Ingested {len(ingredients)} canonical ingredients from {DATA_PATH}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ingest()
