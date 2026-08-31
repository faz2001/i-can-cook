from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, Numeric, Text, TIMESTAMP,
    UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class BookmarkCollection(Base):
    __tablename__ = "bookmark_collections"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_bookmark_collections_user_name"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    bookmarks = relationship("Bookmark", back_populates="collection", cascade="all, delete-orphan")


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("collection_id", "recipe_id", name="uq_bookmarks_collection_recipe"),)

    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey("bookmark_collections.id", ondelete="CASCADE"), nullable=False, index=True)
    recipe_id = Column(Text, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    collection = relationship("BookmarkCollection", back_populates="bookmarks")
    recipe = relationship("Recipe")


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("bookmark_collections.id", ondelete="SET NULL"), nullable=True)
    name = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    items = relationship("ShoppingListItem", back_populates="shopping_list", cascade="all, delete-orphan")


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id = Column(Integer, primary_key=True)
    shopping_list_id = Column(Integer, ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    quantity = Column(Numeric, nullable=True)
    unit = Column(Text, nullable=True)
    is_checked = Column(Boolean, nullable=False, server_default="false")
    # True for a manually-typed item, False for one generated from a recipe's ingredients.
    is_manual = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    shopping_list = relationship("ShoppingList", back_populates="items")
