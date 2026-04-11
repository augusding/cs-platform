"""add tenants table

Revision ID: a001
Revises:
Create Date: 2026-04-10
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name                TEXT NOT NULL,
            plan                TEXT NOT NULL DEFAULT 'free',
            status              TEXT NOT NULL DEFAULT 'active',
            max_bots            INT  NOT NULL DEFAULT 1,
            monthly_quota       INT  NOT NULL DEFAULT 200,
            current_month_msgs  INT  NOT NULL DEFAULT 0,
            master_api_key      TEXT NOT NULL UNIQUE,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_tenants_status    ON tenants(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tenants_api_key   ON tenants(master_api_key)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")
