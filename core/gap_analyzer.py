"""
知识盲区分析引擎。
从 traces 表中识别 AI 答不好的查询，聚类归纳为知识盲区，生成补充建议。
"""
import json
import logging
import time

logger = logging.getLogger(__name__)

GRADER_LOW_THRESHOLD = 0.45
CLUSTER_SIMILARITY_THRESHOLD = 0.80
MAX_SAMPLE_QUERIES = 5
MIN_QUERIES_FOR_GAP = 2


async def analyze_gaps(db_pool, bot_id: str, tenant_id: str,
                       days: int = 7) -> list[dict]:
    """主入口：分析指定 Bot 最近 N 天的知识盲区"""
    start_time = time.time()

    failed_queries = await _collect_failed_queries(db_pool, bot_id, tenant_id, days)
    if not failed_queries:
        logger.info(f"[GapAnalyzer] No failed queries for bot {bot_id[:8]} in {days} days")
        return []

    logger.info(f"[GapAnalyzer] Found {len(failed_queries)} failed queries for bot {bot_id[:8]}")

    clusters = await _cluster_queries(failed_queries)
    logger.info(f"[GapAnalyzer] Clustered into {len(clusters)} groups")

    significant = [c for c in clusters if c["count"] >= MIN_QUERIES_FOR_GAP]
    logger.info(f"[GapAnalyzer] {len(significant)} significant clusters (>= {MIN_QUERIES_FOR_GAP} queries)")

    gaps = []
    for cluster in significant:
        gap = await _generate_gap_info(cluster, bot_id, tenant_id)
        gaps.append(gap)

    saved = await _save_gaps(db_pool, gaps, bot_id, tenant_id)

    duration = int((time.time() - start_time) * 1000)
    logger.info(
        f"[GapAnalyzer] Done: {len(saved)} gaps saved/updated, {duration}ms"
    )
    return saved


async def _collect_failed_queries(db_pool, bot_id: str, tenant_id: str,
                                   days: int) -> list[dict]:
    """从 traces 表收集失败查询"""
    rows = await db_pool.fetch("""
        SELECT trace_id, user_query, intent, grader_score,
               exit_branch, hallucination_action, session_id,
               created_at
        FROM traces
        WHERE bot_id = $1::uuid
          AND tenant_id = $2::uuid
          AND created_at > NOW() - INTERVAL '1 day' * $3
          AND (
              grader_score < $4
              OR exit_branch IN ('out_of_scope', 'transfer', 'clarification')
              OR (hallucination_action IS NOT NULL AND hallucination_action != 'pass')
          )
          AND user_query IS NOT NULL
          AND LENGTH(user_query) > 2
        ORDER BY created_at DESC
        LIMIT 500
    """, bot_id, tenant_id, days, GRADER_LOW_THRESHOLD)

    queries = []
    for r in rows:
        signal = _classify_signal(r)
        queries.append({
            "query": r["user_query"],
            "signal": signal,
            "grader_score": float(r["grader_score"] or 0),
            "session_id": r["session_id"],
            "trace_id": r["trace_id"],
            "created_at": r["created_at"],
        })
    return queries


def _classify_signal(row) -> str:
    """判断失败信号类型"""
    if row["exit_branch"] == "out_of_scope":
        return "out_of_scope"
    if row["exit_branch"] == "transfer":
        return "transfer"
    if row["hallucination_action"] and row["hallucination_action"] != "pass":
        return "hallucination"
    if row["exit_branch"] == "clarification":
        return "clarification"
    return "low_grader"


async def _cluster_queries(queries: list[dict]) -> list[dict]:
    """语义聚类：embedding cosine + 贪心聚类"""
    import math
    from knowledge.embedder import embed_texts

    texts = [q["query"] for q in queries]
    try:
        vectors = await embed_texts(texts)
    except Exception as e:
        logger.warning(f"[GapAnalyzer] Embedding failed: {e}, fallback to no clustering")
        return [
            {"queries": [q], "count": 1, "centroid_idx": 0, "unique_sessions": 1}
            for q in queries
        ]

    clusters: list[dict] = []
    assigned = [False] * len(queries)

    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb) if na and nb else 0

    for i in range(len(queries)):
        if assigned[i]:
            continue
        sessions = {queries[i]["session_id"]}
        cluster = {
            "queries": [queries[i]],
            "count": 1,
            "centroid_idx": i,
        }
        assigned[i] = True

        for j in range(i + 1, len(queries)):
            if assigned[j]:
                continue
            sim = cosine(vectors[i], vectors[j])
            if sim >= CLUSTER_SIMILARITY_THRESHOLD:
                cluster["queries"].append(queries[j])
                cluster["count"] += 1
                sessions.add(queries[j]["session_id"])
                assigned[j] = True

        cluster["unique_sessions"] = len(sessions)
        clusters.append(cluster)

    clusters.sort(key=lambda c: c["count"], reverse=True)
    return clusters


