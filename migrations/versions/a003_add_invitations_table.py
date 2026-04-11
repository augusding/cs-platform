"""add invitations table

Revision ID: a003
Revises: a002
Create Date: 2026-04-10
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a003"
down_revision: Union[str, None] = "a002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS invitations (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            inviter_id  UUID NOT NULL REFERENCES users(id),
            email       TEXT NOT NULL,
            role        TEXT NOT NULL,
            token       TEXT NOT NULL UNIQUE,
            expires_at  TIMESTAMPTZ NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_invitations_tenant ON invitations(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_invitations_token  ON invitations(token)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS invitations CASCADE")
