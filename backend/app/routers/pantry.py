from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.ingredient import Ingredient
from app.models.pantry import PantryItem
from app.models.user import User
from app.schemas.pantry import PantryItemCreate, PantryItemOut, PantryItemUpdate
from app.services import ml02_shelf_life, rb05_waste
from app.services.ingredient_matching import load_ingredient_index, match_ingredient

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


def _to_out(item: PantryItem) -> PantryItemOut:
    days_to_expiry = (item.expiry_date - date.today()).days if item.expiry_date else None
    urgency = rb05_waste.urgency_level_for_days(days_to_expiry) if days_to_expiry is not None else None
    return PantryItemOut(
        id=item.id,
        ingredient_id=item.ingredient_id,
        raw_name=item.raw_name,
        quantity=float(item.quantity) if item.quantity is not None else None,
        unit=item.unit,
        storage_condition=item.storage_condition,
        purchase_date=item.purchase_date,
        expiry_date=item.expiry_date,
        expiry_source=item.expiry_source,
        days_to_expiry=days_to_expiry,
        urgency=urgency,
    )


def _get_owned_item_or_404(db: Session, item_id: int, user_id: int) -> PantryItem:
    item = db.query(PantryItem).filter(PantryItem.id == item_id, PantryItem.user_id == user_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pantry item not found")
    return item


@router.get("", response_model=list[PantryItemOut])
def list_pantry_items(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(PantryItem)
        .filter(PantryItem.user_id == current_user.id)
        .order_by(PantryItem.expiry_date.is_(None), PantryItem.expiry_date.asc())
        .all()
    )
    return [_to_out(i) for i in items]


@router.post("", response_model=PantryItemOut, status_code=status.HTTP_201_CREATED)
def create_pantry_item(
    payload: PantryItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ing_index = load_ingredient_index(db)
    ingredient_id = match_ingredient(payload.raw_name, ing_index)
    ingredient = db.query(Ingredient).filter(Ingredient.canonical_id == ingredient_id).first() if ingredient_id else None

    # purchase_date is optional on the request, but the shelf-life prediction
    # (and the stored row) both need a concrete date to anchor against, so
    # default to today rather than letting a None reach `purchase_date + timedelta(...)`.
    purchase_date = payload.purchase_date or date.today()

    expiry_date = payload.expiry_date
    expiry_source = "label" if expiry_date else None
    if expiry_date is None:
        expiry_date = ml02_shelf_life.predict_shelf_life(ingredient, payload.storage_condition, purchase_date)
        expiry_source = "predicted"

    item = PantryItem(
        user_id=current_user.id,
        ingredient_id=ingredient_id,
        raw_name=payload.raw_name,
        quantity=payload.quantity,
        unit=payload.unit,
        storage_condition=payload.storage_condition,
        purchase_date=purchase_date,
        expiry_date=expiry_date,
        expiry_source=expiry_source,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.patch("/{item_id}", response_model=PantryItemOut)
def update_pantry_item(
    item_id: int,
    payload: PantryItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item_or_404(db, item_id, current_user.id)
    updates = payload.model_dump(exclude_unset=True)

    # Re-match the ingredient if the name changed.
    if "raw_name" in updates:
        ing_index = load_ingredient_index(db)
        item.ingredient_id = match_ingredient(updates["raw_name"], ing_index)

    # A manually supplied expiry_date always means the user is overriding with a known
    # (usually label) date -- flip the source so RB-05/urgency badges reflect that trust.
    if "expiry_date" in updates and updates["expiry_date"] is not None:
        item.expiry_source = "label"

    for field, value in updates.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pantry_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item_or_404(db, item_id, current_user.id)
    db.delete(item)
    db.commit()
