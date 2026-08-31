from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.models.favorite import Favorite
from app.models.recipe import Recipe
from app.schemas.favorite import FavoriteOut

router = APIRouter(tags=["favorites"])


@router.post("/api/recipes/{recipe_id}/favorite", response_model=FavoriteOut, status_code=201)
def add_favorite(
    recipe_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    existing = db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.recipe_id == recipe_id).first()
    if existing:
        # Idempotent: favoriting an already-favorited recipe just returns
        # the existing row rather than erroring, since from the frontend's
        # perspective the desired end state ("this is favorited") is met.
        existing.recipe = recipe
        return existing

    fav = Favorite(user_id=user_id, recipe_id=recipe_id)
    db.add(fav)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Race: another request favorited it between our check and insert.
        existing = db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.recipe_id == recipe_id).first()
        existing.recipe = recipe
        return existing

    db.refresh(fav)
    fav.recipe = recipe
    return fav


@router.delete("/api/recipes/{recipe_id}/favorite", status_code=204)
def remove_favorite(
    recipe_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    fav = db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.recipe_id == recipe_id).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(fav)
    db.commit()
    return None


@router.get("/api/favorites", response_model=list[FavoriteOut])
def list_favorites(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    favs = (
        db.query(Favorite)
        .filter(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    # Attach recipe summaries in one extra query rather than N+1.
    recipe_ids = [f.recipe_id for f in favs]
    recipes_by_id = {
        r.id: r for r in db.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()
    } if recipe_ids else {}
    for f in favs:
        f.recipe = recipes_by_id.get(f.recipe_id)
    return favs
