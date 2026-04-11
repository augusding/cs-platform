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

    # ── 中途 lead_capture 检测：有挂起的 lead 状态则跳过缓存 + Router ──
    pending_lead = await _load_lead_state(state.session_id)
    if pending_lead:
        state.intent = "lead_capture"
        state.lead_info = pending_lead
    else:
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

    if state.intent == "lead_capture":
        from core.rag.lead_collector import (
            extract_info,
            get_next_missing_field,
            calculate_intent_score,
            prompt_for,
        )

        lead_info = dict(state.lead_info or {})

        # 把本次用户输入写入下一个缺失字段
        next_missing = get_next_missing_field(lead_info)
        if next_missing:
            extracted = await extract_info(
                user_query, next_missing["key"], language
            )
            if extracted:
                lead_info[next_missing["key"]] = extracted

        state.lead_info = lead_info
        next_missing = get_next_missing_field(lead_info)

        if next_missing:
            prompt = prompt_for(next_missing, language)
            state.generated_answer = prompt
            state.is_grounded = True
            state.hallucination_action = "pass"
            await _save_lead_state(state.session_id, lead_info)
            if on_token:
                await on_token(prompt)
        else:
            state.lead_info["_score"] = calculate_intent_score(lead_info)
            state.lead_info["_complete"] = True
            complete_msg = (
                "感谢您提供的信息！我们已记录您的需求，业务人员将在 24 小时内与您联系。"
                if language == "zh"
                else "Thank you for your information! Our team will contact you within 24 hours."
            )
            state.generated_answer = complete_msg
            state.is_grounded = True
            state.hallucination_action = "pass"
            await _clear_lead_state(state.session_id)
            if on_token:
                await on_token(complete_msg)

        state.total_latency_ms = int((time.time() - start) * 1000)
        return state

    if state.skip_retrieval:
        state = await generator.run(state, on_token=on_token)
        state.is_grounded = True
        state.hallucination_action = "pass"
        await _write_semantic_cache(state)
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


# Redis 实例由 api/app.py 的 _on_startup 通过 set_redis() 注入
_redis = None


def set_redis(redis) -> None:
    """由 app startup 调用，注入 Redis 实例到 engine 模块"""
    global _redis
    _redis = redis


async def _check_semantic_cache(state: RAGState) -> str | None:
    """检查语义缓存，命中返回答案，未命中返回 None"""
    if _redis is None:
        return None
    from cache.semantic import get as cache_get
    return await cache_get(_redis, state.bot_id, state.user_query)


async def _write_semantic_cache(state: RAGState) -> None:
    """写入语义缓存"""
    if _redis is None:
        return
    from cache.semantic import set as cache_set
    await cache_set(
        _redis, state.bot_id, state.user_query, state.generated_answer
    )


# ── Lead capture 多轮状态（Redis 键：lead_state:{session_id}）────────
_LEAD_STATE_PREFIX = "lead_state:"
_LEAD_STATE_TTL = 3600  # 1 小时未完成自动清除


async def _load_lead_state(session_id: str) -> dict:
    if _redis is None:
        return {}
    try:
        import json
        raw = await _redis.get(_LEAD_STATE_PREFIX + session_id)
        return json.loads(raw) if raw else {}
    except Exception as e:
        logger.warning(f"lead_state load error: {e}")
        return {}


async def _save_lead_state(session_id: str, lead_info: dict) -> None:
    if _redis is None:
        return
    try:
        import json
        persistable = {
            k: v for k, v in lead_info.items() if not k.startswith("_")
        }
        await _redis.setex(
            _LEAD_STATE_PREFIX + session_id,
            _LEAD_STATE_TTL,
            json.dumps(persistable, ensure_ascii=False),
        )
    except Exception as e:
        logger.warning(f"lead_state save error: {e}")


async def _clear_lead_state(session_id: str) -> None:
    if _redis is None:
        return
    try:
        await _redis.delete(_LEAD_STATE_PREFIX + session_id)
    except Exception as e:
        logger.warning(f"lead_state clear error: {e}")
