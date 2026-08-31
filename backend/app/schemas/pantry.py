from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

VALID_STORAGE_CONDITIONS = {"Refrigerated", "Frozen", "Pantry"}


class PantryItemCreate(BaseModel):
    raw_name: str
    quantity: Decimal | None = None
    unit: str | None = None
    storage_condition: str
    purchase_date: date | None = None
    expiry_date: date | None = None  # provided by the user (label date); predicted server-side if omitted

    @field_validator("storage_condition")
    @classmethod
    def validate_storage_condition(cls, v: str) -> str:
        if v not in VALID_STORAGE_CONDITIONS:
            raise ValueError(f"storage_condition must be one of {sorted(VALID_STORAGE_CONDITIONS)}")
        return v

    @field_validator("raw_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class PantryItemUpdate(BaseModel):
    """All fields optional -- partial update (PATCH)."""
    raw_name: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    storage_condition: str | None = None
    purchase_date: date | None = None
    expiry_date: date | None = None

    @field_validator("storage_condition")
    @classmethod
    def validate_storage_condition(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_STORAGE_CONDITIONS:
            raise ValueError(f"storage_condition must be one of {sorted(VALID_STORAGE_CONDITIONS)}")
        return v


class PantryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_id: str | None
    raw_name: str
    quantity: float | None
    unit: str | None
    storage_condition: str | None
    purchase_date: date | None
    expiry_date: date | None
    expiry_source: str | None  # 'label' | 'predicted'
    days_to_expiry: int | None
    urgency: str | None
