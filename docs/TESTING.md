# 测试规范

> 不跑测试就不算完成。每次修改后必须执行对应的验证命令。

---

## 测试分层与触发时机

| 层次 | 文件 | 触发时机 | 耗时 |
|------|------|---------|------|
| 语法检查 | 无测试文件，命令行验证 | 每次修改 .py | < 1s |
| 单元测试 | `tests/test_*.py` | 每次 commit 前 | ~30s |
| 租户隔离 | `tests/test_tenant_isolation.py` | 任何涉及数据访问的改动 | ~30s |
| Golden Set 回归 | `tests/test_golden_set.py` | 每次 RAG 核心改动 + 上线前 | ~5min |
| 压测 | `tests/locustfile.py` | Phase 3 + 每次大版本上线前 | ~10min |

---

## 运行命令

```powershell
# 语法验证
python -c "import ast; ast.parse(open('path/to/file.py').read()); print('OK')"

# 认证测试
python tests/test_auth.py

# RAG 核心测试
python tests/test_rag.py

# 租户隔离测试（必须）
python tests/test_tenant_isolation.py

# 知识库摄取测试
python tests/test_knowledge.py

# Golden Set 回归
python tests/test_golden_set.py

# 前端类型检查
cd frontend && npx tsc --noEmit

# 压测（Phase 3 上线前）
locust -f tests/locustfile.py --headless -u 100 -r 10 --run-time 5m
```

---

## 单元测试规范

### LLM Mock 策略

**核心原则**：测试不得依赖真实 LLM API（慢、贵、不确定）。

```python
# tests/mocks/llm.py
from unittest.mock import AsyncMock, patch

MOCK_RESPONSES = {
    "router_knowledge_qa": {
        "intent": "knowledge_qa",
        "skip_retrieval": False
    },
    "router_out_of_scope": {
        "intent": "out_of_scope",
        "skip_retrieval": True
    },
    "generator_product_price": {
        "content": "我们的产品价格从100元起，具体取决于规格和数量。",
        "is_stream": True
    },
    "hallucination_pass": {
        "is_grounded": True,
        "action": "pass"
    },
    "hallucination_fail": {
        "is_grounded": False,
        "action": "clarify"
    }
}

def mock_llm_call(response_key: str):
    """返回指定 mock 响应的装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with patch("core.rag.llm_client.call") as mock:
                mock.return_value = MOCK_RESPONSES[response_key]
                return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Milvus Mock 策略

```python
# tests/mocks/milvus.py

MOCK_CHUNKS = {
    "product_price": [
        {"content": "产品价格从100元起，具体价格依规格不同", "score": 0.92, "chunk_id": "c001"},
        {"content": "批量采购可享受9折优惠", "score": 0.88, "chunk_id": "c002"},
    ],
    "empty": []
}

