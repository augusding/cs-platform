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


async def _expansion(query: str, language: str) -> str:
    """扩展同义词 / 行业术语 / 相关词"""
    lang_hint = "中文" if language == "zh" else "English"
    prompt = (
        f"将以下查询扩展为包含同义词和相关术语的搜索词组，{lang_hint}，"
        f"词之间用空格分隔，不要写成句子：\n{query}"
    )
    client = _get_client()
    resp = await client.chat.completions.create(
        model=settings.QWEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0,
    )
    return resp.choices[0].message.content.strip()


async def _decompose(query: str, language: str) -> list[str]:
    """将复杂多跳问题拆成 2-3 个子查询"""
    lang_hint = "中文" if language == "zh" else "in English"
    prompt = (
        f"将以下复杂问题拆分为 2-3 个独立的简单子问题，{lang_hint}，"
        f"每行一个子问题，不要编号：\n{query}"
    )
    client = _get_client()
    try:
        resp = await client.chat.completions.create(
            model=settings.QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0,
        )
        lines = [
            line.strip()
            for line in resp.choices[0].message.content.strip().split("\n")
            if line.strip()
        ]
        return lines[:3] if lines else [query]
    except Exception as e:
        logger.warning(f"Decompose failed: {e}")
        return [query]


async def run(state: RAGState, ctx=None) -> RAGState:
    if ctx is None:
        from core.observability import NullTraceContext
        ctx = NullTraceContext()

    async with ctx.span("query_transform") as _qs:
        result = await _run_inner(state)
        _qs.attributes["strategy"] = state.transform_strategy
        _qs.attributes["original"] = state.user_query[:80]
        _qs.attributes["transformed"] = state.transformed_query[:80]
        return result


async def _run_inner(state: RAGState) -> RAGState:
    query = state.user_query
    hint = state.transform_strategy  # Router 写入的策略提示

    try:
        if state.attempts > 0:
            # re-retrieve：升级到 Step-Back
            transformed = await _step_back(query, state.language)
            state.transform_strategy = "step_back"
        elif hint == "expansion_hint":
            transformed = await _expansion(query, state.language)
            state.transform_strategy = "expansion"
        elif hint == "decompose_hint":
            sub_queries = await _decompose(query, state.language)
            state.sub_queries = sub_queries
            transformed = " ".join(sub_queries)
            state.transform_strategy = "decompose"
        else:
            transformed = await _hyde(query, state.language)
            state.transform_strategy = "hyde"

        state.transformed_query = transformed
        logger.debug(
            f"QueryTransform [{state.transform_strategy}]: {transformed[:80]}"
        )
    except Exception as e:
        logger.warning(f"QueryTransform failed, using original query: {e}")
        state.transformed_query = query
        state.transform_strategy = "passthrough"

    state.trace("query_transform", {
        "original": state.user_query[:80],
        "transformed": state.transformed_query[:80],
        "strategy": state.transform_strategy,
    })
    return state
