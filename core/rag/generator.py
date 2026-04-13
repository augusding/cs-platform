"""
Generator 节点：基于检索结果生成回答（流式）。
写字段：generated_answer
支持流式回调 on_token(token: str)
"""
import logging
import time

from openai import AsyncOpenAI

from config import settings
from core.rag.state import RAGState

logger = logging.getLogger(__name__)

_STYLE_INSTRUCTIONS = {
    "zh": {
        "professional": """回答风格：
- 信息完整准确，可以使用列表格式
- 语气简洁专业，不使用语气词
- 直接给出客户需要的全部信息，减少来回沟通""",
        "friendly": """回答风格：
- 信息完整准确，可以适当使用列表
- 语气友好热情，可以用"您好"、"呢"、"哦"等语气词
- 回答末尾可以加一句关心或引导（如"还有什么我可以帮您的吗？"）""",
        "humanized": """回答风格——请严格遵守：
- 像一个真实的客服在微信上和客户聊天，不像产品说明书
- 禁止使用列表格式（-、*、1.2.3.），所有信息用自然的口语句子表达
- 一次只重点回答客户问的问题，不要主动补充客户没问的信息
- 回答控制在 2-4 句话，不要写长段落
- 末尾自然地抛出一个问题引导客户继续对话（如"您大概要多少台？"、"对哪款感兴趣呀？"）
- 适当使用口语词："的话"、"大概"、"挺不错的"、"没问题"、"这款"
- 可以用"哈"、"呢"、"呀"等语气助词，但不要过度""",
    },
    "en": {
        "professional": """Response style:
- Complete and accurate info, use bullet points if helpful
- Concise and business-like tone
- Provide all needed info upfront to minimize back-and-forth""",
        "friendly": """Response style:
- Complete and accurate info, lists are OK
- Warm and approachable tone
- End with a helpful follow-up like "Is there anything else I can help with?" """,
        "humanized": """Response style \u2014 follow strictly:
- Write like a real customer service agent chatting, not a product manual
- Do NOT use bullet points, numbered lists, or markdown formatting
- Answer only what was asked, don't volunteer extra info the customer didn't ask for
- Keep responses to 2-4 sentences max
- End with a natural question to keep the conversation going ("How many units are you looking for?", "Which model interests you?")
- Use casual connectors: "basically", "around", "pretty good", "sure thing"
- Be warm but not over-the-top""",
    },
}

_ZH_BASE = """你是一个专业的智能客服助手。请根据以下参考资料回答用户问题。

基本规则：
1. 优先基于参考资料回答，确保信息准确
2. 如果参考资料中有部分相关信息，尽量基于已有信息回答
3. 只有在参考资料完全无关且无法提供任何有用信息时，才说"抱歉，这个问题我暂时无法解答，建议联系我们的客服团队"
4. 不要提及"参考资料"这个词

绝对禁止（违反会被视为严重错误）：
- 严禁编造参考资料中不存在的信息，包括但不限于：价格承诺、代理政策、独家协议、区域保护、交货承诺、返点方案
- 如果客户问到参考资料中没有的话题（如代理政策、售后赔偿方案、独家合作），必须明确说"这个问题我需要和业务团队确认后回复您，方便留个联系方式吗？"
- 宁可说"我帮您确认一下"，也绝对不要编造回答

上下文规则：
- 仔细阅读对话历史。如果你上一条消息中向用户提出了选择题或问题，用户的简短回复就是在回答你的问题，不要把它当成新话题
- 例如：你问"分销还是贴牌？"，用户说"贴牌"，你应该基于"用户选择了贴牌合作模式"来继续对话，而不是去检索"贴牌"这个词
- 当用户的回复和你之前的问题明显相关时，优先从对话上下文理解意图

去重规则：
- 如果你发现自己即将给出和上一条回复几乎相同的内容，停下来重新理解用户意图
- 如果连续两轮回答内容相似，说明你可能误解了用户，此时应该换一种方式理解，或者直接问"抱歉，我可能没理解准确，您具体是想了解什么呢？"

{style_instructions}"""

