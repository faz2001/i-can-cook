"""
Public, read-only tag vocabulary endpoints.

Two unrelated things live here, both small enough not to need their own router:

1. GET /api/tags/equipment -- the canonical "kitchen equipment a user owns" list,
   backed by `recipe_tag_vocabulary` (category='equipment'). Replaces the
   hardcoded EQUIPMENT_OPTIONS that used to live in ProfilePage.tsx, so the
   frontend can't drift out of sync with the backend's list again. This is
   deliberately a *separate* category from RB-01's `equipment` tag list (see
   app/services/rb01_intent.py) -- "equipment I own" and "equipment mentioned in
   a search query" are different vocabularies with different valid values (e.g.
   "Air Fryer" / "Pressure Cooker" are common owned appliances but aren't in
   RB-01's query-side list, and RB-01's "no-equipment" is meaningless as an
   owned-appliance checkbox).
2. GET /api/tags/extract -- RB-01's rule-based free-text intent/filter-tag
   extraction, exposed directly (not through the recommend pipeline -- see the
   placement-decision comment at the top of app/services/rb01_intent.py for why).

Both are public (no auth) since regular signed-in users need the equipment list
on their own profile page, and tag extraction is a stateless, harmless read.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tag_vocabulary import RecipeTagVocabulary
from app.schemas.tags import EquipmentTagOut, ExtractedIntentOut
from app.services.rb01_intent import extract_intent

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("/equipment", response_model=list[EquipmentTagOut])
def list_equipment_tags(db: Session = Depends(get_db)):
    return (
        db.query(RecipeTagVocabulary)
        .filter(RecipeTagVocabulary.category == "equipment", RecipeTagVocabulary.status == "approved")
        .order_by(RecipeTagVocabulary.label)
        .all()
    )


@router.get("/extract", response_model=ExtractedIntentOut)
def extract_filter_tags(q: str):
    """Rule-based (RB-01) tag guess from free text -- e.g. for suggesting filter
    chips as someone types a search. Not used by /api/recommendations."""
    return extract_intent(q).as_dict()
