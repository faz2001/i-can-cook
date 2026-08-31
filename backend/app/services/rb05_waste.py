"""
RB-05 -- Zero-Waste Prioritisation.

Re-ranks candidate recipes using an urgency-weighted score that rewards consumption of
near-expiry pantry ingredients. In this backend-first pass, urgency is computed straight
from `pantry_items.expiry_date` (either a label date or a manually-entered estimate) --
once ML-02 (the Gradient Boosting shelf-life predictor) is wired into pantry item
creation, its predicted expiry dates land in the same column and this module needs no
changes.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.models.pantry import PantryItem
from app.services.rb02_pantry import IngredientAvailability

HIGH_URGENCY_DAYS = 3
MEDIUM_URGENCY_DAYS = 7


def urgency_level_for_days(days_to_expiry: int) -> str:
    """Shared classification so pantry list badges and recipe re-ranking agree on what
    counts as 'high'/'medium'/'low' urgency -- used directly by app/routers/pantry.py."""
    if days_to_expiry <= HIGH_URGENCY_DAYS:
        return "high"
    if days_to_expiry <= MEDIUM_URGENCY_DAYS:
        return "medium"
    return "low"


def compute_expiry_urgency(db: Session, user_id: int, availabilities: list[IngredientAvailability]) -> tuple[str | None, float]:
    """Returns (urgency_level, urgency_boost) for a single recipe, based on how soon the
    pantry ingredients it would actually use are due to expire. urgency_boost is added
    into the recipe's overall ranking score by the recommendations router."""
    matched_ingredient_ids = {
        a.recipe_ingredient.ingredient_id
        for a in availabilities
        if a.status in ("have", "partial") and a.recipe_ingredient.ingredient_id is not None
    }
    if not matched_ingredient_ids:
        return None, 0.0

    today = date.today()
    relevant_items = (
        db.query(PantryItem)
        .filter(PantryItem.user_id == user_id)
        .filter(PantryItem.ingredient_id.in_(matched_ingredient_ids))
        .filter(PantryItem.expiry_date.isnot(None))
        .all()
    )
    if not relevant_items:
        return None, 0.0

    min_days_to_expiry = min((item.expiry_date - today).days for item in relevant_items)
    level = urgency_level_for_days(min_days_to_expiry)
    boost = {"high": 1.0, "medium": 0.5, "low": 0.1}[level]
    return level, boost
