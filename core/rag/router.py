"""
Router 节点：混合意图识别
Step1 规则预筛 → Step2 上下文增强 → Step3 LLM语义 → Step4 信号融合 → Step5 置信度决策
"""
import re
import json
import logging
from core.rag.state import RAGState
from core.rag.intent import Intent

logger = logging.getLogger(__name__)

# ── 规则信号词典 ──────────────────────────────────────────
RULE_SIGNALS: list[tuple[str, list[str], float]] = [
    # (intent, patterns, confidence)
    (Intent.TRANSFER_EXPLICIT,
     [r"(转人工|转客服|找真人|不要AI|转接客服|要人工客服|real human|live agent)",
      r"(?<!是)(?<!是不是)人工(?!还是|智能|的)"],
     0.98),
    (Intent.BOT_IDENTITY,
     [r"(是人工|是机器人|是AI|是真人|是不是人|你是谁|who are you|are you a bot|are you real|are you human)"],
     0.92),
    (Intent.GREETING,
     [r"^[\s\W]*(你好|hi|hello|早上好|下午好|晚上好|嗨|hey|哈喽|在吗)[\s\W]*$"],
     0.95),
    (Intent.FAREWELL,
     [r"^[\s\W]*(再见|拜拜|bye|goodbye|谢谢|感谢|没问题了|好的谢谢)[\s\W]*$"],
     0.90),
    (Intent.PRICE_INQUIRY,
     [r"(价格|报价|多少钱|费用|收费|折扣|优惠|怎么收费|price|discount|cost)"],
     0.88),
    (Intent.BULK_INQUIRY,
     [r"(批量|大量采购|MOQ|最小起订|代理商|经销商|wholesale|bulk order)"],
     0.88),
    (Intent.COMPLAINT,
     [r"(投诉|太差|垃圾|骗人|不满意|质量问题|要退款|太烂了|差评)"],
     0.85),
    (Intent.URGENT,
     [r"(紧急|urgent|ASAP|马上|立刻|很重要|等不了|火急)"],
     0.82),
    (Intent.CHITCHAT,
     [r"(讲个故事|讲个笑话|说个笑话|给我讲|天气怎么样|你喜欢|你觉得好玩|聊聊天)"],
     0.88),
    (Intent.PURCHASE_INTENT,
     # 只匹配明确的动词/意向表达，避免误伤"代理政策"这类询问
     [r"(想做|要做|申请做|成为|我们做)(代理|经销|分销)",
      r"(我们|我方|我司).{0,4}(代理|经销|分销)",
      r"(distribution|dealership|reseller)\s+(opportunity|application|inquiry)",
      r"become.*(?:distributor|dealer|reseller|agent)"],
     0.88),
    (Intent.ACKNOWLEDGMENT,
     [r"^[\s\W]*(好的|明白|收到|了解|知道了|OK|ok|嗯|好)[\s\W]*$"],
     0.90),
]


def _rule_match(query: str) -> tuple[str, float] | None:
    """规则预筛：返回 (intent, confidence) 或 None"""
    q = query.strip()
    for intent, patterns, conf in RULE_SIGNALS:
        for pat in patterns:
            if re.search(pat, q, re.IGNORECASE):
                logger.debug(f"[Router] Rule hit: {intent} conf={conf} pattern={pat}")
                return intent, conf
    return None


def _context_signals(state: RAGState) -> dict:
    """上下文信号分析"""
    signals = {
        "is_follow_up": False,
        "emotion_trend": "neutral",
        "in_lead_flow": False,
        "already_transferred": False,
    }

    if getattr(state, 'lead_in_progress', False):
        signals["in_lead_flow"] = True

    if not state.history:
        return signals

    query = state.user_query.strip()
    is_short = len(query) <= 10
    has_follow_marker = bool(re.search(
        r'^(那|还有|呢|也|另外|what about|how about|and |also )', query, re.IGNORECASE
    ))
    ends_with_ne = query.endswith('呢') or query.endswith('呢？')
    if (is_short or has_follow_marker or ends_with_ne) and state.history:
        signals["is_follow_up"] = True

    # 情绪升级检测：包括持续不满和单句直接否定
    ESCALATION_PATTERNS = [
        # 持续不满
        r'(说了好几遍|重复了好多次|一直没解决|还是不行|太差了|烂死了|垃圾系统|要投诉)',
        r'(帮不了|解决不了|AI没用|机器人没用|你没用)',
        # 单句直接否定
        r'(太傻|太蠢|太笨|太烂|太差|废物|智障|白痴|脑残)',
        r'(答非所问|文不对题|牛头不对马嘴|听不懂人话|不知所云)',
        r'(算了|不想聊了|没法沟通|聊不下去|浪费时间)',
        r'(stupid|useless|terrible|awful|worst|dumb|idiot)',
    ]
    recent = [m.get('content', '') for m in state.history[-4:]]
    escalation_count = sum(
        1 for msg in recent
        for pat in ESCALATION_PATTERNS
        if re.search(pat, msg)
    )
    if escalation_count >= 2:
        signals["emotion_trend"] = "escalating"
    elif escalation_count >= 1:
        signals["emotion_trend"] = "negative"

    return signals


