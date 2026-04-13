"""
CSEngine：Agentic RAG Pipeline 编排器。
控制节点执行顺序和 re-retrieve 循环。
"""
import asyncio
import logging
import re
import time
import uuid

from config import settings
from core.rag.state import RAGState
from core.rag.intent import Intent
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
    db_pool=None,
    ctx=None,
) -> RAGState:
    """
    执行完整 RAG pipeline，返回最终 RAGState。
    on_token: 流式输出回调，每个 token 调用一次。
    db_pool:  asyncpg.Pool，注入后节点可直接查 DB（retriever FAQ 等）。
    ctx:      TraceContext，可观测性追踪上下文（None 时自动创建）
    """
    start = time.time()
    user_query = sanitize_input(user_query)

    from core.observability import TraceContext
    if ctx is None:
        ctx = TraceContext(
            bot_id=bot_id,
            tenant_id=tenant_id,
            session_id=session_id or "",
            user_query=user_query,
            language=language,
        )
    else:
        # 外部传入的 ctx 补齐字段（channel 由调用方设置）
        ctx.bot_id = bot_id
        ctx.tenant_id = tenant_id
        ctx.session_id = session_id or ""
        ctx.user_query = user_query
        ctx.language = language

    state = RAGState(
        session_id=session_id or str(uuid.uuid4()),
        bot_id=bot_id,
        tenant_id=tenant_id,
        user_query=user_query,
        language=language,
        history=history or [],
    )
    state.db_pool = db_pool

    # ── 中途 lead_capture 检测：有挂起的 lead 状态则跳过缓存 + Router ──
    pending_lead = await _load_lead_state(state.session_id)
    if pending_lead:
        state.intent = "lead_capture"
        state.lead_info = pending_lead
        state.lead_in_progress = True
    else:
        # ── 语义缓存检查 ─────────────────────────────────────
        async with ctx.span("cache_check") as _cs:
            cached = await _check_semantic_cache(state)
            _cs.attributes["hit"] = cached is not None
        if cached:
            state.generated_answer = cached
            state.is_grounded = True
            state.hallucination_action = "pass"
            state.cache_hit = True
            if on_token:
                await on_token(cached)
            state.total_latency_ms = int((time.time() - start) * 1000)
            ctx.exit_branch = "cache_hit"
            asyncio.create_task(_persist_trace_safe(ctx, state))
            state.pipeline_trace = [s.to_dict() for s in ctx.spans]
            return state

        # ── 1. Router ──────────────────────────────────────
        state = await router.run(state, ctx=ctx)
        logger.debug(f"[{state.session_id}] Router: intent={state.intent}")

    # ── 路由分支（基于 Intent 层级）───────────────────────
    if state.intent == Intent.OUT_OF_SCOPE:
        msg = _OUT_OF_SCOPE_ZH if language == "zh" else _OUT_OF_SCOPE_EN
        state.generated_answer = msg
        state.is_grounded = True
        state.hallucination_action = "pass"
        if on_token:
            await on_token(msg)
        state.total_latency_ms = int((time.time() - start) * 1000)
        ctx.exit_branch = "out_of_scope"
        asyncio.create_task(_persist_trace_safe(ctx, state))
        state.pipeline_trace = [s.to_dict() for s in ctx.spans]
        return state

    if state.intent == Intent.CLARIFICATION:
        msg = (
            "请您说得更具体一些，我好为您准确解答。"
            if language == "zh"
            else "Could you provide more details so I can help you better?"
        )
        state.generated_answer = msg
        state.is_grounded = True
        state.hallucination_action = "pass"
        if on_token:
            await on_token(msg)
        state.total_latency_ms = int((time.time() - start) * 1000)
        ctx.exit_branch = "clarification"
        asyncio.create_task(_persist_trace_safe(ctx, state))
        state.pipeline_trace = [s.to_dict() for s in ctx.spans]
        return state

    if state.should_transfer:
        state.generated_answer = (
            "我来帮您转接人工客服，请稍候。"
            if state.intent == Intent.TRANSFER_EXPLICIT
            else "我注意到您可能需要更专业的帮助，建议转接人工客服，是否需要？"
        ) if language == "zh" else (
            "Let me transfer you to a human agent. Please hold on."
            if state.intent == Intent.TRANSFER_EXPLICIT
            else "I think you might need more specialized help. Shall I transfer you?"
        )
        state.is_grounded = True
        state.hallucination_action = "pass"
        if on_token:
            await on_token(state.generated_answer)
        state.total_latency_ms = int((time.time() - start) * 1000)
        ctx.exit_branch = "transfer"
        asyncio.create_task(_persist_trace_safe(ctx, state))
        state.pipeline_trace = [s.to_dict() for s in ctx.spans]
        return state

    if state.intent in Intent.L3_LEAD or state.intent == "lead_capture":
        from core.rag.lead_collector import (
            extract_info,
            get_next_missing_field,
            calculate_intent_score,
            prompt_for,
        )

        lead_info = dict(state.lead_info or {})

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
        ctx.exit_branch = "lead_capture"
        asyncio.create_task(_persist_trace_safe(ctx, state))
        state.pipeline_trace = [s.to_dict() for s in ctx.spans]
        return state

    # ── L1 对话层：用专属 prompt（不走 RAG prompt，避免误转人工）──
    if state.intent in Intent.L1_NO_RETRIEVAL and state.skip_retrieval:
        bot_name = "智能客服助手"
        try:
            from store.base import fetch_one
            row = await fetch_one(db_pool, "SELECT name FROM bots WHERE id = $1", bot_id)
            if row:
                bot_name = row["name"]
        except Exception:
            pass

        if state.language == "en":
            l1_system = (
                f"You are \"{bot_name}\", a professional AI customer service assistant.\n"
                "You can help with: product info, pricing, MOQ, delivery, payment, "
                "customization, shipping, after-sales.\n"
                "You can collect purchasing needs (product, quantity, budget, contact).\n"
                "Rules: respond naturally, be friendly and professional, keep it concise."
            )
        else:
            l1_system = (
                f"你是「{bot_name}」，一个专业的AI智能客服助手。\n"
                "你的能力包括：产品咨询、报价、起订量、交货期、付款方式、定制服务、物流运输、售后政策等。\n"
                "你可以收集客户的采购需求（产品、数量、预算、联系方式）。\n"
                "回答规则：根据用户问题自然回答，保持友好专业，回答简洁。"
            )

        state = await generator.run(
            state, on_token=on_token, ctx=ctx, system_override=l1_system
        )
        state.is_grounded = True
        state.hallucination_action = "pass"
        await _write_semantic_cache(state)
        state.total_latency_ms = int((time.time() - start) * 1000)
        ctx.exit_branch = "l1_direct"
        asyncio.create_task(_persist_trace_safe(ctx, state))
        state.pipeline_trace = [s.to_dict() for s in ctx.spans]
        return state

    if state.skip_retrieval:
        state = await generator.run(state, on_token=on_token, ctx=ctx)
        state.is_grounded = True
        state.hallucination_action = "pass"
        await _write_semantic_cache(state)
        state.total_latency_ms = int((time.time() - start) * 1000)
        ctx.exit_branch = "skip_retrieval"
        asyncio.create_task(_persist_trace_safe(ctx, state))
        state.pipeline_trace = [s.to_dict() for s in ctx.spans]
        return state

    # 低置信度标记（中置信度区间回答末尾加确认语）
    add_confirmation = 0.60 <= state.intent_confidence < 0.75

    # ── 2-4. QueryTransform → Retriever → Grader（含 re-retrieve 循环）
    while True:
        state = await query_transform.run(state, ctx=ctx)
        state = await retriever.run(state, ctx=ctx)
        state = await grader.run(state, ctx=ctx)

        logger.debug(
            f"[{state.session_id}] Grader: score={state.grader_score:.3f} "
            f"attempts={state.attempts}"
        )

        if not grader.should_retry(state):
            break

        state.prev_grader_score = state.grader_score
        state.attempts += 1
        logger.info(
            f"[{state.session_id}] Re-retrieve #{state.attempts} "
            f"(score={state.grader_score:.3f})"
        )

    # ── 5. Generator（流式）─────────────────────────────
    state = await generator.run(state, on_token=on_token, ctx=ctx)

    # 低置信度确认语
    if add_confirmation and state.generated_answer:
        suffix = (
            "\n\n（如果理解有误，请告诉我更多细节）"
            if language == "zh"
            else "\n\n(If I misunderstood, please provide more details.)"
        )
        state.generated_answer += suffix
        if on_token:
            await on_token(suffix)

    # ── 6. HallucinationChecker（后台异步，不阻塞 done 帧）────
    # 乐观默认 pass，让用户立即收到回答
    state.hallucination_action = "pass"
    state.is_grounded = state.grader_score >= settings.GRADER_THRESHOLD

    checker_task = asyncio.create_task(hallucination_checker.run(state, ctx=ctx))

    async def _run_checker():
        try:
            checked = await asyncio.wait_for(checker_task, timeout=8.0)
            # Checker 结果写回 state（对本次 done 帧无影响，供 DB/日志参考）
            logger.debug(
                f"[{state.session_id}] Hallucination (async): "
                f"grounded={checked.is_grounded} action={checked.hallucination_action}"
            )
            if checked.hallucination_action != "pass":
                logger.warning(
                    f"[{state.session_id}] Hallucination check failed: "
                    f"action={checked.hallucination_action}"
                )
        except asyncio.TimeoutError:
            logger.warning(
                f"[{state.session_id}] HallucinationChecker timeout (8s)"
            )
        except Exception as e:
            logger.warning(
                f"[{state.session_id}] HallucinationChecker error: {e}"
            )

    asyncio.create_task(_run_checker())

    # ── 7. PostProcess 输出安全过滤 ──────────────────────
    if state.generated_answer:
        try:
            from core.rag.post_process import run as post_run
            async with ctx.span("post_process") as _pp:
                post_result = await post_run(state.generated_answer)
                state.generated_answer = post_result["text"]
                _pp.attributes["pii_detected"] = bool(post_result.get("pii_detected"))
            if post_result["pii_detected"]:
                logger.warning(
                    f"[{state.session_id}] PII in output: "
                    f"{[f['type'] for f in post_result['pii_detected']]}"
                )
        except Exception as pe:
            logger.warning(f"[{state.session_id}] PostProcess failed: {pe}")

    if state.is_grounded and state.hallucination_action == "pass":
        await _write_semantic_cache(state)

    state.total_latency_ms = int((time.time() - start) * 1000)
    logger.info(
        f"[{state.session_id}] Pipeline done: "
        f"{state.total_latency_ms}ms grader={state.grader_score:.2f} "
        f"cache_hit={state.cache_hit}"
    )
    ctx.exit_branch = ctx.exit_branch or "full_rag"
    asyncio.create_task(_persist_trace_safe(ctx, state))
    state.pipeline_trace = [s.to_dict() for s in ctx.spans]
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


async def _persist_trace_safe(ctx, state):
    """安全的异步 trace 持久化，不抛异常"""
    try:
        from core.observability import persist_trace
        await persist_trace(ctx, state)
    except Exception as e:
        logger.warning(f"trace persist failed: {e}")


async def _clear_lead_state(session_id: str) -> None:
    if _redis is None:
        return
    try:
        await _redis.delete(_LEAD_STATE_PREFIX + session_id)
    except Exception as e:
        logger.warning(f"lead_state clear error: {e}")
