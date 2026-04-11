"""健康检查接口，用于验证服务是否正常运行"""
import asyncio
import logging
from aiohttp import web

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


@routes.get("/health")
async def health_check(request: web.Request) -> web.Response:
    """基础健康检查"""
    return web.json_response({
        "status": "ok",
        "service": "cs-platform",
        "version": "0.1.0",
    })


@routes.get("/health/detail")
async def health_detail(request: web.Request) -> web.Response:
    """详细健康检查（含各组件状态）"""
    checks: dict = {}

    # PostgreSQL
    try:
        db = request.app["db"]
        await db.fetchval("SELECT 1")
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Redis
    try:
        redis = request.app["redis"]
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # RQ 队列可达（不强制 worker 在线，仅校验 redis 队列后端可访问）
    try:
        import redis as sync_redis
        from rq import Queue
        from config import settings
        r = sync_redis.from_url(settings.REDIS_URL)
        Queue("ingestion", connection=r).get_job_ids()
        checks["rq_queue"] = "ok"
    except Exception as e:
        checks["rq_queue"] = f"error: {e}"

    # Milvus 可选检查（失败不致 503，仅标注）
    try:
        from knowledge.vector_store import _connect
        _connect()
        checks["milvus"] = "ok"
    except Exception as e:
        checks["milvus"] = f"warning: {e}"

    # rq_queue/milvus 失败不计入整体不健康（摄取 pipeline 是可选子系统）
    critical = {"postgres", "redis"}
    all_ok = all(
        v == "ok" for k, v in checks.items() if k in critical
    )
    return web.json_response(
        {"status": "ok" if all_ok else "degraded", "checks": checks},
        status=200 if all_ok else 503,
    )


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
