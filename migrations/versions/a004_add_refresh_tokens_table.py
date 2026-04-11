"""add refresh tokens table

Revision ID: a004
Revises: a003
Create Date: 2026-04-11
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a004"
down_revision: Union[str, None] = "a003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tenant_id   UUID NOT NULL,
            token_hash  TEXT NOT NULL UNIQUE,
            expires_at  TIMESTAMPTZ NOT NULL,
            revoked_at  TIMESTAMPTZ,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS refresh_tokens CASCADE")
