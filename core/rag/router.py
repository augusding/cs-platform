"""
Router 节点：意图分类 + skip 判断。
写字段：intent, skip_retrieval
禁止：访问 Vector DB
"""
import logging

from openai import AsyncOpenAI

from config import settings
from core.rag.state import RAGState

logger = logging.getLogger(__name__)

_SYSTEM = """你是一个意图分类助手。将用户的问题分类为以下之一：
- knowledge_qa：询问产品/服务/政策等需要检索知识库的问题
- lead_capture：有明确采购/合作意向，需要收集联系方式
- out_of_scope：与业务无关的闲聊或越界请求
- transfer：明确要求转人工客服

只返回分类标签，不要解释。"""

_VALID_INTENTS = {"knowledge_qa", "lead_capture", "out_of_scope", "transfer"}
_SKIP_INTENTS = {"out_of_scope", "transfer"}

_SIMPLE_PATTERNS = [
    "你好", "您好", "hello", "hi", "谢谢", "thank", "再见", "bye",
]


def _is_simple(query: str) -> bool:
    q = query.lower().strip()
    return any(p in q for p in _SIMPLE_PATTERNS) and len(q) < 20


async def run(state: RAGState) -> RAGState:
    if _is_simple(state.user_query):
        state.intent = "knowledge_qa"
        state.skip_retrieval = True
        return state

    try:
        client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        resp = await client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": state.user_query},
            ],
            max_tokens=20,
            temperature=0,
        )
        intent = resp.choices[0].message.content.strip().lower()
        if intent not in _VALID_INTENTS:
            intent = "knowledge_qa"
    except Exception as e:
        logger.warning(f"Router LLM failed, defaulting to knowledge_qa: {e}")
        intent = "knowledge_qa"

    state.intent = intent
    state.skip_retrieval = intent in _SKIP_INTENTS
    return state
