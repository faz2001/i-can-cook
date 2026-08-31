import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.community import OccasionTag, RecipeOccasionVote, RecipeVariation, Review
from app.models.recipe import Recipe
from app.models.user import User
from app.schemas.community import (
    OccasionTagOut, OccasionTagProposeIn, OccasionTagVoteOut,
    ReviewCreate, ReviewOut, VariationCreate, VariationOut,
)
from app.services import rating_aggregate

router = APIRouter(prefix="/api/recipes/{recipe_id}", tags=["community"])


def _get_recipe_or_404(db: Session, recipe_id: str) -> Recipe:
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


def _slugify(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    return f"occ_{slug}"


# ---------------------------------------------------------------------------
# Reviews -- star rating + written review, one per user per recipe (editable)
# ---------------------------------------------------------------------------

@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_recipe_or_404(db, recipe_id)
    reviews = (
        db.query(Review)
        .filter(Review.recipe_id == recipe_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return reviews


@router.post("/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def upsert_review(
    recipe_id: str,
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates the user's review, or replaces their existing one for this recipe --
    matches the common "you already reviewed this, edit it" pattern rather than allowing
    duplicate reviews from the same person."""
    _get_recipe_or_404(db, recipe_id)

    review = db.query(Review).filter(Review.recipe_id == recipe_id, Review.user_id == current_user.id).first()
    if review:
        review.rating = payload.rating
        review.review_text = payload.review_text
    else:
        review = Review(recipe_id=recipe_id, user_id=current_user.id,
                         rating=payload.rating, review_text=payload.review_text)
        db.add(review)

    db.flush()
    rating_aggregate.recompute(db, recipe_id)
    db.commit()
    db.refresh(review)
    return review


@router.delete("/reviews", status_code=status.HTTP_204_NO_CONTENT)
def delete_own_review(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review = db.query(Review).filter(Review.recipe_id == recipe_id, Review.user_id == current_user.id).first()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You haven't reviewed this recipe")
    db.delete(review)
    db.flush()
    rating_aggregate.recompute(db, recipe_id)
    db.commit()


# ---------------------------------------------------------------------------
# Occasion tag voting -- approved tags are votable on any recipe; a newly proposed tag
# is only visible on the recipe it was proposed against until an admin approves it
# (Admin > Tag Management: "Review and approve community-proposed tag additions").
# ---------------------------------------------------------------------------

@router.get("/occasion-tags", response_model=list[OccasionTagOut])
def list_occasion_tags(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_recipe_or_404(db, recipe_id)

    votes = db.query(RecipeOccasionVote).filter(RecipeOccasionVote.recipe_id == recipe_id).all()
    vote_counts: dict[str, int] = {}
    user_voted_ids: set[str] = set()
    for v in votes:
        vote_counts[v.occasion_tag_id] = vote_counts.get(v.occasion_tag_id, 0) + 1
        if v.user_id == current_user.id:
            user_voted_ids.add(v.occasion_tag_id)

    proposed_with_votes_ids = {v.occasion_tag_id for v in votes}
    tags = (
        db.query(OccasionTag)
        .filter(
            (OccasionTag.status == "approved")
            | (
                OccasionTag.id.in_(proposed_with_votes_ids)
                & (OccasionTag.status != "rejected")
            )
        )
        .all()
    )

    return [
        OccasionTagOut(
            id=t.id, label=t.label, status=t.status,
            vote_count=vote_counts.get(t.id, 0),
            user_has_voted=t.id in user_voted_ids,
        )
        for t in tags
    ]


@router.post("/occasion-tags", response_model=OccasionTagOut, status_code=status.HTTP_201_CREATED)
def propose_occasion_tag(
    recipe_id: str,
    payload: OccasionTagProposeIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Proposes a new occasion tag (or reuses an existing one with the same label) and
    immediately casts the proposer's own vote for it on this recipe."""
    _get_recipe_or_404(db, recipe_id)

    existing = db.query(OccasionTag).filter(func_lower_label(payload.label)).first()
    if existing is None:
        tag = OccasionTag(id=_slugify(payload.label), label=payload.label.strip(),
                           status="proposed", proposed_by=current_user.id)
        db.add(tag)
        db.flush()
    else:
        tag = existing
        if tag.status == "rejected":
            # Send a previously-rejected tag back through moderation instead of
            # silently reappearing to users while its status still says "rejected".
            tag.status = "proposed"
            tag.proposed_by = current_user.id

    vote = db.query(RecipeOccasionVote).filter(
        RecipeOccasionVote.recipe_id == recipe_id,
        RecipeOccasionVote.occasion_tag_id == tag.id,
        RecipeOccasionVote.user_id == current_user.id,
    ).first()
    if vote is None:
        db.add(RecipeOccasionVote(recipe_id=recipe_id, occasion_tag_id=tag.id, user_id=current_user.id))

    db.commit()
    db.refresh(tag)

    vote_count = db.query(RecipeOccasionVote).filter(
        RecipeOccasionVote.recipe_id == recipe_id, RecipeOccasionVote.occasion_tag_id == tag.id
    ).count()
    return OccasionTagOut(id=tag.id, label=tag.label, status=tag.status, vote_count=vote_count, user_has_voted=True)


def func_lower_label(label: str):
    # kept as a tiny helper so the case-insensitive lookup above reads clearly at the call site
    from sqlalchemy import func
    return func.lower(OccasionTag.label) == label.strip().lower()


@router.post("/occasion-tags/{tag_id}/vote", response_model=OccasionTagVoteOut)
def toggle_occasion_tag_vote(
    recipe_id: str,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Toggles the current user's vote for this tag on this recipe -- vote if not yet
    voted, un-vote if they already had. Simpler UX than separate vote/unvote endpoints."""
    _get_recipe_or_404(db, recipe_id)
    tag = db.query(OccasionTag).filter(OccasionTag.id == tag_id).first()
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occasion tag not found")

    existing_vote = db.query(RecipeOccasionVote).filter(
        RecipeOccasionVote.recipe_id == recipe_id,
        RecipeOccasionVote.occasion_tag_id == tag_id,
        RecipeOccasionVote.user_id == current_user.id,
    ).first()

    if existing_vote:
        db.delete(existing_vote)
        user_has_voted = False
    else:
        db.add(RecipeOccasionVote(recipe_id=recipe_id, occasion_tag_id=tag_id, user_id=current_user.id))
        user_has_voted = True

    db.commit()
    vote_count = db.query(RecipeOccasionVote).filter(
        RecipeOccasionVote.recipe_id == recipe_id, RecipeOccasionVote.occasion_tag_id == tag_id
    ).count()
    return OccasionTagVoteOut(occasion_tag_id=tag_id, vote_count=vote_count, user_has_voted=user_has_voted)


# ---------------------------------------------------------------------------
# Recipe variation logging
# ---------------------------------------------------------------------------

@router.get("/variations", response_model=list[VariationOut])
def list_variations(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_recipe_or_404(db, recipe_id)
    return (
        db.query(RecipeVariation)
        .filter(RecipeVariation.recipe_id == recipe_id)
        .order_by(RecipeVariation.created_at.desc())
        .all()
    )


@router.post("/variations", response_model=VariationOut, status_code=status.HTTP_201_CREATED)
def log_variation(
    recipe_id: str,
    payload: VariationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_recipe_or_404(db, recipe_id)
    variation = RecipeVariation(
        recipe_id=recipe_id, user_id=current_user.id,
        description=payload.description, substitutions=payload.substitutions,
    )
    db.add(variation)
    db.commit()
    db.refresh(variation)
    return variation
