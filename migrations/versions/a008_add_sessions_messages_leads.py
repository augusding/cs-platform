"""add sessions messages leads tables

Revision ID: a008
Revises: a007
Create Date: 2026-04-11
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a008"
down_revision: Union[str, None] = "a007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL,
            bot_id          UUID NOT NULL REFERENCES bots(id),
            visitor_id      TEXT NOT NULL,
            language        TEXT NOT NULL DEFAULT 'zh',
            status          TEXT NOT NULL DEFAULT 'active',
            transferred_to  UUID REFERENCES users(id),
            lead_id         UUID,
            started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at        TIMESTAMPTZ,
            message_count   INT NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_tenant ON sessions(tenant_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_bot    ON sessions(bot_id, started_at DESC)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id   UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            tenant_id    UUID NOT NULL,
            role         TEXT NOT NULL,
            content      TEXT NOT NULL,
            grader_score FLOAT,
            is_grounded  BOOLEAN,
            tokens_used  INT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id    UUID NOT NULL,
            bot_id       UUID NOT NULL,
            session_id   UUID REFERENCES sessions(id),
            lead_info    JSONB NOT NULL DEFAULT '{}',
            status       TEXT NOT NULL DEFAULT 'new',
            intent_score FLOAT NOT NULL DEFAULT 0.5,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_tenant ON leads(tenant_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_leads_intent ON leads(tenant_id, intent_score DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS leads CASCADE")
    op.execute("DROP TABLE IF EXISTS messages CASCADE")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE")
