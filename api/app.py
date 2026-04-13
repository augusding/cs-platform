"""
aiohttp Application 工厂。
注册中间件、路由、生命周期钩子。
"""
import asyncio
import logging
from aiohttp import web

from api.middleware import (
    jwt_middleware,
    rate_limit_middleware,
    cors_middleware,
)

# ─── 路由注册（按开发阶段解注释）────────────────────────
from api.routes.health import register as reg_health
from api.routes.auth import register as reg_auth
from api.routes.bots import register as reg_bots
from api.routes.knowledge import register as reg_knowledge
from api.routes.chat import register as reg_chat
from api.routes.widget import register as reg_widget
from api.routes.admin import register as reg_admin
from api.routes.leads import register as reg_leads
from api.routes.billing import register as reg_billing
from api.routes.members import register as reg_members

logger = logging.getLogger(__name__)


async def _on_startup(app: web.Application) -> None:
    """启动时初始化所有连接池"""
    from store.base import init_db_pool
    from cache.client import init_redis

    # PostgreSQL 连接池
    app["db"] = await init_db_pool()

    # Redis 连接
    app["redis"] = await init_redis()

    # Milvus 连接（Week 2 知识库摄取时启用）
    # from knowledge.vector_store import init_milvus
    # app["milvus"] = init_milvus()

    # 注入 Redis 到 RAG engine（用于语义缓存）
    from core.engine import set_redis
    set_redis(app["redis"])

    # 注入 DB pool 到 observability（用于 trace 持久化）
    from core.observability import set_db_pool as set_trace_db
    set_trace_db(app["db"])

    logger.info("所有连接池已就绪")


async def _on_cleanup(app: web.Application) -> None:
    """关闭时释放所有连接"""
    if "db" in app:
        await app["db"].close()
        logger.info("PostgreSQL 连接池已关闭")
    if "redis" in app:
        await app["redis"].aclose()
        logger.info("Redis 连接已关闭")


def create_app() -> web.Application:
    """创建并配置 aiohttp Application"""
    app = web.Application(
        middlewares=[
            cors_middleware,        # 最外层：CORS / preflight
            rate_limit_middleware,  # 第二层：IP 限流
            jwt_middleware,         # 第三层：鉴权
        ]
    )

    # ─── 注册路由 ──────────────────────────────────────────
    reg_health(app)
    reg_widget(app)
    reg_auth(app)
    reg_bots(app)
    reg_knowledge(app)
    reg_chat(app)
    reg_admin(app)
    reg_leads(app)
    reg_billing(app)
    reg_members(app)

    # ─── 生命周期钩子 ──────────────────────────────────────
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)

    return app
