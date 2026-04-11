"""add plan fields to tenants

Revision ID: a009
Revises: a008
Create Date: 2026-04-11
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a009"
down_revision: Union[str, None] = "a008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS billing_email TEXT")
    op.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            plan            TEXT NOT NULL,
            amount_fen      INT  NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending',
            pay_method      TEXT NOT NULL DEFAULT 'wechat',
            out_trade_no    TEXT NOT NULL UNIQUE,
            transaction_id  TEXT,
            paid_at         TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_tenant ON orders(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_trade  ON orders(out_trade_no)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS orders CASCADE")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS plan_expires_at")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS billing_email")
