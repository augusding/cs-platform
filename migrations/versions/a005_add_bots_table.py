"""add bots table

Revision ID: a005
Revises: a004
Create Date: 2026-04-11
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a005"
down_revision: Union[str, None] = "a004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id             UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name                  TEXT NOT NULL,
            avatar_url            TEXT,
            welcome_message       TEXT NOT NULL DEFAULT '您好，有什么可以帮您？',
            language              TEXT NOT NULL DEFAULT 'zh',
            style                 TEXT NOT NULL DEFAULT 'friendly',
            system_prompt         TEXT,
            bot_api_key           TEXT NOT NULL UNIQUE,
            lead_capture_fields   JSONB NOT NULL DEFAULT '[]',
            private_domain_config JSONB,
            status                TEXT NOT NULL DEFAULT 'active',
            created_by            UUID NOT NULL REFERENCES users(id),
            created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bots_tenant  ON bots(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bots_api_key ON bots(bot_api_key)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bots CASCADE")
