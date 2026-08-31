"""
Thin HTTP wrapper around app/services/shelf_life.py, which does the real
work (loads the trained GradientBoostingRegressor .pkl, runs predictions
in-process). This exposes it directly for cases that aren't tied to a
pantry item -- e.g. a frontend "what's the shelf life of X?" lookup before
the user decides to add anything to their pantry.

The Pantry module already calls predict_shelf_life() internally on
create/update (via app/services/ml02_shelf_life.py), so these endpoints
don't duplicate that -- they're for standalone lookups. Public, no auth
needed (this is a stateless prediction, not a read of anyone's data).
"""
from fastapi import APIRouter, HTTPException

from app.schemas.shelf_life import ShelfLifeBatchQuery, ShelfLifeQuery, ShelfLifeResult
from app.services.shelf_life import predict_shelf_life

router = APIRouter(prefix="/api/ingredients", tags=["shelf-life"])


@router.post("/shelf-life", response_model=ShelfLifeResult)
def get_shelf_life(body: ShelfLifeQuery):
    try:
        result = predict_shelf_life(
            body.category, body.subcategory, body.storage_condition, body.ingredient_name or "Unknown"
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return ShelfLifeResult(
        category=body.category,
        subcategory=body.subcategory,
        storage_condition=body.storage_condition,
        **result,
    )


@router.post("/shelf-life/batch", response_model=list[ShelfLifeResult])
def get_shelf_life_batch(body: ShelfLifeBatchQuery):
    if not body.items:
        return []
    if len(body.items) > 100:
        raise HTTPException(status_code=422, detail="Batch limited to 100 items per request")

    results = []
    for item in body.items:
        try:
            result = predict_shelf_life(
                item.category, item.subcategory, item.storage_condition, item.ingredient_name or "Unknown"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid item ({item.category}/{item.storage_condition}): {e}",
            )
        results.append(ShelfLifeResult(
            category=item.category,
            subcategory=item.subcategory,
            storage_condition=item.storage_condition,
            **result,
        ))
    return results
