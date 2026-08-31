from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---- /admin dashboard ----

class DashboardSummaryOut(BaseModel):
    total_recipes: int
    recipes_by_source_type: dict[str, int]
    pending_recipe_moderation: int
    pending_occasion_tag_proposals: int
    recipes_below_trust_threshold: int   # trust_score < 0.5, candidates for editorial review
    unmatched_ingredient_lines: int      # recipe_ingredients rows with no canonical ingredient_id
    total_users: int
    total_reviews: int


# ---- /admin/recipes ----

class AdminIngredientLineIn(BaseModel):
    raw_name: str
    ingredient_id: Optional[str] = None  # leave unset to auto-match by raw_name
    quantity: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


class AdminStepIn(BaseModel):
    step_number: int
    instruction: str
    duration_min: Optional[int] = None


class AdminRecipeCreate(BaseModel):
    id: Optional[str] = None   # omit to auto-generate (admin-authored curated recipes may want a chosen id)
    name_en: str
    name_native: Optional[str] = None
    cuisine: str
    regional_origin: Optional[str] = None
    course: Optional[str] = None
    servings: Optional[int] = None
    prep_time_min: Optional[int] = None
    cook_time_min: Optional[int] = None
    total_time_min: Optional[int] = None
    tags: list[str] = []
    ayurvedic_balance: Optional[str] = None
    trust_score: float = Field(default=0.9, ge=0, le=1)
    source_type: Literal["curated", "imported", "community"] = "curated"
    ingredients: list[AdminIngredientLineIn]
    steps: list[AdminStepIn]


class AdminRecipeUpdate(BaseModel):
    """Partial update -- any field omitted is left unchanged. Ingredients/steps, if
    provided, REPLACE the full existing list (simpler and safer than diffing)."""
    name_en: Optional[str] = None
    name_native: Optional[str] = None
    cuisine: Optional[str] = None
    regional_origin: Optional[str] = None
    course: Optional[str] = None
    servings: Optional[int] = None
    prep_time_min: Optional[int] = None
    cook_time_min: Optional[int] = None
    total_time_min: Optional[int] = None
    tags: Optional[list[str]] = None
    ayurvedic_balance: Optional[str] = None
    ingredients: Optional[list[AdminIngredientLineIn]] = None
    steps: Optional[list[AdminStepIn]] = None


class ModerationAction(BaseModel):
    action: Literal["approve", "reject"]
    reason: Optional[str] = None


class AdminRecipeListItemOut(BaseModel):
    id: str
    name_en: str
    cuisine: str
    source_type: str
    moderation_status: str
    trust_score: float
    average_rating: Optional[float] = None
    review_count: int
    submitted_by: Optional[int] = None

    model_config = {"from_attributes": True}


# ---- /admin/dataset ----

class ValidationIssueOut(BaseModel):
    recipe_id: str
    recipe_name: str
    issue: str
    severity: Literal["error", "warning"]


class UnmatchedIngredientGroupOut(BaseModel):
    raw_name: str
    occurrence_count: int
    sample_recipe_ids: list[str]


class ResolveUnmatchedIngredientIn(BaseModel):
    raw_name: str
    ingredient_id: str   # canonical ingredient to assign to every matching raw_name


class AdminIngredientCreate(BaseModel):
    id: Optional[str] = None   # omit to auto-slug from name
    name: str
    category: Optional[str] = None
    unit_default: Optional[str] = None


class AdminIngredientUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_default: Optional[str] = None


class IngredientOut(BaseModel):
    canonical_id: str
    name: str
    category: Optional[str] = None
    unit_default: Optional[str] = None

    model_config = {"from_attributes": True}


# ---- /admin/tags ----

class TagVocabularyCreate(BaseModel):
    label: str = Field(min_length=2, max_length=60)
    category: Optional[str] = None


class TagVocabularyOut(BaseModel):
    id: str
    label: str
    category: Optional[str] = None
    status: Literal["approved", "retired"]

    model_config = {"from_attributes": True}


class OccasionTagReviewAction(BaseModel):
    action: Literal["approve", "reject"]


class OccasionTagAdminOut(BaseModel):
    id: str
    label: str
    status: Literal["approved", "proposed", "rejected"]
    proposed_by: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- /admin/trust-scores ----

class TrustScoreOverrideIn(BaseModel):
    trust_score: float = Field(ge=0, le=1)
    reason: Optional[str] = None


class TrustScoreFlaggedRecipeOut(BaseModel):
    id: str
    name_en: str
    source_type: str
    trust_score: float
    average_rating: Optional[float] = None
    review_count: int
    flag_reason: str   # e.g. "trust_score below 0.5", "trust/rating mismatch"


class TrustScoreAuditOut(BaseModel):
    id: int
    recipe_id: str
    admin_user_id: int
    old_value: Optional[float] = None
    new_value: float
    reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
