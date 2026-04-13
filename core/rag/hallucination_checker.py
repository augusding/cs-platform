"""
HallucinationChecker 节点：校验回答是否有依据。
写字段：is_grounded, hallucination_action
action: "pass" | "regenerate" | "clarify"
"""
import json
import logging

from openai import AsyncOpenAI

from config import settings
from core.rag.state import RAGState

logger = logging.getLogger(__name__)

_SYSTEM = """判断以下回答是否有依据于给定的参考资料。
只返回 JSON：{"grounded": true/false, "reason": "简短理由"}
不要输出其他内容。"""


async def run(state: RAGState, ctx=None) -> RAGState:
    import time as _time
    if ctx is None:
        from core.observability import NullTraceContext
        ctx = NullTraceContext()

    async with ctx.span("hallucination_checker") as _hs:
        if not state.retrieved_chunks:
            state.is_grounded = False
            state.hallucination_action = "clarify"
            _hs.attributes["action"] = state.hallucination_action
            _hs.attributes["is_grounded"] = state.is_grounded
            state.trace("hallucination_checker", {"action": state.hallucination_action, "is_grounded": state.is_grounded})
            return state

        fallback_phrases = ["转接人工", "human agent", "无法回答", "请稍后"]
        if any(p in state.generated_answer for p in fallback_phrases):
            state.is_grounded = True
            state.hallucination_action = "pass"
            _hs.attributes["action"] = state.hallucination_action
            _hs.attributes["is_grounded"] = state.is_grounded
            _hs.attributes["shortcircuit"] = "fallback_phrase"
            state.trace("hallucination_checker", {"action": state.hallucination_action, "is_grounded": state.is_grounded})
            return state

        context = "\n".join(
            c["content"][:500] for c in state.retrieved_chunks[:3]
        )
        prompt = (
            f"参考资料：\n{context}\n\n"
            f"回答：{state.generated_answer[:600]}"
        )

        _t0 = _time.time()
        try:
            client = AsyncOpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL,
            )
            resp = await client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=80,
                temperature=0,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.strip("`").lstrip("json").strip()
            result = json.loads(raw)
            grounded = bool(result.get("grounded", True))
            ctx.add_span(
                "llm_call", "llm_hallucination_check",
                duration_ms=int((_time.time() - _t0) * 1000),
                attributes={
                    "model": settings.QWEN_MODEL,
                    "tokens_out": len(raw) // 2,
                    "grounded": grounded,
                },
            )
        except Exception as e:
            logger.warning(
                f"HallucinationChecker failed, defaulting to pass: {e}"
            )
            grounded = True

        state.is_grounded = grounded
        state.hallucination_action = "pass" if grounded else "clarify"
        _hs.attributes["action"] = state.hallucination_action
        _hs.attributes["is_grounded"] = state.is_grounded
        state.trace("hallucination_checker", {"action": state.hallucination_action, "is_grounded": state.is_grounded})
        return state