async def _rewrite_follow_up(state: RAGState) -> str | None:
    """
    将追问改写为完整的独立查询。
    "那运动款呢" + 上文 "StarPods Pro 多少钱" → "StarPods Sport 运动款的价格是多少"
    """
    from config import settings

    recent = state.history[-4:]
    history_text = "\n".join(
        f"{'用户' if m['role'] == 'user' else 'AI'}: {m.get('content', '')[:100]}"
        for m in recent
    )

    prompt = f"""将用户的追问改写为一个完整的、独立的查询语句，使其不依赖上下文也能被理解。

对话历史：
{history_text}

用户追问：{state.user_query}

要求：
1. 只输出改写后的查询，不要解释
2. 保持用户原始语言（中文追问输出中文，英文追问输出英文）
3. 如果追问本身已经是完整查询，原样输出
4. 改写后的查询应该简洁（一句话）"""

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        resp = await client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0,
        )
        rewritten = resp.choices[0].message.content.strip()
        # 去掉可能的引号包裹（中英文）
        for q in ('"', "'", "\u201c", "\u201d", "\u2018", "\u2019"):
            rewritten = rewritten.strip(q)
        rewritten = rewritten.strip()
        if rewritten and len(rewritten) >= 2:
            logger.info(
                f"[Router] follow_up rewrite: '{state.user_query}' → '{rewritten}'"
            )
            return rewritten
    except Exception as e:
        logger.warning(f"[Router] follow_up rewrite failed: {e}")

    last_user = next(
        (m['content'] for m in reversed(state.history) if m['role'] == 'user'), ""
    )
    if last_user:
        return f"{last_user} {state.user_query}".strip()
    return None


_LLM_INTENT_LIST = """
greeting       - 问候、打招呼（你好/hi/早/晚上好）
farewell       - 道别、感谢结束（再见/谢谢/没问题了）
acknowledgment - 简短确认（好的/明白/收到/嗯）
bot_identity   - 询问AI身份（你是机器人吗/谁开发的）
capability     - 询问能力（你能做什么/你懂哪些）
chitchat       - 闲聊（天气/笑话/随便聊）
product_info   - 产品咨询（有什么产品/功能介绍/规格参数）
price_inquiry  - 价格询问（多少钱/报价/怎么收费）
availability   - 库存/发货（有没有货/几天发货/现货）
how_to_use     - 使用方法（怎么用/如何安装/使用步骤）
policy_query   - 政策咨询（退换货/保修/售后规定）
comparison     - 对比比较（A和B哪个好/区别/对比）
purchase_intent - 明确表达采购意向或合作意向动词，包括：想买/要下单/需要采购/want to order；想做代理/我们想做经销/成为代理/become a distributor。**仅询问"是否有代理政策"/"代理条件是什么"属于 policy_query 不属于 purchase_intent**，只有主动声明要合作才算
bulk_inquiry   - 明确表达批量采购意向（我要批量采购/想大量订购/need to order in bulk）。仅询问MOQ或批量价格属于 price_inquiry 而非 bulk_inquiry
custom_request - 明确表达定制需求并有合作意向（我需要定制/要OEM合作）。仅询问是否支持定制属于 product_info 而非 custom_request
complaint      - 投诉不满（太差/质量问题/投诉/不满意）
urgent         - 紧急需求（紧急/马上/ASAP/等不了）
transfer_explicit - 明确要求人工（要人工/转客服/找真人）
transfer_implicit - 隐式转接（AI解决不了/说了好几遍/越来越不满）
clarification  - 问题太模糊需要反问（指代不清/无法理解）
follow_up      - 追问上文（那价格呢/还有吗/继续）
multi_intent   - 一句话包含多个【不同主题】的独立问题（如"价格多少钱、能定制吗"涉及价格+定制两个主题）。同一主题的补充细节（如"多少钱？批量价呢？"都是问价格）不算 multi_intent，应归为主要意图
out_of_scope   - 完全无关（写代码/天气预报/股票/算命）
"""


