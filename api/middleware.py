"""
HTTP 中间件：CORS + 限流 + JWT 鉴权。
注入 request["tenant_id"] / request["user_id"] / request["role"]。
Widget 接口走 Bot API Key 鉴权（无需 JWT）。
"""
import logging
import time
from collections import defaultdict, deque

from aiohttp import web

logger = logging.getLogger(__name__)

# 不需要任何鉴权的路径
PUBLIC_PATHS: set[str] = {
    "/health",
    "/health/detail",
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/logout",
    "/api/auth/invite/accept",
    "/widget.js",
    "/api/billing/plans",
    "/api/billing/webhook",
}


@web.middleware
async def jwt_middleware(request: web.Request, handler):
    # ── 1. 公开路径直接放行 ──────────────────────────────
    if request.path in PUBLIC_PATHS or request.path.startswith("/api/demo/"):
        return await handler(request)
    # Standalone 对话页 /chat/{bot_id} 公开（widget.js 会自行带 Bot API Key 连 WS）
    if request.path.startswith("/chat/"):
        return await handler(request)

    # ── 2. Chat / Widget 路由：Bot API Key 鉴权 ──────────
    if request.path.startswith("/api/chat/"):
        bot_api_key = (
            request.headers.get("X-Bot-Key")
            or request.rel_url.query.get("key")
        )
        if not bot_api_key:
            raise web.HTTPUnauthorized(
                reason="Missing bot API key",
                content_type="application/json",
            )
        db = request.app["db"]
        try:
            from store.bot_store import get_bot_by_api_key
            bot = await get_bot_by_api_key(db, bot_api_key)
        except Exception:
            bot = None

        if not bot:
            raise web.HTTPUnauthorized(
                reason="Invalid bot API key",
                content_type="application/json",
            )
        request["bot_id"] = bot["id"]
        request["tenant_id"] = bot["tenant_id"]
        request["role"] = "bot"

        # ── 配额预检（按月消息数） ───────────────────────────
        # 不在此处 increment：每条消息由 chat.py 处理时递增，避免与
        # WebSocket 连接级的检查重复计数。
        try:
            redis_client = request.app.get("redis")
            if redis_client is not None:
                from cache.quota import check_limit
                from store.base import fetch_val
                quota = await fetch_val(
                    request.app["db"],
                    "SELECT monthly_quota FROM tenants WHERE id = $1",
                    bot["tenant_id"],
                )
                quota = int(quota) if quota is not None else 200
                if not await check_limit(
                    redis_client, str(bot["tenant_id"]), quota
                ):
                    raise web.HTTPPaymentRequired(
                        reason="Monthly quota exceeded. Please upgrade your plan."
                    )
        except web.HTTPPaymentRequired:
            raise
        except Exception as qe:
            logger.warning(f"Quota check error: {qe}")

        return await handler(request)

    # ── 3. 标准 JWT 路由 ──────────────────────────────────
    # Admin 实时监听 / 调试 WS 允许查询参数携带 JWT
    # （浏览器 WebSocket API 无法设置自定义 header）
    token: str | None = None
    if request.path.startswith("/api/admin/listen/"):
        token = request.rel_url.query.get("key")
    elif request.path.startswith("/api/admin/debug/"):
        token = request.rel_url.query.get("token")

    if not token:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise web.HTTPUnauthorized(
                reason="Missing or invalid Authorization header",
                content_type="application/json",
            )
        token = auth_header[7:]
    try:
        from auth.jwt_utils import verify_access_token
        payload = verify_access_token(token)
    except ValueError as e:
        raise web.HTTPUnauthorized(
            reason=str(e),
            content_type="application/json",
        )

    request["user_id"] = payload["sub"]
    request["tenant_id"] = payload["tid"]
    request["role"] = payload["role"]
    request["plan"] = payload.get("plan", "free")

    return await handler(request)


# ── Redis 滑动窗口限流（进程重启/多实例保持状态） ─────────────
# 内存限流的 dict 仍保留作 Redis 不可用时的兜底
_rate_limit_buckets: dict[str, deque] = defaultdict(deque)
_RATE_WINDOW_SECONDS = 60


async def _memory_limit_check(ip: str, limit: int) -> bool:
    """Redis 不可用时的进程内存兜底"""
    now = time.time()
    bucket = _rate_limit_buckets[ip]
    while bucket and now - bucket[0] >= _RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


@web.middleware
async def rate_limit_middleware(request: web.Request, handler):
    """IP + tenant 级滑动窗口限流。"""
    if not request.path.startswith("/api/"):
        return await handler(request)

    from config import settings
    ip_limit = settings.RATE_LIMIT_PER_MIN
    # 取第一跳真实 IP；多级代理时信任最外层 header
    ip = (
        request.headers.get("X-Forwarded-For", request.remote or "unknown")
        .split(",")[0]
        .strip()
    )

    redis = request.app.get("redis")
    if redis is None:
        # Redis 未就绪：退回进程内存
        if not await _memory_limit_check(ip, ip_limit):
            raise web.HTTPTooManyRequests(
                reason="Too many requests. Please slow down.",
                headers={"Retry-After": "60"},
            )
        return await handler(request)

    from cache.ratelimit import (
        is_allowed,
        ip_key,
        tenant_key,
        TENANT_LIMIT,
    )

    if not await is_allowed(redis, ip_key(ip), ip_limit):
        raise web.HTTPTooManyRequests(
            reason="Too many requests from this IP. Please slow down.",
            headers={"Retry-After": "60"},
        )

    # 租户级限流（仅 WebSocket 对话路由；此时 request['tenant_id']
    # 已被 bot-key 分支注入——限流在 JWT 之前所以通常拿不到，这里是一个占位，
    # 未来接入 X-Tenant-Id 头或 session cookie 时生效）
    tenant_id = request.get("tenant_id")
    if tenant_id and request.path.startswith("/api/chat/"):
        if not await is_allowed(redis, tenant_key(str(tenant_id)), TENANT_LIMIT):
            raise web.HTTPTooManyRequests(
                reason="Tenant request limit exceeded.",
                headers={"Retry-After": "60"},
            )

    return await handler(request)


# ── CORS ─────────────────────────────────────────────────────
@web.middleware
async def cors_middleware(request: web.Request, handler):
    """CORS 处理，支持 Widget 跨域调用。"""
    from config import settings
    allowed = settings.WIDGET_ALLOWED_ORIGINS
    origin = request.headers.get("Origin", "")

    if allowed == "*":
        allow_origin = "*"
    else:
        whitelist = [o.strip() for o in allowed.split(",") if o.strip()]
        allow_origin = origin if origin in whitelist else (
            whitelist[0] if whitelist else ""
        )

    if request.method == "OPTIONS":
        return web.Response(
            status=204,
            headers={
                "Access-Control-Allow-Origin": allow_origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Bot-Key",
                "Access-Control-Max-Age": "86400",
            },
        )

    try:
        response = await handler(request)
    except web.HTTPException as exc:
        exc.headers["Access-Control-Allow-Origin"] = allow_origin
        raise

    response.headers["Access-Control-Allow-Origin"] = allow_origin
    response.headers["Access-Control-Allow-Headers"] = (
        "Authorization, Content-Type, X-Bot-Key"
    )
    return response
