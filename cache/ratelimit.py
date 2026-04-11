"""
Redis 滑动窗口限流。
使用 Sorted Set：member=时间戳, score=时间戳。
窗口内 member 数量 = 请求次数。
进程重启后仍有效，多实例共享状态。
"""
import logging
import time

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60
IP_LIMIT = 300      # 每 IP 每分钟
TENANT_LIMIT = 500  # 每租户每分钟（仅对 /api/chat/ 生效）


async def is_allowed(
    redis, key: str, limit: int, window: int = WINDOW_SECONDS
) -> bool:
    """
    滑动窗口限流检查。返回 True 允许 / False 限流。
    Redis 异常时放行（fail-open），避免因缓存问题影响业务。
    """
    try:
        now = time.time()
        window_start = now - window
        member = f"{now:.6f}"

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, window * 2)
        results = await pipe.execute()

        count = results[2]
        return count <= limit
    except Exception as e:
        logger.warning(f"Rate limit check failed (fail-open): {e}")
        return True


def ip_key(ip: str) -> str:
    return f"rl:ip:{ip}"


def tenant_key(tenant_id: str) -> str:
    return f"rl:tenant:{tenant_id}"