def mock_milvus_search(chunks_key: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with patch("knowledge.vector_store.VectorStore.search") as mock:
                mock.return_value = MOCK_CHUNKS[chunks_key]
                return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 测试用例结构

```python
# tests/test_rag.py

import asyncio
import pytest
from core.rag.state import RAGState
from core.rag.router import Router
from core.rag.grader import Grader
from tests.mocks.llm import mock_llm_call
from tests.mocks.milvus import mock_milvus_search

class TestRouter:
    @mock_llm_call("router_knowledge_qa")
    async def test_knowledge_qa_intent(self):
        state = make_test_state("你们产品的价格是多少")
        result = await Router().run(state)
        assert result.intent == "knowledge_qa"
        assert result.skip_retrieval == False

    @mock_llm_call("router_out_of_scope")
    async def test_out_of_scope(self):
        state = make_test_state("帮我写一首诗")
        result = await Router().run(state)
        assert result.intent == "out_of_scope"

class TestGrader:
    async def test_low_score_triggers_retry(self):
        state = make_test_state("产品规格")
        state.retrieved_chunks = [{"content": "完全无关内容", "score": 0.3}]
        result = await Grader().run(state)
        assert result.grader_score < 0.6
        # re-retrieve 由 Pipeline 控制，Grader 只负责打分

class TestRAGPipeline:
    @mock_llm_call("router_knowledge_qa")
    @mock_milvus_search("product_price")
    @mock_llm_call("generator_product_price")
    @mock_llm_call("hallucination_pass")
    async def test_happy_path(self):
        """正常路径：问知识库内的问题，返回有依据的答案"""
        result = await run_rag_pipeline(
            query="产品价格是多少",
            bot_id=TEST_BOT_ID,
            tenant_id=TEST_TENANT_ID
        )
        assert result.is_grounded == True
        assert len(result.generated_answer) > 0

    @mock_milvus_search("empty")
    async def test_no_hit_triggers_clarify(self):
        """检索为空时，应触发 clarify"""
        result = await run_rag_pipeline(
            query="完全不在知识库里的问题",
            bot_id=TEST_BOT_ID,
            tenant_id=TEST_TENANT_ID
        )
        assert result.hallucination_action == "clarify"

def make_test_state(query: str) -> RAGState:
    return RAGState(
        session_id="test_session",
        bot_id=TEST_BOT_ID,
        tenant_id=TEST_TENANT_ID,
        user_query=query,
        language="zh",
        history=[],
        intent="",
        skip_retrieval=False,
        transformed_query=query,
        sub_queries=[],
        transform_strategy="",
        retrieved_chunks=[],
        grader_score=0.0,
        attempts=0,
        generated_answer="",
        is_grounded=False,
        hallucination_action="",
        lead_info={},
        should_transfer=False,
    )
```

---

## 租户隔离测试规范

**这是最重要的安全测试，每次改动数据访问层后必须运行。**

```python
# tests/test_tenant_isolation.py

# 测试前准备：创建两个独立的测试租户
# TENANT_A: 有 Bot A，知识库 A，会话 A
# TENANT_B: 有 Bot B，知识库 B，会话 B

class TestTenantIsolation:

    async def test_cannot_access_other_tenant_bot(self):
        """用户 A 无法访问租户 B 的 Bot"""
        response = await client.get(
            f"/api/bots/{TENANT_B_BOT_ID}",
            headers={"Authorization": f"Bearer {TENANT_A_TOKEN}"}
        )
        assert response.status == 403

    async def test_cannot_list_other_tenant_bots(self):
        """用户 A 的 Bot 列表中不包含租户 B 的 Bot"""
        response = await client.get(
            "/api/bots",
            headers={"Authorization": f"Bearer {TENANT_A_TOKEN}"}
        )
        bots = response.json()["data"]
        bot_ids = [b["id"] for b in bots]
        assert TENANT_B_BOT_ID not in bot_ids

    async def test_cannot_delete_other_tenant_bot(self):
        """用户 A 无法删除租户 B 的 Bot"""
        response = await client.delete(
            f"/api/bots/{TENANT_B_BOT_ID}",
            headers={"Authorization": f"Bearer {TENANT_A_TOKEN}"}
        )
        assert response.status == 403
        # 验证 Bot B 仍然存在
        assert await bot_store.exists(TENANT_B_BOT_ID)

    async def test_cannot_access_other_tenant_sessions(self):
        """用户 A 无法访问租户 B 的会话记录"""
        response = await client.get(
            "/api/sessions",
            headers={"Authorization": f"Bearer {TENANT_A_TOKEN}"}
        )
        sessions = response.json()["data"]
        session_ids = [s["id"] for s in sessions]
        assert TENANT_B_SESSION_ID not in session_ids

    async def test_bot_api_key_isolation(self):
        """租户 A 的 Bot API Key 不能触发租户 B 的知识库检索"""
        # 用 TENANT_A 的 bot_api_key 连接到 TENANT_B 的 bot_id
        # 应该返回 401 或 403
        response = await ws_client.connect(
            f"/api/chat/{TENANT_B_BOT_ID}?key={TENANT_A_BOT_API_KEY}"
        )
        assert response.status in [401, 403]

    async def test_forged_tenant_id_rejected(self):
        """伪造 tenant_id 的请求被服务端忽略（使用 JWT 中的 tenant_id）"""
        # 即使请求 body 中包含 tenant_id，服务端应忽略并使用 JWT 中的
        response = await client.post(
            "/api/bots",
            json={"name": "Hacker Bot", "tenant_id": TENANT_B_ID},  # 伪造
            headers={"Authorization": f"Bearer {TENANT_A_TOKEN}"}
        )
        # Bot 应被创建，但 tenant_id 是 TENANT_A，不是 TENANT_B
        if response.status == 201:
            bot = response.json()["data"]
            assert bot["tenant_id"] == TENANT_A_ID
            assert bot["tenant_id"] != TENANT_B_ID
```

---

## Golden Set 规范

### cases.json 格式

```json
[
  {
    "id": "gs_001",
    "category": "faq",
    "language": "zh",
    "query": "你们的最小起订量是多少",
    "expected_contains": ["MOQ", "起订量", "最小"],
    "expected_not_contains": ["不知道", "无法回答"],
    "expected_grounded": true,
    "expected_no_transfer": true,
    "baseline_score": 0.85,
    "notes": "核心外贸FAQ，必须答对"
  },
  {
    "id": "gs_002",
    "category": "out_of_scope",
    "language": "zh",
    "query": "帮我写一首诗",
    "expected_contains": ["无法", "专注于", "客服"],
    "expected_grounded": true,
    "baseline_score": 0.90,
    "notes": "越界请求，必须礼貌拒绝"
  },
  {
    "id": "gs_003",
    "category": "faq",
    "language": "en",
    "query": "What is your minimum order quantity?",
    "expected_contains": ["MOQ", "minimum order"],
    "expected_grounded": true,
    "baseline_score": 0.80,
    "notes": "英文外贸场景"
  }
]
```

### 评分逻辑

```python
# tests/test_golden_set.py

def score_case(result: RAGState, case: dict) -> float:
    score = 0.0

    # 1. grounding 检查（40%权重）
    if result.is_grounded == case.get("expected_grounded", True):
        score += 0.4

    # 2. 内容包含检查（40%权重）
    answer = result.generated_answer.lower()
    contains_all = all(
        keyword.lower() in answer
        for keyword in case.get("expected_contains", [])
    )
    if contains_all:
        score += 0.4

    # 3. 内容排除检查（20%权重）
    contains_bad = any(
        bad.lower() in answer
        for bad in case.get("expected_not_contains", [])
    )
    if not contains_bad:
        score += 0.2

    return score

# 通过条件：score >= case["baseline_score"]
# 全部通过才允许部署
```

---

## 测试数据管理

### 测试租户（不得修改生产数据）

```python
# tests/fixtures.py

TEST_TENANT_A = {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "测试企业A",
    "plan": "pro"
}

TEST_BOT_A = {
    "id": "00000000-0000-0000-0000-000000000011",
    "tenant_id": TEST_TENANT_A["id"],
    "name": "测试Bot A"
}

# Golden Set 专用 Bot（有预加载的产品知识库）
GOLDEN_SET_BOT_ID = "00000000-0000-0000-0000-000000000099"
```

### 测试数据清理

```python
# 每次测试套件结束后清理
@pytest.fixture(autouse=True, scope="session")
async def cleanup():
    yield
    await db.execute("DELETE FROM tenants WHERE id LIKE '00000000-0000%'")
    # Milvus collections 自动清理（按 bot_id）
```

---

## 测试覆盖率目标

| 模块 | 目标覆盖率 | 关键 |
|------|-----------|------|
| `auth/` | 90%+ | 是 |
| `core/rag/` | 80%+ | 是 |
| `store/` | 85%+ | 是（含隔离测试） |
| `cache/` | 70%+ | 否 |
| `queue/tasks/` | 60%+ | 否 |
| `api/routes/` | 75%+ | 是 |

```powershell
# 查看覆盖率报告
pip install pytest-cov
python -m pytest tests/ --cov=. --cov-report=html
# 报告生成在 htmlcov/index.html
```
