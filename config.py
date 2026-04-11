"""
配置加载模块。
从 .env 文件读取所有配置，单例模式供全局使用。
"""
import os
from dotenv import load_dotenv

load_dotenv(override=False)


class Settings:
    # ─── 应用基础 ──────────────────────────────────────────
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8080"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ─── 数据库 ────────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://cs_user:cs_pass@localhost:5432/cs_platform"
    )
    DATABASE_POOL_MIN: int = int(os.getenv("DATABASE_POOL_MIN", "5"))
    DATABASE_POOL_MAX: int = int(os.getenv("DATABASE_POOL_MAX", "20"))

    # ─── Redis ────────────────────────────────────────────
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ─── Milvus ───────────────────────────────────────────
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))

    # ─── JWT ──────────────────────────────────────────────
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_SECONDS", "900")
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

    # ─── AI / LLM ──────────────────────────────────────────
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen-plus")
    QWEN_BASE_URL: str = os.getenv(
        "QWEN_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_BASE_URL: str = os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com/v1"
    )

    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")

    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    LLM_FALLBACK_ENABLED: bool = os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true"

    # ─── 并发控制 ──────────────────────────────────────────
    LLM_GLOBAL_CONCURRENCY: int = int(os.getenv("LLM_GLOBAL_CONCURRENCY", "30"))
    LLM_TENANT_CONCURRENCY: int = int(os.getenv("LLM_TENANT_CONCURRENCY", "5"))

    # ─── 缓存 ─────────────────────────────────────────────
    SEMANTIC_CACHE_ENABLED: bool = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
    SEMANTIC_CACHE_THRESHOLD: float = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))
    SEMANTIC_CACHE_TTL: int = int(os.getenv("SEMANTIC_CACHE_TTL", "86400"))
    SESSION_CACHE_TTL: int = int(os.getenv("SESSION_CACHE_TTL", "1800"))

    # ─── 知识库 ────────────────────────────────────────────
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "data/uploads")
    CHUNK_SIZE_ZH: int = int(os.getenv("CHUNK_SIZE_ZH", "400"))
    CHUNK_SIZE_EN: int = int(os.getenv("CHUNK_SIZE_EN", "300"))
    GRADER_THRESHOLD: float = float(os.getenv("GRADER_THRESHOLD", "0.6"))
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "10"))

    # ─── 安全 ─────────────────────────────────────────────
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))
    INVITATION_EXPIRE_DAYS: int = int(os.getenv("INVITATION_EXPIRE_DAYS", "7"))
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))

    # ─── SMTP（通知推送，未配置时跳过发送）───────────────────
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "CS Platform")

    # ─── 微信支付（未配置时 create-order 仍可用，仅支持模拟支付）────
    WECHAT_PAY_MCH_ID: str = os.getenv("WECHAT_PAY_MCH_ID", "")
    WECHAT_PAY_API_KEY: str = os.getenv("WECHAT_PAY_API_KEY", "")
    WECHAT_PAY_APP_ID: str = os.getenv("WECHAT_PAY_APP_ID", "")
    WECHAT_PAY_NOTIFY_URL: str = os.getenv("WECHAT_PAY_NOTIFY_URL", "")


# 全局单例，整个应用通过 `from config import settings` 使用
settings = Settings()
