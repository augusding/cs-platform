"""RefreshToken 数据访问层"""
from datetime import datetime, timezone, timedelta

import asyncpg

from config import settings
from store.base import fetch_one, execute_returning, execute


async def create_refresh_token(
    pool: asyncpg.Pool,
    user_id: str,
    tenant_id: str,
    token_hash: str,
) -> dict:
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    row = await execute_returning(
        pool,
        """
        INSERT INTO refresh_tokens (user_id, tenant_id, token_hash, expires_at)
        VALUES ($1, $2, $3, $4)
        RETURNING id, expires_at
        """,
        user_id, tenant_id, token_hash, expires_at,
    )
    return dict(row)


async def get_refresh_token(
    pool: asyncpg.Pool, token_hash: str
) -> dict | None:
    row = await fetch_one(
        pool,
        """
        SELECT rt.*, u.tenant_id AS u_tenant_id, u.role, u.status AS user_status
        FROM refresh_tokens rt
        JOIN users u ON u.id = rt.user_id
        WHERE rt.token_hash = $1
          AND rt.revoked_at IS NULL
          AND rt.expires_at > NOW()
        """,
        token_hash,
    )
    return dict(row) if row else None


async def revoke_refresh_token(pool: asyncpg.Pool, token_hash: str) -> None:
    await execute(
        pool,
        "UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = $1",
        token_hash,
    )


async def revoke_all_user_tokens(pool: asyncpg.Pool, user_id: str) -> None:
    """登出或改密时吊销该用户所有 refresh token"""
    await execute(
        pool,
        """
        UPDATE refresh_tokens SET revoked_at = NOW()
        WHERE user_id = $1 AND revoked_at IS NULL
        """,
        user_id,
    )
