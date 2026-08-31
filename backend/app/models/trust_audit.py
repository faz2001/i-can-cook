from sqlalchemy import Column, Integer, Text, Numeric, TIMESTAMP, ForeignKey, func

from app.core.database import Base


class TrustScoreAuditLog(Base):
    """Editorial audit trail for /admin/trust-scores overrides -- who changed a recipe's
    Trust Score, from what, to what, and why. Append-only; never updated or deleted."""
    __tablename__ = "trust_score_audit_log"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Text, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    # RESTRICT (not SET NULL): this column is nullable=False, so an admin who
    # has made a trust-score override can't be deleted while their audit rows
    # still reference them -- that combination previously contradicted itself.
    admin_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    old_value = Column(Numeric(3, 2), nullable=True)
    new_value = Column(Numeric(3, 2), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
