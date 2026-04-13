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

        fallback_phrases = ["转接人工", "human agent", "无法回答", "请稍后", "确认后回复", "业务团队"]
        if any(p in state.generated_answer for p in fallback_phrases):
            state.is_grounded = True
            state.hallucination_action = "pass"
            _hs.attributes["action"] = state.hallucination_action
            _hs.attributes["is_grounded"] = state.is_grounded
            _hs.attributes["shortcircuit"] = "fallback_phrase"
            state.trace("hallucination_checker", {"action": state.hallucination_action, "is_grounded": state.is_grounded})
            return state

        # ── 承诺性表述检测：回答含强承诺但 chunks 里没有对应内容 ──
        import re as _re
        PROMISE_PATTERNS = [
            r'(独家|唯一|只授权|专属|exclusive)',
            r'(保证|承诺|guaranteed|promise)',
            r'(签.{0,4}协议|签.{0,4}合同|sign.{0,4}agreement|sign.{0,4}contract)',
            r'(区域保护|territory protection)',
            r'(赔偿|补偿|compensat)',
            r'(返点|rebate|commission)',
        ]
        context_text = " ".join(c.get("content", "") for c in state.retrieved_chunks[:5])
        answer_text = state.generated_answer
        for pat in PROMISE_PATTERNS:
            if _re.search(pat, answer_text, _re.IGNORECASE) and not _re.search(pat, context_text, _re.IGNORECASE):
                logger.warning(
                    f"[HallucinationChecker] Promise pattern detected: {pat} "
                    f"in answer but not in chunks"
                )
                state.is_grounded = False
                state.hallucination_action = "clarify"
                _hs.attributes["action"] = "clarify"
                _hs.attributes["is_grounded"] = False
                _hs.attributes["reason"] = f"promise_pattern: {pat}"
                state.trace("hallucination_checker", {
                    "action": "clarify", "is_grounded": False,
                    "reason": f"promise_pattern_detected: {pat}",
                })
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
