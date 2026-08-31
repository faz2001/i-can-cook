from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---- shared building blocks ----

class NutritionOut(BaseModel):
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fibre_g: float | None = None
    per: str = "serving"
    available: bool = False


class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_number: int
    instruction: str
    duration_min: int | None


# ---- GET /api/recipes/{id} ----

class IngredientLineOut(BaseModel):
    ingredient_id: str | None
    name: str
    quantity: float | None
    unit: str | None
    notes: str | None
    pantry_status: str  # "have" | "partial" | "missing" | "unmatched"
    pantry_quantity_available: float | None


class RecipeDetailOut(BaseModel):
    id: str
    name_en: str
    name_native: str | None
    cuisine: str
    regional_origin: str | None
    course: str | None
    ayurvedic_balance: str | None
    tags: list[str]
    image_url: str | None
    base_servings: int | None
    requested_servings: int
    scale_factor: float
    ingredients: list[IngredientLineOut]
    steps: list[StepOut]
    nutrition: NutritionOut
    trust_score: float
    health_score: float | None
    source_type: str
    source_url: str | None
    average_rating: float | None
    review_count: int
    is_favorited: bool


# ---- POST /api/recipes ----

class IngredientLineIn(BaseModel):
    raw_name: str
    quantity: float | None = None
    unit: str | None = None
    notes: str | None = None


class StepIn(BaseModel):
    step_number: int
    instruction: str
    duration_min: int | None = None


class RecipeSubmissionIn(BaseModel):
    name_en: str = Field(min_length=1, max_length=200)
    cuisine: str
    course: str | None = None
    servings: int | None = Field(default=None, ge=1, le=100)
    prep_time_min: int | None = Field(default=None, ge=0)
    cook_time_min: int | None = Field(default=None, ge=0)
    tags: list[str] = Field(default_factory=list)
    ingredients: list[IngredientLineIn]
    steps: list[StepIn]


class RecipeSubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name_en: str
    moderation_status: str


# ---- GET /api/recipes/{id}/cook ----

class ChecklistItemOut(BaseModel):
    name: str
    quantity: float | None
    unit: str | None
    notes: str | None


class CookStepOut(BaseModel):
    step_number: int
    instruction: str
    duration_min: int | None
    timer_seconds: int | None


class CookSessionOut(BaseModel):
    recipe_id: str
    name_en: str
    requested_servings: int
    scale_factor: float
    total_active_time_min: int
    prep_checklist: list[ChecklistItemOut]
    steps: list[CookStepOut]
