"""
Alembic 迁移环境。
使用 psycopg2（同步）执行 DDL，与运行时的 asyncpg 无关。
迁移文件使用原生 SQL（op.execute），不依赖 SQLAlchemy ORM。
"""
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 从 .env 读取 DATABASE_URL，将 asyncpg 格式转换为 psycopg2 格式
_db_url = os.getenv(
    "DATABASE_URL",
    "postgresql://cs_user:cs_pass@localhost:5432/cs_platform"
)
# asyncpg 用 postgresql://，psycopg2 用 postgresql+psycopg2://
_sync_url = _db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
config.set_main_option("sqlalchemy.url", _sync_url)

# 不使用 ORM 模型，target_metadata = None
target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
