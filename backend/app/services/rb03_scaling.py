"""
RB-03 -- Recipe Scaling Engine.

Adjusts all ingredient quantities proportionally for a user-specified serving count. A
damping factor is applied to salt and chilli quantities at larger scales, per your
proposal, to prevent over-seasoning -- doubling a curry for 8 people shouldn't double the
salt, since seasoning doesn't scale linearly with mass the way most ingredients do.
"""
from app.models.recipe import Recipe, RecipeIngredient

# canonical_id substrings that get damped rather than scaled linearly. Matched by
# substring so both 'ing_salt' and any future 'ing_salt_flaky' style id are caught.
_DAMPED_INGREDIENT_MARKERS = ("salt", "chilli", "chili", "pepper")
_DAMPING_EXPONENT = 0.7   # scaled_qty = base_qty * factor ** 0.7 instead of factor ** 1.0


def scale_factor(recipe: Recipe, requested_servings: int) -> float:
    if not recipe.servings or recipe.servings <= 0:
        return 1.0
    return requested_servings / recipe.servings


def scale_ingredients(recipe_ingredients: list[RecipeIngredient], factor: float) -> dict[int, float | None]:
    """Returns {recipe_ingredient.id: scaled_quantity}. Quantity is None when the source
    ingredient had no quantity to begin with (e.g. 'salt to taste' style entries)."""
    scaled: dict[int, float | None] = {}
    for ri in recipe_ingredients:
        if ri.quantity is None:
            scaled[ri.id] = None
            continue

        is_damped = ri.ingredient_id is not None and any(m in ri.ingredient_id for m in _DAMPED_INGREDIENT_MARKERS)
        effective_factor = factor ** _DAMPING_EXPONENT if is_damped else factor
        scaled[ri.id] = round(float(ri.quantity) * effective_factor, 3)
    return scaled
