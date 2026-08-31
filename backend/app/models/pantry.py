from sqlalchemy import (
    Column, Integer, Text, Numeric, Date, ForeignKey,
    TIMESTAMP, CheckConstraint, func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class PantryItem(Base):
    __tablename__ = "pantry_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Fixed: the Ingredient model's primary key column is `canonical_id`,
    # not `id` -- the original version of this file predates
    # app/models/ingredient.py and pointed at the wrong column name.
    ingredient_id = Column(Text, ForeignKey("ingredients.canonical_id", ondelete="SET NULL"), nullable=True, index=True)
    raw_name = Column(Text, nullable=False)
    quantity = Column(Numeric, nullable=True)
    unit = Column(Text, nullable=True)
    storage_condition = Column(Text, nullable=True)
    purchase_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True, index=True)
    expiry_source = Column(Text, nullable=True)  # 'label' | 'predicted'

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    ingredient = relationship("Ingredient")

    __table_args__ = (
        CheckConstraint("expiry_source IN ('label', 'predicted')", name="ck_pantry_items_expiry_source"),
    )
