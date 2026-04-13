"""
Demo 公开 API。
无需鉴权，仅暴露标记为 is_demo=True 的 Bot 信息。
"""
import logging

from aiohttp import web

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


@routes.get("/api/demo/bots")
async def list_demo_bots(request: web.Request) -> web.Response:
    """列出所有公开的 Demo Bot"""
    db = request.app["db"]
    rows = await db.fetch("""
        SELECT id::text, name, welcome_message, language, style, avatar_url,
               (SELECT COUNT(*) FROM knowledge_sources
                WHERE bot_id = bots.id AND status = 'ready') AS doc_count,
               (SELECT COUNT(*) FROM faq_items
                WHERE bot_id = bots.id AND is_active = TRUE) AS faq_count
        FROM bots
        WHERE is_demo = TRUE AND status = 'active'
        ORDER BY created_at DESC
    """)
    return web.json_response({"data": [dict(r) for r in rows]})


@routes.get("/api/demo/bots/{bot_id}")
async def get_demo_bot(request: web.Request) -> web.Response:
    """获取单个 Demo Bot 的详情 + API Key（用于 WS 连接）"""
    bot_id = request.match_info["bot_id"]
    db = request.app["db"]

    row = await db.fetchrow("""
        SELECT id::text, name, welcome_message, language, style, avatar_url, bot_api_key,
               (SELECT COUNT(*) FROM knowledge_sources
                WHERE bot_id = bots.id AND status = 'ready') AS doc_count,
               (SELECT COUNT(*) FROM faq_items
                WHERE bot_id = bots.id AND is_active = TRUE) AS faq_count
        FROM bots
        WHERE id = $1 AND is_demo = TRUE AND status = 'active'
    """, bot_id)

    if not row:
        return web.json_response({"error": "Demo bot not found"}, status=404)

    return web.json_response({"data": dict(row)})


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
