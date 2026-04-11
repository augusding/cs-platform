"""
QueryTransform 节点：按策略变换查询。
首次检索默认 HyDE；re-retrieve 时升级到 Step-Back。
写字段：transformed_query, transform_strategy
"""
import logging

from openai import AsyncOpenAI

from config import settings
from core.rag.state import RAGState

logger = logging.getLogger(__name__)


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.QWEN_API_KEY,
        base_url=settings.QWEN_BASE_URL,
    )


async def _hyde(query: str, language: str) -> str:
    """生成假设性回答文档，用于检索"""
    lang_hint = "用中文" if language == "zh" else "in English"
    prompt = (
        f"请{lang_hint}为以下问题生成一个简短的假设性答案（2-3句话），"
        f"不需要准确，只需要语义接近：\n{query}"
    )
    client = _get_client()
    resp = await client.chat.completions.create(
        model=settings.QWEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


async def _step_back(query: str, language: str) -> str:
    """将具体问题抽象化，粒度上升"""
    lang_hint = "用中文" if language == "zh" else "in English"
    prompt = (
        f"请{lang_hint}将以下具体问题改写为更宽泛的上层概念问题（一句话）：\n{query}"
    )
    client = _get_client()
    resp = await client.chat.completions.create(
        model=settings.QWEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
        temperature=0,
    )
    return resp.choices[0].message.content.strip()


async def _expansion(query: str) -> str:
    """扩展同义词和相关词"""
    prompt = (
        f"请将以下问题扩展，加入同义词和相关术语，"
        f"用空格分隔关键词（不要完整句子）：\n{query}"
    )
    client = _get_client()
    resp = await client.chat.completions.create(
        model=settings.QWEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
        temperature=0,
    )
    return resp.choices[0].message.content.strip()


async def run(state: RAGState) -> RAGState:
    query = state.user_query

    try:
        if state.attempts == 0:
            transformed = await _hyde(query, state.language)
            state.transform_strategy = "hyde"
        else:
            transformed = await _step_back(query, state.language)
            state.transform_strategy = "step_back"

        state.transformed_query = transformed
        logger.debug(
            f"QueryTransform [{state.transform_strategy}]: {transformed[:80]}"
        )
    except Exception as e:
        logger.warning(f"QueryTransform failed, using original query: {e}")
        state.transformed_query = query
        state.transform_strategy = "passthrough"

    return state
