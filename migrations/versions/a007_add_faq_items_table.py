"""add faq_items table

Revision ID: a007
Revises: a006
Create Date: 2026-04-11
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a007"
down_revision: Union[str, None] = "a006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS faq_items (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL,
            bot_id      UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
            question    TEXT NOT NULL,
            answer      TEXT NOT NULL,
            priority    INT  NOT NULL DEFAULT 0,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            created_by  UUID NOT NULL REFERENCES users(id),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_faq_bot ON faq_items(bot_id, is_active)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS faq_items CASCADE")
