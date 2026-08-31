from pydantic import BaseModel


class EquipmentTagOut(BaseModel):
    id: str
    label: str

    model_config = {"from_attributes": True}


class ExtractedIntentOut(BaseModel):
    """Shape of RB-01's `ExtractedIntent.as_dict()` -- see app/services/rb01_intent.py
    for why this is its own endpoint rather than a recommend-pipeline tier."""
    cuisine: str | None = None
    course: str | None = None
    dietary: str | None = None
    spice_level: str | None = None
    cooking_method: str | None = None
    occasion: str | None = None
    equipment: str | None = None
    allergen: str | None = None
    texture: str | None = None
    keywords: list[str] = []
