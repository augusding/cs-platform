"""
配额计数缓存。
用 Redis INCR 原子累加，每 5min 同步到 DB。
Key: quota:{tenant_id}:{YYYY-MM}:msgs
"""
import calendar
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _key(tenant_id: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"quota:{tenant_id}:{month}:msgs"


async def increment(redis, tenant_id: str) -> int:
    """消息数 +1，返回当月累计数"""
    try:
        key = _key(tenant_id)
        count = await redis.incr(key)
        if count == 1:
            await redis.expireat(key, _month_end_ts())
        return count
    except Exception as e:
        logger.warning(f"Quota INCR error: {e}")
        return 0


async def get_count(redis, tenant_id: str) -> int:
    """获取当月消息数"""
    try:
        value = await redis.get(_key(tenant_id))
        return int(value) if value else 0
    except Exception as e:
        logger.warning(f"Quota GET error: {e}")
        return 0


async def check_limit(redis, tenant_id: str, limit: int) -> bool:
    """返回 True 表示未超限，False 表示已超限"""
    if limit == -1:
        return True
    count = await get_count(redis, tenant_id)
    return count < limit


def _month_end_ts() -> int:
    """计算当月最后一天 23:59:59 的 Unix 时间戳"""
    now = datetime.now(timezone.utc)
    last_day = calendar.monthrange(now.year, now.month)[1]
    end = now.replace(
        day=last_day, hour=23, minute=59, second=59, microsecond=0
    )
    return int(end.timestamp())
