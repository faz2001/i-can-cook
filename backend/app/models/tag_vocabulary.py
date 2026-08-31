from sqlalchemy import Column, Text, TIMESTAMP, CheckConstraint, func

from app.core.database import Base


class RecipeTagVocabulary(Base):
    """The ~80 controlled semantic tags (tag_vocabulary.json), now DB-backed so
    /admin/tags can manage them through the API instead of hand-editing the JSON file.
    Distinct from OccasionTag (app/models/community.py), which is the narrower
    community-voted 'what occasion is this for' vocabulary."""
    __tablename__ = "recipe_tag_vocabulary"

    id = Column(Text, primary_key=True)     # slug, e.g. 'tag_one_pot'
    label = Column(Text, nullable=False, unique=True)
    category = Column(Text, nullable=True)  # e.g. 'cooking_method', 'dietary', 'flavor'
    status = Column(Text, nullable=False, server_default="approved")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('approved', 'retired')", name="ck_recipe_tag_vocabulary_status"),
    )
