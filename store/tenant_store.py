"""Tenant 数据访问层"""
import os
import asyncpg

from store.base import fetch_one, execute_returning


async def create_tenant(pool: asyncpg.Pool, name: str) -> dict:
    master_key = "cs_master_" + os.urandom(16).hex()
    row = await execute_returning(
        pool,
        """
        INSERT INTO tenants (name, master_api_key)
        VALUES ($1, $2)
        RETURNING id, name, plan, status, max_bots, monthly_quota, master_api_key, created_at
        """,
        name, master_key,
    )
    return dict(row)


async def get_tenant(pool: asyncpg.Pool, tenant_id: str) -> dict | None:
    row = await fetch_one(
        pool,
        "SELECT * FROM tenants WHERE id = $1",
        tenant_id,
    )
    return dict(row) if row else None
