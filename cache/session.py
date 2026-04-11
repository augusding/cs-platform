"""
会话上下文缓存。
存储多轮对话历史，避免每轮都查 DB。
Key: session:{session_id}:ctx  TTL: 1800s（30min 空闲）
"""
import json
import logging

from config import settings

logger = logging.getLogger(__name__)


def _key(session_id: str) -> str:
    return f"session:{session_id}:ctx"


async def get_history(redis, session_id: str) -> list[dict]:
    """获取缓存的对话历史"""
    try:
        value = await redis.get(_key(session_id))
        if value:
            return json.loads(value)
    except Exception as e:
        logger.warning(f"Session cache GET error: {e}")
    return []


async def append_turn(
    redis, session_id: str, user_content: str, assistant_content: str
) -> None:
    """追加一轮对话到缓存，自动刷新 TTL"""
    try:
        history = await get_history(redis, session_id)
        history.append({"role": "user", "content": user_content})
        history.append({"role": "assistant", "content": assistant_content})
        history = history[-20:]
        await redis.setex(
            _key(session_id),
            settings.SESSION_CACHE_TTL,
            json.dumps(history, ensure_ascii=False),
        )
    except Exception as e:
        logger.warning(f"Session cache SET error: {e}")


async def clear(redis, session_id: str) -> None:
    """会话结束时清除缓存"""
    try:
        await redis.delete(_key(session_id))
    except Exception as e:
        logger.warning(f"Session cache clear error: {e}")
