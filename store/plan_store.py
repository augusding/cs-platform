"""套餐与订单数据访问层"""
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg

from store.base import fetch_one, execute_returning, execute

PLAN_CONFIG: dict[str, dict] = {
    "free":   {"max_bots": 1,  "monthly_quota": 200,   "price_fen": 0},
    "entity": {"max_bots": 3,  "monthly_quota": 5000,  "price_fen": 19900},
    "trade":  {"max_bots": 3,  "monthly_quota": 5000,  "price_fen": 29900},
    "pro":    {"max_bots": 10, "monthly_quota": -1,    "price_fen": 59900},
}


async def get_tenant_plan(pool: asyncpg.Pool, tenant_id: str) -> dict:
    row = await fetch_one(
        pool,
        """
        SELECT plan, max_bots, monthly_quota, plan_expires_at
        FROM tenants WHERE id = $1
        """,
        tenant_id,
    )
    return dict(row) if row else {}


async def upgrade_plan(
    pool: asyncpg.Pool, tenant_id: str, new_plan: str
) -> None:
    cfg = PLAN_CONFIG.get(new_plan)
    if not cfg:
        raise ValueError(f"Unknown plan: {new_plan}")
    expires = datetime.now(timezone.utc) + timedelta(days=31)
    await execute(
        pool,
        """
        UPDATE tenants
        SET plan = $1, max_bots = $2, monthly_quota = $3,
            plan_expires_at = $4, updated_at = NOW()
        WHERE id = $5
        """,
        new_plan, cfg["max_bots"], cfg["monthly_quota"], expires, tenant_id,
    )


async def create_order(
    pool: asyncpg.Pool,
    tenant_id: str,
    plan: str,
    pay_method: str = "wechat",
) -> dict:
    cfg = PLAN_CONFIG.get(plan)
    if not cfg:
        raise ValueError(f"Unknown plan: {plan}")
    out_trade_no = (
        "CS"
        + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        + uuid.uuid4().hex[:8].upper()
    )
    row = await execute_returning(
        pool,
        """
        INSERT INTO orders (tenant_id, plan, amount_fen, pay_method, out_trade_no)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, out_trade_no, amount_fen, status, plan
        """,
        tenant_id, plan, cfg["price_fen"], pay_method, out_trade_no,
    )
    return dict(row)


async def confirm_order(
    pool: asyncpg.Pool, out_trade_no: str, transaction_id: str
) -> str | None:
    """确认订单已支付，返回对应 tenant_id，订单不存在或已支付返回 None。"""
    row = await fetch_one(
        pool,
        """
        SELECT id, tenant_id, plan FROM orders
        WHERE out_trade_no = $1 AND status = 'pending'
        """,
        out_trade_no,
    )
    if not row:
        return None
    await execute(
        pool,
        """
        UPDATE orders
        SET status = 'paid', transaction_id = $1, paid_at = NOW()
        WHERE out_trade_no = $2
        """,
        transaction_id, out_trade_no,
    )
    await upgrade_plan(pool, str(row["tenant_id"]), row["plan"])
    return str(row["tenant_id"])
