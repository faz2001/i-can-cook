"""
One-off ingestion script: loads the Kaggle "Food Ingredients and Recipes Dataset
with Images" CSV (Epicurious scrape) into recipes / recipe_ingredients /
recipe_steps -- same tables ingest_recipes.py uses for SL-Cook100, so both
sets show up side by side once imported.

Usage (from /backend, after placing the CSV somewhere accessible):

    python3 scripts/import_epicurious.py --csv path/to/the.csv
    python3 scripts/import_epicurious.py --csv path/to/the.csv --limit 300   # test on a subset first
    python3 scripts/import_epicurious.py --csv path/to/the.csv --limit 300 --only-with-image   # guarantee every imported row has a real photo

Idempotent: ids are derived from the CSV's own row index (ep_<n>), and each
run deletes-then-reinserts by id, so it's safe to re-run after fixing the
parser or after editing the CSV.

What this CSV does NOT have, and how that's handled here (not faked):
  - No cuisine column      -> cuisine defaults to "International" (flagged below)
  - No course column       -> left NULL
  - No servings column     -> left NULL (RB-03 scaling falls back to 1 serving
                               at request time when this is NULL -- see
                               get_recipe_detail in app/routers/recipes.py)
  - No nutrition columns   -> all left NULL, so RB-04 correctly reports
                               available=False for every recipe from this import,
                               same as any other recipe with no nutrition data.
                               Fill these in afterward with a separate nutrition
                               script if you want computed values.
  - Ingredients are one free-text string each (e.g. "2 Tbsp. finely chopped
    sage"), not separate quantity/unit/name fields -- parse_ingredient() below
    splits each line into (quantity, unit, name, notes) before ingredient
    matching runs, since match_ingredient() works much better against a bare
    name ("sage") than against the whole line.
  - Image_Name is a filename slug with NO extension and no actual image file
    included in the CSV -- you need the matching Kaggle "Images/" folder too.
    Copy those files into icc_frontend/public/images/imported/<slug>.jpg and
    this script points image_url at /images/imported/<slug>.jpg. ~30 rows in
    the CSV have Image_Name == "#NAME?" (an Excel artifact baked into the
    source file) or are blank -- those fall back to DEFAULT_IMAGE instead.

Only ~20% of ingredient lines will fuzzy-match the current 112-item taxonomy
(measured on the real CSV) -- it's Sri-Lankan-specific and this is a global
dataset. That's expected, not a bug: unmatched ingredients keep their raw
name/quantity/unit (so the recipe still displays correctly) but get
ingredient_id=None, so pantry-matching/substitutions won't work for them
until you expand the taxonomy. This script prints the most common unmatched
names at the end so you know exactly what to add first.
"""
import argparse
import ast
import csv
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.recipe import Recipe, RecipeIngredient, RecipeStep
from app.services.ingredient_matching import load_ingredient_index, match_ingredient

DEFAULT_IMAGE = "/images/categories/default.jpg"  # same catch-all as ingest_recipes.py
IMAGE_BASE_PATH = "/images/imported"

# -- free-text ingredient-line parsing --------------------------------------

