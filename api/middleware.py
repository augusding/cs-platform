"""
JWT 鉴权中间件。
注入 request["tenant_id"] / request["user_id"] / request["role"]。
Widget 接口走 Bot API Key 鉴权（无需 JWT）。
"""
import logging
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
}


@web.middleware
async def jwt_middleware(request: web.Request, handler):
    # ── 1. 公开路径直接放行 ──────────────────────────────
    if request.path in PUBLIC_PATHS:
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
        return await handler(request)

    # ── 3. 标准 JWT 路由 ──────────────────────────────────
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
