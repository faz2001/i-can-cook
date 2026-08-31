from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.database import get_db
from app.models.recipe import Recipe
from app.models.trust_audit import TrustScoreAuditLog
from app.models.user import User
from app.schemas.admin import TrustScoreAuditOut, TrustScoreFlaggedRecipeOut, TrustScoreOverrideIn

router = APIRouter(prefix="/api/admin/trust-scores", tags=["admin"], dependencies=[Depends(require_admin)])

LOW_TRUST_THRESHOLD = 0.5
MIN_REVIEWS_FOR_MISMATCH_CHECK = 3
MISMATCH_THRESHOLD = 1.5   # on a 5-point scale (trust_score * 5 vs average_rating)


@router.get("/flagged", response_model=list[TrustScoreFlaggedRecipeOut])
def list_flagged_recipes(db: Session = Depends(get_db)):
    """Two independent flags: a low Trust Score on its own face, or a Trust Score that
    disagrees with what the community is actually rating the recipe -- either is a
    reasonable prompt for editorial review, for different reasons."""
    flagged: dict[str, TrustScoreFlaggedRecipeOut] = {}

    for r in db.query(Recipe).filter(Recipe.trust_score < LOW_TRUST_THRESHOLD).all():
        flagged[r.id] = TrustScoreFlaggedRecipeOut(
            id=r.id, name_en=r.name_en, source_type=r.source_type, trust_score=float(r.trust_score),
            average_rating=float(r.average_rating) if r.average_rating is not None else None,
            review_count=r.review_count,
            flag_reason=f"Trust Score ({r.trust_score}) is below {LOW_TRUST_THRESHOLD}",
        )

    mismatch_candidates = db.query(Recipe).filter(
        Recipe.review_count >= MIN_REVIEWS_FOR_MISMATCH_CHECK, Recipe.average_rating.isnot(None)
    ).all()
    for r in mismatch_candidates:
        trust_on_five = float(r.trust_score) * 5
        gap = abs(trust_on_five - float(r.average_rating))
        if gap > MISMATCH_THRESHOLD and r.id not in flagged:
            flagged[r.id] = TrustScoreFlaggedRecipeOut(
                id=r.id, name_en=r.name_en, source_type=r.source_type, trust_score=float(r.trust_score),
                average_rating=float(r.average_rating), review_count=r.review_count,
                flag_reason=f"Trust Score implies ~{trust_on_five:.1f}/5 but community average is "
                            f"{r.average_rating}/5 across {r.review_count} reviews",
            )

    return list(flagged.values())


@router.patch("/{recipe_id}", response_model=TrustScoreAuditOut)
def override_trust_score(
    recipe_id: str,
    payload: TrustScoreOverrideIn,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    old_value = float(recipe.trust_score)
    recipe.trust_score = payload.trust_score

    audit_entry = TrustScoreAuditLog(
        recipe_id=recipe_id, admin_user_id=current_user.id,
        old_value=old_value, new_value=payload.trust_score, reason=payload.reason,
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry


@router.get("/{recipe_id}/audit", response_model=list[TrustScoreAuditOut])
def get_trust_score_audit_trail(recipe_id: str, db: Session = Depends(get_db)):
    return (
        db.query(TrustScoreAuditLog)
        .filter(TrustScoreAuditLog.recipe_id == recipe_id)
        .order_by(TrustScoreAuditLog.created_at.desc())
        .all()
    )
