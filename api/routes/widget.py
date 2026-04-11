"""
Widget JS 文件服务 + Standalone 独立对话页。
"""
import html
import os

from aiohttp import web

routes = web.RouteTableDef()

_WIDGET_JS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "widget", "widget.js"
)

_STUB_JS = """\
(function(){
  var cfg = window.CS_CONFIG || {};
  if(!cfg.botId){ console.warn('[CS Widget] botId required'); return; }
  console.log('[CS Widget] stub loaded for bot:', cfg.botId);
})();
"""


@routes.get("/widget.js")
async def serve_widget_js(request: web.Request) -> web.Response:
    """服务 Widget JS 文件（公开，无鉴权）"""
    if not os.path.exists(_WIDGET_JS_PATH):
        return web.Response(text=_STUB_JS, content_type="application/javascript")
    with open(_WIDGET_JS_PATH, "r", encoding="utf-8") as f:
        js = f.read()
    return web.Response(text=js, content_type="application/javascript")


@routes.get("/chat/{bot_id}")
async def standalone_chat(request: web.Request) -> web.Response:
    """Standalone 独立对话页 — 可直接用 URL 分享给客户。公开访问。"""
    bot_id = request.match_info["bot_id"]
    origin = f"{request.scheme}://{request.host}"

    # 从 DB 读取 bot 的 api key + 基础配置（标准化到公共信息）
    db = request.app["db"]
    from store.base import fetch_one
    row = await fetch_one(
        db,
        """
        SELECT id, name, bot_api_key, welcome_message, language, status
        FROM bots WHERE id = $1 AND status = 'active'
        """,
        bot_id,
    )
    if not row:
        return web.Response(text="Bot not found", status=404)

    bot_id_safe = html.escape(str(row["id"]), quote=True)
    api_key_safe = html.escape(row["bot_api_key"], quote=True)
    title_safe = html.escape(row["name"] or "智能客服", quote=True)
    origin_safe = html.escape(origin, quote=True)

    page = f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_safe}</title>
  <style>
    body {{ margin: 0; background: #f5f7fa; min-height: 100vh;
           font-family: -apple-system, sans-serif; }}
  </style>
</head>
<body>
  <script>
    window.CS_CONFIG = {{
      botId: "{bot_id_safe}",
      apiKey: "{api_key_safe}",
      baseUrl: "{origin_safe}",
      position: "bottom-right"
    }};
  </script>
  <script src="{origin_safe}/widget.js" async></script>
</body>
</html>"""
    return web.Response(text=page, content_type="text/html")


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
