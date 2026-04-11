"""Admin Console 数据接口 + 实时接管 WebSocket"""
import json
import logging
from datetime import date, datetime
from uuid import UUID

from aiohttp import WSMsgType, web

from store.base import fetch_all, fetch_one, fetch_val

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()

# 全局连接注册表：session_id -> set of admin WebSocketResponse
# 单实例进程内广播；多实例生产环境应改用 Redis Pub/Sub。
_admin_listeners: dict[str, set[web.WebSocketResponse]] = {}


def _serialize(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _row_to_dict(row) -> dict:
    return {k: _serialize(v) for k, v in dict(row).items()}


@routes.get("/api/admin/sessions")
async def list_sessions(request: web.Request) -> web.Response:
    tenant_id = request["tenant_id"]
    try:
        page = max(int(request.rel_url.query.get("page", 1)), 1)
    except ValueError:
        page = 1
    try:
        page_size = min(
            max(int(request.rel_url.query.get("page_size", 20)), 1), 100
        )
    except ValueError:
        page_size = 20
    offset = (page - 1) * page_size

    db = request.app["db"]
    rows = await fetch_all(
        db,
        """
        SELECT id, bot_id, visitor_id, language, status, message_count, started_at
        FROM sessions
        WHERE tenant_id = $1
        ORDER BY started_at DESC
        LIMIT $2 OFFSET $3
        """,
        tenant_id, page_size, offset,
    )
    total = await fetch_val(
        db,
        "SELECT COUNT(*) FROM sessions WHERE tenant_id = $1",
        tenant_id,
    ) or 0

    return web.json_response({
        "data": [
            {
                **dict(r),
                "id": str(r["id"]),
                "bot_id": str(r["bot_id"]),
                "started_at": r["started_at"].isoformat(),
            }
            for r in rows
        ],
        "meta": {
            "total": int(total),
            "page": page,
            "page_size": page_size,
        },
    })


_PERIOD_EXPR = {
    "today": "{col} >= CURRENT_DATE",
    "week": "{col} >= CURRENT_DATE - INTERVAL '7 days'",
    "month": "{col} >= CURRENT_DATE - INTERVAL '30 days'",
}


def _period_clause(period: str, col: str) -> str:
    template = _PERIOD_EXPR.get(period, _PERIOD_EXPR["month"])
    return template.format(col=col)


@routes.get("/api/admin/stats")
async def get_stats(request: web.Request) -> web.Response:
    tenant_id = request["tenant_id"]
    db = request.app["db"]

    period = request.rel_url.query.get("period", "month")
    if period not in _PERIOD_EXPR:
        period = "month"
    s_clause = _period_clause(period, "started_at")
    js_clause = _period_clause(period, "s.started_at")

    total = await fetch_val(
        db,
        f"SELECT COUNT(*) FROM sessions "
        f"WHERE tenant_id = $1 AND {s_clause}",
        tenant_id,
    ) or 0

    resolved = await fetch_val(
        db,
        f"SELECT COUNT(*) FROM sessions "
        f"WHERE tenant_id = $1 AND is_resolved = TRUE AND {s_clause}",
        tenant_id,
    ) or 0

    no_hit = await fetch_val(
        db,
        f"""
        SELECT COUNT(*) FROM messages m
        JOIN sessions s ON s.id = m.session_id
        WHERE m.tenant_id = $1
          AND m.role = 'assistant'
          AND m.is_grounded = FALSE
          AND {js_clause}
        """,
        tenant_id,
    ) or 0

    total_assistant_msgs = await fetch_val(
        db,
        f"""
        SELECT COUNT(*) FROM messages m
        JOIN sessions s ON s.id = m.session_id
        WHERE m.tenant_id = $1
          AND m.role = 'assistant'
          AND {js_clause}
        """,
        tenant_id,
    ) or 0

    avg_lat = await fetch_val(
        db,
        f"""
        SELECT ROUND(AVG(m.latency_ms)) FROM messages m
        JOIN sessions s ON s.id = m.session_id
        WHERE m.tenant_id = $1
          AND m.role = 'assistant'
          AND m.latency_ms IS NOT NULL
          AND {js_clause}
        """,
        tenant_id,
    ) or 0

    total_i = int(total)
    msgs_i = max(int(total_assistant_msgs), 1)
    return web.json_response({
        "data": {
            "total_sessions": total_i,
            "resolved_rate": round(float(resolved) / max(total_i, 1), 3),
            "no_hit_rate": round(float(no_hit) / msgs_i, 3),
            "avg_latency_ms": int(avg_lat),
            "period": period,
        }
    })


@routes.get("/api/admin/sessions/{session_id}")
async def get_session_detail(request: web.Request) -> web.Response:
    tenant_id = request["tenant_id"]
    session_id = request.match_info["session_id"]
    db = request.app["db"]

    session = await fetch_one(
        db,
        """
        SELECT s.*, b.name AS bot_name
        FROM sessions s
        LEFT JOIN bots b ON b.id = s.bot_id
        WHERE s.id = $1 AND s.tenant_id = $2
        """,
        session_id, tenant_id,
    )
    if not session:
        raise web.HTTPForbidden(reason="Session not found or access denied")

    messages = await fetch_all(
        db,
        """
        SELECT id, role, content, grader_score, is_grounded, created_at
        FROM messages
        WHERE session_id = $1
        ORDER BY created_at ASC
        """,
        session_id,
    )

    data = _row_to_dict(session)
    data["messages"] = [_row_to_dict(m) for m in messages]
    return web.json_response({"data": data})


@routes.post("/api/admin/sessions/{session_id}/transfer")
async def transfer_session(request: web.Request) -> web.Response:
    """Admin 接管会话（将 status 置为 transferred，记录接管人）。"""
    tenant_id = request["tenant_id"]
    session_id = request.match_info["session_id"]
    user_id = request["user_id"]
    db = request.app["db"]

    from store.base import execute as db_exec
    result = await db_exec(
        db,
        """
        UPDATE sessions
        SET status = 'transferred', transferred_to = $1
        WHERE id = $2 AND tenant_id = $3
        """,
        user_id, session_id, tenant_id,
    )
    if result == "UPDATE 0":
        raise web.HTTPForbidden(reason="Session not found")
    return web.json_response({"data": {"message": "Session transferred"}})


@routes.get("/api/admin/listen/{session_id}")
async def admin_listen_ws(request: web.Request) -> web.WebSocketResponse:
    """Admin 监听特定会话的实时消息推送；接管后可发送 human_agent 消息。"""
    tenant_id = request["tenant_id"]
    session_id = request.match_info["session_id"]
    db = request.app["db"]

    session = await fetch_one(
        db,
        "SELECT id, status FROM sessions WHERE id = $1 AND tenant_id = $2",
        session_id, tenant_id,
    )
    if not session:
        return web.Response(
            status=403, text="Session not found or access denied"
        )

    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    _admin_listeners.setdefault(session_id, set()).add(ws)
    logger.info(
        f"Admin WS connected session={session_id} "
        f"listeners={len(_admin_listeners[session_id])}"
    )

    try:
        await ws.send_json({
            "type": "connected",
            "session_id": session_id,
            "status": session["status"],
        })

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue

                if data.get("type") != "message":
                    continue
                content = (data.get("content") or "").strip()
                if not content:
                    continue

                from store.session_store import save_message
                await save_message(
                    db, session_id, tenant_id,
                    role="human_agent", content=content,
                )

                # 推送给访客侧
                await _broadcast_to_visitor(session_id, {
                    "type": "human_agent_message",
                    "content": content,
                })
                # 给当前 admin 自己也回执一下
                await ws.send_json({"type": "sent", "content": content})

            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                break
    finally:
        listeners = _admin_listeners.get(session_id)
        if listeners:
            listeners.discard(ws)
            if not listeners:
                _admin_listeners.pop(session_id, None)

    return ws


async def _broadcast_to_visitor(session_id: str, data: dict) -> None:
    """通过进程内共享字典把消息推送给访客 WebSocket。"""
    try:
        from api.routes.chat import _visitor_sessions
    except Exception:
        return
    ws_set = _visitor_sessions.get(session_id)
    if not ws_set:
        return
    dead: set = set()
    for ws in ws_set:
        try:
            if not ws.closed:
                await ws.send_json(data)
        except Exception:
            dead.add(ws)
    ws_set -= dead


async def notify_admin_listeners(session_id: str, data: dict) -> None:
    """chat.py 在产生新消息时调用，推送给所有监听该会话的 admin ws。"""
    ws_set = _admin_listeners.get(session_id)
    if not ws_set:
        return
    dead: set = set()
    for ws in ws_set:
        try:
            if not ws.closed:
                await ws.send_json(data)
        except Exception:
            dead.add(ws)
    ws_set -= dead


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
