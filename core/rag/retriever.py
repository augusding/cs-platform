"""
Retriever 节点：hybrid search（vector + BM25 + RRF 融合 + LLM 精排）。
写字段：retrieved_chunks
"""
import logging
import re

from config import settings
from core.rag.state import RAGState

logger = logging.getLogger(__name__)

_FAQ_STOP_WORDS = {
    "的", "了", "是", "在", "有", "和", "与", "或", "怎么", "什么", "如何",
    "吗", "呢", "啊", "哦", "那", "这", "请问", "一下", "可以",
    "the", "is", "are", "what", "how", "do", "does", "of", "to", "a", "an",
    "can", "you", "your", "i", "we", "my",
}

_RRF_K = 60


def _bm25_score(chunks: list[dict], query: str) -> list[dict]:
    """BM25 关键词评分（简化版：命中比例归一化）"""
    query_lower = query.lower()
    raw_tokens = re.findall(r'[\w\u4e00-\u9fff]+', query_lower)
    keywords = [t for t in raw_tokens if t not in _FAQ_STOP_WORDS and len(t) > 1]

    # 中文补充 bigram
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', query_lower)
    bigrams = []
    for seg in chinese_chars:
        for i in range(len(seg) - 1):
            bigrams.append(seg[i:i+2])
    keywords.extend(bigrams)

    if not keywords:
        return [{**c, "bm25_score": 0.0} for c in chunks]

    scored = []
    for chunk in chunks:
        content_lower = (chunk.get("content") or "").lower()
        hits = sum(1 for kw in keywords if kw in content_lower)
        score = min(hits / max(len(keywords), 1), 1.0)
        scored.append({**chunk, "bm25_score": score})
    return scored


def _rrf_merge(vector_chunks: list[dict], bm25_chunks: list[dict],
               top_k: int = 10) -> list[dict]:
    """Reciprocal Rank Fusion 合并 vector + BM25"""
    vector_ranks = {}
    for rank, c in enumerate(vector_chunks):
        cid = c.get("chunk_id") or str(id(c))
        vector_ranks[cid] = rank

    bm25_sorted = sorted(bm25_chunks, key=lambda x: x.get("bm25_score", 0), reverse=True)
    bm25_ranks = {}
    for rank, c in enumerate(bm25_sorted):
        cid = c.get("chunk_id") or str(id(c))
        bm25_ranks[cid] = rank

    all_chunks = {}
    for c in vector_chunks:
        cid = c.get("chunk_id") or str(id(c))
        all_chunks[cid] = c
    for c in bm25_sorted:
        cid = c.get("chunk_id") or str(id(c))
        if cid not in all_chunks:
            all_chunks[cid] = c

    max_rank = len(all_chunks) + 1
    rrf_scored = []
    for cid, chunk in all_chunks.items():
        v_rank = vector_ranks.get(cid, max_rank)
        b_rank = bm25_ranks.get(cid, max_rank)
        rrf_score = 1.0 / (_RRF_K + v_rank) + 1.0 / (_RRF_K + b_rank)
        # 保留原始 cosine score，无 rerank 时 Grader 需要用它作为 relevance
        cosine_score = chunk.get("score", 0.0)
        rrf_scored.append({
            **chunk,
            "cosine_score": cosine_score,
            "rrf_score": rrf_score,
            "score": rrf_score,
        })

    rrf_scored.sort(key=lambda x: x["rrf_score"], reverse=True)
    return rrf_scored[:top_k]


