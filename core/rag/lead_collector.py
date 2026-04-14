"""
Lead Capture 节点：柔性多轮收集询盘信息。
支持中途反问（走 RAG 回答）、跑题（回答后拉回）、拒绝（跳过非必填字段）。
默认收集字段：product_requirement → quantity → target_price → contact
"""
import json
import logging

from openai import AsyncOpenAI

from config import settings

logger = logging.getLogger(__name__)

DEFAULT_FIELDS = [
    {
        "key": "product_requirement",
        "label": "产品需求",
        "required": False,
        "prompt_zh": "请问您需要什么产品或有什么具体要求？",
        "prompt_en": "What product or specific requirements do you have?",
    },
    {
        "key": "quantity",
        "label": "采购数量",
        "required": False,
        "prompt_zh": "请问大概的采购数量是多少？",
        "prompt_en": "What is your approximate order quantity?",
    },
    {
        "key": "target_price",
        "label": "目标价格",
        "required": False,
        "prompt_zh": "请问您的目标价格或预算是多少？",
        "prompt_en": "What is your target price or budget?",
    },
    {
        "key": "contact",
        "label": "联系方式",
        "required": True,
        "prompt_zh": "方便留个邮箱或 WhatsApp 吗？我们安排业务同事给您发正式报价。",
        "prompt_en": "Could you share your email or WhatsApp? We'll have our sales team send you a formal quote.",
    },
]

# 连续问同一字段的最大次数（超过则跳过）
_MAX_ASK_SAME_FIELD = 2


async def classify_user_reply(
    user_reply: str, current_field: dict, lead_info: dict, language: str
) -> dict:
    """
    判断用户回复的类型。返回：
    {
        "type": "answer" | "counter_question" | "off_topic" | "refusal" | "frustration",
        "extracted_value": str | None,
        "user_question": str | None,
    }
    """
    collected_summary = ", ".join(
        f"{k}={v}" for k, v in lead_info.items()
        if not k.startswith("_") and v
    )

    prompt = f"""你是一个对话分析器。当前正在收集客户的采购信息。

已收集信息：{collected_summary or "暂无"}
当前正在询问：{current_field['label']}（{current_field['key']}）
上一条 AI 消息问的是：{current_field['prompt_zh'] if language == 'zh' else current_field['prompt_en']}

客户回复：{user_reply}

请判断客户回复属于哪种类型，返回 JSON（不要输出其他内容）：

1. 如果客户在回答当前问题（给出了{current_field['label']}的信息）：
   {{"type": "answer", "extracted_value": "提取的值"}}

2. 如果客户在反问/要求 AI 先报价/先提供信息：
   {{"type": "counter_question", "user_question": "客户的问题"}}

3. 如果客户在聊别的话题（和采购无关）：
   {{"type": "off_topic", "user_question": "客户的问题"}}

4. 如果客户拒绝回答（"不方便说"、"不告诉你"、"跳过"、"还没定"）：
   {{"type": "refusal"}}

5. 如果客户表达不满/烦躁（"问这么多干嘛"、"烦"、"算了"）：
   {{"type": "frustration"}}"""

    try:
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
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
        result = json.loads(raw)
        logger.debug(f"[LeadCollector] classify: {result.get('type')} for '{user_reply[:30]}'")
        return result
    except Exception as e:
        logger.warning(f"[LeadCollector] classify failed: {e}")
        return {"type": "answer", "extracted_value": user_reply.strip()[:200]}


async def extract_info(user_reply: str, field_key: str, language: str) -> str:
    """从用户回复中提取对应字段的值。返回空字符串表示提取失败。"""
    prompt = (
        f"从以下用户回复中提取「{field_key}」字段的值。"
        f"严格要求：只有当用户明确提到了该字段的具体值时才提取，"
        f"不要推测或猜测。如果用户没有明确提到则返回空字符串。"
        f"只返回提取的值本身，不要解释。\n用户回复：{user_reply}"
    )
    try:
        client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        resp = await client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0,
        )
        val = resp.choices[0].message.content.strip()
        if not val or val in ("", "无", "null", "None", "无法提取", "N/A"):
            return ""
        return val
    except Exception as e:
        logger.warning(f"LeadCollector extract failed: {e}")
        return ""


def get_next_missing_field(lead_info: dict) -> dict | None:
    """返回下一个未收集的字段定义，全部完成返回 None"""
    for field in DEFAULT_FIELDS:
        if not lead_info.get(field["key"]):
            return field
    return None


def get_next_missing_required(lead_info: dict) -> dict | None:
    """返回下一个未收集的必填字段"""
    for field in DEFAULT_FIELDS:
        if field.get("required") and not lead_info.get(field["key"]):
            return field
    return None


def can_skip_field(field: dict) -> bool:
    """非必填字段可以跳过"""
    return not field.get("required", False)


def calculate_intent_score(lead_info: dict) -> float:
    """根据收集完整度计算意向分（0.0-1.0）"""
    filled = sum(
        1 for f in DEFAULT_FIELDS if lead_info.get(f["key"])
    )
    return round(filled / len(DEFAULT_FIELDS), 2)


def prompt_for(field: dict, language: str) -> str:
    return field["prompt_en"] if language == "en" else field["prompt_zh"]


def build_lead_rag_system_prompt(
    lead_info: dict, next_field: dict, language: str, bot_name: str = ""
) -> str:
    """
    为 Lead Capture 中的 RAG 回答构建 system prompt。
    让 AI 先回答用户的反问，然后自然引导到下一个待收集字段。
    """
    name = bot_name or "智能客服助手"

    collected_parts = []
    for f in DEFAULT_FIELDS:
        val = lead_info.get(f["key"])
        if val:
            collected_parts.append(f"{f['label']}: {val}")
    collected_text = "、".join(collected_parts) if collected_parts else "暂无"

    if language == "zh":
        return f"""你是「{name}」，正在和客户进行采购咨询对话。

已收集的客户信息：{collected_text}
接下来需要了解的：{next_field['label']}

你的任务：
1. 先回答客户当前提出的问题（基于参考资料，不要编造）
2. 回答完之后，在末尾自然地引导客户提供「{next_field['label']}」
   - 不要生硬地问"请问您的xx是多少"
   - 要结合上下文自然过渡，比如：
     报完价后说"这个价位您觉得合适吗？"
     介绍完产品后说"您大概需要多少台呀？"
     回答完交期后说"方便留个联系方式吗？我让同事发正式报价给您"
3. 回答简洁（2-4句话），不要写长段落
4. 严禁编造参考资料中没有的信息（价格、政策、承诺）"""
    else:
        return f"""You are "{name}", in a purchasing inquiry conversation.

Collected info: {collected_text}
Next to collect: {next_field['label']}

Your task:
1. Answer the customer's current question first (based on reference materials, never fabricate)
2. After answering, naturally guide toward collecting "{next_field['label']}"
   - Don't ask rigidly "what is your xx"
   - Transition naturally, e.g.:
     After quoting price: "Does this price range work for you?"
     After product info: "How many units are you thinking?"
     After delivery info: "Could you share your email? We'll send a formal quote."
3. Keep it brief (2-4 sentences)
4. NEVER fabricate info not in reference materials"""
