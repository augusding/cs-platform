"""add traces and spans tables

Revision ID: a014
Revises: a013
"""
from alembic import op

revision = "a014"
down_revision = "a013"


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            trace_id VARCHAR(36) NOT NULL,
            session_id VARCHAR(64),
            bot_id UUID NOT NULL,
            tenant_id UUID NOT NULL,
            channel VARCHAR(20) NOT NULL DEFAULT 'widget',
            user_query TEXT NOT NULL DEFAULT '',
            language VARCHAR(5) DEFAULT 'zh',
            intent VARCHAR(30),
            intent_confidence FLOAT,
            transform_strategy VARCHAR(30),
            grader_score FLOAT,
            attempts INT DEFAULT 0,
            is_grounded BOOLEAN,
            hallucination_action VARCHAR(20),
            cache_hit BOOLEAN DEFAULT FALSE,
            should_transfer BOOLEAN DEFAULT FALSE,
            total_latency_ms INT,
            llm_calls_count INT DEFAULT 0,
            llm_total_tokens INT DEFAULT 0,
            retrieval_chunks INT DEFAULT 0,
            answer_preview VARCHAR(200),
            exit_branch VARCHAR(30),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_traces_tenant_time
            ON traces (tenant_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_traces_bot_time
            ON traces (bot_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_traces_session
            ON traces (session_id);

        CREATE TABLE IF NOT EXISTS spans (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            trace_id VARCHAR(36) NOT NULL,
            parent_span_id VARCHAR(16),
            node VARCHAR(30) NOT NULL,
            operation VARCHAR(50),
            start_ms BIGINT NOT NULL DEFAULT 0,
            end_ms BIGINT DEFAULT 0,
            duration_ms INT DEFAULT 0,
            status VARCHAR(10) DEFAULT 'ok',
            error_msg TEXT DEFAULT '',
            attributes JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_spans_trace
            ON spans (trace_id);
        CREATE INDEX IF NOT EXISTS idx_spans_node_time
            ON spans (node, created_at DESC);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS spans; DROP TABLE IF EXISTS traces;")
