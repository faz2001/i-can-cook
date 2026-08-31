from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---- Collections ----

class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CollectionOut(BaseModel):
    id: int
    name: str
    recipe_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Bookmarks (recipes inside a collection) ----

class BookmarkCreate(BaseModel):
    recipe_id: str
    collection_id: Optional[int] = None  # omit -> default "My Favorites" collection


class BookmarkRecipeOut(BaseModel):
    recipe_id: str
    name_en: str
    cuisine: Optional[str] = None
    course: Optional[str] = None
    added_at: datetime


class CollectionDetailOut(BaseModel):
    id: int
    name: str
    recipes: list[BookmarkRecipeOut]


# ---- Shopping lists ----

class ShoppingListCreate(BaseModel):
    name: Optional[str] = None  # defaults to "{collection name} shopping list" if omitted


class ShoppingListItemIn(BaseModel):
    name: str = Field(min_length=1)
    quantity: Optional[float] = None
    unit: Optional[str] = None


class ShoppingListItemOut(BaseModel):
    id: int
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    is_checked: bool
    is_manual: bool

    model_config = {"from_attributes": True}


class ShoppingListOut(BaseModel):
    id: int
    name: str
    items: list[ShoppingListItemOut]
