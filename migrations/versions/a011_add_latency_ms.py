"""add latency_ms to messages + is_resolved to sessions

Revision ID: a011
Revises: a010
Create Date: 2026-04-11
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a011"
down_revision: Union[str, None] = "a010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS latency_ms INT")
    op.execute("ALTER TABLE sessions  ADD COLUMN IF NOT EXISTS is_resolved BOOLEAN DEFAULT FALSE")


def downgrade() -> None:
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS latency_ms")
    op.execute("ALTER TABLE sessions  DROP COLUMN IF EXISTS is_resolved")