FRACTION_MAP = {"¼": 0.25, "½": 0.5, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3,
                "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875}

UNIT_WORDS = {
    "tsp", "teaspoon", "teaspoons", "tbsp", "tablespoon", "tablespoons",
    "cup", "cups", "oz", "ounce", "ounces", "lb", "lbs", "pound", "pounds",
    "g", "gram", "grams", "kg", "kilogram", "kilograms",
    "ml", "milliliter", "milliliters", "l", "liter", "liters",
    "pinch", "pinches", "clove", "cloves", "sprig", "sprigs",
    "slice", "slices", "can", "cans", "stick", "sticks",
    "bunch", "bunches", "quart", "quarts", "pint", "pints", "dash", "dashes",
}

QTY_RE = re.compile(
    r"^("
    r"\d+\s+\d+/\d+"                                          # "1 1/2"
    r"|\d+/\d+"                                                # "1/4"
    r"|[\d¼½¾⅓⅔⅛⅜⅝⅞]+(?:[\-\u2013]\s*[\d¼½¾⅓⅔⅛⅜⅝⅞]+)?"       # "2", "2¾", "3½–4"
    r")\s*"
)


def parse_number(s: str) -> float | None:
    s = s.strip()

    m = re.match(r"^(\d+)\s+(\d+)/(\d+)$", s)  # mixed ascii fraction, e.g. "1 1/2"
    if m:
        whole, num, den = m.groups()
        return float(whole) + float(num) / float(den)

    m = re.match(r"^(\d+)/(\d+)$", s)  # plain ascii fraction, e.g. "1/4"
    if m:
        num, den = m.groups()
        return float(num) / float(den) if float(den) != 0 else None

    total, matched = 0.0, False
    for ch, val in FRACTION_MAP.items():
        if ch in s:
            total += val
            s = s.replace(ch, "")
            matched = True
    s = s.strip()
    if s:
        try:
            total += float(s)
            matched = True
        except ValueError:
            pass
    return total if matched else None


def parse_ingredient(raw: str) -> tuple[float | None, str | None, str, str | None]:
    """'2¾ tsp. kosher salt, divided, plus more' -> (2.75, 'tsp', 'kosher salt', 'divided, plus more')"""
    text = raw.strip()

    qty_match = QTY_RE.match(text)
    quantity, rest = None, text
    if qty_match:
        first_num = re.split(r"[\-\u2013]", qty_match.group(1))[0].strip()
        quantity = parse_number(first_num)
        rest = text[qty_match.end():].strip()

    rest = re.sub(r"^\([^)]*\)\s*", "", rest)  # drop a leading parenthetical like "(3½–4-lb.)"

    unit = None
    tokens = rest.split(" ", 1)
    if tokens:
        first_tok = tokens[0].strip(".").lower()
        if first_tok in UNIT_WORDS:
            unit = tokens[0].strip(".")
            rest = tokens[1] if len(tokens) > 1 else ""
            if rest.lower().startswith("of "):
                rest = rest[3:]

    if "," in rest:
        name, notes = rest.split(",", 1)
        name, notes = name.strip(), notes.strip()
    else:
        name, notes = rest.strip(), None

    name_clean = re.sub(r"\([^)]*\)", "", name).strip()
    if name_clean:
        name = name_clean

    return quantity, unit, (name or rest.strip() or raw), notes


def parse_list_field(value: str) -> list[str]:
    """Ingredients/Cleaned_Ingredients are stored as Python-list literals, e.g.
    "['1 cup flour', '2 eggs']" -- ast.literal_eval, not json, since they use
    single quotes and aren't valid JSON."""
    try:
        result = ast.literal_eval(value)
        return result if isinstance(result, list) else []
    except (ValueError, SyntaxError):
        return []


def image_url_for(image_name: str) -> str:
    name = (image_name or "").strip()
    if not name or name.startswith("#"):
        return DEFAULT_IMAGE
    return f"{IMAGE_BASE_PATH}/{name}.jpg"


def has_valid_image_name(image_name: str) -> bool:
    name = (image_name or "").strip()
    return bool(name) and not name.startswith("#")


def import_epicurious(csv_path: str, limit: int | None, only_with_image: bool = False):
    db = SessionLocal()
    ing_index = load_ingredient_index(db)
    unmatched_counter: Counter[str] = Counter()

    inserted, skipped, skipped_no_image = 0, 0, 0
    total_ing_lines, matched_ing_lines = 0, 0

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if limit is not None and inserted >= limit:
                    break

                title = (row.get("Title") or "").strip()
                ingredients_raw = (row.get("Cleaned_Ingredients") or row.get("Ingredients") or "").strip()
                instructions_raw = (row.get("Instructions") or "").strip()
                if not title or not ingredients_raw or ingredients_raw == "[]" or not instructions_raw:
                    skipped += 1
                    continue

                if only_with_image and not has_valid_image_name(row.get("Image_Name", "")):
                    skipped_no_image += 1
                    continue

                recipe_id = f"ep_{row.get('', '').strip() or inserted}"

                db.query(Recipe).filter(Recipe.id == recipe_id).delete()

                recipe = Recipe(
                    id=recipe_id,
                    name_en=title,
                    name_native=None,
                    cuisine="International",  # not present in this dataset -- explicit placeholder, not a guess per-recipe
                    regional_origin=None,
                    course=None,              # not present -- left honestly NULL rather than guessed
                    servings=None,            # not present -- left honestly NULL
                    prep_time_min=None,
                    cook_time_min=None,
                    total_time_min=None,
                    tags=[],
                    ayurvedic_balance=None,
                    image_url=image_url_for(row.get("Image_Name", "")),
                    calories_kcal=None, protein_g=None, carbs_g=None, fat_g=None, fibre_g=None,
                    trust_score=0.5,          # imported, not hand-curated -- below SL-Cook100's 0.9 default
                    source_type="imported",
                    moderation_status="approved",
                    source_site="Epicurious (via Kaggle CSV)",
                    collection_method="kaggle_csv_import",
                    notes=None,
                )
                db.add(recipe)

                for idx, raw_line in enumerate(parse_list_field(ingredients_raw)):
                    quantity, unit, name, notes = parse_ingredient(raw_line)
                    total_ing_lines += 1
                    ingredient_id = match_ingredient(name, ing_index)
                    if ingredient_id:
                        matched_ing_lines += 1
                    else:
                        unmatched_counter[name.lower()] += 1

                    db.add(RecipeIngredient(
                        recipe_id=recipe_id,
                        ingredient_id=ingredient_id,
                        raw_name=name,
                        quantity=quantity,
                        unit=unit,
                        notes=notes,
                        position=idx,
                    ))

                steps = [s.strip() for s in instructions_raw.split("\n") if s.strip()]
                for step_number, instruction in enumerate(steps, start=1):
                    db.add(RecipeStep(
                        recipe_id=recipe_id,
                        step_number=step_number,
                        instruction=instruction,
                        duration_min=None,
                    ))

                inserted += 1

        db.commit()
        print(f"Imported {inserted} recipes ({skipped} skipped: missing title/ingredients/instructions)")
        if only_with_image:
            print(f"Skipped {skipped_no_image} more for --only-with-image (blank or '#NAME?' Image_Name)")
        if total_ing_lines:
            pct = matched_ing_lines / total_ing_lines * 100
            print(f"Ingredient matching: {matched_ing_lines}/{total_ing_lines} lines matched the taxonomy ({pct:.1f}%)")
        print("\nMost common UNMATCHED ingredient names (best candidates to add to the taxonomy next):")
        for name, count in unmatched_counter.most_common(30):
            print(f"  {count:5d}  {name}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", required=True, help="Path to the Kaggle Epicurious CSV")
    parser.add_argument("--limit", type=int, default=None, help="Only import the first N usable rows (recommended for a first test run)")
    parser.add_argument("--only-with-image", action="store_true",
                         help="Skip rows with a blank or '#NAME?' Image_Name, so every imported recipe has a real photo slug (guarantees --limit rows all get an image instead of some falling back to default.jpg)")
    args = parser.parse_args()
    import_epicurious(args.csv, args.limit, args.only_with_image)
