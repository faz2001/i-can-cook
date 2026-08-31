"""
RB-02 -- Pantry Matching & Ingredient Availability.

Performs a set-difference between a recipe's ingredient requirements and the user's
pantry inventory, flagging each recipe ingredient as one of:
  - "have"          canonical match found in pantry, quantity sufficient (or no qty on either side to compare)
  - "partial"       canonical match found, pantry quantity is comparable to what the recipe
                     needs (same unit, or a known conversion), and it's below that amount
  - "missing"       canonical match found in the taxonomy, but nothing in the user's pantry
  - "unit_mismatch" canonical match found and the user has *some* of it, but the pantry unit
                     and the recipe unit can't be reconciled (e.g. pantry logged in kg, recipe
                     wants a count like "4 medium" onions, and no conversion is known) -- we
                     do NOT compare the raw numbers in that case, since e.g. "1 kg" >= "4"
                     is not a meaningful comparison and was previously reported as "partial,
                     need 3 more" even when 1kg is actually several times more onion by weight
                     than 4 medium onions. See _comparable_amount() below.
  - "unmatched"      the recipe ingredient has no canonical ingredient_id at all (can't be checked --
                      typically an imported recipe whose ingredient text didn't fuzzy-match during ETL)
"""
import math
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.pantry import PantryItem
from app.models.recipe import RecipeIngredient

# Ingredient-independent physical conversions (all lowercase unit strings).
_WEIGHT_TO_GRAMS: dict[str, float] = {"g": 1.0, "kg": 1000.0, "oz": 28.3495, "lb": 453.592}
_VOLUME_TO_ML: dict[str, float] = {
    "ml": 1.0, "l": 1000.0, "cup": 240.0, "cups": 240.0,
    "tbsp": 15.0, "tsp": 5.0, "fl_oz": 29.5735,
}
# Unit words that mean "some number of discrete items" rather than a weight or
# volume. Recipe/pantry data in this app uses these interchangeably with
# size-qualified words (see the unit vocabulary actually present in
# data_sl_cook100/*.json: clove, cloves, cm, count, cup, cups, g, medium, ml,
# pinch, tbsp, tsp). "cm" and "pinch" are deliberately excluded -- neither
# maps to a reliable weight, so they stay unconvertible (unit_mismatch) rather
# than guessed at.
_COUNT_UNIT_WORDS = {"count", "each", "medium", "small", "large", "clove", "cloves"}

# Approximate grams for one unit of a count-style measurement, per ingredient.
# Matched by substring against ingredient_id (same pattern rb03_scaling.py
# uses for its damping markers). This is what makes "1 kg onions" satisfy
# "4 medium onions" instead of comparing 1 >= 4 directly. Extend as more
# ingredients turn out to need count<->weight comparisons; anything not
# listed here simply can't be converted and falls through to
# "unit_mismatch" -- an honest "can't tell" rather than a wrong "partial".
_COUNT_GRAMS_PER_INGREDIENT: dict[str, dict[str, float]] = {
    "onion":  {"small": 110, "medium": 150, "large": 200, "count": 150},
    "tomato": {"small": 90,  "medium": 150, "large": 200, "count": 150},
    "garlic": {"clove": 5,   "cloves": 5,   "count": 5},
    "egg":    {"small": 43,  "medium": 50,  "large": 58,  "count": 50},
    "potato": {"small": 100, "medium": 170, "large": 300, "count": 170},
    "lemon":  {"small": 60,  "medium": 80,  "large": 100, "count": 80},
    "lime":   {"small": 45,  "medium": 60,  "large": 75,  "count": 60},
    "carrot": {"small": 40,  "medium": 60,  "large": 90,  "count": 60},
    "apple":  {"small": 130, "medium": 180, "large": 220, "count": 180},
    "banana": {"small": 100, "medium": 120, "large": 150, "count": 120},
}


@dataclass
class IngredientAvailability:
    recipe_ingredient: RecipeIngredient
    status: str                       # "have" | "partial" | "missing" | "unit_mismatch" | "unmatched"
    pantry_quantity_available: float | None


def _count_grams(ingredient_id: str, unit: str) -> float | None:
    for marker, sizes in _COUNT_GRAMS_PER_INGREDIENT.items():
        if marker in ingredient_id:
            return sizes.get(unit, sizes.get("count"))
    return None


def _to_grams(ingredient_id: str, quantity: float, unit: str) -> float | None:
    if unit in _WEIGHT_TO_GRAMS:
        return quantity * _WEIGHT_TO_GRAMS[unit]
    if unit in _COUNT_UNIT_WORDS:
        per_unit = _count_grams(ingredient_id, unit)
        return quantity * per_unit if per_unit is not None else None
    return None


