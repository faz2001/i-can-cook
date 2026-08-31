from pydantic import BaseModel


class MatchedIngredient(BaseModel):
    canonical_id: str
    pantry_item_name: str


class ZeroWasteSuggestion(BaseModel):
    recipe_id: str
    name_en: str
    total_time_min: int | None
    matched_ingredient_count: int
    total_ingredient_count: int
    coverage_fraction: float
    matched_ingredients: list[MatchedIngredient]
