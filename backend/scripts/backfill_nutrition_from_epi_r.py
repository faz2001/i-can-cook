"""
Nutrition backfill, pass 1: the epi_r.csv Kaggle dataset ("Epicurious - Recipes
with Rating and Nutrition") has real per-recipe calories/protein/fat -- matched
here to already-imported recipes by exact (case-insensitive) title, since the
two Kaggle datasets aren't natively linked by ID.

Usage (from /backend):
    python3 scripts/backfill_nutrition_from_epi_r.py --csv path/to/epi_r.csv
    python3 scripts/backfill_nutrition_from_epi_r.py --csv path/to/epi_r.csv --dry-run

Idempotent and non-destructive: only fills recipes where calories_kcal IS NULL --
never overwrites nutrition that's already set (hand-annotated SL-Cook100 figures,
or a previous run of this same script).

Real, measured coverage on this dataset (13,463 already-imported recipes): ~39%
match, because ~21% of epi_r.csv rows have no title match at all in the image
dataset, and matches are additionally dropped here for two honest reasons:
  - Ambiguous duplicate titles in epi_r.csv (2,319 rows) -- if two different
    recipes share a title with different nutrition values, there's no reliable
    way to know which one a given imported recipe actually corresponds to, so
    BOTH are skipped rather than guessing.
  - Implausible outlier values -- this specific dataset has known scraping
    errors (one row claims 30,111,218 calories). Anything <=0 or >5000 kcal
    per serving is treated as bad data and skipped, not clamped or "fixed".

epi_r.csv has no carbs or fibre columns -- calories_kcal/protein_g/fat_g get
filled, carbs_g/fibre_g are left NULL (honestly -- RB-04 doesn't require every
field, just calories_kcal, to report available=True; carbs/fibre stay null
in the response for these recipes until something else fills them, e.g. the
USDA per-ingredient script for whatever this pass doesn't cover).
"""
import argparse
import csv
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.recipe import Recipe

MIN_PLAUSIBLE_CALORIES = 0
MAX_PLAUSIBLE_CALORIES = 5000


def load_usable_nutrition(csv_path: str) -> dict[str, dict]:
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))

    title_counts = Counter(r["title"].strip().lower() for r in rows if r.get("title"))

    usable: dict[str, dict] = {}
    skipped_dupe, skipped_bad = 0, 0
    for r in rows:
        title = (r.get("title") or "").strip()
        if not title:
            continue
        key = title.lower()
        if title_counts[key] > 1:
            skipped_dupe += 1
            continue

        def to_float(field):
            val = r.get(field)
            if val in (None, "", "NA"):
                return None
            try:
                return float(val)
            except ValueError:
                return None

        calories = to_float("calories")
        if calories is not None and not (MIN_PLAUSIBLE_CALORIES < calories <= MAX_PLAUSIBLE_CALORIES):
            skipped_bad += 1
            continue

        usable[key] = {
            "calories_kcal": calories,
            "protein_g": to_float("protein"),
            "fat_g": to_float("fat"),
        }

    print(f"epi_r.csv: {len(rows)} rows -> {len(usable)} usable (skipped {skipped_dupe} ambiguous duplicate titles, {skipped_bad} implausible outliers)")
    return usable


def backfill(csv_path: str, dry_run: bool):
    usable = load_usable_nutrition(csv_path)

    db = SessionLocal()
    try:
        candidates = db.query(Recipe).filter(Recipe.calories_kcal.is_(None)).all()
        print(f"Recipes currently missing nutrition: {len(candidates)}")

        updated = 0
        for recipe in candidates:
            match = usable.get(recipe.name_en.strip().lower())
            if not match or match["calories_kcal"] is None:
                continue
            recipe.calories_kcal = match["calories_kcal"]
            recipe.protein_g = match["protein_g"]
            recipe.fat_g = match["fat_g"]
            # carbs_g / fibre_g intentionally left as-is (NULL) -- epi_r.csv doesn't have them
            updated += 1

        if dry_run:
            db.rollback()
            print(f"[dry run] Would update {updated} recipes -- no changes written")
        else:
            db.commit()
            print(f"Updated {updated} recipes with real calories/protein/fat")
            print(f"Still missing nutrition after this pass: {len(candidates) - updated}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", required=True, help="Path to epi_r.csv")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing to the DB")
    args = parser.parse_args()
    backfill(args.csv, args.dry_run)
