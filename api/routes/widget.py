"""
Widget JS 文件服务 + Standalone 独立对话页。
"""
import html
import json
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

    db = request.app["db"]
    from store.base import fetch_one
    row = await fetch_one(
        db,
        "SELECT id, name, bot_api_key, welcome_message "
        "FROM bots WHERE id = $1 AND status = 'active'",
        bot_id,
    )
    if not row:
        return web.Response(text="Bot not found", status=404)

    bot_name = row["name"] or "智能客服"
    welcome_msg = row["welcome_message"] or "您好，请问有什么可以帮您？"
    api_key = row["bot_api_key"]

    # HTML 文本节点（escape 防 XSS）
    bot_name_html = html.escape(bot_name, quote=True)
    # JS 字符串字面量（json.dumps 保证正确转义，已自带引号）
    bot_id_js = json.dumps(str(row["id"]))
    api_key_js = json.dumps(api_key)
    origin_js = json.dumps(origin)
    welcome_js = json.dumps(welcome_msg)

    html_page = f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{bot_name_html} - 智能客服</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #f5f7fa; font-family: -apple-system, sans-serif;
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; }}
    #cs-standalone {{
      width: 100%; max-width: 480px; height: 100vh;
      background: #fff; display: flex; flex-direction: column;
      box-shadow: 0 0 40px rgba(0,0,0,.08);
    }}
    #cs-header {{
      background: #1565C0; color: #fff; padding: 16px 20px;
      font-size: 16px; font-weight: 600;
    }}
    #cs-messages {{
      flex: 1; overflow-y: auto; padding: 16px;
      display: flex; flex-direction: column; gap: 10px;
    }}
    .cs-msg {{ max-width: 80%; padding: 10px 14px; border-radius: 12px;
               font-size: 14px; line-height: 1.5; word-break: break-word; }}
    .cs-msg.user {{ align-self: flex-end; background: #1565C0; color: #fff;
                    border-radius: 12px 12px 2px 12px; }}
    .cs-msg.bot  {{ align-self: flex-start; background: #f0f4f8; color: #2c3e50;
                    border-radius: 12px 12px 12px 2px; }}
    #cs-input-row {{
      display: flex; gap: 8px; padding: 12px;
      border-top: 1px solid #eee; background: #fff;
    }}
    #cs-input {{
      flex: 1; border: 1px solid #ddd; border-radius: 8px;
      padding: 9px 12px; font-size: 14px; outline: none;
    }}
    #cs-input:focus {{ border-color: #1565C0; }}
    #cs-send {{
      background: #1565C0; color: #fff; border: none;
      border-radius: 8px; padding: 9px 16px;
      font-size: 14px; cursor: pointer;
    }}
  </style>
</head>
<body>
  <div id="cs-standalone">
    <div id="cs-header">{bot_name_html}</div>
    <div id="cs-messages"></div>
    <div id="cs-input-row">
      <input id="cs-input" type="text" placeholder="输入消息…" />
      <button id="cs-send">发送</button>
    </div>
  </div>
  <script>
    const BOT_ID   = {bot_id_js};
    const API_KEY  = {api_key_js};
    const BASE_URL = {origin_js};
    const WELCOME  = {welcome_js};
    const VISITOR  = "vis_" + Math.random().toString(36).slice(2);

    const msgs  = document.getElementById("cs-messages");
    const input = document.getElementById("cs-input");
    const send  = document.getElementById("cs-send");

    let ws, sessionId, curBot;

    function addMsg(text, role) {{
      const d = document.createElement("div");
      d.className = "cs-msg " + role;
      d.textContent = text;
      msgs.appendChild(d);
      msgs.scrollTop = msgs.scrollHeight;
      return d;
    }}

    function connect() {{
      const proto = BASE_URL.startsWith("https") ? "wss" : "ws";
      const url = proto + "://" + BASE_URL.replace(/^https?:\\/\\//, "") +
                  "/api/chat/" + BOT_ID + "?key=" + API_KEY + "&visitor_id=" + VISITOR;
      ws = new WebSocket(url);
      ws.onmessage = function(e) {{
        const m = JSON.parse(e.data);
        if (m.type === "connected") {{
          sessionId = m.session_id;
          addMsg(m.welcome || WELCOME, "bot");
        }} else if (m.type === "token") {{
          if (!curBot) curBot = addMsg("", "bot");
          curBot.textContent += m.content;
          msgs.scrollTop = msgs.scrollHeight;
        }} else if (m.type === "done") {{
          curBot = null;
          send.disabled = false; input.disabled = false;
        }} else if (m.type === "transfer") {{
          addMsg(m.message, "bot");
        }} else if (m.type === "error") {{
          if (curBot) {{ curBot.remove(); curBot = null; }}
          addMsg("发送失败，请重试", "bot");
          send.disabled = false; input.disabled = false;
        }} else if (m.type === "ping") {{
          ws.send(JSON.stringify({{type:"pong"}}));
        }}
      }};
      ws.onerror = function() {{ addMsg("连接错误，请刷新页面", "bot"); }};
    }}

    function sendMsg() {{
      const text = input.value.trim();
      if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
      addMsg(text, "user");
      input.value = "";
      send.disabled = true; input.disabled = true;
      ws.send(JSON.stringify({{type:"message", content:text, visitor_id:VISITOR}}));
    }}

    send.addEventListener("click", sendMsg);
    input.addEventListener("keydown", function(e) {{ if (e.key==="Enter") sendMsg(); }});
    connect();
  </script>
</body>
</html>"""
    return web.Response(text=html_page, content_type="text/html")


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
