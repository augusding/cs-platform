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


def _extract_comparison_entities(query: str) -> list[str]:
    """
    从对比查询中提取两个实体名称（纯规则，不调 LLM）。
    "SP-100 和 SL-200 有什么区别" → ["SP-100", "SL-200"]
    "StarPods Pro和Lite哪个好" → ["StarPods Pro", "Lite"]
    """
    import re as _re

    # 模式 1：型号匹配（SP-100、SL-200、SW-500 等）
    models = _re.findall(r'[A-Z]{1,5}[\-]?\d{2,5}[A-Za-z]*', query)
    if len(models) >= 2:
        return [models[0], models[1]]

    # 模式 2：中文"和/与/跟/还是" 或英文 vs/compared to 分割
    parts = _re.split(
        r'[和与跟]|还是|vs\.?|versus|compared?\s+to',
        query,
        flags=_re.IGNORECASE,
    )
    if len(parts) >= 2:
        cleaned = []
        for p in parts:
            p = _re.sub(
                r'(有什么区别|哪个好|差异|不同|区别|对比|比较|what|difference|which|better).*$',
                '', p, flags=_re.IGNORECASE,
            ).strip()
            if p and len(p) >= 2:
                cleaned.append(p)
        if len(cleaned) >= 2:
            return cleaned[:2]

    return [query]


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

    # follow_up_rewrite 已在 Router 中用 LLM 改写过，直接使用
    if hint == "follow_up_rewrite":
        state.transformed_query = query
        state.transform_strategy = "follow_up_rewrite"
        logger.debug("QueryTransform [follow_up_rewrite]: using rewritten query")
        return state

    # 短查询首轮检索跳过 HyDE（节省 ~3s），直接用原始查询
    # re-retrieve 时仍走完整变换策略
    if len(query) <= 15 and state.attempts == 0 and hint not in ("expansion_hint", "decompose_hint"):
        state.transformed_query = query
        state.transform_strategy = "passthrough"
        logger.debug(f"QueryTransform [passthrough]: short query, skipped HyDE")
        return state

    try:
        if state.attempts > 0:
            # re-retrieve：升级到 Step-Back
            transformed = await _step_back(query, state.language)
            state.transform_strategy = "step_back"
        elif hint == "expansion_hint":
            transformed = await _expansion(query, state.language)
            state.transform_strategy = "expansion"
        elif hint == "decompose_hint" and state.intent == "comparison":
            # Comparison 快速路径：规则提取实体名，不调 LLM
            sub = _extract_comparison_entities(query)
            state.sub_queries = sub
            transformed = " ".join(sub)
            state.transform_strategy = "comparison_split"
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
