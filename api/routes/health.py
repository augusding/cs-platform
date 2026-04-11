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

    all_ok = all(v == "ok" for v in checks.values())
    return web.json_response(
        {"status": "ok" if all_ok else "degraded", "checks": checks},
        status=200 if all_ok else 503,
    )


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
