"""
PostgreSQL 连接池 + 基础查询封装。
所有 store 模块通过此模块获取连接。
"""
import asyncio
import logging
from typing import Any

import asyncpg

from config import settings

logger = logging.getLogger(__name__)


async def init_db_pool(retries: int = 5, delay: float = 2.0) -> asyncpg.Pool:
    """创建连接池，启动时自动重试（等待 PostgreSQL 就绪）"""
    for attempt in range(1, retries + 1):
        try:
            pool = await asyncpg.create_pool(
                dsn=settings.DATABASE_URL,
                min_size=settings.DATABASE_POOL_MIN,
                max_size=settings.DATABASE_POOL_MAX,
                command_timeout=30,
            )
            logger.info(
                f"PostgreSQL 连接池已就绪 "
                f"({settings.DATABASE_POOL_MIN}–{settings.DATABASE_POOL_MAX} 连接)"
            )
            return pool
        except Exception as e:
            if attempt < retries:
                logger.warning(
                    f"PostgreSQL 连接失败，{delay}s 后重试 "
                    f"({attempt}/{retries}): {e}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"PostgreSQL 连接失败，已放弃: {e}")
                raise


# ─── 便捷查询函数（减少 acquire 样板代码）─────────────────

async def fetch_one(
    pool: asyncpg.Pool, query: str, *args
) -> asyncpg.Record | None:
    """查询单行，不存在返回 None"""
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetch_all(
    pool: asyncpg.Pool, query: str, *args
) -> list[asyncpg.Record]:
    """查询多行"""
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def execute(pool: asyncpg.Pool, query: str, *args) -> str:
    """执行 INSERT/UPDATE/DELETE，返回状态字符串如 'INSERT 0 1'"""
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def execute_returning(
    pool: asyncpg.Pool, query: str, *args
) -> asyncpg.Record | None:
    """执行 INSERT/UPDATE ... RETURNING，返回第一行"""
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetch_val(pool: asyncpg.Pool, query: str, *args) -> Any:
    """查询单个值"""
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


# ── RLS-aware helpers ──────────────────────────────────────
# 每次 acquire 连接后先 SET app.current_tenant_id，让 PostgreSQL Row-Level
# Security 策略生效。供需要严格第二层租户隔离的关键查询使用。
#
# 注意：当前迁移 a012 配置为 "session var 未设则放行"，所以不用这些
# helpers 的旧查询继续工作。需要 RLS 真正生效时，调用这些 _rls 版本
# 并在 Alembic 中把 policy 的 OR-NULL 分支去掉。

_NULL_TENANT = "00000000-0000-0000-0000-000000000000"


async def _set_tenant(conn: asyncpg.Connection, tenant_id: str | None) -> None:
    tid = tenant_id or _NULL_TENANT
    # 无法参数化 SET；用字面值拼接。tid 必须是 UUID 字符串，调用方校验。
    await conn.execute(f"SET LOCAL app.current_tenant_id = '{tid}'")


async def fetch_one_rls(
    pool: asyncpg.Pool, query: str, *args, tenant_id: str | None = None
) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _set_tenant(conn, tenant_id)
            return await conn.fetchrow(query, *args)


async def fetch_all_rls(
    pool: asyncpg.Pool, query: str, *args, tenant_id: str | None = None
) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _set_tenant(conn, tenant_id)
            return await conn.fetch(query, *args)


async def execute_rls(
    pool: asyncpg.Pool, query: str, *args, tenant_id: str | None = None
) -> str:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _set_tenant(conn, tenant_id)
            return await conn.execute(query, *args)


async def execute_returning_rls(
    pool: asyncpg.Pool, query: str, *args, tenant_id: str | None = None
) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _set_tenant(conn, tenant_id)
            return await conn.fetchrow(query, *args)


async def fetch_val_rls(
    pool: asyncpg.Pool, query: str, *args, tenant_id: str | None = None
) -> Any:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _set_tenant(conn, tenant_id)
            return await conn.fetchval(query, *args)
