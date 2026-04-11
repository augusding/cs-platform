"""
Lead 线索路由
"""
import json

from aiohttp import web

from store.lead_store import list_leads, update_lead_status, get_lead

routes = web.RouteTableDef()

VALID_STATUSES = {"new", "contacted", "qualified", "closed"}


def _serialize_lead(r: dict) -> dict:
    d = {**r, "id": str(r["id"]), "bot_id": str(r["bot_id"])}
    if d.get("session_id"):
        d["session_id"] = str(d["session_id"])
    if d.get("tenant_id"):
        d["tenant_id"] = str(d["tenant_id"])
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    if d.get("updated_at"):
        d["updated_at"] = d["updated_at"].isoformat()
    raw = d.get("lead_info")
    if isinstance(raw, str):
        try:
            d["lead_info"] = json.loads(raw)
        except Exception:
            d["lead_info"] = {}
    if isinstance(d.get("intent_score"), float):
        d["intent_score"] = round(d["intent_score"], 3)
    return d


@routes.get("/api/leads")
async def list_leads_handler(request: web.Request) -> web.Response:
    tenant_id = request["tenant_id"]
    status = request.rel_url.query.get("status")
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

    db = request.app["db"]
    rows, total = await list_leads(db, tenant_id, status, page, page_size)
    return web.json_response({
        "data": [_serialize_lead(r) for r in rows],
        "meta": {"total": total, "page": page, "page_size": page_size},
    })


@routes.get("/api/leads/{lead_id}")
async def get_lead_handler(request: web.Request) -> web.Response:
    tenant_id = request["tenant_id"]
    lead_id = request.match_info["lead_id"]
    db = request.app["db"]

    lead = await get_lead(db, lead_id, tenant_id)
    if not lead:
        raise web.HTTPForbidden(reason="Lead not found or access denied")
    return web.json_response({"data": _serialize_lead(lead)})


@routes.put("/api/leads/{lead_id}")
async def update_lead_handler(request: web.Request) -> web.Response:
    tenant_id = request["tenant_id"]
    lead_id = request.match_info["lead_id"]
    data = await request.json()
    status = data.get("status")

    if status not in VALID_STATUSES:
        raise web.HTTPBadRequest(
            reason=f"Invalid status. Allowed: {sorted(VALID_STATUSES)}"
        )

    db = request.app["db"]
    ok = await update_lead_status(db, lead_id, tenant_id, status)
    if not ok:
        raise web.HTTPForbidden(reason="Lead not found or access denied")

    lead = await get_lead(db, lead_id, tenant_id)
    return web.json_response({"data": _serialize_lead(lead)})


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
