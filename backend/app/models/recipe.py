from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Date, ARRAY,
    TIMESTAMP, ForeignKey, CheckConstraint, func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Text, primary_key=True)  # 'sl_013' curated, uuid-based imported/community
    name_en = Column(Text, nullable=False)
    name_native = Column(Text, nullable=True)
    cuisine = Column(Text, nullable=False)
    regional_origin = Column(Text, nullable=True)
    course = Column(Text, nullable=True)
    servings = Column(Integer, nullable=True)
    prep_time_min = Column(Integer, nullable=True)
    cook_time_min = Column(Integer, nullable=True)
    total_time_min = Column(Integer, nullable=True)
    tags = Column(ARRAY(Text), nullable=False, server_default="{}")
    ayurvedic_balance = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)  # course-based fallback, set at ingest time

    calories_kcal = Column(Numeric, nullable=True)
    protein_g = Column(Numeric, nullable=True)
    carbs_g = Column(Numeric, nullable=True)
    fat_g = Column(Numeric, nullable=True)
    fibre_g = Column(Numeric, nullable=True)

    trust_score = Column(Numeric(3, 2), nullable=False, server_default="0.50")
    source_type = Column(Text, nullable=False, server_default="imported")
    moderation_status = Column(Text, nullable=False, server_default="approved")
    submitted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    source_url = Column(Text, nullable=True)
    source_site = Column(Text, nullable=True)
    collection_method = Column(Text, nullable=True)
    annotated_by = Column(Text, nullable=True)
    annotation_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    average_rating = Column(Numeric(2, 1), nullable=True)  # denormalised from reviews
    review_count = Column(Integer, nullable=False, server_default="0")

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("trust_score BETWEEN 0 AND 1", name="ck_recipes_trust_score"),
        CheckConstraint("source_type IN ('curated', 'imported', 'community')", name="ck_recipes_source_type"),
        CheckConstraint("moderation_status IN ('approved', 'pending', 'rejected')", name="ck_recipes_moderation_status"),
    )

    ingredients = relationship(
        "RecipeIngredient", back_populates="recipe", order_by="RecipeIngredient.position",
        cascade="all, delete-orphan",
    )
    steps = relationship(
        "RecipeStep", back_populates="recipe", order_by="RecipeStep.step_number",
        cascade="all, delete-orphan",
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Text, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id = Column(Text, ForeignKey("ingredients.canonical_id", ondelete="SET NULL"), nullable=True, index=True)
    raw_name = Column(Text, nullable=False)  # original ingredient text, kept after canonical matching
    quantity = Column(Numeric, nullable=True)
    unit = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    position = Column(Integer, nullable=False, server_default="0")

    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient")


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Text, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    instruction = Column(Text, nullable=False)
    duration_min = Column(Integer, nullable=True)

    recipe = relationship("Recipe", back_populates="steps")