async def run(state: RAGState, ctx=None) -> RAGState:
    query = state.transformed_query or state.user_query
    top_k = settings.RETRIEVAL_TOP_K

    logger.info(
        f"[Retriever] bot={state.bot_id[:8]} "
        f"query='{query[:60]}' "
        f"strategy={state.transform_strategy}"
    )

    # ── 1. FAQ 搜索 ──
    if ctx and hasattr(ctx, 'span'):
        async with ctx.span("retriever", "faq_search") as _fs:
            faq_chunks = await _search_faq(state)
            _fs.attributes["count"] = len(faq_chunks)
    else:
        faq_chunks = await _search_faq(state)

    # ── 2. 向量搜索 ──
    if state.sub_queries and len(state.sub_queries) >= 2:
        # Comparison / decompose：对每个子查询并行检索，合并去重
        import asyncio as _aio
        vector_top_per = top_k

        async def _parallel_search():
            tasks = [
                _search_vector(state, sq, vector_top_per)
                for sq in state.sub_queries[:3]
            ]
            results = await _aio.gather(*tasks)
            seen_ids = set()
            merged_vec = []
            for chunk_list in results:
                for c in chunk_list:
                    cid = c.get("chunk_id", "")
                    if cid and cid in seen_ids:
                        continue
                    if cid:
                        seen_ids.add(cid)
                    merged_vec.append(c)
            return merged_vec

        if ctx and hasattr(ctx, 'span'):
            async with ctx.span("retriever", "vector_search_parallel") as _vs:
                vector_chunks = await _parallel_search()
                _vs.attributes["sub_queries"] = len(state.sub_queries)
                _vs.attributes["count"] = len(vector_chunks)
                _vs.attributes["top_score"] = (
                    vector_chunks[0]["score"] if vector_chunks else 0
                )
        else:
            vector_chunks = await _parallel_search()
    else:
        # 常规单查询检索
        vector_top = top_k * 2
        if ctx and hasattr(ctx, 'span'):
            async with ctx.span("retriever", "vector_search") as _vs:
                vector_chunks = await _search_vector(state, query, vector_top)
                _vs.attributes["count"] = len(vector_chunks)
                _vs.attributes["top_score"] = (
                    vector_chunks[0]["score"] if vector_chunks else 0
                )
        else:
            vector_chunks = await _search_vector(state, query, vector_top)

    # ── 3. BM25 评分 ──
    if ctx and hasattr(ctx, 'span'):
        async with ctx.span("retriever", "bm25_score") as _bs:
            bm25_chunks = _bm25_score(vector_chunks, query)
            _bs.attributes["top_bm25"] = (
                max((c["bm25_score"] for c in bm25_chunks), default=0)
            )
    else:
        bm25_chunks = _bm25_score(vector_chunks, query)

    # ── 4. RRF 融合 ──
    merged = _rrf_merge(vector_chunks, bm25_chunks, top_k=top_k)

    # ── 5. LLM 精排（仅对长查询或 re-retrieve 时启用）──
    use_rerank = (
        len(state.user_query) > 15  # 短查询跳过
        and state.attempts > 0      # 首次检索不精排，re-retrieve 时才精排
    )  # comparison 不再强制精排，BM25 + RRF 已足够

    if use_rerank:
        try:
            from core.rag.reranker import rerank
            reranked = await rerank(
                query=state.user_query,
                chunks=merged,
                top_n=min(top_k, 5),
                ctx=ctx,
            )
        except Exception as e:
            logger.warning(f"[Retriever] Rerank failed: {e}")
            reranked = merged[:5]
    else:
        # 不精排：直接用 RRF 排序的 top-5
        # relevance 用原始 cosine score（RRF score 是相对排序分，不是绝对相关度）
        reranked = merged[:5]
        for c in reranked:
            c["relevance"] = c.get("cosine_score", c.get("score", 0.5))

    # ── 6. 合并 FAQ + 精排结果 ──
    final_chunks = faq_chunks + reranked

    # 去重
    seen = set()
    deduped = []
    for c in final_chunks:
        cid = c.get("chunk_id", "")
        if cid and cid in seen:
            continue
        if cid:
            seen.add(cid)
        deduped.append(c)

    state.retrieved_chunks = deduped[:top_k]

    top_score = 0.0
    if state.retrieved_chunks:
        first = state.retrieved_chunks[0]
        top_score = first.get("relevance", first.get("score", 0)) or 0
    logger.info(
        f"[Retriever] returned {len(state.retrieved_chunks)} chunks, "
        f"top_relevance={top_score:.3f}, faq={len(faq_chunks)}, reranked={len(reranked)}"
    )

    if ctx and hasattr(ctx, 'add_span'):
        ctx.add_span("retriever", "retriever_final",
                     attributes={
                         "total_chunks": len(state.retrieved_chunks),
                         "faq_count": len(faq_chunks),
                         "vector_count": len(vector_chunks),
                         "reranked_count": len(reranked),
                         "top_relevance": round(top_score, 3),
                     })

    return state


async def _search_faq(state: RAGState) -> list[dict]:
    """FAQ 关键词检索"""
    pool = getattr(state, "db_pool", None)
    if pool is None:
        logger.debug("FAQ search skipped: no db_pool in state")
        return []

    try:
        query_lower = state.user_query.lower()
        raw_tokens = query_lower.split()
        keywords: list[str] = []
        for tok in raw_tokens:
            if len(tok) > 1 and tok not in _FAQ_STOP_WORDS:
                keywords.append(tok)
        if not keywords and len(query_lower.strip()) >= 2:
            keywords = [query_lower.strip()]

        if not keywords:
            rows = await pool.fetch(
                """
                SELECT question, answer, priority
                FROM faq_items
                WHERE bot_id = $1 AND is_active = TRUE
                ORDER BY priority DESC
                LIMIT 3
                """,
                state.bot_id,
            )
        else:
            patterns = [f"%{kw}%" for kw in keywords]
            rows = await pool.fetch(
                """
                SELECT question, answer, priority
                FROM faq_items
                WHERE bot_id = $1
                  AND is_active = TRUE
                  AND (
                      LOWER(question) LIKE ANY($2::text[])
                      OR LOWER(answer)   LIKE ANY($2::text[])
                  )
                ORDER BY priority DESC, LENGTH(question) ASC
                LIMIT 5
                """,
                state.bot_id,
                patterns,
            )

        chunks: list[dict] = []
        for row in rows:
            base = 0.95 + (row["priority"] or 0) * 0.001
            chunks.append({
                "content": f"问：{row['question']}\n答：{row['answer']}",
                "score": min(base + 0.15, 1.0),
                "relevance": 0.95,
                "chunk_id": f"faq_{row['question'][:20]}",
                "source_id": "faq",
                "page": 0,
            })
        if chunks:
            logger.debug(
                f"FAQ search: {len(chunks)} matches for '{state.user_query[:30]}'"
            )
        return chunks

    except Exception as e:
        logger.warning(f"FAQ search failed: {e}")
        return []


async def _search_vector(state: RAGState, query: str, top_k: int) -> list[dict]:
    """向量检索"""
    try:
        from knowledge.embedder import embed_single
        from knowledge.vector_store import search
        vector = await embed_single(query)
        chunks = search(state.bot_id, vector, top_k=top_k)
        return chunks
    except Exception as e:
        logger.warning(f"Vector search failed: {e}")
        return []