_EN_BASE = """You are a professional customer service assistant. Answer based on the provided reference materials.

Base rules:
1. Prioritize answering based on reference materials to ensure accuracy
2. If materials contain partially relevant info, answer based on what's available
3. Only say "I'm sorry, I don't have enough info for this" when materials are completely irrelevant
4. Do not mention "reference materials" in your answer

Absolute rules (violations are serious errors):
- NEVER fabricate information not in the reference materials, including pricing commitments, agency policies, exclusive agreements, territory protection, delivery promises, commission schemes
- If the customer asks about topics not covered (agency policies, compensation, exclusive cooperation), say "Let me check with our team and get back to you. Could you leave your contact info?"
- It's always better to say "let me confirm" than to make something up

Context rules:
- Read the conversation history carefully. If your last message asked a question or offered choices, the user's short reply is answering YOUR question -- do not treat it as a new independent query
- Example: you asked "distribution or OEM?" and user says "OEM" -- continue based on "user chose OEM", don't search for "OEM" as a new topic
- When the user's reply clearly relates to your previous question, prioritize understanding from conversation context

Anti-repetition rules:
- If you realize you're about to give nearly the same answer as last time, stop and reconsider the user's intent
- If two consecutive replies are similar, you may have misunderstood. Try a different angle, or ask "Sorry, I may have misunderstood. What specifically would you like to know?"

{style_instructions}"""


def _build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "（无相关资料）"
    parts = []
    for i, chunk in enumerate(chunks[:5], 1):
        parts.append(f"[{i}] {chunk['content']}")
    return "\n\n".join(parts)


_ASSISTANT_MAX_LEN = 150


def _trim_history(history: list[dict]) -> list[dict]:
    """
    智能截断对话历史：
    - user 消息：保留全文
    - assistant 消息：截断到 150 字符，但最后一条保留到 300（含追问尾段）
    """
    trimmed = []
    last_idx = len(history) - 1
    for i, msg in enumerate(history):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            max_len = 300 if i == last_idx else _ASSISTANT_MAX_LEN
            if len(content) > max_len:
                content = content[:max_len].rstrip() + "…"
            trimmed.append({"role": "assistant", "content": content})
        else:
            trimmed.append(msg)
    return trimmed


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


async def run(state: RAGState, on_token=None, ctx=None, system_override: str = "") -> RAGState:
    if ctx is None:
        from core.observability import NullTraceContext
        ctx = NullTraceContext()

    if system_override:
        system = system_override
    else:
        lang = "zh" if state.language == "zh" else "en"
        style = getattr(state, "style", "friendly")
        style_instr = _STYLE_INSTRUCTIONS[lang].get(
            style, _STYLE_INSTRUCTIONS[lang]["friendly"]
        )
        base = _ZH_BASE if lang == "zh" else _EN_BASE
        system = base.format(style_instructions=style_instr)
    context = _build_context(state.retrieved_chunks)

    # 对 history 做智能截断：assistant 消息截断到 150 字，user 消息保留全文
    trimmed_history = _trim_history(state.history[-6:])

    # L1 等无检索场景：不带"参考资料"前缀，避免 LLM 误以为有上下文要遵守
    if system_override and not state.retrieved_chunks:
        user_msg = state.user_query
    else:
        user_msg = f"参考资料：\n{context}\n\n用户问题：{state.user_query}"

    # 情绪升级场景：追加安抚指令
    emotion_hint = getattr(state, "_emotion_prompt", "")
    if emotion_hint:
        user_msg = user_msg + emotion_hint

    messages = [
        {"role": "system", "content": system},
        *trimmed_history,
        {
            "role": "user",
            "content": user_msg,
        },
    ]

    answer_parts: list[str] = []
    use_fallback = False
    _gen_start = time.time()
    model = settings.QWEN_MODEL

    for attempt in range(2):
        try:
            client = _get_client(use_fallback=use_fallback)
            model = (
                settings.DEEPSEEK_MODEL if use_fallback else settings.QWEN_MODEL
            )
            _call_start = time.time()
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
            ctx.add_span(
                "llm_call", "llm_generate",
                start_ms=int(_call_start * 1000),
                duration_ms=int((time.time() - _call_start) * 1000),
                attributes={
                    "model": model,
                    "provider": "deepseek" if use_fallback else "qwen",
                    "stream": True,
                    "tokens_out": len(state.generated_answer) // 2,
                    "fallback_used": use_fallback,
                    "answer_len": len(state.generated_answer),
                },
            )
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

    ctx.add_span("generator", attributes={
        "answer_len": len(state.generated_answer),
        "fallback_used": use_fallback,
        "duration_ms": int((time.time() - _gen_start) * 1000),
    })
    return state
