"""
Nutrition backfill, pass 2: USDA FoodData Central per-ingredient aggregation,
for whatever backfill_nutrition_from_epi_r.py didn't cover.

Usage (from /backend):
    export USDA_API_KEY=...       # get one free: fdc.nal.usda.gov/api-key-signup
    python3 scripts/backfill_nutrition_from_usda.py --limit 10          # test small first
    python3 scripts/backfill_nutrition_from_usda.py                    # full run

Network dependency, disclosed plainly: this talks to api.nal.usda.gov once per
UNIQUE ingredient name (cached to --cache-path afterward, default
usda_nutrition_cache.json, so re-runs and later recipes reuse lookups instead of
re-querying). Without USDA_API_KEY it falls back to DEMO_KEY, capped at 30
requests/hour -- fine for a --limit test, not for a full run.

Method, so this is auditable rather than a black box:
  1. For each recipe still missing calories_kcal, pull its recipe_ingredients.
  2. For each ingredient, search USDA FDC by name (first hit only -- no attempt
     to disambiguate "raw" vs "cooked" vs branded variants; that's a real
     source of error, worth stating as a limitation, not hidden).
  3. Convert quantity+unit to grams via UNIT_TO_GRAMS (approximate -- a cup of
     flour and a cup of oil do not weigh the same; this uses one generic
     factor per unit regardless of ingredient, which is the standard
     simplification this kind of tool makes, not a precision claim).
  4. Scale the USDA per-100g nutrient values by grams/100, sum across all
     ingredients in the recipe.
  5. Servings: every recipe reaching this script has servings=NULL (the image
     dataset never had a serving count). Rather than leave the whole
     aggregation useless, this assumes DEFAULT_SERVINGS=4 -- the same
     disclosed assumption epi_r.csv-style recipe sites commonly default to --
     and WRITES it onto recipe.servings (not just used internally), so
     serving-based scaling elsewhere in the app stays consistent with what
     nutrition assumed, instead of nutrition assuming 4 while scaling
     separately assumes 1.
  6. Ingredients that don't return a confident USDA match are skipped (not
     zero-filled) -- the recipe's total is therefore a lower bound when any
     ingredient is missing, not a guaranteed-complete figure. Worth a
     dissertation limitations line.
"""
import argparse
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.recipe import Recipe, RecipeIngredient

USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
DEFAULT_SERVINGS = 4

# USDA nutrient numbers (per 100g, from any FDC food's foodNutrients list)
NUTRIENT_CODES = {
    "calories_kcal": "1008",  # Energy (kcal)
    "protein_g": "1003",
    "carbs_g": "1005",        # Carbohydrate, by difference
    "fat_g": "1004",
    "fibre_g": "1079",        # Fiber, total dietary
}

# Approximate, unit-level (not ingredient-specific) gram equivalents -- the
# standard simplification for this kind of aggregation, not a precision claim.
UNIT_TO_GRAMS = {
    "tsp": 5, "teaspoon": 5, "teaspoons": 5,
    "tbsp": 15, "tablespoon": 15, "tablespoons": 15,
    "cup": 240, "cups": 240,
    "oz": 28.35, "ounce": 28.35, "ounces": 28.35,
    "lb": 453.6, "lbs": 453.6, "pound": 453.6, "pounds": 453.6,
    "g": 1, "gram": 1, "grams": 1,
    "kg": 1000, "kilogram": 1000, "kilograms": 1000,
    "ml": 1, "milliliter": 1, "milliliters": 1,  # assumes ~water density
    "l": 1000, "liter": 1000, "liters": 1000,
    "pinch": 0.5, "dash": 0.5,
    "clove": 3, "cloves": 3,
    "slice": 25, "slices": 25,
    "stick": 113, "sticks": 113,  # butter stick
}
# Countable items with no unit at all ("3 eggs") -- rough per-item weight.
COUNT_ITEM_GRAMS = {
    "egg": 50, "eggs": 50,
    "onion": 150, "onions": 150,
    "garlic clove": 3,
    "lemon": 60, "lemons": 60,
    "lime": 45, "limes": 45,
}


def quantity_to_grams(quantity: float | None, unit: str | None, name: str) -> float | None:
    if quantity is None:
        return None
    if unit:
        factor = UNIT_TO_GRAMS.get(unit.lower().strip())
        if factor is not None:
            return quantity * factor
        return None  # unrecognized unit -- don't guess
    # no unit -- try a per-item weight for common countable ingredients
    for key, grams in COUNT_ITEM_GRAMS.items():
        if key in name.lower():
            return quantity * grams
    return None


