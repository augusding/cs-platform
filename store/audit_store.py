"""审计日志数据访问层（append-only）"""
import json
import logging
from datetime import date, datetime
from uuid import UUID

import asyncpg

from store.base import execute, fetch_all

logger = logging.getLogger(__name__)


async def log_action(
    pool: asyncpg.Pool,
    tenant_id: str,
    action: str,
    resource: str,
    resource_id: str | None = None,
    user_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    ip: str | None = None,
) -> None:
    """
    写入一条审计日志。失败时 log.error 但不抛出，避免业务路径被审计故障打断。
    action 命名约定：<resource>.<verb>（如 bot.create / member.role_change）。
    """
    try:
        await execute(
            pool,
            """
            INSERT INTO audit_log
                (tenant_id, user_id, action, resource, resource_id,
                 before_json, after_json, ip)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            tenant_id,
            user_id,
            action,
            resource,
            resource_id,
            json.dumps(before, ensure_ascii=False, default=str) if before else None,
            json.dumps(after, ensure_ascii=False, default=str) if after else None,
            ip,
        )
    except Exception as e:
        logger.error(f"Audit log write failed: {e}")


def _serialize(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


async def list_audit_log(
    pool: asyncpg.Pool,
    tenant_id: str,
    resource: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    if resource:
        rows = await fetch_all(
            pool,
            """
            SELECT id, user_id, action, resource, resource_id, ip, created_at
            FROM audit_log
            WHERE tenant_id = $1 AND resource = $2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
            """,
            tenant_id, resource, limit, offset,
        )
    else:
        rows = await fetch_all(
            pool,
            """
            SELECT id, user_id, action, resource, resource_id, ip, created_at
            FROM audit_log
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            tenant_id, limit, offset,
        )
    return [{k: _serialize(v) for k, v in dict(r).items()} for r in rows]
