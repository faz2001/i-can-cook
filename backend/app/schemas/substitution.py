from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class SubstitutionCreate(BaseModel):
    canonical_id: str
    substitute_canonical_id: str | None = None
    substitute_name: str
    ratio: str | None = None
    notes: str | None = None
    context: str | None = None

    @field_validator("canonical_id", "substitute_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class SubstitutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    canonical_id: str
    substitute_canonical_id: str | None
    substitute_name: str
    ratio: str | None
    notes: str | None
    context: str | None
    created_at: datetime
