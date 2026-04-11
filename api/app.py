"""
aiohttp Application 工厂。
注册中间件、路由、生命周期钩子。
"""
import asyncio
import logging
from aiohttp import web

from api.middleware import jwt_middleware

# ─── 路由注册（按开发阶段解注释）────────────────────────
from api.routes.health import register as reg_health
from api.routes.auth import register as reg_auth
from api.routes.bots import register as reg_bots
# Week 2：from api.routes.knowledge import register as reg_knowledge
# Week 3：from api.routes.chat import register as reg_chat
# Week 4：from api.routes.admin import register as reg_admin
# Week 5：from api.routes.leads import register as reg_leads

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
    app = web.Application(middlewares=[jwt_middleware])

    # ─── 注册路由 ──────────────────────────────────────────
    reg_health(app)
    reg_auth(app)
    reg_bots(app)
    # reg_knowledge(app)  # Week 2 解注释
    # reg_chat(app)       # Week 3 解注释
    # reg_admin(app)      # Week 4 解注释
    # reg_leads(app)      # Week 5 解注释

    # ─── 生命周期钩子 ──────────────────────────────────────
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)

    return app
