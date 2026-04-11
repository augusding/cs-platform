"""User 数据访问层"""
import asyncpg

from store.base import fetch_one, execute_returning, execute


async def create_user(
    pool: asyncpg.Pool,
    tenant_id: str,
    email: str,
    name: str,
    role: str,
    password_hash: str | None = None,
    status: str = "active",
) -> dict:
    row = await execute_returning(
        pool,
        """
        INSERT INTO users (tenant_id, email, name, role, password_hash, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, tenant_id, email, name, role, status, created_at
        """,
        tenant_id, email, name, role, password_hash, status,
    )
    return dict(row)


async def get_user_by_email(pool: asyncpg.Pool, email: str) -> dict | None:
    row = await fetch_one(
        pool,
        "SELECT * FROM users WHERE email = $1",
        email,
    )
    return dict(row) if row else None


async def get_user(
    pool: asyncpg.Pool, user_id: str, tenant_id: str
) -> dict | None:
    row = await fetch_one(
        pool,
        "SELECT * FROM users WHERE id = $1 AND tenant_id = $2",
        user_id, tenant_id,
    )
    return dict(row) if row else None


async def update_last_login(pool: asyncpg.Pool, user_id: str) -> None:
    await execute(
        pool,
        "UPDATE users SET last_login_at = NOW() WHERE id = $1",
        user_id,
    )


async def activate_user(
    pool: asyncpg.Pool, user_id: str, password_hash: str
) -> None:
    await execute(
        pool,
        "UPDATE users SET status = 'active', password_hash = $1 WHERE id = $2",
        password_hash, user_id,
    )
