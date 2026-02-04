"""change verification token to 4-digit code

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-04 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clear old long-format tokens — they are incompatible with the new 4-digit codes
    op.execute("DELETE FROM verification_tokens")
    # Drop unique index on token (4-digit codes are not globally unique)
    op.drop_index("ix_verification_tokens_token", table_name="verification_tokens")
    # Shrink column from String(255) to String(4)
    op.alter_column(
        "verification_tokens",
        "token",
        type_=sa.String(4),
        existing_type=sa.String(255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "verification_tokens",
        "token",
        type_=sa.String(255),
        existing_type=sa.String(4),
        existing_nullable=False,
    )
    op.create_index(
        "ix_verification_tokens_token",
        "verification_tokens",
        ["token"],
        unique=True,
    )
