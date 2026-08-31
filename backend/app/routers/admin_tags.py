import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.database import get_db
from app.models.community import OccasionTag
from app.models.tag_vocabulary import RecipeTagVocabulary
from app.schemas.admin import OccasionTagAdminOut, OccasionTagReviewAction, TagVocabularyCreate, TagVocabularyOut

router = APIRouter(prefix="/api/admin/tags", tags=["admin"], dependencies=[Depends(require_admin)])


class TagStatusUpdate(BaseModel):
    status: Literal["approved", "retired"]


def _slugify_tag(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    return f"tag_{slug}"


# ---------------------------------------------------------------------------
# General controlled vocabulary (~80 semantic tags)
# ---------------------------------------------------------------------------

@router.get("/vocabulary", response_model=list[TagVocabularyOut])
def list_vocabulary(status_filter: str | None = None, db: Session = Depends(get_db)):
    query = db.query(RecipeTagVocabulary)
    if status_filter:
        query = query.filter(RecipeTagVocabulary.status == status_filter)
    return query.order_by(RecipeTagVocabulary.category, RecipeTagVocabulary.label).all()


@router.post("/vocabulary", response_model=TagVocabularyOut, status_code=status.HTTP_201_CREATED)
def create_vocabulary_tag(payload: TagVocabularyCreate, db: Session = Depends(get_db)):
    tag_id = _slugify_tag(payload.label)
    if db.query(RecipeTagVocabulary).filter(RecipeTagVocabulary.id == tag_id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists")
    tag = RecipeTagVocabulary(id=tag_id, label=payload.label.strip(), category=payload.category, status="approved")
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.patch("/vocabulary/{tag_id}", response_model=TagVocabularyOut)
def update_vocabulary_tag_status(tag_id: str, payload: TagStatusUpdate, db: Session = Depends(get_db)):
    """Retiring rather than deleting -- existing recipes may still carry this tag in
    their tags[] array, and a hard delete would leave those referencing a vanished tag
    with no record it ever existed."""
    tag = db.query(RecipeTagVocabulary).filter(RecipeTagVocabulary.id == tag_id).first()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    tag.status = payload.status
    db.commit()
    db.refresh(tag)
    return tag


# ---------------------------------------------------------------------------
# Community-proposed occasion tags -- approve/reject queue
# ---------------------------------------------------------------------------

@router.get("/occasion-proposals", response_model=list[OccasionTagAdminOut])
def list_occasion_proposals(db: Session = Depends(get_db)):
    return (
        db.query(OccasionTag)
        .filter(OccasionTag.status == "proposed")
        .order_by(OccasionTag.created_at.asc())
        .all()
    )


@router.post("/occasion-proposals/{tag_id}/review", response_model=OccasionTagAdminOut)
def review_occasion_proposal(tag_id: str, payload: OccasionTagReviewAction, db: Session = Depends(get_db)):
    tag = db.query(OccasionTag).filter(OccasionTag.id == tag_id).first()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occasion tag not found")
    if tag.status != "proposed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag is not pending review")

    tag.status = "approved" if payload.action == "approve" else "rejected"
    db.commit()
    db.refresh(tag)
    return tag
