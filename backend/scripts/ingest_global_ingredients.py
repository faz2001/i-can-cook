"""
One-off ingestion: loads data_kaggle/global_ingredient_taxonomy.json into the
SAME ingredients table SL-Cook100 uses (source='kaggle_epicurious', vs
ingest_ingredients.py's 'sl_cook100'). Idempotent (upserts by canonical_id).

Run this AFTER ingest_ingredients.py and BEFORE import_epicurious.py, so the
Epicurious import can actually match against these entries on its first pass:

    python3 scripts/ingest_ingredients.py           # SL-Cook100 taxonomy first
    python3 scripts/ingest_global_ingredients.py     # then this
    python3 scripts/import_epicurious.py --csv ...   # then the recipe import

Deliberately the SAME table and ID space as SL-Cook100's taxonomy, not a
separate one -- see the `source` column comment in db/schema.sql for why:
pantry matching needs one shared canonical_id space to work across every
recipe regardless of which dataset it came from.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.ingredient import Ingredient

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data_kaggle", "global_ingredient_taxonomy.json")


def ingest():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    ingredients = data.get("ingredients", [])
    db = SessionLocal()
    try:
        # Guard against exact-name collisions with the OTHER source. load_ingredient_index()
        # keys purely by lowercased name -- two different canonical_ids with the same name
        # (e.g. this file adding "Onion" when SL-Cook100 already has "Onion") silently shadow
        # each other in matching, with whichever loads last winning. Caught this exact bug
        # once already (onion, egg) -- this check is what would have caught it automatically.
        existing = {row.name.lower(): row.canonical_id for row in db.query(Ingredient).all()}

        added, skipped_dupes = 0, []
        for ing in ingredients:
            name_lower = ing["name"].lower()
            if name_lower in existing and existing[name_lower] != ing["id"]:
                skipped_dupes.append((ing["name"], ing["id"], existing[name_lower]))
                continue
            db.merge(Ingredient(
                canonical_id=ing["id"],
                name=ing["name"],
                category=ing["category"],
                unit_default=ing.get("unit_default"),
                source="kaggle_epicurious",
            ))
            added += 1

        db.commit()
        print(f"Ingested {added} global canonical ingredients from {DATA_PATH}")
        if skipped_dupes:
            print(f"Skipped {len(skipped_dupes)} entries that duplicate an existing name (use the existing canonical_id instead):")
            for name, new_id, existing_id in skipped_dupes:
                print(f"  '{name}' ({new_id}) already exists as {existing_id}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ingest()
