from decimal import Decimal

from pydantic import BaseModel


class ScaledIngredient(BaseModel):
    canonical_id: str | None
    name: str
    original_quantity: Decimal | None
    original_unit: str | None
    scaled_quantity: Decimal | None
    notes: str | None


class RecipeScaleOut(BaseModel):
    recipe_id: str
    name_en: str
    original_servings: int
    requested_servings: int
    scale_factor: float
    ingredients: list[ScaledIngredient]
