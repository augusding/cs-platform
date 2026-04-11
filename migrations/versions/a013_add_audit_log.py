"""add audit_log table

Revision ID: a013
Revises: a012
Create Date: 2026-04-11
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a013"
down_revision: Union[str, None] = "a012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL,
            user_id     UUID,
            action      TEXT NOT NULL,
            resource    TEXT NOT NULL,
            resource_id TEXT,
            before_json JSONB,
            after_json  JSONB,
            ip          TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_tenant "
        "ON audit_log(tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_resource "
        "ON audit_log(resource, resource_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")
