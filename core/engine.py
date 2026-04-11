"""
CSEngine：Agentic RAG Pipeline 编排器。
控制节点执行顺序和 re-retrieve 循环。
"""
import logging
import re
import time
import uuid

from config import settings
from core.rag.state import RAGState
from core.rag import (
    router,
    query_transform,
    retriever,
    grader,
    generator,
    hallucination_checker,
)

logger = logging.getLogger(__name__)

_OUT_OF_SCOPE_ZH = "抱歉，这个问题超出了我的服务范围，请咨询相关专业人士。"
_OUT_OF_SCOPE_EN = "Sorry, this question is outside my scope of service."
_CLARIFY_ZH = "这个问题我需要为您转接人工确认，请稍候。"
_CLARIFY_EN = "I need to transfer you to a human agent for this question."

_INJECTION_PATTERN = re.compile(
    r"(?i)(ignore|forget|disregard|override)\s{0,10}"
    r"(previous|above|all|prior|system|instruction)"
)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MAX_INPUT_LEN = 2000


def sanitize_input(text: str) -> str:
    """
    Prompt 注入防御：清洗用户输入。
    1. 过滤常见注入模式（ignore/forget/disregard/override + previous/system/…）
    2. Strip HTML 标签和控制字符
    3. 截断超长输入至 2000 字符
    """
    text = _INJECTION_PATTERN.sub("[filtered]", text)
    text = _HTML_TAG_PATTERN.sub("", text)
    text = _CONTROL_CHAR_PATTERN.sub("", text)
    return text[:_MAX_INPUT_LEN].strip()


async def run_pipeline(
    user_query: str,
    bot_id: str,
    tenant_id: str,
    session_id: str | None = None,
    language: str = "zh",
    history: list[dict] | None = None,
    on_token=None,
) -> RAGState:
    """
    执行完整 RAG pipeline，返回最终 RAGState。
    on_token: 流式输出回调，每个 token 调用一次。
    """
    start = time.time()
    user_query = sanitize_input(user_query)
    state = RAGState(
        session_id=session_id or str(uuid.uuid4()),
        bot_id=bot_id,
        tenant_id=tenant_id,
        user_query=user_query,
        language=language,
        history=history or [],
    )

    # ── 语义缓存检查 ─────────────────────────────────────
    cached = await _check_semantic_cache(state)
    if cached:
        state.generated_answer = cached
        state.is_grounded = True
        state.hallucination_action = "pass"
        state.cache_hit = True
        if on_token:
            await on_token(cached)
        state.total_latency_ms = int((time.time() - start) * 1000)
        return state

    # ── 1. Router ──────────────────────────────────────
    state = await router.run(state)
    logger.debug(f"[{state.session_id}] Router: intent={state.intent}")

    if state.intent == "out_of_scope":
        msg = _OUT_OF_SCOPE_ZH if language == "zh" else _OUT_OF_SCOPE_EN
        state.generated_answer = msg
        state.is_grounded = True
        state.hallucination_action = "pass"
        if on_token:
            await on_token(msg)
        state.total_latency_ms = int((time.time() - start) * 1000)
        return state

    if state.intent == "transfer":
        state.should_transfer = True
        state.total_latency_ms = int((time.time() - start) * 1000)
        return state

    if state.skip_retrieval:
        state = await generator.run(state, on_token=on_token)
        state.is_grounded = True
        state.hallucination_action = "pass"
        state.total_latency_ms = int((time.time() - start) * 1000)
        return state

    # ── 2-4. QueryTransform → Retriever → Grader（含 re-retrieve 循环）
    while True:
        state = await query_transform.run(state)
        state = await retriever.run(state)
        state = await grader.run(state)

        logger.debug(
            f"[{state.session_id}] Grader: score={state.grader_score:.3f} "
            f"attempts={state.attempts}"
        )

        if not grader.should_retry(state):
            break

        state.attempts += 1
        logger.info(
            f"[{state.session_id}] Re-retrieve #{state.attempts} "
            f"(score={state.grader_score:.3f})"
        )

    # ── 5. Generator（流式）─────────────────────────────
    state = await generator.run(state, on_token=on_token)

    # ── 6. HallucinationChecker ──────────────────────────
    state = await hallucination_checker.run(state)
    logger.debug(
        f"[{state.session_id}] Hallucination: "
        f"grounded={state.is_grounded} action={state.hallucination_action}"
    )

    if state.hallucination_action == "clarify":
        msg = _CLARIFY_ZH if language == "zh" else _CLARIFY_EN
        state.generated_answer = msg
        state.should_transfer = True

    if state.is_grounded and state.hallucination_action == "pass":
        await _write_semantic_cache(state)

    state.total_latency_ms = int((time.time() - start) * 1000)
    logger.info(
        f"[{state.session_id}] Pipeline done: "
        f"{state.total_latency_ms}ms grader={state.grader_score:.2f} "
        f"cache_hit={state.cache_hit}"
    )
    return state


async def _check_semantic_cache(state: RAGState) -> str | None:
    """Phase 2 实现：精确命中 → 语义相似度匹配。当前返回 None。"""
    if not settings.SEMANTIC_CACHE_ENABLED:
        return None
    return None


async def _write_semantic_cache(state: RAGState) -> None:
    """Week 4 缓存模块完成后补充"""
    return None
