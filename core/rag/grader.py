"""
Grader 节点：评估检索质量，决定是否 re-retrieve。
优先使用 LLM reranker 的 relevance 分数，fallback 到 cosine score。
写字段：grader_score, attempts
"""
import logging

from config import settings
from core.rag.state import RAGState

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 2


async def run(state: RAGState, ctx=None) -> RAGState:
    if ctx is None:
        from core.observability import NullTraceContext
        ctx = NullTraceContext()

    if not state.retrieved_chunks:
        state.grader_score = 0.0
        async with ctx.span("grader") as _s:
            _s.attributes["score"] = 0.0
            _s.attributes["no_chunks"] = True
        state.trace("grader", {"score": 0.0, "passed": False, "attempts": state.attempts})
        return state

    async with ctx.span("grader") as _s:
        _grade(state, _s)

    state.trace("grader", {
        "score": state.grader_score,
        "passed": state.grader_score >= settings.GRADER_THRESHOLD,
        "attempts": state.attempts,
    })
    return state


def _grade(state: RAGState, span=None):
    """计算 grader_score：优先用 relevance，fallback 用 score"""
    top_chunks = state.retrieved_chunks[:3]

    scores = []
    for c in top_chunks:
        rel = c.get("relevance")
        if rel is not None:
            scores.append(float(rel))
        else:
            scores.append(float(c.get("score", 0.0)))

    state.grader_score = sum(scores) / len(scores) if scores else 0.0

    logger.debug(
        f"Grader score: {state.grader_score:.3f} "
        f"(threshold={settings.GRADER_THRESHOLD}, attempts={state.attempts}) "
        f"individual=[{', '.join(f'{s:.2f}' for s in scores)}]"
    )

    if span:
        span.attributes["score"] = round(state.grader_score, 3)
        span.attributes["threshold"] = settings.GRADER_THRESHOLD
        span.attributes["passed"] = state.grader_score >= settings.GRADER_THRESHOLD
        span.attributes["attempts"] = state.attempts
        span.attributes["individual_scores"] = [round(s, 3) for s in scores]
        span.attributes["score_source"] = (
            "relevance" if state.retrieved_chunks[0].get("relevance") is not None
            else "cosine"
        )


def should_retry(state: RAGState) -> bool:
    """返回 True 表示需要 re-retrieve"""
    # 所有 chunk relevance 都极低（< 0.2），不值得重试
    if state.retrieved_chunks:
        top_rel = max(
            c.get("relevance", c.get("score", 0))
            for c in state.retrieved_chunks[:3]
        )
        if top_rel < 0.2:
            logger.info(
                f"Grader: all chunks very low relevance ({top_rel:.2f}), skip retry"
            )
            return False

    return (
        state.grader_score < settings.GRADER_THRESHOLD
        and state.attempts < _MAX_ATTEMPTS
    )