async def _generate_gap_info(cluster: dict, bot_id: str, tenant_id: str) -> dict:
    """为一个聚类生成标签和补充建议"""
    sample_queries = [q["query"] for q in cluster["queries"][:MAX_SAMPLE_QUERIES]]
    signals: dict = {}
    total_grader = 0.0
    for q in cluster["queries"]:
        sig = q["signal"]
        signals[sig] = signals.get(sig, 0) + 1
        total_grader += q["grader_score"]

    primary_signal = max(signals, key=signals.get)
    avg_grader = total_grader / len(cluster["queries"]) if cluster["queries"] else 0

    first_seen = min(q["created_at"] for q in cluster["queries"])
    last_seen = max(q["created_at"] for q in cluster["queries"])

    label, suggestion = await _llm_generate_suggestion(sample_queries)

    return {
        "bot_id": bot_id,
        "tenant_id": tenant_id,
        "cluster_label": label,
        "sample_queries": sample_queries,
        "query_count": cluster["count"],
        "unique_sessions": cluster.get("unique_sessions", cluster["count"]),
        "avg_grader_score": round(avg_grader, 3),
        "primary_signal": primary_signal,
        "signal_breakdown": signals,
        "suggested_content": suggestion,
        "first_seen": first_seen,
        "last_seen": last_seen,
    }


async def _llm_generate_suggestion(sample_queries: list[str]) -> tuple[str, str]:
    """LLM 生成盲区标签 + 补充内容建议"""
    from config import settings

    queries_text = "\n".join(f"- {q}" for q in sample_queries)

    prompt = f"""以下是客户咨询中AI客服无法有效回答的问题列表：

{queries_text}

请完成两个任务：

1. 用一个短标签（5-10个字）概括这些问题的共同主题
2. 建议企业应该补充哪些知识内容才能回答这类问题，列出 3-5 条具体内容要点

输出 JSON 格式：
{{"label": "标签", "suggestion": "1. 内容点一\\n2. 内容点二\\n3. 内容点三"}}

只输出 JSON，不要其他内容。"""

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        resp = await client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        return data.get("label", "未分类问题"), data.get("suggestion", "")
    except Exception as e:
        logger.warning(f"[GapAnalyzer] LLM suggestion failed: {e}")
        return sample_queries[0][:20] + "相关", "请补充相关产品或服务信息"


async def _save_gaps(db_pool, gaps: list[dict], bot_id: str,
                     tenant_id: str) -> list[dict]:
    """写入 DB，已有同标签的 open gap 则更新计数"""
    saved = []
    for gap in gaps:
        existing = await db_pool.fetchrow("""
            SELECT id, query_count, sample_queries FROM knowledge_gaps
            WHERE bot_id = $1::uuid AND tenant_id = $2::uuid
              AND cluster_label = $3 AND status = 'open'
        """, bot_id, tenant_id, gap["cluster_label"])

        if existing:
            existing_samples = existing["sample_queries"]
            if isinstance(existing_samples, str):
                existing_samples = json.loads(existing_samples)
            merged_samples = list(dict.fromkeys(
                list(existing_samples) + list(gap["sample_queries"])
            ))[:MAX_SAMPLE_QUERIES]

            await db_pool.execute("""
                UPDATE knowledge_gaps
                SET query_count = query_count + $1,
                    unique_sessions = unique_sessions + $2,
                    sample_queries = $3::jsonb,
                    avg_grader_score = $4,
                    last_seen = $5,
                    suggested_content = COALESCE($6, suggested_content),
                    updated_at = NOW()
                WHERE id = $7
            """,
                gap["query_count"],
                gap["unique_sessions"],
                json.dumps(merged_samples, ensure_ascii=False),
                gap["avg_grader_score"],
                gap["last_seen"],
                gap["suggested_content"],
                existing["id"],
            )
            gap["id"] = str(existing["id"])
        else:
            row = await db_pool.fetchrow("""
                INSERT INTO knowledge_gaps (
                    tenant_id, bot_id, cluster_label, sample_queries,
                    query_count, unique_sessions, avg_grader_score,
                    primary_signal, signal_breakdown, suggested_content,
                    first_seen, last_seen
                ) VALUES (
                    $1::uuid, $2::uuid, $3, $4::jsonb,
                    $5, $6, $7,
                    $8, $9::jsonb, $10,
                    $11, $12
                ) RETURNING id::text
            """,
                tenant_id, bot_id, gap["cluster_label"],
                json.dumps(gap["sample_queries"], ensure_ascii=False),
                gap["query_count"], gap["unique_sessions"], gap["avg_grader_score"],
                gap["primary_signal"],
                json.dumps(gap["signal_breakdown"], ensure_ascii=False),
                gap["suggested_content"],
                gap["first_seen"], gap["last_seen"],
            )
            gap["id"] = row["id"]

        saved.append(gap)
    return saved
