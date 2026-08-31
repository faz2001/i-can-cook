from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FavoriteCreate(BaseModel):
    recipe_id: str


class FavoriteRecipeSummary(BaseModel):
    """Minimal recipe info embedded in a favorite, enough for a list view
    without a second round trip per item."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name_en: str
    cuisine: str | None
    course: str | None
    image_url: str | None
    servings: int | None
    total_time_min: int | None


class FavoriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    recipe: FavoriteRecipeSummary
