from pydantic import BaseModel, Field, field_validator


class ProfileUpdate(BaseModel):
    """Partial update -- any field omitted (not just null) is left unchanged.
    Use exclude_unset in the router so this actually behaves as PATCH semantics
    rather than clobbering fields the frontend didn't send."""
    full_name: str | None = None
    dietary_preferences: list[str] | None = None
    kitchen_equipment: list[str] | None = None

    @field_validator("full_name")
    @classmethod
    def blank_name_is_none(cls, v: str | None) -> str | None:
        """A trimmed empty string means "no name set", same as never having
        sent one -- without this, clearing the name field would save "" and
        the UI would show a blank instead of falling back to 'No name set'."""
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ProfileStatsOut(BaseModel):
    """Small aggregate for the profile page header -- avoids the frontend
    fetching /api/pantry and /api/favorites in full just to show counts."""
    pantry_item_count: int
    favorites_count: int
