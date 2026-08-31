"""
Keeps recipes.average_rating / recipes.review_count in sync with the reviews table.

These are denormalised onto the recipe row (rather than computed with a JOIN + AVG on
every request) because average_rating is worth showing on the /results list card, which
already does real work per candidate in RB-02/RB-05 -- one extra aggregate query per
recipe per list request isn't worth it. Call recompute() inside the same transaction
right after any review create/update/delete.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.community import Review
from app.models.recipe import Recipe


def recompute(db: Session, recipe_id: str) -> None:
    avg, count = (
        db.query(func.avg(Review.rating), func.count(Review.id))
        .filter(Review.recipe_id == recipe_id)
        .one()
    )
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        return
    recipe.average_rating = round(float(avg), 1) if avg is not None else None
    recipe.review_count = count or 0
