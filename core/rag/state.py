"""
RAG Pipeline 唯一状态对象。
所有节点只能读写 RAGState，不得直接互相调用。
字段职责见 CLAUDE.md「节点职责边界」表格。
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class RAGState:
    # ─── 基础标识（所有节点只读）──────────────────────────
    session_id: str
    bot_id: str
    tenant_id: str          # 安全边界，所有节点必须携带

    # ─── 输入（只读）──────────────────────────────────────
    user_query: str
    language: str = "zh"    # "zh" | "en"
    history: list[dict] = field(default_factory=list)
    # [{"role": "user"|"assistant", "content": "..."}]

    # ─── Router 输出 ───────────────────────────────────────
    intent: str = ""
    # "knowledge_qa" | "lead_capture" | "out_of_scope" | "transfer"
    skip_retrieval: bool = False

    # ─── QueryTransform 输出 ───────────────────────────────
    transformed_query: str = ""
    sub_queries: list[str] = field(default_factory=list)
    transform_strategy: str = ""
    # "hyde" | "expansion" | "step_back" | "decompose"

    # ─── Retriever 输出 ────────────────────────────────────
    retrieved_chunks: list[dict] = field(default_factory=list)
    # [{"content": str, "score": float, "chunk_id": str, "source": str}]

    # ─── Grader 输出 ───────────────────────────────────────
    grader_score: float = 0.0    # 0.0 – 1.0
    attempts: int = 0            # re-retrieve 次数，最多 2

    # ─── Generator 输出 ────────────────────────────────────
    generated_answer: str = ""   # 流式更新时逐渐填充

    # ─── HallucinationChecker 输出 ─────────────────────────
    is_grounded: bool = False
    hallucination_action: str = ""
    # "pass" | "regenerate" | "clarify"

    # ─── 业务输出 ──────────────────────────────────────────
    lead_info: dict = field(default_factory=dict)
    # {"product_requirement": ..., "quantity": ..., "contact": ...}
    should_transfer: bool = False

    # ─── 调试信息（不影响主流程）──────────────────────────
    cache_hit: bool = False
    total_latency_ms: int = 0
    tokens_used: int = 0
