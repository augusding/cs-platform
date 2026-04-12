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
     [r"(人工|转客服|找真人|不要AI|转接客服|real human|live agent)"],
     0.98),
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

    if len(state.user_query.strip()) <= 6 and '?' not in state.user_query:
        signals["is_follow_up"] = True

    # 更严格的情绪升级检测：需要明确的负面表达
    ESCALATION_PATTERNS = [
        r'(说了好几遍|重复了好多次|一直没解决|还是不行|太差了|烂死了|垃圾系统|要投诉)',
        r'(帮不了|解决不了|AI没用|机器人没用|你没用)',
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
purchase_intent - 购买意向（想买/要下单/有采购需求）
bulk_inquiry   - 批量采购（批量/大量/代理商/MOQ）
custom_request - 定制需求（定制/OEM/改色/打logo）
complaint      - 投诉不满（太差/质量问题/投诉/不满意）
urgent         - 紧急需求（紧急/马上/ASAP/等不了）
transfer_explicit - 明确要求人工（要人工/转客服/找真人）
transfer_implicit - 隐式转接（AI解决不了/说了好几遍/越来越不满）
clarification  - 问题太模糊需要反问（指代不清/无法理解）
follow_up      - 追问上文（那价格呢/还有吗/继续）
multi_intent   - 一句话多个问题（价格多少，能定制吗，几天发货）
out_of_scope   - 完全无关（写代码/天气预报/股票/算命）
"""


async def _llm_classify(state: RAGState, context: dict) -> tuple[str, float, str]:
    """LLM 语义分类，返回 (intent, confidence, reason)"""
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
4. 如果包含多个独立问题，intent 填 multi_intent，sub_intents 填子意图列表
5. 只输出 JSON，不要其他内容

示例输出：
{{"intent": "greeting", "confidence": 0.95, "reason": "用户说晚上好是典型问候语"}}
{{"intent": "price_inquiry", "confidence": 0.88, "reason": "询问多少钱"}}
{{"intent": "multi_intent", "confidence": 0.90, "reason": "包含价格和库存两个问题", "sub_intents": ["price_inquiry", "availability"]}}
"""

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


async def run(state: RAGState) -> RAGState:
    """Router 主函数：混合识别 → 写入 state"""

    # Step 1: 规则预筛
    rule_result = _rule_match(state.user_query)
    rule_intent, rule_conf = rule_result if rule_result else (None, 0.0)

    # Step 2: 上下文信号
    context = _context_signals(state)

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

    # 追问：注入上文
    if context["is_follow_up"] and state.history:
        last_user = next((m['content'] for m in reversed(state.history) if m['role'] == 'user'), "")
        if last_user:
            state.user_query = f"{last_user} {state.user_query}".strip()
            state.transform_strategy = "follow_up"

    # Step 3: LLM 分类
    llm_intent, llm_conf, llm_reason = await _llm_classify(state, context)

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