async def _llm_classify(state: RAGState, context: dict, ctx=None) -> tuple[str, float, str]:
    """LLM 语义分类，返回 (intent, confidence, reason)"""
    import time as _time
    from config import settings

    history_text = ""
    if state.history:
        recent = state.history[-3:]
        history_text = "\n".join(
            f"{'用户' if m['role']=='user' else 'AI'}: {m.get('content','')[:80]}"
            for m in recent
        )

    context_note = ""
    if context["is_follow_up"]:
        context_note += "注意：这条消息很短，可能是追问上文。"
    if context["emotion_trend"] == "escalating":
        context_note += "注意：用户情绪在升级，可能需要转人工。"
    if context["in_lead_flow"]:
        context_note += "注意：当前在询盘收集流程中。"

    prompt = f"""你是一个客服意图分类器。将用户消息分类为以下意图之一：

{_LLM_INTENT_LIST}

{f"对话历史：{chr(10)}{history_text}" if history_text else ""}
{f"上下文提示：{context_note}" if context_note else ""}

用户消息：{state.user_query}

要求：
1. 输出 JSON 格式，包含 intent/confidence/reason 三个字段
2. confidence 为 0-1 的浮点数
3. reason 简短说明分类依据（中文，20字以内）
4. 只有包含不同主题的独立问题时才填 multi_intent。同一主题的追问补充（如"多少钱？批量呢？"都是价格）应归为主要意图（如 price_inquiry），不填 multi_intent
5. 只输出 JSON，不要其他内容

示例输出：
{{"intent": "greeting", "confidence": 0.95, "reason": "用户说晚上好是典型问候语"}}
{{"intent": "price_inquiry", "confidence": 0.88, "reason": "询问多少钱"}}
{{"intent": "multi_intent", "confidence": 0.90, "reason": "包含价格和库存两个问题", "sub_intents": ["price_inquiry", "availability"]}}
"""

    _t0 = _time.time()
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        resp = await client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        if ctx:
            ctx.add_span(
                "llm_call", "llm_router_classify",
                duration_ms=int((_time.time() - _t0) * 1000),
                attributes={
                    "model": settings.QWEN_MODEL,
                    "tokens_out": len(raw) // 2,
                },
            )
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        intent = data.get("intent", Intent.PRODUCT_INFO)
        confidence = float(data.get("confidence", 0.7))
        reason = data.get("reason", "")
        return intent, confidence, reason
    except Exception as e:
        logger.warning(f"[Router] LLM classify failed: {e}")
        return Intent.PRODUCT_INFO, 0.5, "LLM失败，fallback"


async def run(state: RAGState, ctx=None) -> RAGState:
    """Router 主函数：混合识别 → 写入 state"""
    if ctx is None:
        from core.observability import NullTraceContext
        ctx = NullTraceContext()

    async with ctx.span("router") as _rs:
        result = await _run_inner(state, ctx)
        _rs.attributes["intent"] = state.intent
        _rs.attributes["confidence"] = state.intent_confidence
        _rs.attributes["skip_retrieval"] = state.skip_retrieval
        _rs.attributes["should_transfer"] = state.should_transfer
        return result


