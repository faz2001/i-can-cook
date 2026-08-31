from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.models.bookmark import Bookmark, BookmarkCollection, ShoppingList, ShoppingListItem
from app.models.recipe import Recipe
from app.schemas.bookmark import (
    BookmarkCreate, BookmarkRecipeOut, CollectionCreate, CollectionDetailOut, CollectionOut,
    ShoppingListCreate, ShoppingListItemIn, ShoppingListItemOut, ShoppingListOut,
)

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])

DEFAULT_COLLECTION_NAME = "My Favorites"


def _get_or_create_default_collection(db: Session, user_id: int) -> BookmarkCollection:
    collection = (
        db.query(BookmarkCollection)
        .filter(BookmarkCollection.user_id == user_id, BookmarkCollection.name == DEFAULT_COLLECTION_NAME)
        .first()
    )
    if collection is None:
        collection = BookmarkCollection(user_id=user_id, name=DEFAULT_COLLECTION_NAME)
        db.add(collection)
        db.flush()
    return collection


def _get_owned_collection_or_404(db: Session, user_id: int, collection_id: int) -> BookmarkCollection:
    collection = (
        db.query(BookmarkCollection)
        .filter(BookmarkCollection.id == collection_id, BookmarkCollection.user_id == user_id)
        .first()
    )
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return collection


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

