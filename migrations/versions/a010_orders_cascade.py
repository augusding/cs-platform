"""orders.tenant_id FK -> ON DELETE CASCADE

Revision ID: a010
Revises: a009
Create Date: 2026-04-11

Rationale: Week 6 added the orders table with a non-cascading FK to tenants.
Deleting a tenant (tests or tenant termination) therefore fails. Cascade the
FK so test cleanup and tenant retirement are consistent with the other
multi-tenant tables (users/bots/etc.).
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a010"
down_revision: Union[str, None] = "a009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_tenant_id_fkey")
    op.execute(
        "ALTER TABLE orders "
        "ADD CONSTRAINT orders_tenant_id_fkey "
        "FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_tenant_id_fkey")
    op.execute(
        "ALTER TABLE orders "
        "ADD CONSTRAINT orders_tenant_id_fkey "
        "FOREIGN KEY (tenant_id) REFERENCES tenants(id)"
    )
