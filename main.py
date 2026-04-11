"""
CS Platform — 启动入口

用法：
    python main.py serve           # 启动 API 服务
    python main.py worker          # 启动 RQ Worker（新终端）
"""
import asyncio
import logging
import os
import sys


def setup_logging() -> None:
    os.makedirs("data/logs", exist_ok=True)
    from config import settings
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("data/logs/app.log", encoding="utf-8"),
        ],
    )


def cmd_serve() -> None:
    """启动 aiohttp API 服务"""
    from api.app import create_app
    from config import settings
    import aiohttp.web as web

    app = create_app()
    print(f"\n  CS Platform API 已启动")
    print(f"  http://{settings.APP_HOST}:{settings.APP_PORT}/health\n")
    web.run_app(
        app,
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        access_log=logging.getLogger("aiohttp.access"),
    )


def cmd_worker() -> None:
    """启动 RQ Worker（Week 2 知识库摄取时使用）"""
    import redis
    from rq import Worker, Queue, Connection
    from config import settings

    conn = redis.from_url(settings.REDIS_URL)
    queues = ["ingestion", "notifications", "signals"]
    print(f"\n  RQ Worker 已启动，监听队列: {queues}\n")
    with Connection(conn):
        worker = Worker(queues)
        worker.work()


COMMANDS = {
    "serve": cmd_serve,
    "worker": cmd_worker,
}


if __name__ == "__main__":
    setup_logging()

    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"用法: python main.py [{' | '.join(COMMANDS)}]")
        sys.exit(1)

    COMMANDS[sys.argv[1]]()
