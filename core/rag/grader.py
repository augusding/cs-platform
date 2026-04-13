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

    # 根据分数来源选择自适应阈值
    # cosine score 天然偏低（0.4-0.6），LLM relevance 更严格（0-1 真实相关度）
    is_reranked = any(
        c.get("relevance") is not None
        and c.get("cosine_score") is not None
        and c.get("relevance") != c.get("cosine_score")
        for c in top_chunks
    )
    if is_reranked:
        effective_threshold = settings.GRADER_THRESHOLD
    else:
        effective_threshold = max(settings.GRADER_THRESHOLD - 0.15, 0.30)

    state._effective_threshold = effective_threshold

    logger.debug(
        f"Grader score: {state.grader_score:.3f} "
        f"(threshold={effective_threshold:.2f}, attempts={state.attempts}) "
        f"individual=[{', '.join(f'{s:.2f}' for s in scores)}]"
    )

    if span:
        span.attributes["score"] = round(state.grader_score, 3)
        span.attributes["threshold"] = settings.GRADER_THRESHOLD
        span.attributes["effective_threshold"] = effective_threshold
        span.attributes["passed"] = state.grader_score >= effective_threshold
        span.attributes["attempts"] = state.attempts
        span.attributes["individual_scores"] = [round(s, 3) for s in scores]
        span.attributes["score_source"] = "relevance_reranked" if is_reranked else "cosine"


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

    # re-retrieve 分数改善 < 0.05，不再重试
    if state.attempts > 0 and state.prev_grader_score > 0:
        improvement = state.grader_score - state.prev_grader_score
        if improvement < 0.05:
            logger.info(
                f"Grader: re-retrieve didn't improve "
                f"({state.prev_grader_score:.3f} -> {state.grader_score:.3f}), stopping retry"
            )
            return False

    # 使用自适应阈值
    threshold = getattr(state, '_effective_threshold', settings.GRADER_THRESHOLD)
    return (
        state.grader_score < threshold
        and state.attempts < _MAX_ATTEMPTS
    )
