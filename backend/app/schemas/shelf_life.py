from pydantic import BaseModel


class ShelfLifeQuery(BaseModel):
    category: str
    subcategory: str | None = None
    storage_condition: str
    # Optional: this endpoint is for standalone category/storage lookups
    # that aren't tied to any specific ingredient (see router docstring), so
    # this won't always be available. Falls back to "Unknown" when absent --
    # harmless today since the served model doesn't use it, see
    # app/services/shelf_life.py.
    ingredient_name: str | None = None


class ShelfLifeResult(BaseModel):
    category: str
    subcategory: str | None
    storage_condition: str
    predicted_days: float
    model: str


class ShelfLifeBatchQuery(BaseModel):
    items: list[ShelfLifeQuery]
