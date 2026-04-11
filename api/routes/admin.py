"""Admin Console 数据接口"""
from datetime import date, datetime
from uuid import UUID

from aiohttp import web

from store.base import fetch_all, fetch_one, fetch_val

routes = web.RouteTableDef()


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


@routes.get("/api/admin/stats")
async def get_stats(request: web.Request) -> web.Response:
    tenant_id = request["tenant_id"]
    db = request.app["db"]

    total = await fetch_val(
        db,
        "SELECT COUNT(*) FROM sessions WHERE tenant_id = $1",
        tenant_id,
    ) or 0
    resolved = await fetch_val(
        db,
        "SELECT COUNT(*) FROM sessions WHERE tenant_id = $1 AND status = 'closed'",
        tenant_id,
    ) or 0
    no_hit = await fetch_val(
        db,
        "SELECT COUNT(*) FROM messages WHERE tenant_id = $1 AND is_grounded = FALSE",
        tenant_id,
    ) or 0

    total_i = int(total)
    return web.json_response({
        "data": {
            "total_sessions": total_i,
            "resolved_rate": round(float(resolved) / max(total_i, 1), 3),
            "no_hit_rate": round(float(no_hit) / max(total_i * 2, 1), 3),
            "avg_latency_ms": 0,
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


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
