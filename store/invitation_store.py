"""Invitation 数据访问层"""
from datetime import datetime, timezone, timedelta

import asyncpg

from config import settings
from store.base import fetch_one, execute_returning, execute


async def create_invitation(
    pool: asyncpg.Pool,
    tenant_id: str,
    inviter_id: str,
    email: str,
    role: str,
    token: str,
) -> dict:
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.INVITATION_EXPIRE_DAYS
    )
    row = await execute_returning(
        pool,
        """
        INSERT INTO invitations (tenant_id, inviter_id, email, role, token, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, tenant_id, email, role, token, expires_at, status
        """,
        tenant_id, inviter_id, email, role, token, expires_at,
    )
    return dict(row)


async def get_invitation_by_token(
    pool: asyncpg.Pool, token: str
) -> dict | None:
    row = await fetch_one(
        pool,
        """
        SELECT * FROM invitations
        WHERE token = $1 AND status = 'pending' AND expires_at > NOW()
        """,
        token,
    )
    return dict(row) if row else None


async def accept_invitation(pool: asyncpg.Pool, invitation_id: str) -> None:
    await execute(
        pool,
        "UPDATE invitations SET status = 'accepted' WHERE id = $1",
        invitation_id,
    )
