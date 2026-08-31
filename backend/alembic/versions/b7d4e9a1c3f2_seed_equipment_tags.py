"""seed equipment tag vocabulary

Revision ID: b7d4e9a1c3f2
Revises: a3f9c1d2e6b0
Create Date: 2026-08-30 00:00:00.000001

Data-only migration (no schema change -- `recipe_tag_vocabulary` already exists
as of the baseline migration). Seeds `category='equipment'` rows so
GET /api/tags/equipment (app/routers/tags.py) has something to return.

The 8 values seeded here are exactly the list that used to be hardcoded as
EQUIPMENT_OPTIONS in frontend_final_pkg/src/pages/ProfilePage.tsx -- this
migration doesn't change what options a user sees, it just moves the source
of truth into the DB (behind the admin-manageable `recipe_tag_vocabulary`
table) so the frontend can fetch it instead of hardcoding a second copy that
can drift out of sync.

Deliberately NOT reusing RB-01's `equipment` keyword list (app/services/
rb01_intent.py) -- that vocabulary is for equipment mentioned in a search
query, not equipment a user owns, and doesn't match this list (e.g. it's
missing "Air Fryer" / "Pressure Cooker", and includes "no-equipment", which
isn't a sensible "owned appliance" checkbox). See the placement-decision
comment at the top of rb01_intent.py.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7d4e9a1c3f2"
down_revision: Union[str, None] = "a3f9c1d2e6b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EQUIPMENT_LABELS = [
    "Stove Top", "Oven", "Rice Cooker", "Blender",
    "Air Fryer", "Pressure Cooker", "Microwave", "Grill",
]

recipe_tag_vocabulary = sa.table(
    "recipe_tag_vocabulary",
    sa.column("id", sa.Text),
    sa.column("label", sa.Text),
    sa.column("category", sa.Text),
    sa.column("status", sa.Text),
)


def _slugify_tag(label: str) -> str:
    # Matches app/routers/admin_tags.py's _slugify_tag exactly, so tags
    # created through this seed and tags created later through the admin
    # UI end up with consistent ids.
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    return f"tag_{slug}"


def upgrade() -> None:
    op.bulk_insert(
        recipe_tag_vocabulary,
        [
            {"id": _slugify_tag(label), "label": label, "category": "equipment", "status": "approved"}
            for label in EQUIPMENT_LABELS
        ],
    )


def downgrade() -> None:
    op.execute(
        recipe_tag_vocabulary.delete().where(recipe_tag_vocabulary.c.category == "equipment")
    )
