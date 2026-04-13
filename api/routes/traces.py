"""
Pipeline 追踪查询 API。
提供 trace 列表、统计聚合、详情三个端点。
注意：stats 路由必须在 {trace_id} 之前注册，否则会被动态参数匹配。
"""
import json
import logging

from aiohttp import web

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


@routes.get("/api/admin/traces")
async def list_traces(request: web.Request) -> web.Response:
    """
    查询 trace 列表，支持筛选。
    Query params:
      bot_id       — 按 Bot 筛选
      intent       — 按意图筛选
      exit_branch  — 按退出分支筛选
      min_latency  — 最小延迟（ms）
      cache_hit    — true/false
      limit        — 默认 50，最大 200
      offset       — 分页偏移
    """
    tenant_id = request["tenant_id"]
    db = request.app["db"]

    bot_id = request.rel_url.query.get("bot_id")
    intent = request.rel_url.query.get("intent")
    exit_branch = request.rel_url.query.get("exit_branch")
    min_latency = request.rel_url.query.get("min_latency")
    cache_hit = request.rel_url.query.get("cache_hit")
    limit = min(int(request.rel_url.query.get("limit", "50")), 200)
    offset = int(request.rel_url.query.get("offset", "0"))

    conditions = ["tenant_id = $1"]
    params: list = [tenant_id]
    idx = 2

    if bot_id:
        conditions.append(f"bot_id = ${idx}::uuid")
        params.append(bot_id)
        idx += 1
    if intent:
        conditions.append(f"intent = ${idx}")
        params.append(intent)
        idx += 1
    if exit_branch:
        conditions.append(f"exit_branch = ${idx}")
        params.append(exit_branch)
        idx += 1
    if min_latency:
        conditions.append(f"total_latency_ms >= ${idx}")
        params.append(int(min_latency))
        idx += 1
    if cache_hit is not None and cache_hit in ("true", "false"):
        conditions.append(f"cache_hit = ${idx}")
        params.append(cache_hit == "true")
        idx += 1

    where = " AND ".join(conditions)

    rows = await db.fetch(f"""
        SELECT trace_id, session_id, bot_id::text, channel, user_query,
               intent, intent_confidence, grader_score, cache_hit,
               total_latency_ms, llm_calls_count, llm_total_tokens,
               retrieval_chunks, exit_branch, answer_preview,
               created_at::text
        FROM traces
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
    """, *params)

    total = await db.fetchval(f"""
        SELECT COUNT(*) FROM traces WHERE {where}
    """, *params)

    return web.json_response({
        "data": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@routes.get("/api/admin/traces/stats")
async def trace_stats(request: web.Request) -> web.Response:
    """聚合统计：最近 N 小时的 Pipeline 健康度指标"""
    tenant_id = request["tenant_id"]
    db = request.app["db"]

    bot_id = request.rel_url.query.get("bot_id")
    hours = int(request.rel_url.query.get("hours", "24"))

    conditions = ["tenant_id = $1", f"created_at > NOW() - INTERVAL '{hours} hours'"]
    params: list = [tenant_id]
    idx = 2

    if bot_id:
        conditions.append(f"bot_id = ${idx}::uuid")
        params.append(bot_id)
        idx += 1

    where = " AND ".join(conditions)

    summary = await db.fetchrow(f"""
        SELECT
            COUNT(*)::int AS total_requests,
            COALESCE(AVG(total_latency_ms), 0)::int AS avg_latency_ms,
            COALESCE(
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms), 0
            )::int AS p95_latency_ms,
            COALESCE(
                AVG(grader_score) FILTER (WHERE grader_score > 0), 0
            )::float AS avg_grader_score,
            COUNT(*) FILTER (WHERE cache_hit = TRUE)::int AS cache_hits,
            COUNT(*) FILTER (WHERE should_transfer = TRUE)::int AS transfers,
            COALESCE(SUM(llm_total_tokens), 0)::int AS total_tokens,
            COALESCE(AVG(llm_calls_count), 0)::float AS avg_llm_calls,
            COUNT(*) FILTER (WHERE hallucination_action IS NOT NULL
                AND hallucination_action != 'pass')::int AS hallucination_failures
        FROM traces
        WHERE {where}
    """, *params)

    intent_dist = await db.fetch(f"""
        SELECT intent, COUNT(*)::int AS count
        FROM traces
        WHERE {where} AND intent IS NOT NULL
        GROUP BY intent
        ORDER BY count DESC
    """, *params)

    exit_dist = await db.fetch(f"""
        SELECT exit_branch, COUNT(*)::int AS count
        FROM traces
        WHERE {where} AND exit_branch IS NOT NULL
        GROUP BY exit_branch
        ORDER BY count DESC
    """, *params)

    latency_trend = await db.fetch(f"""
        SELECT
            DATE_TRUNC('hour', created_at)::text AS hour,
            COUNT(*)::int AS requests,
            COALESCE(AVG(total_latency_ms), 0)::int AS avg_latency,
            COALESCE(AVG(grader_score) FILTER (WHERE grader_score > 0), 0)::float AS avg_grader
        FROM traces
        WHERE {where}
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour ASC
    """, *params)

    return web.json_response({
        "summary": dict(summary) if summary else {},
        "intent_distribution": [dict(r) for r in intent_dist],
        "exit_distribution": [dict(r) for r in exit_dist],
        "latency_trend": [dict(r) for r in latency_trend],
        "hours": hours,
    })


@routes.get("/api/admin/traces/{trace_id}")
async def get_trace_detail(request: web.Request) -> web.Response:
    """获取单条 trace 的完整 span 列表（用于瀑布图渲染）"""
    tenant_id = request["tenant_id"]
    trace_id = request.match_info["trace_id"]
    db = request.app["db"]

    trace = await db.fetchrow("""
        SELECT trace_id, session_id, bot_id::text, tenant_id::text,
               channel, user_query, language,
               intent, intent_confidence, transform_strategy,
               grader_score, attempts, is_grounded, hallucination_action,
               cache_hit, should_transfer,
               total_latency_ms, llm_calls_count, llm_total_tokens,
               retrieval_chunks, answer_preview, exit_branch,
               created_at::text
        FROM traces
        WHERE trace_id = $1 AND tenant_id = $2
    """, trace_id, tenant_id)

    if not trace:
        return web.json_response({"error": "not found"}, status=404)

    spans = await db.fetch("""
        SELECT parent_span_id, node, operation,
               start_ms, end_ms, duration_ms,
               status, error_msg, attributes,
               created_at::text
        FROM spans
        WHERE trace_id = $1
        ORDER BY start_ms ASC
    """, trace_id)

    pipeline_start = min((s["start_ms"] for s in spans), default=0)

    span_list = []
    for s in spans:
        sd = dict(s)
        if isinstance(sd.get("attributes"), str):
            try:
                sd["attributes"] = json.loads(sd["attributes"])
            except Exception:
                sd["attributes"] = {}
        sd["offset_ms"] = sd["start_ms"] - pipeline_start
        span_list.append(sd)

    return web.json_response({
        "trace": dict(trace),
        "spans": span_list,
        "pipeline_start_ms": pipeline_start,
    })


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
