"""add users table

Revision ID: a002
Revises: a001
Create Date: 2026-04-10
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a002"
down_revision: Union[str, None] = "a001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            email           TEXT NOT NULL UNIQUE,
            password_hash   TEXT,
            name            TEXT NOT NULL DEFAULT '',
            role            TEXT NOT NULL DEFAULT 'operator',
            status          TEXT NOT NULL DEFAULT 'invited',
            last_login_at   TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email  ON users(email)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users CASCADE")
