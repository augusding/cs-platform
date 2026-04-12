"""
Retriever 节点：hybrid search（vector + BM25 关键词）。
写字段：retrieved_chunks
"""
import logging
import re

from config import settings
from core.rag.state import RAGState

logger = logging.getLogger(__name__)


def _bm25_filter(chunks: list[dict], query: str, top_k: int) -> list[dict]:
    """
    简单 BM25 近似：统计 query 关键词命中次数作为补充分数。
    生产环境可替换为 Elasticsearch / Meilisearch。
    """
    keywords = set(re.findall(r"\w+", query.lower()))
    scored: list[dict] = []
    for chunk in chunks:
        content_lower = chunk["content"].lower()
        kw_hits = sum(1 for kw in keywords if kw in content_lower)
        combined = (
            chunk["score"] * 0.7
            + min(kw_hits / max(len(keywords), 1), 1.0) * 0.3
        )
        scored.append({**chunk, "score": combined})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


async def run(state: RAGState) -> RAGState:
    query = state.transformed_query or state.user_query
    top_k = settings.RETRIEVAL_TOP_K

    logger.info(
        f"[Retriever] bot={state.bot_id[:8]} "
        f"query='{query[:60]}' "
        f"strategy={state.transform_strategy}"
    )

    faq_chunks = await _search_faq(state)
    vector_chunks = await _search_vector(state, query, top_k)

    all_chunks = faq_chunks + vector_chunks
    state.retrieved_chunks = all_chunks[:top_k]

    top_score = state.retrieved_chunks[0]["score"] if state.retrieved_chunks else 0.0
    logger.info(
        f"[Retriever] returned {len(state.retrieved_chunks)} chunks, "
        f"top_score={top_score:.3f}"
    )
    for i, c in enumerate(state.retrieved_chunks[:3]):
        logger.debug(
            f"  chunk[{i}] score={c.get('score',0):.3f} "
            f"source={c.get('source_id','')[:8]} "
            f"content='{c.get('content','')[:50]}'"
        )

    state.trace("retriever", {
        "chunks_count": len(state.retrieved_chunks),
        "top_score": state.retrieved_chunks[0]["score"] if state.retrieved_chunks else 0,
        "sources": list({c.get("source_id", "") for c in state.retrieved_chunks[:5]}),
    })
    return state


_FAQ_STOP_WORDS = {
    "的", "了", "是", "在", "有", "和", "与", "或", "怎么", "什么", "如何",
    "吗", "呢", "啊", "哦", "那", "这",
    "the", "is", "are", "what", "how", "do", "does", "of", "to", "a", "an",
}


async def _search_faq(state: RAGState) -> list[dict]:
    """使用注入的 db_pool 检索 FAQ（按关键词 LIKE 匹配）。"""
    pool = getattr(state, "db_pool", None)
    if pool is None:
        logger.debug("FAQ search skipped: no db_pool in state")
        return []

    try:
        query_lower = state.user_query.lower()
        # 中英混合：先按空格分词，再对每个分词按字符过滤停用词
        raw_tokens = query_lower.split()
        keywords: list[str] = []
        for tok in raw_tokens:
            if len(tok) > 1 and tok not in _FAQ_STOP_WORDS:
                keywords.append(tok)
        # 没有英文分词时，取整条 query 作为单个关键词（中文短句常见）
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
            chunks.append({
                "content": f"问：{row['question']}\n答：{row['answer']}",
                # FAQ 优先级最高，+ priority 微调避免同分
                "score": 0.95 + (row["priority"] or 0) * 0.001,
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
