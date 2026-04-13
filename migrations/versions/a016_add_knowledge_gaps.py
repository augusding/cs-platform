"""add knowledge_gaps table

Revision ID: a016
Revises: a015
"""
from alembic import op

revision = "a016"
down_revision = "a015"


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_gaps (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL,
            bot_id          UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,

            cluster_label   TEXT NOT NULL,
            sample_queries  JSONB NOT NULL DEFAULT '[]',
            query_count     INT NOT NULL DEFAULT 1,
            unique_sessions INT NOT NULL DEFAULT 1,

            avg_grader_score    FLOAT,
            primary_signal      TEXT NOT NULL DEFAULT 'low_grader',
            signal_breakdown    JSONB DEFAULT '{}',

            suggested_content   TEXT,

            status          TEXT NOT NULL DEFAULT 'open',
            resolved_at     TIMESTAMPTZ,
            resolved_by     UUID,
            dismiss_reason  TEXT,

            first_seen      TIMESTAMPTZ,
            last_seen       TIMESTAMPTZ,

            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_gaps_tenant_bot
            ON knowledge_gaps (tenant_id, bot_id, status);
        CREATE INDEX IF NOT EXISTS idx_gaps_status
            ON knowledge_gaps (status, query_count DESC);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS knowledge_gaps CASCADE;")
