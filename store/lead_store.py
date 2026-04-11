"""Lead 询盘线索数据访问层"""
import json

import asyncpg

from store.base import fetch_one, fetch_all, execute_returning, execute, fetch_val


async def create_lead(
    pool: asyncpg.Pool,
    tenant_id: str,
    bot_id: str,
    session_id: str,
    lead_info: dict,
    intent_score: float = 0.5,
) -> dict:
    row = await execute_returning(
        pool,
        """
        INSERT INTO leads (tenant_id, bot_id, session_id, lead_info, intent_score)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, tenant_id, bot_id, session_id, lead_info,
                  status, intent_score, created_at
        """,
        tenant_id, bot_id, session_id,
        json.dumps(lead_info, ensure_ascii=False),
        intent_score,
    )
    return dict(row)


async def list_leads(
    pool: asyncpg.Pool,
    tenant_id: str,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    offset = (page - 1) * page_size
    where = "WHERE tenant_id = $1"
    args: list = [tenant_id]
    if status:
        where += " AND status = $2"
        args.append(status)

    rows = await fetch_all(
        pool,
        f"""
        SELECT id, bot_id, session_id, lead_info, status, intent_score, created_at
        FROM leads {where}
        ORDER BY intent_score DESC, created_at DESC
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
        """,
        *args, page_size, offset,
    )
    total = await fetch_val(
        pool,
        f"SELECT COUNT(*) FROM leads {where}",
        *args,
    )
    return [dict(r) for r in rows], int(total or 0)


async def update_lead_status(
    pool: asyncpg.Pool,
    lead_id: str,
    tenant_id: str,
    status: str,
) -> bool:
    result = await execute(
        pool,
        """
        UPDATE leads SET status = $1, updated_at = NOW()
        WHERE id = $2 AND tenant_id = $3
        """,
        status, lead_id, tenant_id,
    )
    return result == "UPDATE 1"


async def get_lead(
    pool: asyncpg.Pool, lead_id: str, tenant_id: str
) -> dict | None:
    row = await fetch_one(
        pool,
        "SELECT * FROM leads WHERE id = $1 AND tenant_id = $2",
        lead_id, tenant_id,
    )
    return dict(row) if row else None
