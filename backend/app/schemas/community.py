from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---- Reviews ----

class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: Optional[str] = None


class ReviewOut(BaseModel):
    id: int
    recipe_id: str
    user_id: int
    rating: int
    review_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecipeRatingSummary(BaseModel):
    average_rating: Optional[float] = None
    review_count: int


# ---- Occasion tags & voting ----

class OccasionTagOut(BaseModel):
    id: str
    label: str
    status: Literal["approved", "proposed", "rejected"]
    vote_count: int
    user_has_voted: bool


class OccasionTagProposeIn(BaseModel):
    label: str = Field(min_length=2, max_length=60)


class OccasionTagVoteOut(BaseModel):
    occasion_tag_id: str
    vote_count: int
    user_has_voted: bool


# ---- Variations ----

class VariationCreate(BaseModel):
    description: str = Field(min_length=1)
    substitutions: Optional[dict] = None


class VariationOut(BaseModel):
    id: int
    recipe_id: str
    user_id: int
    description: str
    substitutions: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
