from sqlalchemy import Column, String

from app.core.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    canonical_id = Column(String, primary_key=True)  # e.g. 'ing_chicken'
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    unit_default = Column(String, nullable=True)
    # Provenance only -- NOT a second foreign-key target. canonical_id stays one
    # shared ID space across every source so pantry matching, substitutions, and
    # shopping-list dedup keep working across SL-Cook100 and imported recipes alike.
    source = Column(String, nullable=False, server_default="sl_cook100")
