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


_STD_LOG_FIELDS = {
    "name", "msg", "args", "levelname", "levelno", "pathname",
    "filename", "module", "exc_info", "exc_text", "stack_info",
    "lineno", "funcName", "created", "msecs", "relativeCreated",
    "thread", "threadName", "processName", "process", "message",
    "asctime", "taskName",
}


class _JsonFormatter(logging.Formatter):
    """结构化 JSON 日志，保留任何 extra 字段。"""

    def format(self, record: logging.LogRecord) -> str:
        import json as _json

        entry: dict = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k in _STD_LOG_FIELDS or k in entry:
                continue
            try:
                _json.dumps(v)
                entry[k] = v
            except (TypeError, ValueError):
                entry[k] = repr(v)

        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)

        return _json.dumps(entry, ensure_ascii=False)


def setup_logging() -> None:
    os.makedirs("data/logs", exist_ok=True)
    from config import settings
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = _JsonFormatter()
    stream_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler("data/logs/app.log", encoding="utf-8")
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)


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
