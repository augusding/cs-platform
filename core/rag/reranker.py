"""
Reranker：LLM 精排模块。
对粗排结果用 LLM 逐条评分 relevance（0-1），返回按 relevance 排序的 top-N。
batch prompt 一次评估所有 chunks，避免 N 次 LLM 调用。
"""
import json
import logging
import time

from config import settings

logger = logging.getLogger(__name__)


async def rerank(
    query: str,
    chunks: list[dict],
    top_n: int = 5,
    ctx=None,
) -> list[dict]:
    """
    LLM relevance 精排。
    返回按 relevance 降序排列的 top_n 个 chunk，每个 chunk 新增 "relevance" 字段。
    失败时退化为原顺序截断。
    """
    if not chunks:
        return []

    if len(chunks) <= top_n:
        for c in chunks:
            if "relevance" not in c:
                c["relevance"] = c.get("score", 0.5)
        return chunks

    _start = time.time()

    chunk_texts = []
    for i, c in enumerate(chunks[:15]):
        preview = (c.get("content") or "")[:200].replace("\n", " ")
        chunk_texts.append(f"[{i+1}] {preview}")

    prompt = f"""你是一个文档相关性评估器。给定用户问题和多段参考文本，为每段文本评估与问题的相关性。

用户问题：{query}

参考文本：
{chr(10).join(chunk_texts)}

请为每段文本打分（0-1），1=完全相关能直接回答问题，0=完全无关。
只输出 JSON 数组，格式如 [0.9, 0.3, 0.8, ...]，数组长度等于文本段数。
不要输出其他内容。"""

    duration_ms = 0
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        resp = await client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

        scores = json.loads(raw)
        if not isinstance(scores, list):
            raise ValueError(f"Expected list, got {type(scores)}")

        evaluated = chunks[:len(scores)]
        for i, c in enumerate(evaluated):
            c["relevance"] = float(scores[i])
        for c in chunks[len(scores):]:
            c["relevance"] = 0.0

        duration_ms = int((time.time() - _start) * 1000)
        logger.info(
            f"[Reranker] Scored {len(scores)} chunks in {duration_ms}ms, "
            f"top={max(scores):.2f} min={min(scores):.2f}"
        )

        if ctx and hasattr(ctx, 'add_span'):
            tokens_out = len(raw) // 2
            ctx.add_span(
                "llm_call", "llm_rerank",
                duration_ms=duration_ms,
                attributes={
                    "model": settings.QWEN_MODEL,
                    "provider": "qwen",
                    "tokens_out": tokens_out,
                    "chunks_scored": len(scores),
                },
            )

    except Exception as e:
        logger.warning(f"[Reranker] LLM scoring failed: {e}, falling back to original order")
        for c in chunks:
            if "relevance" not in c:
                c["relevance"] = c.get("score", 0.5)
        duration_ms = int((time.time() - _start) * 1000)

    sorted_chunks = sorted(chunks, key=lambda x: x.get("relevance", 0), reverse=True)

    if ctx and hasattr(ctx, 'add_span'):
        ctx.add_span(
            "reranker", "rerank_sort",
            duration_ms=duration_ms,
            attributes={
                "input_count": len(chunks),
                "output_count": min(top_n, len(sorted_chunks)),
                "top_relevance": sorted_chunks[0].get("relevance", 0) if sorted_chunks else 0,
            },
        )

    return sorted_chunks[:top_n]
