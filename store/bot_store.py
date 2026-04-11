"""Bot 数据访问层"""
import os

import asyncpg

from store.base import fetch_one, fetch_all, execute_returning, execute, fetch_val


def _generate_bot_api_key() -> str:
    return "cs_bot_" + os.urandom(16).hex()


async def create_bot(
    pool: asyncpg.Pool,
    tenant_id: str,
    created_by: str,
    name: str,
    welcome_message: str = "您好，有什么可以帮您？",
    language: str = "zh",
    style: str = "friendly",
    system_prompt: str | None = None,
) -> dict:
    api_key = _generate_bot_api_key()
    row = await execute_returning(
        pool,
        """
        INSERT INTO bots
            (tenant_id, created_by, name, welcome_message,
             language, style, system_prompt, bot_api_key)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """,
        tenant_id, created_by, name, welcome_message,
        language, style, system_prompt, api_key,
    )
    return dict(row)


async def list_bots(pool: asyncpg.Pool, tenant_id: str) -> list[dict]:
    rows = await fetch_all(
        pool,
        """
        SELECT * FROM bots
        WHERE tenant_id = $1 AND status != 'deleted'
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    return [dict(r) for r in rows]


async def get_bot(
    pool: asyncpg.Pool, bot_id: str, tenant_id: str
) -> dict | None:
    row = await fetch_one(
        pool,
        "SELECT * FROM bots WHERE id = $1 AND tenant_id = $2",
        bot_id, tenant_id,
    )
    return dict(row) if row else None


async def update_bot(
    pool: asyncpg.Pool,
    bot_id: str,
    tenant_id: str,
    **fields,
) -> dict | None:
    allowed = {
        "name", "welcome_message", "language", "style",
        "system_prompt", "avatar_url",
        "lead_capture_fields", "private_domain_config",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return await get_bot(pool, bot_id, tenant_id)

    set_clause = ", ".join(
        f"{col} = ${i + 3}" for i, col in enumerate(updates)
    )
    values = list(updates.values())
    row = await execute_returning(
        pool,
        f"""
        UPDATE bots
        SET {set_clause}, updated_at = NOW()
        WHERE id = $1 AND tenant_id = $2
        RETURNING *
        """,
        bot_id, tenant_id, *values,
    )
    return dict(row) if row else None


async def delete_bot(
    pool: asyncpg.Pool, bot_id: str, tenant_id: str
) -> bool:
    result = await execute(
        pool,
        "UPDATE bots SET status = 'deleted' WHERE id = $1 AND tenant_id = $2",
        bot_id, tenant_id,
    )
    return result == "UPDATE 1"


async def rotate_api_key(
    pool: asyncpg.Pool, bot_id: str, tenant_id: str
) -> dict | None:
    new_key = _generate_bot_api_key()
    row = await execute_returning(
        pool,
        """
        UPDATE bots SET bot_api_key = $1, updated_at = NOW()
        WHERE id = $2 AND tenant_id = $3
        RETURNING id, bot_api_key
        """,
        new_key, bot_id, tenant_id,
    )
    return dict(row) if row else None


async def get_bot_by_api_key(
    pool: asyncpg.Pool, api_key: str
) -> dict | None:
    """Used by JWT middleware to resolve bot API keys on widget/chat routes."""
    try:
        row = await fetch_one(
            pool,
            """
            SELECT id, tenant_id, name, status
            FROM bots
            WHERE bot_api_key = $1 AND status = 'active'
            """,
            api_key,
        )
        return dict(row) if row else None
    except asyncpg.UndefinedTableError:
        return None


async def count_bots(pool: asyncpg.Pool, tenant_id: str) -> int:
    return await fetch_val(
        pool,
        "SELECT COUNT(*) FROM bots WHERE tenant_id = $1 AND status != 'deleted'",
        tenant_id,
    )
