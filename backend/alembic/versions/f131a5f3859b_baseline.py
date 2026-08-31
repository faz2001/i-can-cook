"""baseline

Revision ID: f131a5f3859b
Revises:
Create Date: 2026-08-30 00:00:00.000000

This is `alembic revision --autogenerate -m "baseline"` run against the
models as they stood when Alembic was introduced, then hand-corrected
against db/schema.sql (the previously-authoritative, manually-applied
schema) so the two agree. Plain autogenerate output differed from
schema.sql in a few places, all fixed below:

- server_defaults: autogenerate renders a Python-side `server_default="x"`
  faithfully, but a few DEFAULTs that only exist in schema.sql (not
  mirrored on the model) were missing outright -- e.g. `users.role`'s
  CHECK, `ingredients.source`'s CHECK, `ingredients.created_at` itself
  (present in schema.sql, absent from the Ingredient model).
- check constraints: `__table_args__` CHECK constraints not present on a
  few models (`users.role`, `ingredients.source`, `pantry_items.
  storage_condition`) were added here to match schema.sql, since it's the
  source of truth for anything the models are missing.
- array columns: `TEXT[] DEFAULT '{}'` columns (`users.dietary_preferences/
  kitchen_equipment`, `recipes.tags`) needed their server_default rendered
  as `'{}'::text[]`, and plain `sa.String()` columns that schema.sql types
  as TEXT were switched to `sa.Text()` to match column-for-column (Postgres
  treats unbounded VARCHAR and TEXT identically, but schema.sql is explicit
  about TEXT everywhere, so this migration follows suit).
- indexes not expressed on any model column (`idx_recipes_cuisine`,
  `idx_recipes_source_type`, `idx_recipes_moderation_status`, and the GIN
  index `idx_recipes_tags`) and the `recipe_steps` UNIQUE(recipe_id,
  step_number) constraint were added by hand to match schema.sql.

Tables are created in FK dependency order; downgrade() drops them in
reverse.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f131a5f3859b"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- users & auth ---------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), nullable=False, server_default=sa.text("'user'::text")),
        sa.Column(
            "dietary_preferences",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "kitchen_equipment",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_users_email"),
        # Not on the User model -- schema.sql source of truth.
        sa.CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # -- ingredient taxonomy & recipe corpus -----------------------------
    op.create_table(
        "ingredients",
        sa.Column("canonical_id", sa.Text(), nullable=False, primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        # schema.sql leaves this nullable (no NOT NULL); the model declares
        # nullable=False, but schema.sql wins per the reconciliation rule.
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("unit_default", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default=sa.text("'sl_cook100'::text")),
        # Not on the Ingredient model at all -- schema.sql source of truth.
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "source IN ('sl_cook100', 'kaggle_epicurious')", name="ck_ingredients_source"
        ),
    )

    op.create_table(
        "recipes",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("name_native", sa.Text(), nullable=True),
        sa.Column("cuisine", sa.Text(), nullable=False),
        sa.Column("regional_origin", sa.Text(), nullable=True),
        sa.Column("course", sa.Text(), nullable=True),
        sa.Column("servings", sa.Integer(), nullable=True),
        sa.Column("prep_time_min", sa.Integer(), nullable=True),
        sa.Column("cook_time_min", sa.Integer(), nullable=True),
        sa.Column("total_time_min", sa.Integer(), nullable=True),
        sa.Column(
            "tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")
        ),
        sa.Column("ayurvedic_balance", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("calories_kcal", sa.Numeric(), nullable=True),
        sa.Column("protein_g", sa.Numeric(), nullable=True),
        sa.Column("carbs_g", sa.Numeric(), nullable=True),
        sa.Column("fat_g", sa.Numeric(), nullable=True),
        sa.Column("fibre_g", sa.Numeric(), nullable=True),
        sa.Column(
            "trust_score", sa.Numeric(3, 2), nullable=False, server_default=sa.text("0.50")
        ),
        sa.Column(
            "source_type", sa.Text(), nullable=False, server_default=sa.text("'imported'::text")
        ),
        sa.Column(
            "moderation_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'approved'::text"),
        ),
        sa.Column("submitted_by", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_site", sa.Text(), nullable=True),
        sa.Column("collection_method", sa.Text(), nullable=True),
        sa.Column("annotated_by", sa.Text(), nullable=True),
        sa.Column("annotation_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("average_rating", sa.Numeric(2, 1), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("trust_score BETWEEN 0 AND 1", name="ck_recipes_trust_score"),
        sa.CheckConstraint(
            "source_type IN ('curated', 'imported', 'community')", name="ck_recipes_source_type"
        ),
        sa.CheckConstraint(
            "moderation_status IN ('approved', 'pending', 'rejected')",
            name="ck_recipes_moderation_status",
        ),
    )
    # None of these four are expressed on the Recipe model (no indexed
    # columns for cuisine/source_type/moderation_status, and a GIN index
    # isn't reachable via plain Column(index=True)) -- added to match
    # schema.sql.
    op.create_index("idx_recipes_cuisine", "recipes", ["cuisine"])
    op.create_index("idx_recipes_source_type", "recipes", ["source_type"])
    op.create_index("idx_recipes_moderation_status", "recipes", ["moderation_status"])
    op.create_index(
        "idx_recipes_tags", "recipes", ["tags"], postgresql_using="gin"
    )

    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("recipe_id", sa.Text(), nullable=False),
        sa.Column("ingredient_id", sa.Text(), nullable=True),
        sa.Column("raw_name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.canonical_id"], ondelete="SET NULL"
        ),
    )
    op.create_index("idx_recipe_ingredients_recipe", "recipe_ingredients", ["recipe_id"])
    op.create_index("idx_recipe_ingredients_ingredient", "recipe_ingredients", ["ingredient_id"])

    op.create_table(
        "recipe_steps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("recipe_id", sa.Text(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        # Not on the RecipeStep model -- schema.sql source of truth.
        sa.UniqueConstraint("recipe_id", "step_number", name="uq_recipe_steps_recipe_step_number"),
    )
    op.create_index("idx_recipe_steps_recipe", "recipe_steps", ["recipe_id"])

    # -- pantry ------------------------------------------------------------
    op.create_table(
        "pantry_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Text(), nullable=True),
        sa.Column("raw_name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("storage_condition", sa.Text(), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("expiry_source", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.canonical_id"], ondelete="SET NULL"
        ),
        # Not on the PantryItem model -- schema.sql source of truth.
        sa.CheckConstraint(
            "storage_condition IN ('Refrigerated', 'Frozen', 'Pantry')",
            name="ck_pantry_items_storage_condition",
        ),
        sa.CheckConstraint(
            "expiry_source IN ('label', 'predicted')", name="ck_pantry_items_expiry_source"
        ),
    )
    op.create_index("idx_pantry_items_user", "pantry_items", ["user_id"])
    op.create_index("idx_pantry_items_ingredient", "pantry_items", ["ingredient_id"])
    op.create_index("idx_pantry_items_expiry", "pantry_items", ["expiry_date"])

    # -- community: reviews, occasion-tag voting, variation logging -------
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("recipe_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
        sa.UniqueConstraint("recipe_id", "user_id", name="uq_reviews_recipe_user"),
    )
    op.create_index("idx_reviews_recipe", "reviews", ["recipe_id"])

    op.create_table(
        "occasion_tags",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'proposed'::text")
        ),
        sa.Column("proposed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["proposed_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("label", name="uq_occasion_tags_label"),
        sa.CheckConstraint(
            "status IN ('approved', 'proposed', 'rejected')", name="ck_occasion_tags_status"
        ),
    )

    op.create_table(
        "recipe_occasion_votes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("recipe_id", sa.Text(), nullable=False),
        sa.Column("occasion_tag_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["occasion_tag_id"], ["occasion_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "recipe_id", "occasion_tag_id", "user_id", name="uq_recipe_occasion_votes_unique"
        ),
    )
    op.create_index("idx_recipe_occasion_votes_recipe", "recipe_occasion_votes", ["recipe_id"])

    op.create_table(
        "recipe_variations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("recipe_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("substitutions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_recipe_variations_recipe", "recipe_variations", ["recipe_id"])

    # -- admin: general tag vocabulary, trust score audit trail -----------
    op.create_table(
        "recipe_tag_vocabulary",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'approved'::text")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("label", name="uq_recipe_tag_vocabulary_label"),
        sa.CheckConstraint(
            "status IN ('approved', 'retired')", name="ck_recipe_tag_vocabulary_status"
        ),
    )

    op.create_table(
        "trust_score_audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("recipe_id", sa.Text(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("old_value", sa.Numeric(3, 2), nullable=True),
        sa.Column("new_value", sa.Numeric(3, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("idx_trust_score_audit_log_recipe", "trust_score_audit_log", ["recipe_id"])

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "recipe_id", name="uq_favorites_user_recipe"),
    )
    # Note: the Favorite model has index=True on user_id (so a real
    # autogenerate run would add an ix_favorites_user_id here), but
    # schema.sql has no standalone index on this column -- only the
    # composite UNIQUE(user_id, recipe_id) above, which already makes
    # user_id-prefixed lookups usable. Left out to match schema.sql exactly.

    op.create_table(
        "ingredient_substitutions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("canonical_id", sa.Text(), nullable=False),
        sa.Column("substitute_canonical_id", sa.Text(), nullable=True),
        sa.Column("substitute_name", sa.Text(), nullable=False),
        sa.Column("ratio", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index(
        "idx_ingredient_substitutions_canonical", "ingredient_substitutions", ["canonical_id"]
    )

    # -- bookmark collections & shopping lists -----------------------------
    op.create_table(
        "bookmark_collections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "name", name="uq_bookmark_collections_user_name"),
    )
    op.create_index("idx_bookmark_collections_user", "bookmark_collections", ["user_id"])

    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Text(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["collection_id"], ["bookmark_collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("collection_id", "recipe_id", name="uq_bookmarks_collection_recipe"),
    )
    op.create_index("idx_bookmarks_collection", "bookmarks", ["collection_id"])

    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["bookmark_collections.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("idx_shopping_lists_user", "shopping_lists", ["user_id"])

    op.create_table(
        "shopping_list_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("shopping_list_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("is_checked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["shopping_list_id"], ["shopping_lists.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_shopping_list_items_list", "shopping_list_items", ["shopping_list_id"])


def downgrade() -> None:
    op.drop_table("shopping_list_items")
    op.drop_table("shopping_lists")
    op.drop_table("bookmarks")
    op.drop_table("bookmark_collections")
    op.drop_table("ingredient_substitutions")
    op.drop_table("favorites")
    op.drop_table("trust_score_audit_log")
    op.drop_table("recipe_tag_vocabulary")
    op.drop_table("recipe_variations")
    op.drop_table("recipe_occasion_votes")
    op.drop_table("occasion_tags")
    op.drop_table("reviews")
    op.drop_table("pantry_items")
    op.drop_table("recipe_steps")
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")
    op.drop_table("ingredients")
    op.drop_table("users")
