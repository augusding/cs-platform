"""add is_demo flag to bots

Revision ID: a015
Revises: a014
"""
from alembic import op

revision = "a015"
down_revision = "a014"


def upgrade():
    op.execute("""
        ALTER TABLE bots ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT FALSE;
        CREATE INDEX IF NOT EXISTS idx_bots_demo ON bots(is_demo) WHERE is_demo = TRUE;
    """)


def downgrade():
    op.execute("ALTER TABLE bots DROP COLUMN IF EXISTS is_demo;")
