"""Session / Message 数据访问层"""
import asyncpg

from store.base import fetch_one, fetch_all, execute_returning, execute


async def create_session(
    pool: asyncpg.Pool,
    tenant_id: str,
    bot_id: str,
    visitor_id: str,
    language: str = "zh",
) -> dict:
    row = await execute_returning(
        pool,
        """
        INSERT INTO sessions (tenant_id, bot_id, visitor_id, language)
        VALUES ($1, $2, $3, $4)
        RETURNING id, tenant_id, bot_id, visitor_id, language, status, started_at
        """,
        tenant_id, bot_id, visitor_id, language,
    )
    return dict(row)


async def get_session(
    pool: asyncpg.Pool, session_id: str, tenant_id: str
) -> dict | None:
    row = await fetch_one(
        pool,
        "SELECT * FROM sessions WHERE id = $1 AND tenant_id = $2",
        session_id, tenant_id,
    )
    return dict(row) if row else None


async def get_or_create_session(
    pool: asyncpg.Pool,
    session_id: str | None,
    tenant_id: str,
    bot_id: str,
    visitor_id: str,
    language: str = "zh",
) -> dict:
    """续接已有会话或创建新会话"""
    if session_id:
        existing = await fetch_one(
            pool,
            """
            SELECT * FROM sessions
            WHERE id = $1 AND bot_id = $2 AND tenant_id = $3 AND status = 'active'
            """,
            session_id, bot_id, tenant_id,
        )
        if existing:
            return dict(existing)
    return await create_session(pool, tenant_id, bot_id, visitor_id, language)


async def save_message(
    pool: asyncpg.Pool,
    session_id: str,
    tenant_id: str,
    role: str,
    content: str,
    grader_score: float | None = None,
    is_grounded: bool | None = None,
    tokens_used: int | None = None,
) -> dict:
    row = await execute_returning(
        pool,
        """
        INSERT INTO messages
            (session_id, tenant_id, role, content, grader_score, is_grounded, tokens_used)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, role, content, created_at
        """,
        session_id, tenant_id, role, content,
        grader_score, is_grounded, tokens_used,
    )
    await execute(
        pool,
        "UPDATE sessions SET message_count = message_count + 1 WHERE id = $1",
        session_id,
    )
    return dict(row)


async def get_history(
    pool: asyncpg.Pool, session_id: str, limit: int = 10
) -> list[dict]:
    """获取最近 N 条消息作为对话历史（返回正序）"""
    rows = await fetch_all(
        pool,
        """
        SELECT role, content FROM messages
        WHERE session_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        session_id, limit,
    )
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def close_session(pool: asyncpg.Pool, session_id: str) -> None:
    await execute(
        pool,
        "UPDATE sessions SET status = 'closed', ended_at = NOW() WHERE id = $1",
        session_id,
    )
