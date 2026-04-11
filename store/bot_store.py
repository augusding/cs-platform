"""
Bot 数据访问层。
Week 2 实现完整 CRUD，当前仅提供 middleware 所需的 api_key 查询。
"""
import asyncpg
from store.base import fetch_one


async def get_bot_by_api_key(
    pool: asyncpg.Pool, api_key: str
) -> dict | None:
    """通过 bot_api_key 查找 Bot，供 JWT 中间件使用。
    
    bots 表在 Week 2 第1天创建，此前调用返回 None（不会崩溃）。
    """
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
        # bots 表尚未创建（Week 1 阶段），返回 None
        return None
