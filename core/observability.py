"""
可观测性核心模块：TraceContext + Span。
每个请求创建一个 TraceContext，贯穿整个 Pipeline 生命周期。
节点通过 async with ctx.span("node_name") as s: 自动记录时间和异常。
"""
import json
import time
import uuid
import logging
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Span:
    """单个执行节点的记录"""
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: Optional[str] = None
    node: str = ""
    operation: str = ""
    start_ms: int = 0
    end_ms: int = 0
    duration_ms: int = 0
    status: str = "ok"
    error_msg: str = ""
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "node": self.node,
            "operation": self.operation,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_msg": self.error_msg,
            "attributes": self.attributes,
        }


@dataclass
class TraceContext:
    """一次请求的完整追踪上下文"""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    bot_id: str = ""
    tenant_id: str = ""
    channel: str = ""
    user_query: str = ""
    language: str = "zh"
    exit_branch: str = ""

    spans: list = field(default_factory=list)
    _span_stack: list = field(default_factory=list)
    _start_time: float = field(default_factory=time.time)

    @asynccontextmanager
    async def span(self, node: str, operation: str = ""):
        """上下文管理器，自动记录节点的开始/结束时间和异常"""
        s = Span(
            node=node,
            operation=operation or node,
            start_ms=int(time.time() * 1000),
            parent_span_id=(
                self._span_stack[-1].span_id if self._span_stack else None
            ),
        )
        self._span_stack.append(s)
        try:
            yield s
        except Exception as e:
            s.status = "error"
            s.error_msg = str(e)[:500]
            raise
        finally:
            s.end_ms = int(time.time() * 1000)
            s.duration_ms = s.end_ms - s.start_ms
            self._span_stack.pop()
            self.spans.append(s)
            logger.info(
                f"[{self.trace_id[:8]}] {node}",
                extra={
                    "trace_id": self.trace_id,
                    "event": "span",
                    "node": node,
                    "operation": s.operation,
                    "duration_ms": s.duration_ms,
                    "status": s.status,
                    **{k: v for k, v in s.attributes.items()
                       if isinstance(v, (str, int, float, bool))},
                },
            )

    def add_span(self, node: str, operation: str = "",
                 start_ms: int = 0, duration_ms: int = 0,
                 attributes: dict = None):
        """手动添加一个已完成的 span（用于 LLM 调用等无法用 async with 的场景）"""
        now = int(time.time() * 1000)
        s = Span(
            node=node,
            operation=operation or node,
            start_ms=start_ms or (now - duration_ms),
            end_ms=now,
            duration_ms=duration_ms,
            parent_span_id=(
                self._span_stack[-1].span_id if self._span_stack else None
            ),
            attributes=attributes or {},
        )
        self.spans.append(s)

    @property
    def total_latency_ms(self) -> int:
        return int((time.time() - self._start_time) * 1000)

    @property
    def llm_calls(self) -> list:
        return [s for s in self.spans if s.node == "llm_call"]

    @property
    def llm_total_tokens(self) -> int:
        return sum(
            s.attributes.get("tokens_in", 0) + s.attributes.get("tokens_out", 0)
            for s in self.llm_calls
        )

    def to_debug_dict(self) -> dict:
        """返回给前端 debug 面板的精简数据"""
        return {
            "trace_id": self.trace_id,
            "total_latency_ms": self.total_latency_ms,
            "exit_branch": self.exit_branch,
            "llm_calls_count": len(self.llm_calls),
            "llm_total_tokens": self.llm_total_tokens,
            "spans": [s.to_dict() for s in self.spans],
        }


class _NullSpan:
    """ctx=None 时的空 span（no-op），仍可写 attributes 但不持久化"""
    def __init__(self):
        self.attributes = {}
        self.span_id = ""
        self.status = "ok"
        self.error_msg = ""


class NullTraceContext:
    """ctx 未传入时的占位 context，所有操作 no-op，保持节点代码简洁"""
    trace_id = ""
    session_id = ""
    bot_id = ""
    tenant_id = ""
    exit_branch = ""
    spans: list = []

    @asynccontextmanager
    async def span(self, node: str, operation: str = ""):
        yield _NullSpan()

    def add_span(self, *args, **kwargs):
        pass

    @property
    def total_latency_ms(self) -> int:
        return 0


# ── 持久化 ─────────────────────────────────────────────────

_db_pool = None


def set_db_pool(pool):
    global _db_pool
    _db_pool = pool


async def persist_trace(ctx: TraceContext, state) -> None:
    """异步将 trace + spans 写入 PostgreSQL。不阻塞主流程。"""
    if not _db_pool:
        return
    if isinstance(ctx, NullTraceContext):
        return
    try:
        await _db_pool.execute("""
            INSERT INTO traces (
                trace_id, session_id, bot_id, tenant_id,
                channel, user_query, language,
                intent, intent_confidence, transform_strategy,
                grader_score, attempts, is_grounded, hallucination_action,
                cache_hit, should_transfer,
                total_latency_ms, llm_calls_count, llm_total_tokens,
                retrieval_chunks, answer_preview, exit_branch
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,
                $11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22
            )
        """,
            ctx.trace_id,
            ctx.session_id,
            ctx.bot_id,
            ctx.tenant_id,
            ctx.channel or "widget",
            (ctx.user_query or "")[:500],
            ctx.language or "zh",
            state.intent,
            float(state.intent_confidence) if state.intent_confidence else None,
            state.transform_strategy,
            float(state.grader_score) if state.grader_score else None,
            int(state.attempts),
            bool(state.is_grounded),
            state.hallucination_action,
            bool(state.cache_hit),
            bool(state.should_transfer),
            int(ctx.total_latency_ms),
            len(ctx.llm_calls),
            int(ctx.llm_total_tokens),
            len(state.retrieved_chunks),
            (state.generated_answer or "")[:200],
            ctx.exit_branch,
        )

        for s in ctx.spans:
            await _db_pool.execute("""
                INSERT INTO spans (
                    trace_id, parent_span_id, node, operation,
                    start_ms, end_ms, duration_ms,
                    status, error_msg, attributes
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            """,
                ctx.trace_id,
                s.parent_span_id,
                s.node,
                s.operation,
                int(s.start_ms),
                int(s.end_ms),
                int(s.duration_ms),
                s.status,
                s.error_msg or "",
                json.dumps(s.attributes, ensure_ascii=False, default=str),
            )
    except Exception as e:
        logger.warning(f"trace persist error: {e}")
