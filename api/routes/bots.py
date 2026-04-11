"""
Bot 路由：CRUD + API Key 轮换
权限：创建/修改/删除 需要 admin+；查询 operator+ 可操作
"""
import logging
from datetime import date, datetime
from uuid import UUID

from aiohttp import web

from store import bot_store

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()

ADMIN_ROLES = {"super_admin", "admin"}
PLAN_BOT_LIMITS = {"free": 1, "entity": 3, "trade": 3, "pro": 10}


def _require_admin(request: web.Request) -> None:
    if request.get("role") not in ADMIN_ROLES:
        raise web.HTTPForbidden(reason="Admin role required")


def _serialize(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _bot_to_dict(bot: dict) -> dict:
    """Serialize a bot row: UUID→str, datetime→isoformat, hide full api key.

    The full `bot_api_key` is only returned by `/api/bots/{id}/reveal-key`;
    list/detail endpoints emit `bot_api_key_preview` (masked) instead.
    """
    d = {k: _serialize(v) for k, v in bot.items()}
    key = d.pop("bot_api_key", None)
    if isinstance(key, str) and len(key) >= 16:
        d["bot_api_key_preview"] = key[:12] + "..." + key[-4:]
    return d


# ── GET /api/bots ────────────────────────────────────────
@routes.get("/api/bots")
async def list_bots_handler(request: web.Request) -> web.Response:
    db = request.app["db"]
    bots = await bot_store.list_bots(db, request["tenant_id"])
    return web.json_response({
        "data": [_bot_to_dict(b) for b in bots],
        "meta": {"total": len(bots)},
    })


# ── GET /api/bots/{bot_id}/detail ───────────────────────
@routes.get("/api/bots/{bot_id}/detail")
async def get_bot_detail_handler(request: web.Request) -> web.Response:
    """返回含完整配置的 Bot 详情 + 知识库统计。"""
    db = request.app["db"]
    bot = await bot_store.get_bot(
        db, request.match_info["bot_id"], request["tenant_id"]
    )
    if not bot:
        raise web.HTTPForbidden(reason="Bot not found or access denied")

    from store.base import fetch_val
    chunk_total = await fetch_val(
        db,
        """
        SELECT COALESCE(SUM(chunk_count), 0)
        FROM knowledge_sources
        WHERE bot_id = $1 AND status = 'ready'
        """,
        request.match_info["bot_id"],
    )
    faq_count = await fetch_val(
        db,
        """
        SELECT COUNT(*) FROM faq_items
        WHERE bot_id = $1 AND is_active = TRUE
        """,
        request.match_info["bot_id"],
    )

    d = _bot_to_dict(bot)
    d["stats"] = {
        "chunk_total": int(chunk_total or 0),
        "faq_count": int(faq_count or 0),
    }
    return web.json_response({"data": d})


# ── POST /api/bots ───────────────────────────────────────
@routes.post("/api/bots")
async def create_bot_handler(request: web.Request) -> web.Response:
    _require_admin(request)

    db = request.app["db"]
    tenant_id = request["tenant_id"]

    plan = request.get("plan", "free")
    max_bots = PLAN_BOT_LIMITS.get(plan, 1)
    current = await bot_store.count_bots(db, tenant_id)
    if current >= max_bots:
        raise web.HTTPPaymentRequired(
            reason=f"Bot limit reached ({max_bots}) for plan '{plan}'"
        )

    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        raise web.HTTPBadRequest(reason="name is required")

    bot = await bot_store.create_bot(
        db,
        tenant_id=tenant_id,
        created_by=request["user_id"],
        name=name,
        welcome_message=data.get("welcome_message", "您好，有什么可以帮您？"),
        language=data.get("language", "zh"),
        style=data.get("style", "friendly"),
        system_prompt=data.get("system_prompt"),
    )

    from store.audit_store import log_action
    await log_action(
        db, tenant_id, "bot.create", "bot", str(bot["id"]),
        user_id=request["user_id"],
        after={"name": bot["name"], "language": bot["language"]},
        ip=request.remote,
    )

    return web.json_response({"data": _bot_to_dict(bot)}, status=201)


# ── GET /api/bots/{bot_id} ───────────────────────────────
@routes.get("/api/bots/{bot_id}")
async def get_bot_handler(request: web.Request) -> web.Response:
    db = request.app["db"]
    bot = await bot_store.get_bot(
        db, request.match_info["bot_id"], request["tenant_id"]
    )
    if not bot:
        raise web.HTTPForbidden(reason="Bot not found or access denied")
    return web.json_response({"data": _bot_to_dict(bot)})


# ── PUT /api/bots/{bot_id} ───────────────────────────────
@routes.put("/api/bots/{bot_id}")
async def update_bot_handler(request: web.Request) -> web.Response:
    _require_admin(request)
    data = await request.json()
    db = request.app["db"]
    bot = await bot_store.update_bot(
        db,
        bot_id=request.match_info["bot_id"],
        tenant_id=request["tenant_id"],
        **data,
    )
    if not bot:
        raise web.HTTPForbidden(reason="Bot not found or access denied")
    return web.json_response({"data": _bot_to_dict(bot)})


# ── DELETE /api/bots/{bot_id} ────────────────────────────
@routes.delete("/api/bots/{bot_id}")
async def delete_bot_handler(request: web.Request) -> web.Response:
    _require_admin(request)
    db = request.app["db"]
    ok = await bot_store.delete_bot(
        db, request.match_info["bot_id"], request["tenant_id"]
    )
    if not ok:
        raise web.HTTPForbidden(reason="Bot not found or access denied")

    from store.audit_store import log_action
    await log_action(
        db, request["tenant_id"], "bot.delete", "bot",
        request.match_info["bot_id"],
        user_id=request["user_id"],
        ip=request.remote,
    )

    return web.json_response({"data": None, "meta": {"affected": 1}})


# ── POST /api/bots/{bot_id}/rotate-key ───────────────────
@routes.post("/api/bots/{bot_id}/rotate-key")
async def rotate_key_handler(request: web.Request) -> web.Response:
    _require_admin(request)
    db = request.app["db"]
    result = await bot_store.rotate_api_key(
        db, request.match_info["bot_id"], request["tenant_id"]
    )
    if not result:
        raise web.HTTPForbidden(reason="Bot not found or access denied")
    return web.json_response({
        "data": {
            "bot_id": str(result["id"]),
            "bot_api_key": result["bot_api_key"],
        }
    })


# ── POST /api/bots/{bot_id}/reveal-key ───────────────────
def _generate_embed_code(bot_id: str, api_key: str, origin: str) -> str:
    return (
        f"<script>\n"
        f"window.CS_CONFIG = {{\n"
        f'  botId: "{bot_id}",\n'
        f'  apiKey: "{api_key}"\n'
        f"}};\n"
        f"</script>\n"
        f'<script src="{origin}/widget.js" async></script>'
    )


@routes.post("/api/bots/{bot_id}/reveal-key")
async def reveal_key_handler(request: web.Request) -> web.Response:
    """返回完整 bot_api_key 和嵌入代码。仅 admin+ 可调用。"""
    _require_admin(request)
    db = request.app["db"]
    bot = await bot_store.get_bot_with_key(
        db, request.match_info["bot_id"], request["tenant_id"]
    )
    if not bot:
        raise web.HTTPForbidden(reason="Bot not found or access denied")

    origin = f"{request.scheme}://{request.host}"
    return web.json_response({
        "data": {
            "bot_id": str(bot["id"]),
            "bot_api_key": bot["bot_api_key"],
            "embed_code": _generate_embed_code(
                str(bot["id"]), bot["bot_api_key"], origin
            ),
        }
    })


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
