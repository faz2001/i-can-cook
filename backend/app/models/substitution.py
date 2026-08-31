from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class IngredientSubstitution(Base):
    __tablename__ = "ingredient_substitutions"

    id = Column(Integer, primary_key=True)
    canonical_id = Column(String, nullable=False, index=True)
    substitute_canonical_id = Column(String, nullable=True)
    substitute_name = Column(String, nullable=False)
    ratio = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    context = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
