"""add knowledge_sources table

Revision ID: a006
Revises: a005
Create Date: 2026-04-11
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a006"
down_revision: Union[str, None] = "a005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_sources (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL,
            bot_id      UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
            type        TEXT NOT NULL,
            name        TEXT NOT NULL,
            file_path   TEXT,
            url         TEXT,
            status      TEXT NOT NULL DEFAULT 'pending',
            chunk_count INT  NOT NULL DEFAULT 0,
            error_msg   TEXT,
            created_by  UUID NOT NULL REFERENCES users(id),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_tenant ON knowledge_sources(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_bot    ON knowledge_sources(bot_id, status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS knowledge_sources CASCADE")
