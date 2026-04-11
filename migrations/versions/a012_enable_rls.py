"""enable row-level security on all tenant-scoped tables

Revision ID: a012
Revises: a011
Create Date: 2026-04-11

Note: RLS is enabled without FORCE so the table owner (cs_user) bypasses
policies. Policies become active for read-only/analytics roles or when
the app explicitly switches to a non-owner role. Existing queries with
`WHERE tenant_id = $1` continue to work unchanged; session-var based
_rls helpers are provided as a second line of defense.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "a012"
down_revision: Union[str, None] = "a011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    "bots",
    "knowledge_sources",
    "faq_items",
    "sessions",
    "messages",
    "leads",
    "orders",
]


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"DROP POLICY IF EXISTS tenant_isolation ON {table}"
        )
        # 允许：未设置 session var（owner / 旧代码）时放行，或 tenant_id 匹配 session var
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                current_setting('app.current_tenant_id', TRUE) = ''
                OR current_setting('app.current_tenant_id', TRUE) IS NULL
                OR tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
            )
            """
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