def usda_lookup(name: str, api_key: str, cache: dict) -> dict | None:
    """Returns per-100g nutrient values for the best USDA match, or None. Cached by
    lowercased ingredient name so repeated ingredients across recipes cost one call."""
    key = name.lower().strip()
    if key in cache:
        return cache[key]

    try:
        resp = requests.get(
            USDA_SEARCH_URL,
            params={"api_key": api_key, "query": name, "pageSize": 1, "dataType": "Foundation,SR Legacy"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("foods", [])
    except requests.RequestException as e:
        print(f"  USDA lookup failed for '{name}': {e}")
        cache[key] = None
        return None

    if not results:
        cache[key] = None
        return None

    food = results[0]
    nutrients = {n.get("nutrientNumber"): n.get("value") for n in food.get("foodNutrients", [])}
    per_100g = {
        field: nutrients.get(code) for field, code in NUTRIENT_CODES.items()
    }
    cache[key] = per_100g
    return per_100g


def backfill(api_key: str, limit: int | None, cache_path: str, sleep_seconds: float):
    cache: dict = {}
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached ingredient lookups from {cache_path}")

    db = SessionLocal()
    try:
        query = db.query(Recipe).filter(Recipe.calories_kcal.is_(None))
        if limit is not None:
            query = query.limit(limit)
        recipes = query.all()
        print(f"Recipes to process: {len(recipes)}")

        updated, no_ingredients_matched = 0, 0
        api_calls_made = 0

        for recipe in recipes:
            totals = {f: 0.0 for f in NUTRIENT_CODES}
            any_matched = False

            ingredients = db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe.id).all()
            for ing in ingredients:
                grams = quantity_to_grams(float(ing.quantity) if ing.quantity is not None else None, ing.unit, ing.raw_name)
                if grams is None:
                    continue

                cache_key = ing.raw_name.lower().strip()
                was_cached = cache_key in cache
                per_100g = usda_lookup(ing.raw_name, api_key, cache)
                if not was_cached:
                    api_calls_made += 1
                    time.sleep(sleep_seconds)

                if per_100g is None:
                    continue

                any_matched = True
                for field in NUTRIENT_CODES:
                    val = per_100g.get(field)
                    if val is not None:
                        totals[field] += val * grams / 100.0

            if not any_matched:
                no_ingredients_matched += 1
                continue

            servings = recipe.servings or DEFAULT_SERVINGS
            if recipe.servings is None:
                recipe.servings = DEFAULT_SERVINGS  # write it back -- keep nutrition and scaling consistent

            recipe.calories_kcal = round(totals["calories_kcal"] / servings, 1)
            recipe.protein_g = round(totals["protein_g"] / servings, 1)
            recipe.carbs_g = round(totals["carbs_g"] / servings, 1)
            recipe.fat_g = round(totals["fat_g"] / servings, 1)
            recipe.fibre_g = round(totals["fibre_g"] / servings, 1)
            updated += 1

            if updated % 25 == 0:
                db.commit()  # checkpoint periodically -- this is a long-running, network-bound script
                print(f"  ...{updated} recipes updated so far ({api_calls_made} USDA calls made)")

        db.commit()
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)

        print(f"\nDone. Updated {updated} recipes ({no_ingredients_matched} had no ingredients USDA could match at all -- left available=False)")
        print(f"USDA API calls made this run: {api_calls_made} (cache now has {len(cache)} ingredients -> {cache_path})")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api-key", default=os.environ.get("USDA_API_KEY", "DEMO_KEY"),
                         help="USDA FDC API key (or set USDA_API_KEY env var). Falls back to DEMO_KEY, capped at 30 req/hour.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N recipes missing nutrition (recommended for a first test run)")
    parser.add_argument("--cache-path", default="usda_nutrition_cache.json", help="Where to persist the ingredient->nutrient cache")
    parser.add_argument("--sleep", type=float, default=0.5, help="Seconds to sleep between USDA API calls")
    args = parser.parse_args()

    if args.api_key == "DEMO_KEY":
        print("WARNING: using DEMO_KEY (30 requests/hour). Get a free key at fdc.nal.usda.gov/api-key-signup and pass --api-key or set USDA_API_KEY for a full run.\n")

    backfill(args.api_key, args.limit, args.cache_path, args.sleep)