@router.get("/collections", response_model=list[CollectionOut])
def list_collections(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    collections = db.query(BookmarkCollection).filter(BookmarkCollection.user_id == user_id).all()
    return [
        CollectionOut(id=c.id, name=c.name, recipe_count=len(c.bookmarks), created_at=c.created_at)
        for c in collections
    ]


@router.post("/collections", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    existing = (
        db.query(BookmarkCollection)
        .filter(BookmarkCollection.user_id == user_id, BookmarkCollection.name == payload.name.strip())
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A collection with this name already exists")

    collection = BookmarkCollection(user_id=user_id, name=payload.name.strip())
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return CollectionOut(id=collection.id, name=collection.name, recipe_count=0, created_at=collection.created_at)


@router.get("/collections/{collection_id}", response_model=CollectionDetailOut)
def get_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    collection = _get_owned_collection_or_404(db, user_id, collection_id)
    bookmarks = (
        db.query(Bookmark)
        .options(joinedload(Bookmark.recipe))
        .filter(Bookmark.collection_id == collection_id)
        .order_by(Bookmark.added_at.desc())
        .all()
    )
    return CollectionDetailOut(
        id=collection.id,
        name=collection.name,
        recipes=[
            BookmarkRecipeOut(
                recipe_id=b.recipe_id, name_en=b.recipe.name_en, cuisine=b.recipe.cuisine,
                course=b.recipe.course, added_at=b.added_at,
            )
            for b in bookmarks
        ],
    )


# ---------------------------------------------------------------------------
# Bookmarks (adding/removing recipes from a collection)
# ---------------------------------------------------------------------------

@router.post("", response_model=BookmarkRecipeOut, status_code=status.HTTP_201_CREATED)
def add_bookmark(
    payload: BookmarkCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    recipe = db.query(Recipe).filter(Recipe.id == payload.recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    if payload.collection_id is not None:
        collection = _get_owned_collection_or_404(db, user_id, payload.collection_id)
    else:
        collection = _get_or_create_default_collection(db, user_id)

    existing = (
        db.query(Bookmark)
        .filter(Bookmark.collection_id == collection.id, Bookmark.recipe_id == payload.recipe_id)
        .first()
    )
    if existing is None:
        existing = Bookmark(collection_id=collection.id, recipe_id=payload.recipe_id)
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return BookmarkRecipeOut(
        recipe_id=recipe.id, name_en=recipe.name_en, cuisine=recipe.cuisine,
        course=recipe.course, added_at=existing.added_at,
    )


@router.delete("/collections/{collection_id}/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_bookmark(
    collection_id: int,
    recipe_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _get_owned_collection_or_404(db, user_id, collection_id)
    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.collection_id == collection_id, Bookmark.recipe_id == recipe_id)
        .first()
    )
    if bookmark is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe is not bookmarked in this collection")
    db.delete(bookmark)
    db.commit()


# ---------------------------------------------------------------------------
# Shopping lists
# ---------------------------------------------------------------------------

@router.post("/collections/{collection_id}/shopping-list", response_model=ShoppingListOut,
             status_code=status.HTTP_201_CREATED)
def generate_shopping_list(
    collection_id: int,
    payload: ShoppingListCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Aggregates every recipe's ingredients in the collection into one list.

    Known real limitation, surfaced to the frontend rather than hidden: items
    are merged only when (raw_name, unit) match exactly -- "Tomato" vs
    "Tomatoes", or the same ingredient in different units, will appear as
    separate lines. Doesn't exclude pantry items the user already has.
    """
    collection = _get_owned_collection_or_404(db, user_id, collection_id)
    name = (payload.name or "").strip() or f"{collection.name} shopping list"

    shopping_list = ShoppingList(user_id=user_id, collection_id=collection_id, name=name)
    db.add(shopping_list)
    db.flush()

    bookmarks = (
        db.query(Bookmark)
        .options(joinedload(Bookmark.recipe).joinedload(Recipe.ingredients))
        .filter(Bookmark.collection_id == collection_id)
        .all()
    )

    aggregated: dict[tuple[str, str | None], float | None] = {}
    for b in bookmarks:
        for ri in b.recipe.ingredients:
            key = (ri.raw_name.strip().lower(), ri.unit)
            if key not in aggregated:
                aggregated[key] = ri.quantity
            elif aggregated[key] is not None and ri.quantity is not None:
                aggregated[key] = aggregated[key] + ri.quantity
            else:
                aggregated[key] = None  # can't sum if either side is missing a quantity

    for (raw_name, unit), quantity in aggregated.items():
        db.add(ShoppingListItem(
            shopping_list_id=shopping_list.id, name=raw_name, quantity=quantity, unit=unit, is_manual=False,
        ))

    db.commit()
    db.refresh(shopping_list)
    return _shopping_list_out(db, shopping_list.id)


def _shopping_list_out(db: Session, shopping_list_id: int) -> ShoppingListOut:
    shopping_list = db.query(ShoppingList).options(joinedload(ShoppingList.items)).filter(
        ShoppingList.id == shopping_list_id
    ).first()
    return ShoppingListOut(
        id=shopping_list.id, name=shopping_list.name,
        items=[ShoppingListItemOut.model_validate(i) for i in shopping_list.items],
    )


def _get_owned_shopping_list_or_404(db: Session, user_id: int, shopping_list_id: int) -> ShoppingList:
    shopping_list = (
        db.query(ShoppingList)
        .filter(ShoppingList.id == shopping_list_id, ShoppingList.user_id == user_id)
        .first()
    )
    if shopping_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping list not found")
    return shopping_list


@router.get("/shopping-lists/{shopping_list_id}", response_model=ShoppingListOut)
def get_shopping_list(
    shopping_list_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _get_owned_shopping_list_or_404(db, user_id, shopping_list_id)
    return _shopping_list_out(db, shopping_list_id)


@router.post("/shopping-lists/{shopping_list_id}/items", response_model=ShoppingListItemOut,
             status_code=status.HTTP_201_CREATED)
def add_shopping_list_item(
    shopping_list_id: int,
    payload: ShoppingListItemIn,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _get_owned_shopping_list_or_404(db, user_id, shopping_list_id)
    item = ShoppingListItem(
        shopping_list_id=shopping_list_id, name=payload.name, quantity=payload.quantity,
        unit=payload.unit, is_manual=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/shopping-lists/{shopping_list_id}/items/{item_id}", response_model=ShoppingListItemOut)
def toggle_shopping_list_item(
    shopping_list_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Toggles is_checked -- matches the checkbox UI, no request body needed."""
    _get_owned_shopping_list_or_404(db, user_id, shopping_list_id)
    item = db.query(ShoppingListItem).filter(
        ShoppingListItem.id == item_id, ShoppingListItem.shopping_list_id == shopping_list_id
    ).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    item.is_checked = not item.is_checked
    db.commit()
    db.refresh(item)
    return item


@router.delete("/shopping-lists/{shopping_list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shopping_list_item(
    shopping_list_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _get_owned_shopping_list_or_404(db, user_id, shopping_list_id)
    item = db.query(ShoppingListItem).filter(
        ShoppingListItem.id == item_id, ShoppingListItem.shopping_list_id == shopping_list_id
    ).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    db.delete(item)
    db.commit()
