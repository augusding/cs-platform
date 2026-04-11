"""
语义缓存模块。
相似度 >= 0.95 命中时直接返回，跳过整个 RAG pipeline。
Key: semantic:{bot_id}:{query_md5}
当前实现：精确 MD5 匹配（快）
升级路径：替换为 embedding 向量相似度匹配（准）
"""
import hashlib
import json
import logging

from config import settings

logger = logging.getLogger(__name__)

_PREFIX = "semantic"


def _key(bot_id: str, query: str) -> str:
    md5 = hashlib.md5(query.strip().lower().encode()).hexdigest()
    return f"{_PREFIX}:{bot_id}:{md5}"


async def get(redis, bot_id: str, query: str) -> str | None:
    """命中返回缓存答案，未命中返回 None"""
    if not settings.SEMANTIC_CACHE_ENABLED:
        return None
    try:
        key = _key(bot_id, query)
        value = await redis.get(key)
        if value:
            data = json.loads(value)
            logger.debug(f"Semantic cache HIT: {key}")
            return data.get("answer")
    except Exception as e:
        logger.warning(f"Semantic cache GET error: {e}")
    return None


async def set(redis, bot_id: str, query: str, answer: str) -> None:
    """写入缓存"""
    if not settings.SEMANTIC_CACHE_ENABLED:
        return
    try:
        key = _key(bot_id, query)
        value = json.dumps({"answer": answer}, ensure_ascii=False)
        await redis.setex(key, settings.SEMANTIC_CACHE_TTL, value)
        logger.debug(
            f"Semantic cache SET: {key} TTL={settings.SEMANTIC_CACHE_TTL}s"
        )
    except Exception as e:
        logger.warning(f"Semantic cache SET error: {e}")


async def invalidate_bot(redis, bot_id: str) -> int:
    """知识库更新时清除该 Bot 的全部语义缓存"""
    try:
        pattern = f"{_PREFIX}:{bot_id}:*"
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
        return len(keys)
    except Exception as e:
        logger.warning(f"Semantic cache invalidate error: {e}")
        return 0
