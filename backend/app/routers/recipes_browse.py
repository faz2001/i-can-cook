"""
Public recipe browse/search list -- ADDITIVE module, not part of the original
backend drop.

Why this exists: the original backend only exposes GET /api/recipes/{id}
(single recipe by id) and POST /api/recipes (community submission). There is
no way for a logged-in, non-admin user to ask "what recipes exist" -- the
only list endpoint (admin_recipes.list_recipes) sits behind require_admin.
The given frontend's Home feed, Explore/search grid, and Cook picker all
need exactly this: a public, paginated, searchable list of approved
recipes. Without it those screens have no data to render.

This file only *adds* a new route; it does not modify any existing file's
behavior. Mounted at the same "/api/recipes" prefix as recipes.py -- FastAPI
dispatches "GET /api/recipes" (this router) and "GET /api/recipes/{id}"
(recipes.py) as distinct routes, so there's no collision or ordering
requirement the way zero_waste.py has with recipes.py's catch-all.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.recipe import Recipe
from app.schemas.recipe_browse import RecipeFacetsOut, RecipeListItemOut, RecipeListOut

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

# sort_by -> ORDER BY clauses. NULLs (e.g. average_rating with no reviews
# yet, total_time_min not recorded) sort last for every option so an
# incomplete row never floats to the top just because a column is empty.
_SORT_OPTIONS: dict[str, list] = {
    "relevance": [Recipe.trust_score.desc(), Recipe.review_count.desc()],
    "rating": [Recipe.average_rating.desc().nulls_last(), Recipe.review_count.desc()],
    "newest": [Recipe.created_at.desc()],
    "quickest": [Recipe.total_time_min.asc().nulls_last()],
}


@router.get("/facets", response_model=RecipeFacetsOut)
def list_facets(db: Session = Depends(get_db)):
    """Distinct, live filter values for the Explore/Discovery UI (course
    chips, cuisine dropdown).

    This intentionally reads straight from the `recipes` table instead of
    a pre-generated file: a static snapshot (e.g. the 99-row SL-Cook100
    extract the frontend used to ship as `CATALOG`) only ever lists the
    values that existed at snapshot time, so any cuisine/course introduced
    by later imports (bulk "International" imports, community submissions,
    etc.) would silently never appear as a filter option even though rows
    with that value are sitting right there in the table. Querying live
    means new values show up automatically, no regeneration step needed.

    Registered before the plain "" route in this file purely by convention
    (route ordering doesn't matter here since "/facets" and "" are distinct
    paths, unlike the "/{id}" catch-all in recipes.py).
    """
    approved = db.query(Recipe).filter(Recipe.moderation_status == "approved")

    courses = [
        row[0]
        for row in approved.with_entities(distinct(Recipe.course))
        .filter(Recipe.course.isnot(None))
        .order_by(Recipe.course)
        .all()
    ]
    cuisines = [
        row[0]
        for row in approved.with_entities(distinct(Recipe.cuisine))
        .filter(Recipe.cuisine.isnot(None))
        .order_by(Recipe.cuisine)
        .all()
    ]

    return RecipeFacetsOut(courses=courses, cuisines=cuisines)


@router.get("", response_model=RecipeListOut)
def list_recipes(
    search: str | None = Query(default=None, description="Matches recipe name or tags"),
    cuisine: str | None = None,
    course: str | None = None,
    tag: str | None = None,
    max_time_min: int | None = Query(default=None, ge=1, description="total_time_min at or below this"),
    sort_by: Literal["relevance", "rating", "newest", "quickest"] = "relevance",
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Approved recipes only -- pending/rejected community submissions never
    appear here (they're only visible to their submitter/admins via the
    detail endpoint's own visibility check)."""
    query = db.query(Recipe).filter(Recipe.moderation_status == "approved")

    if cuisine:
        query = query.filter(Recipe.cuisine.ilike(cuisine))
    if course:
        # `course` was previously accepted by the frontend's course chips
        # but silently dropped here -- FastAPI ignores query params that
        # don't match a declared parameter, so clicking a chip re-fetched
        # the *unfiltered* list every time rather than raising an error.
        query = query.filter(Recipe.course.ilike(course))
    if tag:
        query = query.filter(Recipe.tags.any(tag))
    if max_time_min is not None:
        query = query.filter(Recipe.total_time_min.isnot(None), Recipe.total_time_min <= max_time_min)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Recipe.name_en.ilike(like), Recipe.tags.any(search)))

    total = query.count()
    rows = (
        query.order_by(*_SORT_OPTIONS[sort_by])
        .offset(offset)
        .limit(limit)
        .all()
    )

    return RecipeListOut(
        total=total,
        limit=limit,
        offset=offset,
        items=[
            RecipeListItemOut(
                id=r.id,
                name_en=r.name_en,
                name_native=r.name_native,
                cuisine=r.cuisine,
                course=r.course,
                image_url=r.image_url,
                tags=r.tags or [],
                servings=r.servings,
                prep_time_min=r.prep_time_min,
                cook_time_min=r.cook_time_min,
                total_time_min=r.total_time_min,
                calories_kcal=float(r.calories_kcal) if r.calories_kcal is not None else None,
                trust_score=float(r.trust_score),
                average_rating=float(r.average_rating) if r.average_rating is not None else None,
                review_count=r.review_count,
                source_type=r.source_type,
            )
            for r in rows
        ],
    )