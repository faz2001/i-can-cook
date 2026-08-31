"""
Bridges the pantry router's expiry-date design to the real trained ML-02
regressor (app/services/shelf_life.py).

The model now predicts remaining days directly (see shelf_life.py's
docstring for the log-target R^2 / MAE figures and why they matter), so
this no longer needs the old classifier-vs-lookup-table disagreement logic
-- the regressor's own output is the expiry estimate. The lookup table is
kept only as a fallback for the cases the model can't handle at all: no
canonical ingredient matched, or no category on the matched ingredient.

`predict_shelf_life` keeps the exact signature the pantry router already
calls, so this is a drop-in replacement -- nothing in pantry.py needs to
change beyond its import path. (It now also passes `ingredient.name` through
to the regressor, since that model accepts an ingredient_name feature --
see app/services/shelf_life.py for whether the currently-loaded model
actually uses it.)
"""
from datetime import date, timedelta

from app.models.ingredient import Ingredient
from app.services.shelf_life import predict_shelf_life as _predict_days

# {category: {storage_condition: shelf_life_days}} -- fallback only, used
# when there's no canonical ingredient/category to hand the model at all.
# Storage conditions match VALID_STORAGE_CONDITIONS in app/schemas/pantry.py.
_SHELF_LIFE_DAYS: dict[str, dict[str, int]] = {
    "Grains":          {"Pantry": 365, "Refrigerated": 180, "Frozen": 720},
    "Legumes":         {"Pantry": 180, "Refrigerated": 120, "Frozen": 365},
    "Vegetables":      {"Pantry": 5,   "Refrigerated": 10,  "Frozen": 180},
    "Greens":          {"Pantry": 2,   "Refrigerated": 4,   "Frozen": 90},
    "Fruits":          {"Pantry": 5,   "Refrigerated": 10,  "Frozen": 180},
    "Meat":            {"Pantry": 1,   "Refrigerated": 2,   "Frozen": 180},
    "Seafood":         {"Pantry": 1,   "Refrigerated": 1,   "Frozen": 90},
    "Dairy":           {"Pantry": 1,   "Refrigerated": 7,   "Frozen": 60},
    "Dairy-alt":       {"Pantry": 30,  "Refrigerated": 4,   "Frozen": 60},
    "Spices":          {"Pantry": 365},
    "Aromatics":       {"Pantry": 7,   "Refrigerated": 14},
    "Herbs":           {"Pantry": 2,   "Refrigerated": 5},
    "Souring agents":  {"Pantry": 180},
    "Seasonings":      {"Pantry": 730},
    "Sweeteners":      {"Pantry": 365},
    "Flours":          {"Pantry": 180, "Refrigerated": 180, "Frozen": 365},
    "Nuts":            {"Pantry": 180, "Refrigerated": 365, "Frozen": 730},
    "Seeds":           {"Pantry": 365},
    "Condiments":      {"Pantry": 365, "Refrigerated": 180},
    "Wrapping leaves": {"Pantry": 2,   "Refrigerated": 7,   "Frozen": 90},
    "Leavening":       {"Pantry": 365},
    "Dried fruits":    {"Pantry": 180},
    "Flavorings":      {"Pantry": 365},
    "Thickeners":      {"Pantry": 365},
    "Coatings":        {"Pantry": 180},
    "Oils":            {"Pantry": 365, "Refrigerated": 365},
}
_FALLBACK_DAYS: dict[str, int] = {"Pantry": 14, "Refrigerated": 7, "Frozen": 90}

