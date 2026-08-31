"""
ML-01 recommendation scoring (proposal 4.2): "These structured features are
then compared against recipe metadata to calculate a recommendation score
based on ingredient similarity, meal type match, spice level match, and
pantry availability. The top-N ranked recipes are returned to the user."

Queries the real `recipes` table (approved recipes only) instead of the
original SL-Cook100 JSON files -- same scoring logic, real data source.
"""
from sqlalchemy.orm import Session, selectinload

from app.models.recipe import Recipe


def load_recipes(db: Session) -> list[Recipe]:
    return (
        db.query(Recipe)
        .filter(Recipe.moderation_status == "approved")
        .options(selectinload(Recipe.ingredients))
        .all()
    )


def _recipe_tag_set(recipe: Recipe) -> set:
    tags = set(t.lower() for t in (recipe.tags or []))
    if recipe.course:
        tags.add(recipe.course.lower())
    if recipe.cuisine:
        tags.add(recipe.cuisine.lower())
    return tags


def score_recipe(recipe: Recipe, intent_tags: dict, pantry_ingredient_ids: set | None = None) -> float:
    """
    Weighted score, roughly matching proposal 4.2's four factors:
      - meal type match       (weight 2)
      - spice level match     (weight 1.5)
      - dietary/cuisine/etc.  (weight 1 each, from remaining categories)
      - pantry availability   (weight 1, only if pantry provided)
    """
    recipe_tags = _recipe_tag_set(recipe)
    score = 0.0

    weights = {
        "meal_type": 2.0,
        "spice_level": 1.5,
        "dietary": 1.0,
        "cooking_constraint": 1.0,
        "occasion": 1.0,
        "cuisine": 1.0,
    }

    for category, wanted_tags in intent_tags.items():
        w = weights.get(category, 1.0)
        for tag in wanted_tags:
            if tag in recipe_tags or tag.replace("-", " ") in recipe_tags:
                score += w
            # "mild" isn't a real dataset tag -- treat as "not tagged spicy"
            if tag == "mild" and "spicy" not in recipe_tags and "very-spicy" not in recipe_tags:
                score += w

    if pantry_ingredient_ids:
        recipe_ids = {ri.ingredient_id for ri in recipe.ingredients if ri.ingredient_id}
        overlap = recipe_ids & pantry_ingredient_ids
        score += len(overlap) * 0.5

    return score


def recommend(intent_tags: dict, recipes: list[Recipe], pantry_ingredient_ids: set | None = None, top_n: int = 5):
    scored = [
        (score_recipe(r, intent_tags, pantry_ingredient_ids), r)
        for r in recipes
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_n]
