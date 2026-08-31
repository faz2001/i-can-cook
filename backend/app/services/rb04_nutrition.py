"""
RB-04 -- Nutrition Analysis Module.

Per your proposal, this module "computes per-serving macronutrient totals by aggregating
ingredient nutritional values ... multiplied by scaled quantities." Full ingredient-level
aggregation needs a per-ingredient nutrition reference table (USDA FoodData Central /
Sri Lanka FCDB, both already listed in your Resources Required table) which isn't built
yet -- that's the natural next piece of backend work after this.

Until that table exists, this module works off the per-serving nutrition figures already
stored directly on curated SL-Cook100 recipes (hand-annotated from source recipes) and
returns `available=False` for imported recipes that don't have one. That's an honest gap
to flag in your dissertation's limitations section, not something to fake with made-up
numbers.

The Health Score is a simple, clearly-labelled heuristic (protein and fibre density,
lightly penalised by fat share of calories) -- treat it as a v1 placeholder to refine
with a nutritionist-reviewed formula, not a validated clinical score.
"""
from app.models.recipe import Recipe


def get_nutrition(recipe: Recipe) -> dict:
    available = recipe.calories_kcal is not None
    return {
        "calories": float(recipe.calories_kcal) if available else None,
        "protein_g": float(recipe.protein_g) if recipe.protein_g is not None else None,
        "carbs_g": float(recipe.carbs_g) if recipe.carbs_g is not None else None,
        "fat_g": float(recipe.fat_g) if recipe.fat_g is not None else None,
        "fibre_g": float(recipe.fibre_g) if recipe.fibre_g is not None else None,
        "per": "serving",
        "available": available,
    }


def compute_health_score(recipe: Recipe) -> float | None:
    """0-100 heuristic. None when nutrition data isn't available for this recipe."""
    if recipe.calories_kcal is None or float(recipe.calories_kcal) <= 0:
        return None

    calories = float(recipe.calories_kcal)
    protein = float(recipe.protein_g or 0)
    fibre = float(recipe.fibre_g or 0)
    fat = float(recipe.fat_g or 0)

    protein_density = min(protein / calories * 400, 40)   # protein calories share, capped
    fibre_score = min(fibre * 4, 20)                        # up to 20 points for fibre
    fat_calories_share = (fat * 9) / calories
    fat_penalty = max(0, (fat_calories_share - 0.35) * 60)  # penalise once fat exceeds ~35% of calories

    score = 50 + protein_density + fibre_score - fat_penalty
    return round(max(0, min(100, score)), 1)
