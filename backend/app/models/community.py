from sqlalchemy import (
    Column, Integer, Text, TIMESTAMP, ForeignKey,
    CheckConstraint, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Text, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
        UniqueConstraint("recipe_id", "user_id", name="uq_reviews_recipe_user"),
    )


class OccasionTag(Base):
    __tablename__ = "occasion_tags"

    id = Column(Text, primary_key=True)   # slug, e.g. 'occ_rainy_day'
    label = Column(Text, nullable=False, unique=True)
    status = Column(Text, nullable=False, server_default="proposed")
    proposed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('approved', 'proposed', 'rejected')", name="ck_occasion_tags_status"),
    )


class RecipeOccasionVote(Base):
    __tablename__ = "recipe_occasion_votes"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Text, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    occasion_tag_id = Column(Text, ForeignKey("occasion_tags.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("recipe_id", "occasion_tag_id", "user_id", name="uq_recipe_occasion_votes_unique"),
    )


class RecipeVariation(Base):
    __tablename__ = "recipe_variations"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Text, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    substitutions = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