# The regressor in shelf_life.py was trained on ml02_shelf_life_train_enriched.csv,
# whose `category` column uses USDA-FoodKeeper-style labels ("Produce",
# "Common Foods", "Pantry/Dry Goods", "Grains, Beans & Pasta", "Meat/Seafood",
# "Dairy Products & Eggs", etc). The app's live ingredient catalog uses a
# different taxonomy entirely (the keys of _SHELF_LIFE_DAYS above, e.g.
# "Vegetables", "Fruits", "Dairy", "Herbs"). Only "Meat" and "Seafood" happen
# to match the training vocabulary verbatim. The model's OneHotEncoder was
# built with handle_unknown='ignore', so passing any of the other 24 app
# categories straight through doesn't error -- it silently zeroes out the
# category feature and the model falls back to predicting off
# storage_condition + subcategory="Unknown" alone, identically for every
# unmapped category (verified: "Vegetables", "Fruits", "Dairy", "Herbs", and
# even a nonsense string all produced the same 119.5/12.2/174.9-day
# Pantry/Refrigerated/Frozen prediction). This table translates the app's
# category into the closest training-vocabulary category so the model
# actually sees a category it learned from. Do not delete this as "unused" --
# it's the fix for that taxonomy mismatch, not incidental scaffolding.
APP_CATEGORY_TO_TRAINING_CATEGORY: dict[str, str | None] = {
    "Grains":          "Grains, Beans & Pasta",
    "Legumes":         "Grains, Beans & Pasta",
    "Vegetables":      "Produce",
    "Greens":          "Produce",
    "Fruits":          "Produce",
    "Meat":            "Meat",
    "Seafood":         "Seafood",
    "Dairy":           "Dairy Products & Eggs",
    "Dairy-alt":       "Dairy Products & Eggs",
    "Spices":          "Pantry/Dry Goods",
    "Aromatics":       "Produce",
    "Herbs":           "Produce",
    "Souring agents":  "Condiments, Sauces & Canned Goods",
    "Seasonings":      "Pantry/Dry Goods",
    "Sweeteners":      "Pantry/Dry Goods",
    "Flours":          "Pantry/Dry Goods",
    "Nuts":            "Pantry/Dry Goods",
    "Seeds":           "Pantry/Dry Goods",
    "Condiments":      "Condiments, Sauces & Canned Goods",
    "Wrapping leaves": None,  # no reasonable training-vocabulary match
    "Leavening":       "Pantry/Dry Goods",
    "Dried fruits":    "Pantry/Dry Goods",
    "Flavorings":      "Condiments, Sauces & Canned Goods",
    "Thickeners":      "Pantry/Dry Goods",
    "Coatings":        "Pantry/Dry Goods",
    "Oils":            "Condiments, Sauces & Canned Goods",
}


def predict_shelf_life(ingredient: Ingredient | None, storage_condition: str, purchase_date: date) -> date:
    category = ingredient.category if ingredient else None

    if ingredient is None or not category:
        # No canonical ingredient matched -- the model needs a category to
        # predict against, so fall back to the table's fallback bucket.
        table_days = _FALLBACK_DAYS.get(storage_condition, 14)
        return purchase_date + timedelta(days=table_days)

    # Translate into the model's training vocabulary (see
    # APP_CATEGORY_TO_TRAINING_CATEGORY above). If there's no entry, or the
    # entry is explicitly None (no reasonable semantic match), don't call the
    # model with a category it can't interpret -- use the lookup table instead.
    training_category = APP_CATEGORY_TO_TRAINING_CATEGORY.get(category)
    if not training_category:
        category_table = _SHELF_LIFE_DAYS.get(category, {})
        table_days = category_table.get(storage_condition) or _FALLBACK_DAYS.get(storage_condition, 14)
        return purchase_date + timedelta(days=table_days)

    try:
        result = _predict_days(training_category, None, storage_condition, ingredient.name)
        return purchase_date + timedelta(days=result["predicted_days"])
    except ValueError:
        # storage_condition the model wasn't trained on -- fall back to the table.
        category_table = _SHELF_LIFE_DAYS.get(category, {})
        table_days = category_table.get(storage_condition) or _FALLBACK_DAYS.get(storage_condition, 14)
        return purchase_date + timedelta(days=table_days)