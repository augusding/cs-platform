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

    # 加载 Bot 配置的对话风格
    try:
        if db_pool:
            from store.base import fetch_one
            bot_row = await fetch_one(
                db_pool, "SELECT style FROM bots WHERE id = $1", bot_id
            )
            if bot_row and bot_row.get("style"):
                state.style = bot_row["style"]
    except Exception:
        pass

    # ── 中途 lead_capture 检测：有挂起的 lead 状态则跳过缓存 + Router ──
    pending_lead = await _load_lead_state(state.session_id)
    if pending_lead is not None:
        # 即使空 dict 也算续接（只要 session 存在 lead_state key）
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
            classify_user_reply,
            extract_info,
            get_next_missing_field,
            get_next_missing_required,
            can_skip_field,
            calculate_intent_score,
            prompt_for,
            build_lead_rag_system_prompt,
            DEFAULT_FIELDS,
            _MAX_ASK_SAME_FIELD,
        )

        lead_info = dict(state.lead_info or {})

        # ── 首次进入 lead_capture：仅预提取最可靠的字段 ──
        # 只预提取 product_requirement 和 quantity（这两个在"我想订购 X 台 Y"模式下高可靠）
        # target_price 和 contact 留给正常多轮流程（避免 LLM 把型号误当价格）
        if not state.lead_in_progress and len(user_query) > 6:
            for field_key in ("product_requirement", "quantity"):
                if not lead_info.get(field_key):
                    try:
                        extracted = await extract_info(
                            user_query, field_key, language
                        )
                        if extracted and extracted.strip() and len(extracted.strip()) > 1:
                            lead_info[field_key] = extracted
                            logger.debug(
                                f"[LeadCapture] Pre-extracted {field_key}: {extracted[:30]}"
                            )
                    except Exception as ex:
                        logger.warning(f"[LeadCapture] pre-extract failed: {ex}")

        state.lead_info = lead_info
        next_field = get_next_missing_field(lead_info)

        # ── 所有字段都收集完了 → 完成 ──
        if not next_field:
            state.lead_info["_score"] = calculate_intent_score(lead_info)
            state.lead_info["_complete"] = True
            complete_msg = (
                "感谢您提供的信息！我们已记录您的需求，业务人员将在 24 小时内与您联系。"
                if language == "zh"
                else "Thank you! Our team will contact you within 24 hours."
            )
            state.generated_answer = complete_msg
            state.is_grounded = True
            state.hallucination_action = "pass"
            await _clear_lead_state(state.session_id)
            if on_token:
                await on_token(complete_msg)
            state.total_latency_ms = int((time.time() - start) * 1000)
            ctx.exit_branch = "lead_capture_complete"
            asyncio.create_task(_persist_trace_safe(ctx, state))
            state.pipeline_trace = [s.to_dict() for s in ctx.spans]
            return state

        # ── 续接对话：分析用户回复类型 ──
        if state.lead_in_progress:
            classification = await classify_user_reply(
                user_query, next_field, lead_info, language
            )
            reply_type = classification.get("type", "answer")

            ask_count_key = f"_ask_count_{next_field['key']}"
            ask_count = lead_info.get(ask_count_key, 0)

            if reply_type == "answer":
                # ── 用户在回答收集问题 ──
                value = classification.get("extracted_value", "")
                if value and value.strip() and len(value.strip()) > 1:
                    lead_info[next_field["key"]] = value
                    lead_info.pop(ask_count_key, None)

                    state.lead_info = lead_info
                    next_field = get_next_missing_field(lead_info)

                    if not next_field:
                        state.lead_info["_score"] = calculate_intent_score(lead_info)
                        state.lead_info["_complete"] = True
                        complete_msg = (
                            "感谢您提供的信息！我们已记录您的需求，业务人员将在 24 小时内与您联系。"
                            if language == "zh"
                            else "Thank you! Our team will contact you within 24 hours."
                        )
                        state.generated_answer = complete_msg
                        state.is_grounded = True
                        state.hallucination_action = "pass"
                        await _clear_lead_state(state.session_id)
                        if on_token:
                            await on_token(complete_msg)
                        state.total_latency_ms = int((time.time() - start) * 1000)
                        ctx.exit_branch = "lead_capture_complete"
                        asyncio.create_task(_persist_trace_safe(ctx, state))
                        state.pipeline_trace = [s.to_dict() for s in ctx.spans]
                        return state

                    ack = f"好的，{next_field['label']}方面，" if language == "zh" else "Got it. "
                    prompt = ack + prompt_for(next_field, language)
                    state.generated_answer = prompt
                    state.is_grounded = True
                    state.hallucination_action = "pass"
                    await _save_lead_state(state.session_id, lead_info)
                    if on_token:
                        await on_token(prompt)
                else:
                    # 提取失败 → 限制重问次数
                    ask_count += 1
                    lead_info[ask_count_key] = ask_count

                    if ask_count >= _MAX_ASK_SAME_FIELD and can_skip_field(next_field):
                        lead_info[next_field["key"]] = "(未提供)"
                        lead_info.pop(ask_count_key, None)
                        state.lead_info = lead_info
                        next_field = get_next_missing_field(lead_info)
                        if next_field:
                            prompt = prompt_for(next_field, language)
                        else:
                            state.lead_info["_score"] = calculate_intent_score(lead_info)
                            state.lead_info["_complete"] = True
                            prompt = (
                                "感谢您提供的信息！我们已记录您的需求，业务人员将在 24 小时内与您联系。"
                                if language == "zh"
                                else "Thank you! Our team will contact you within 24 hours."
                            )
                            await _clear_lead_state(state.session_id)
                        state.generated_answer = prompt
                        state.is_grounded = True
                        state.hallucination_action = "pass"
                        await _save_lead_state(state.session_id, lead_info)
                        if on_token:
                            await on_token(prompt)
                    else:
                        retry_prompt = (
                            f"不好意思没听清，{prompt_for(next_field, language)}"
                            if language == "zh"
                            else f"Sorry I didn't quite catch that. {prompt_for(next_field, language)}"
                        )
                        state.generated_answer = retry_prompt
                        state.is_grounded = True
                        state.hallucination_action = "pass"
                        await _save_lead_state(state.session_id, lead_info)
                        if on_token:
                            await on_token(retry_prompt)

            elif reply_type in ("counter_question", "off_topic"):
                # ── 用户在反问/跑题 → 走 RAG 回答 + 末尾引导 ──
                logger.info(
                    f"[LeadCapture] User {reply_type}: '{user_query[:40]}', "
                    f"falling through to RAG with lead context"
                )

                bot_name = "智能客服助手"
                try:
                    from store.base import fetch_one
                    bot_row = await fetch_one(db_pool, "SELECT name FROM bots WHERE id = $1", bot_id)
                    if bot_row:
                        bot_name = bot_row["name"]
                except Exception:
                    pass

                lead_system = build_lead_rag_system_prompt(
                    lead_info, next_field, language, bot_name
                )

                state = await query_transform.run(state, ctx=ctx)
                state = await retriever.run(state, ctx=ctx)
                state = await grader.run(state, ctx=ctx)

                state = await generator.run(
                    state, on_token=on_token, ctx=ctx,
                    system_override=lead_system,
                )

                await _save_lead_state(state.session_id, lead_info)

                state.is_grounded = True
                state.hallucination_action = "pass"
                state.total_latency_ms = int((time.time() - start) * 1000)
                ctx.exit_branch = "lead_capture_rag"
                asyncio.create_task(_persist_trace_safe(ctx, state))
                state.pipeline_trace = [s.to_dict() for s in ctx.spans]
                return state

            elif reply_type == "refusal":
                # ── 用户拒绝 → 跳过非必填，必填换温和方式问 ──
                if can_skip_field(next_field):
                    lead_info[next_field["key"]] = "(客户选择不提供)"
                    state.lead_info = lead_info
                    next_field = get_next_missing_field(lead_info)
                    if next_field:
                        skip_msg = (
                            f"没问题，那关于{next_field['label']}，{prompt_for(next_field, language)}"
                            if language == "zh"
                            else f"No problem. Regarding {next_field['label']}, {prompt_for(next_field, language)}"
                        )
                    else:
                        state.lead_info["_score"] = calculate_intent_score(lead_info)
                        state.lead_info["_complete"] = True
                        skip_msg = (
                            "感谢您提供的信息！我们已记录您的需求，业务人员将在 24 小时内与您联系。"
                            if language == "zh"
                            else "Thank you! Our team will contact you within 24 hours."
                        )
                        await _clear_lead_state(state.session_id)
                else:
                    skip_msg = (
                        "理解，方便的话留个联系方式就行，邮箱或者 WhatsApp 都可以～"
                        "这样我们业务同事可以直接给您发正式报价。"
                        if language == "zh"
                        else "I understand. Just an email or WhatsApp would be great — "
                        "our team can send you a formal quote directly."
                    )
                state.generated_answer = skip_msg
                state.is_grounded = True
                state.hallucination_action = "pass"
                await _save_lead_state(state.session_id, lead_info)
                if on_token:
                    await on_token(skip_msg)

            elif reply_type == "frustration":
                # ── 用户不耐烦 → 道歉 + 简化到只问必填字段 ──
                remaining_required = get_next_missing_required(lead_info)
                if remaining_required and remaining_required["key"] == "contact":
                    frustration_msg = (
                        "抱歉问多了！最后一个问题——方便留个联系方式吗？邮箱或 WhatsApp 就行，"
                        "我们直接给您发报价，就不用再这样来回了。"
                        if language == "zh"
                        else "Sorry for all the questions! Just one more — could you share your email or WhatsApp? "
                        "We'll send you a formal quote directly."
                    )
                else:
                    for f in DEFAULT_FIELDS:
                        if not f.get("required") and not lead_info.get(f["key"]):
                            lead_info[f["key"]] = "(跳过)"
                    state.lead_info = lead_info
                    next_field = get_next_missing_field(lead_info)
                    if next_field:
                        frustration_msg = (
                            "抱歉给您造成了不好的体验！要不这样，方便留个联系方式吗？"
                            "我直接让业务同事联系您，一对一沟通更高效。"
                            if language == "zh"
                            else "Sorry about that! How about this — just leave your contact info "
                            "and our team will reach out directly."
                        )
                    else:
                        state.lead_info["_score"] = calculate_intent_score(lead_info)
                        state.lead_info["_complete"] = True
                        frustration_msg = (
                            "感谢您的耐心！我们已记录您的需求，业务人员将尽快联系您。"
                            if language == "zh"
                            else "Thanks for your patience! Our team will reach out soon."
                        )
                        await _clear_lead_state(state.session_id)

                state.generated_answer = frustration_msg
                state.is_grounded = True
                state.hallucination_action = "pass"
                await _save_lead_state(state.session_id, lead_info)
                if on_token:
                    await on_token(frustration_msg)

        else:
            # ── 首次进入 → 问第一个缺失字段 ──
            prompt = prompt_for(next_field, language)
            state.generated_answer = prompt
            state.is_grounded = True
            state.hallucination_action = "pass"
            await _save_lead_state(state.session_id, lead_info)
            if on_token:
                await on_token(prompt)

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

        style_hint_zh = {
            "humanized": "\n5. 用口语化的方式回答，像朋友聊天一样，不要太正式",
            "professional": "\n5. 保持简洁高效，直接给出关键信息",
        }.get(state.style, "")
        style_hint_en = {
            "humanized": "\n5. Respond casually like a real person chatting, not formal",
            "professional": "\n5. Be concise and give the key info directly",
        }.get(state.style, "")

        if state.language == "en":
            l1_system = (
                f"You are \"{bot_name}\", a professional AI customer service assistant.\n"
                "You can help with: product info, pricing, MOQ, delivery, payment, "
                "customization, shipping, after-sales.\n"
                "You can collect purchasing needs (product, quantity, budget, contact).\n"
                "Rules: respond naturally, be friendly and professional, keep it concise."
                + style_hint_en
            )
        else:
            l1_system = (
                f"你是「{bot_name}」，一个专业的AI智能客服助手。\n"
                "你的能力包括：产品咨询、报价、起订量、交货期、付款方式、定制服务、物流运输、售后政策等。\n"
                "你可以收集客户的采购需求（产品、数量、预算、联系方式）。\n"
                "回答规则：根据用户问题自然回答，保持友好专业，回答简洁。"
                + style_hint_zh
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

    # 负面情绪注入安抚指令
    if getattr(state, "_emotion_trend", "neutral") in ("negative", "escalating"):
        state._emotion_prompt = (
            "\n\n【重要】用户表达了不满或负面情绪，请先道歉并表示理解，"
            "然后尝试从新的角度理解用户需求。如果连续多轮无法满足，主动提出转接人工。"
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


async def _load_lead_state(session_id: str):
    """加载 lead_state；返回 None 表示无 session，dict（含空 dict）表示进行中"""
    if _redis is None:
        return None
    try:
        import json
        raw = await _redis.get(_LEAD_STATE_PREFIX + session_id)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"lead_state load error: {e}")
        return None


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
