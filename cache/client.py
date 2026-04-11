"""Redis 连接初始化"""
import asyncio
import logging
import redis.asyncio as aioredis
from config import settings

logger = logging.getLogger(__name__)


async def init_redis(retries: int = 5, delay: float = 2.0) -> aioredis.Redis:
    """创建 Redis 连接，启动时自动重试"""
    for attempt in range(1, retries + 1):
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await client.ping()
            logger.info(f"Redis 已连接: {settings.REDIS_URL}")
            return client
        except Exception as e:
            if attempt < retries:
                logger.warning(
                    f"Redis 连接失败，{delay}s 后重试 ({attempt}/{retries}): {e}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Redis 连接失败，已放弃: {e}")
                raise
