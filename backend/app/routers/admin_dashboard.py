from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.database import get_db
from app.models.community import OccasionTag, Review
from app.models.recipe import Recipe, RecipeIngredient
from app.models.user import User
from app.schemas.admin import DashboardSummaryOut

router = APIRouter(prefix="/api/admin/dashboard", tags=["admin"], dependencies=[Depends(require_admin)])

TRUST_SCORE_REVIEW_THRESHOLD = 0.5


@router.get("", response_model=DashboardSummaryOut)
def get_dashboard(db: Session = Depends(get_db)):
    by_source_type = dict(
        db.query(Recipe.source_type, func.count(Recipe.id)).group_by(Recipe.source_type).all()
    )

    return DashboardSummaryOut(
        total_recipes=db.query(Recipe).count(),
        recipes_by_source_type=by_source_type,
        pending_recipe_moderation=db.query(Recipe).filter(Recipe.moderation_status == "pending").count(),
        pending_occasion_tag_proposals=db.query(OccasionTag).filter(OccasionTag.status == "proposed").count(),
        recipes_below_trust_threshold=db.query(Recipe).filter(Recipe.trust_score < TRUST_SCORE_REVIEW_THRESHOLD).count(),
        unmatched_ingredient_lines=db.query(RecipeIngredient).filter(RecipeIngredient.ingredient_id.is_(None)).count(),
        total_users=db.query(User).count(),
        total_reviews=db.query(Review).count(),
    )
