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

    faq_chunks = await _search_faq(state)
    vector_chunks = await _search_vector(state, query, top_k)

    all_chunks = faq_chunks + vector_chunks
    state.retrieved_chunks = all_chunks[:top_k]

    logger.debug(
        f"Retrieved {len(faq_chunks)} faq + {len(vector_chunks)} vector chunks"
    )
    return state


async def _search_faq(state: RAGState) -> list[dict]:
    """从 DB 检索 FAQ（简单关键词匹配）"""
    try:
        import asyncpg
        pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL, min_size=1, max_size=2
        )
        query_lower = state.user_query.lower()
        rows = await pool.fetch(
            """
            SELECT question, answer, priority
            FROM faq_items
            WHERE bot_id = $1 AND is_active = TRUE
            ORDER BY priority DESC
            LIMIT 20
            """,
            state.bot_id,
        )
        await pool.close()
        chunks: list[dict] = []
        for row in rows:
            if any(kw in row["question"].lower() for kw in query_lower.split()):
                chunks.append({
                    "content": f"Q: {row['question']}\nA: {row['answer']}",
                    "score": 1.0,
                    "chunk_id": f"faq_{row['question'][:16]}",
                    "source_id": "faq",
                })
        return chunks[:3]
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
