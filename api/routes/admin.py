"""Admin Console 数据接口"""
from aiohttp import web

from store.base import fetch_all, fetch_val

routes = web.RouteTableDef()


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


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
