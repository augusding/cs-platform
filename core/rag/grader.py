"""
Grader 节点：评估检索质量，决定是否 re-retrieve。
使用 embedding 相似度评分（轻量，无额外 LLM 调用）。
写字段：grader_score, attempts
"""
import logging
import math

from config import settings
from core.rag.state import RAGState

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 2


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def run(state: RAGState) -> RAGState:
    if not state.retrieved_chunks:
        state.grader_score = 0.0
        return state

    top_chunks = state.retrieved_chunks[:3]
    scores = [c.get("score", 0.0) for c in top_chunks]
    state.grader_score = sum(scores) / len(scores)

    logger.debug(
        f"Grader score: {state.grader_score:.3f} "
        f"(threshold={settings.GRADER_THRESHOLD}, attempts={state.attempts})"
    )
    state.trace("grader", {
        "score": state.grader_score,
        "passed": state.grader_score >= settings.GRADER_THRESHOLD,
        "attempts": state.attempts,
    })
    return state


def should_retry(state: RAGState) -> bool:
    """返回 True 表示需要 re-retrieve"""
    return (
        state.grader_score < settings.GRADER_THRESHOLD
        and state.attempts < _MAX_ATTEMPTS
    )
