"""
Generator 节点：基于检索结果生成回答（流式）。
写字段：generated_answer
支持流式回调 on_token(token: str)
"""
import logging

from openai import AsyncOpenAI

from config import settings
from core.rag.state import RAGState

logger = logging.getLogger(__name__)

_ZH_SYSTEM = """你是一个专业的智能客服助手。请根据以下参考资料回答用户问题。
规则：
1. 只基于参考资料回答，不要编造信息
2. 如果参考资料不足以回答，直接说"这个问题我需要为您转接人工确认"
3. 回答简洁专业，中文回答
4. 不要提及"参考资料"这个词"""

_EN_SYSTEM = """You are a professional customer service assistant. Answer based on the provided reference materials.
Rules:
1. Only answer based on the reference materials, do not fabricate information
2. If materials are insufficient, say "I need to transfer you to a human agent for this question"
3. Keep answers concise and professional
4. Do not mention "reference materials" in your answer"""


def _build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "（无相关资料）"
    parts = []
    for i, chunk in enumerate(chunks[:5], 1):
        parts.append(f"[{i}] {chunk['content']}")
    return "\n\n".join(parts)


def _get_client(use_fallback: bool = False) -> AsyncOpenAI:
    if use_fallback and settings.DEEPSEEK_API_KEY:
        return AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
    return AsyncOpenAI(
        api_key=settings.QWEN_API_KEY,
        base_url=settings.QWEN_BASE_URL,
    )


async def run(state: RAGState, on_token=None) -> RAGState:
    system = _ZH_SYSTEM if state.language == "zh" else _EN_SYSTEM
    context = _build_context(state.retrieved_chunks)

    messages = [
        {"role": "system", "content": system},
        *state.history[-6:],
        {
            "role": "user",
            "content": f"参考资料：\n{context}\n\n用户问题：{state.user_query}",
        },
    ]

    answer_parts: list[str] = []
    use_fallback = False

    for attempt in range(2):
        try:
            client = _get_client(use_fallback=use_fallback)
            model = (
                settings.DEEPSEEK_MODEL if use_fallback else settings.QWEN_MODEL
            )
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.1,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    answer_parts.append(delta)
                    state.generated_answer = "".join(answer_parts)
                    if on_token:
                        await on_token(delta)
            break
        except Exception as e:
            if (
                attempt == 0
                and settings.LLM_FALLBACK_ENABLED
                and settings.DEEPSEEK_API_KEY
            ):
                logger.warning(
                    f"Primary LLM failed, switching to fallback: {e}"
                )
                use_fallback = True
                answer_parts = []
                state.generated_answer = ""
            else:
                logger.error(f"Generator failed: {e}")
                state.generated_answer = (
                    "抱歉，服务暂时不可用，请稍后重试。"
                    if state.language == "zh"
                    else "Sorry, service is temporarily unavailable."
                )
                if on_token:
                    await on_token(state.generated_answer)
                break

    return state
