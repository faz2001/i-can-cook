"""add email verification

Revision ID: a3f9c1d2e6b0
Revises: f131a5f3859b
Create Date: 2026-08-30 00:00:00.000000

Adds `users.is_verified` and the `email_verification_tokens` table.

This is deliberately a separate migration from baseline, not folded into
it, so that `alembic stamp <revision>` gives you a real choice of where a
pre-existing database (e.g. the seeded dump, which predates this feature)
actually sits in history:

    gunzip -c icancook_seeded_dump_sql.gz | psql -d icancook
    alembic stamp f131a5f3859b   # dump already has everything baseline creates
    alembic upgrade head         # actually runs this migration for real,
                                  # adding is_verified + email_verification_tokens

Stamping straight to `head` (skipping this migration too) would leave a
database that's missing both -- the app expects `users.is_verified` to
exist and would fail validating `UserOut` / calling `/api/auth/verify` and
`/api/auth/resend-verification` against a database stamped that way.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a3f9c1d2e6b0"
down_revision: Union[str, None] = "f131a5f3859b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token", name="uq_email_verification_tokens_token"),
    )
    op.create_index("idx_email_verification_tokens_user", "email_verification_tokens", ["user_id"])
    op.create_index("idx_email_verification_tokens_token", "email_verification_tokens", ["token"])


def downgrade() -> None:
    op.drop_table("email_verification_tokens")
    op.drop_column("users", "is_verified")
