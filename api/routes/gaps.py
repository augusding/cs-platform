"""
知识盲区管理 API。
列表 / 详情 / 触发分析 / 状态更新 / 一键添加 FAQ
"""
import json
import logging

from aiohttp import web

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


@routes.get("/api/admin/gaps/summary")
async def gaps_summary(request: web.Request) -> web.Response:
    """知识盲区概览统计（Dashboard 用）"""
    tenant_id = request["tenant_id"]
    db = request.app["db"]
    bot_id = request.rel_url.query.get("bot_id")

    conditions = ["tenant_id = $1"]
    params: list = [tenant_id]
    idx = 2
    if bot_id:
        conditions.append(f"bot_id = ${idx}::uuid")
        params.append(bot_id)
        idx += 1

    where = " AND ".join(conditions)

    row = await db.fetchrow(f"""
        SELECT
            COUNT(*) FILTER (WHERE status = 'open')::int AS open_count,
            COUNT(*) FILTER (WHERE status = 'resolved')::int AS resolved_count,
            COUNT(*) FILTER (WHERE status = 'dismissed')::int AS dismissed_count,
            COALESCE(SUM(query_count) FILTER (WHERE status = 'open'), 0)::int AS total_affected_queries,
            COALESCE(SUM(unique_sessions) FILTER (WHERE status = 'open'), 0)::int AS total_affected_sessions
        FROM knowledge_gaps
        WHERE {where}
    """, *params)

    top_gaps = await db.fetch(f"""
        SELECT id::text, cluster_label, query_count, primary_signal
        FROM knowledge_gaps
        WHERE {where} AND status = 'open'
        ORDER BY query_count DESC
        LIMIT 3
    """, *params)

    return web.json_response({
        "summary": dict(row) if row else {},
        "top_gaps": [dict(r) for r in top_gaps],
    })


@routes.post("/api/admin/gaps/analyze")
async def trigger_analysis(request: web.Request) -> web.Response:
    """手动触发知识盲区分析"""
    tenant_id = request["tenant_id"]
    db = request.app["db"]
    body = await request.json()
    bot_id = body.get("bot_id")
    days = int(body.get("days", 7))

    if not bot_id:
        return web.json_response({"error": "bot_id required"}, status=400)

    from core.gap_analyzer import analyze_gaps
    gaps = await analyze_gaps(db, bot_id, tenant_id, days=days)

    return web.json_response({
        "data": {
            "gaps_found": len(gaps),
            "labels": [g["cluster_label"] for g in gaps],
        }
    })


@routes.get("/api/admin/gaps")
async def list_gaps(request: web.Request) -> web.Response:
    """知识盲区列表"""
    tenant_id = request["tenant_id"]
    db = request.app["db"]

    bot_id = request.rel_url.query.get("bot_id")
    status = request.rel_url.query.get("status", "open")
    limit = min(int(request.rel_url.query.get("limit", "30")), 100)
    offset = int(request.rel_url.query.get("offset", "0"))

    conditions = ["g.tenant_id = $1", "g.status = $2"]
    params: list = [tenant_id, status]
    idx = 3

    if bot_id:
        conditions.append(f"g.bot_id = ${idx}::uuid")
        params.append(bot_id)
        idx += 1

    where = " AND ".join(conditions)

    rows = await db.fetch(f"""
        SELECT g.id::text, g.bot_id::text, b.name AS bot_name,
               g.cluster_label, g.sample_queries,
               g.query_count, g.unique_sessions,
               g.avg_grader_score, g.primary_signal, g.signal_breakdown,
               g.suggested_content, g.status,
               g.first_seen::text, g.last_seen::text,
               g.created_at::text, g.updated_at::text
        FROM knowledge_gaps g
        LEFT JOIN bots b ON b.id = g.bot_id
        WHERE {where}
        ORDER BY g.query_count DESC, g.last_seen DESC
        LIMIT {limit} OFFSET {offset}
    """, *params)

    total = await db.fetchval(f"""
        SELECT COUNT(*) FROM knowledge_gaps g WHERE {where}
    """, *params)

    result = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("sample_queries"), str):
            d["sample_queries"] = json.loads(d["sample_queries"])
        if isinstance(d.get("signal_breakdown"), str):
            d["signal_breakdown"] = json.loads(d["signal_breakdown"])
        result.append(d)

    return web.json_response({"data": result, "total": total})


@routes.post("/api/admin/gaps/{gap_id}/add-faq")
async def add_gap_as_faq(request: web.Request) -> web.Response:
    """将盲区建议一键添加为 FAQ 条目"""
    tenant_id = request["tenant_id"]
    user_id = request["user_id"]
    gap_id = request.match_info["gap_id"]
    db = request.app["db"]
    body = await request.json()

    question = body.get("question", "").strip()
    answer = body.get("answer", "").strip()

    if not question or not answer:
        return web.json_response({"error": "question and answer required"}, status=400)

    gap = await db.fetchrow("""
        SELECT bot_id::text FROM knowledge_gaps
        WHERE id = $1::uuid AND tenant_id = $2
    """, gap_id, tenant_id)

    if not gap:
        return web.json_response({"error": "gap not found"}, status=404)

    await db.execute("""
        INSERT INTO faq_items (tenant_id, bot_id, question, answer, priority, is_active, created_by)
        VALUES ($1::uuid, $2::uuid, $3, $4, 0, TRUE, $5::uuid)
    """, tenant_id, gap["bot_id"], question, answer, user_id)

    await db.execute("""
        UPDATE knowledge_gaps
        SET status = 'resolved', resolved_at = NOW(), resolved_by = $1::uuid, updated_at = NOW()
        WHERE id = $2::uuid
    """, user_id, gap_id)

    return web.json_response({"status": "ok", "message": "FAQ added and gap resolved"})


@routes.put("/api/admin/gaps/{gap_id}")
async def update_gap_status(request: web.Request) -> web.Response:
    """更新盲区状态：resolved / dismissed / open"""
    tenant_id = request["tenant_id"]
    user_id = request["user_id"]
    gap_id = request.match_info["gap_id"]
    db = request.app["db"]
    body = await request.json()

    new_status = body.get("status")
    if new_status not in ("resolved", "dismissed", "open"):
        return web.json_response({"error": "invalid status"}, status=400)

    await db.execute("""
        UPDATE knowledge_gaps
        SET status = $1,
            resolved_at = CASE WHEN $1 = 'resolved' THEN NOW() ELSE NULL END,
            resolved_by = CASE WHEN $1 = 'resolved' THEN $2::uuid ELSE NULL END,
            dismiss_reason = $3,
            updated_at = NOW()
        WHERE id = $4::uuid AND tenant_id = $5
    """, new_status, user_id, body.get("reason", ""), gap_id, tenant_id)

    return web.json_response({"status": "ok"})


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
