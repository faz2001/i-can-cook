from pydantic import BaseModel


class RecipeListItemOut(BaseModel):
    id: str
    name_en: str
    name_native: str | None
    cuisine: str
    course: str | None
    image_url: str | None
    tags: list[str]
    servings: int | None
    prep_time_min: int | None
    cook_time_min: int | None
    total_time_min: int | None
    calories_kcal: float | None
    trust_score: float
    average_rating: float | None
    review_count: int
    source_type: str


class RecipeListOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[RecipeListItemOut]


class RecipeFacetsOut(BaseModel):
    courses: list[str]
    cuisines: list[str]