def _to_ml(quantity: float, unit: str) -> float | None:
    if unit in _VOLUME_TO_ML:
        return quantity * _VOLUME_TO_ML[unit]
    return None


def _comparable_amount(ingredient_id: str, have_qty: float, have_unit: str | None, need_unit: str | None) -> float | None:
    """Converts have_qty (in have_unit) into an amount expressed in need_unit's
    terms, so it can be compared/summed directly against the recipe's required
    quantity. Returns None if the two units can't be reconciled -- callers
    must NOT fall back to comparing the raw numbers in that case, since that's
    exactly the bug this replaces (e.g. comparing "1" of kg against "4" of
    medium-onions as if they were the same unit)."""
    hu = (have_unit or "").strip().lower()
    nu = (need_unit or "").strip().lower()
    if not hu or not nu:
        return None
    if hu == nu:
        return have_qty

    have_g = _to_grams(ingredient_id, have_qty, hu)
    need_one_g = _to_grams(ingredient_id, 1.0, nu)
    if have_g is not None and need_one_g:
        return have_g / need_one_g

    have_ml = _to_ml(have_qty, hu)
    need_one_ml = _to_ml(1.0, nu)
    if have_ml is not None and need_one_ml:
        return have_ml / need_one_ml

    return None


def match_pantry(db: Session, user_id: int, recipe_ingredients: list[RecipeIngredient]) -> list[IngredientAvailability]:
    # Keep each pantry entry's own unit rather than summing raw numbers across
    # entries -- a user could have "2 medium" onions and separately "1 kg"
    # onions logged, and those can't be added together without converting
    # first (that was also part of the original bug: the old version summed
    # quantity regardless of unit).
    pantry_by_ingredient: dict[str, list[tuple[float, str | None]]] = {}
    for item in db.query(PantryItem).filter(PantryItem.user_id == user_id).all():
        if item.ingredient_id is None:
            continue
        qty = float(item.quantity) if item.quantity is not None else math.inf
        pantry_by_ingredient.setdefault(item.ingredient_id, []).append((qty, item.unit))

    results = []
    for ri in recipe_ingredients:
        if ri.ingredient_id is None:
            results.append(IngredientAvailability(ri, "unmatched", None))
            continue

        entries = pantry_by_ingredient.get(ri.ingredient_id)
        if not entries:
            results.append(IngredientAvailability(ri, "missing", None))
            continue

        has_unspecified_qty = any(q == math.inf for q, _ in entries)
        display_qty = math.inf if has_unspecified_qty else sum(q for q, _ in entries)

        if ri.quantity is None or has_unspecified_qty:
            # No quantity specified on the recipe side, or at least one pantry
            # entry has no logged quantity at all ("I have some, didn't say
            # how much") -- nothing meaningful to compare against, so presence
            # is treated as sufficient, same as the pre-existing behaviour.
            results.append(IngredientAvailability(ri, "have", None if display_qty == math.inf else display_qty))
            continue

        comparable_total = 0.0
        saw_comparable = False
        for qty, unit in entries:
            amount = _comparable_amount(ri.ingredient_id, qty, unit, ri.unit)
            if amount is not None:
                saw_comparable = True
                comparable_total += amount

        if not saw_comparable:
            # Every pantry entry's unit is incompatible with the recipe's unit
            # and no conversion is known -- report honestly rather than
            # comparing raw numbers across different units.
            results.append(IngredientAvailability(ri, "unit_mismatch", display_qty))
        elif comparable_total >= float(ri.quantity):
            results.append(IngredientAvailability(ri, "have", display_qty))
        else:
            results.append(IngredientAvailability(ri, "partial", display_qty))

    return results


def availability_summary(availabilities: list[IngredientAvailability]) -> dict:
    """Rolls a per-ingredient breakdown up into the summary stats /results needs per recipe card."""
    total = len(availabilities) or 1
    have = sum(1 for a in availabilities if a.status == "have")
    partial = sum(1 for a in availabilities if a.status == "partial")
    missing = sum(1 for a in availabilities if a.status == "missing")
    unmatched = sum(1 for a in availabilities if a.status == "unmatched")
    unit_mismatch = sum(1 for a in availabilities if a.status == "unit_mismatch")

    # Partial counts as half-available for the summary percentage shown on the recipe card.
    # unit_mismatch does NOT count towards the numerator -- we genuinely don't know if
    # there's enough, so treating it as anything but "unknown" would just move the same
    # silent-guess problem into the summary stats instead of the per-ingredient status.
    pct = ((have + 0.5 * partial) / total) * 100
    return {
        "pantry_availability_pct": round(pct, 1),
        "missing_count": missing,
        "unmatched_count": unmatched,
        "unit_mismatch_count": unit_mismatch,
    }