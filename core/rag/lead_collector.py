"""
Lead Capture 节点：多轮收集询盘信息。
当 Router 判断 intent=lead_capture 时，进入多轮收集模式。
默认收集字段（可由 Bot 配置覆盖）：
  product_requirement → quantity → target_price → contact
"""
import logging

from openai import AsyncOpenAI

from config import settings

logger = logging.getLogger(__name__)

DEFAULT_FIELDS = [
    {
        "key": "product_requirement",
        "label": "产品需求",
        "prompt_zh": "请问您需要什么产品或有什么具体要求？",
        "prompt_en": "What product or specific requirements do you have?",
    },
    {
        "key": "quantity",
        "label": "采购数量",
        "prompt_zh": "请问大概的采购数量是多少？",
        "prompt_en": "What is your approximate order quantity?",
    },
    {
        "key": "target_price",
        "label": "目标价格",
        "prompt_zh": "请问您的目标价格或预算是多少？",
        "prompt_en": "What is your target price or budget?",
    },
    {
        "key": "contact",
        "label": "联系方式",
        "prompt_zh": "请留下您的邮箱或联系方式，我们会尽快与您联系。",
        "prompt_en": "Please leave your email or contact information.",
    },
]


async def extract_info(user_reply: str, field_key: str, language: str) -> str:
    """从用户回复中提取对应字段的值；失败时返回原文截断。"""
    prompt = (
        f"从以下用户回复中提取「{field_key}」字段的值，只返回提取的值本身，"
        f"不要解释。如果用户回复中没有相关信息则返回空字符串：\n{user_reply}"
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
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"LeadCollector extract failed: {e}")
        return user_reply.strip()[:200]


def get_next_missing_field(lead_info: dict) -> dict | None:
    """返回下一个未收集的字段定义（按 DEFAULT_FIELDS 顺序），全部完成返回 None"""
    for field in DEFAULT_FIELDS:
        if not lead_info.get(field["key"]):
            return field
    return None


def calculate_intent_score(lead_info: dict) -> float:
    """根据收集完整度计算意向分（0.0-1.0）"""
    filled = sum(
        1 for f in DEFAULT_FIELDS if lead_info.get(f["key"])
    )
    return round(filled / len(DEFAULT_FIELDS), 2)


def prompt_for(field: dict, language: str) -> str:
    return field["prompt_en"] if language == "en" else field["prompt_zh"]
