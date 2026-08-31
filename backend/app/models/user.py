"""
STUB: minimal User model, just enough for pantry_items.user_id to FK against
and for a dependency to return a real row. Replace with the real Auth
module's User model when you paste those files back in -- don't keep both.
"""
from sqlalchemy import Column, Integer, String, ARRAY, Boolean, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user")
    is_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    dietary_preferences = Column(ARRAY(String), default=list)
    kitchen_equipment = Column(ARRAY(String), default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