async def _run_inner(state: RAGState, ctx) -> RAGState:
    # Step 1: 规则预筛
    rule_result = _rule_match(state.user_query)
    rule_intent, rule_conf = rule_result if rule_result else (None, 0.0)

    # Step 2: 上下文信号
    context = _context_signals(state)
    state._emotion_trend = context.get("emotion_trend", "neutral")

    # 上下文快速路径
    if context["in_lead_flow"]:
        state.intent = "lead_capture"
        state.intent_confidence = 0.98
        state.skip_retrieval = True
        state.trace("router", {"intent": state.intent, "confidence": 0.98, "source": "context_lead"})
        return state

    if context["emotion_trend"] == "escalating":
        state.intent = Intent.TRANSFER_IMPLICIT
        state.intent_confidence = 0.85
        state.should_transfer = True
        state.skip_retrieval = True
        state.trace("router", {"intent": state.intent, "confidence": 0.85, "source": "context_emotion"})
        return state

    # 追问：LLM 改写为完整独立查询
    if context["is_follow_up"] and state.history:
        rewritten = await _rewrite_follow_up(state)
        if rewritten:
            state.user_query = rewritten
            state.transform_strategy = "follow_up_rewrite"

    # 规则高置信度短路：跳过 LLM 调用，节省 ~2s
    if rule_intent and rule_conf >= 0.92:
        state.intent = rule_intent
        state.intent_confidence = round(rule_conf, 3)
        state.intent_reason = f"规则直接命中 ({rule_conf})"
        state.skip_retrieval = rule_intent in Intent.L1_NO_RETRIEVAL or rule_intent in {
            Intent.TRANSFER_EXPLICIT, Intent.TRANSFER_IMPLICIT, Intent.CLARIFICATION,
        }
        state.should_transfer = rule_intent in {Intent.TRANSFER_EXPLICIT, Intent.TRANSFER_IMPLICIT}

        if rule_intent in {Intent.PRICE_INQUIRY, Intent.AVAILABILITY}:
            state.transform_strategy = "expansion_hint"
        elif rule_intent == Intent.COMPARISON:
            state.transform_strategy = "decompose_hint"

        logger.info(
            f"[Router] SHORTCIRCUIT intent={rule_intent} conf={rule_conf:.2f} "
            f"source=rule_shortcircuit"
        )
        state.trace("router", {
            "intent": rule_intent, "confidence": rule_conf,
            "source": "rule_shortcircuit", "skip_retrieval": state.skip_retrieval,
        })
        return state

    # Step 3: LLM 分类
    llm_intent, llm_conf, llm_reason = await _llm_classify(state, context, ctx=ctx)

    # Step 4: 信号融合
    if rule_intent and rule_intent == llm_intent:
        final_conf = max(rule_conf, llm_conf)
        final_intent = rule_intent
        source = "rule+llm_agree"
    elif rule_intent and rule_conf >= 0.90:
        final_conf = rule_conf * 0.4 + llm_conf * 0.6
        final_intent = rule_intent
        source = "rule_dominant"
    else:
        final_conf = llm_conf
        final_intent = llm_intent
        source = "llm_dominant"

    # Step 5: 置信度决策
    if final_conf < 0.40:
        final_intent = Intent.CLARIFICATION
        source += "_fallback_clarification"
    elif final_conf < 0.60:
        final_intent = Intent.PRODUCT_INFO
        source += "_fallback_rag"

    # 写入 state
    state.intent = final_intent
    state.intent_confidence = round(final_conf, 3)
    state.intent_reason = llm_reason

    state.skip_retrieval = final_intent in Intent.L1_NO_RETRIEVAL or final_intent in {
        Intent.TRANSFER_EXPLICIT, Intent.TRANSFER_IMPLICIT, Intent.CLARIFICATION,
        Intent.PURCHASE_INTENT, Intent.BULK_INQUIRY, Intent.CUSTOM_REQUEST,
    }
    state.should_transfer = final_intent in {Intent.TRANSFER_EXPLICIT, Intent.TRANSFER_IMPLICIT}

    # transform_strategy hint
    if final_intent in {Intent.PRICE_INQUIRY, Intent.AVAILABILITY}:
        state.transform_strategy = "expansion_hint"
    elif final_intent == Intent.COMPARISON:
        state.transform_strategy = "decompose_hint"
    elif state.transform_strategy != "follow_up":
        state.transform_strategy = ""

    logger.info(
        f"[Router] intent={final_intent} conf={final_conf:.2f} "
        f"source={source} reason={llm_reason}"
    )
    state.trace("router", {
        "intent": final_intent,
        "confidence": final_conf,
        "source": source,
        "reason": llm_reason,
        "skip_retrieval": state.skip_retrieval,
    })
    return state
