# 开发计划 — CS Platform

> 版本 v1.0 · 总周期 7 周 + 预备期 2 天

---

## 整体原则

- **先跑通主链路，再叠加差异化功能**
- **每周有且仅有一个可演示的交付物**
- **租户隔离从第一行代码开始，不补救**
- **不在没有真实用户数据前优化数据飞轮**

---

## 预备期（Day 0-1，2天）

**目标**：项目骨架跑起来，所有协作工具到位。

### 任务清单

```powershell
# 1. 初始化仓库
git init cs-platform
cd cs-platform
git remote add origin <your-repo-url>

# 2. 创建目录结构
# 见 CLAUDE.md 目录结构，手动或脚本创建所有目录和空的 __init__.py

# 3. 配置 Docker Compose（PostgreSQL + Redis + Milvus）
# 复制 docker-compose.yml 模板，配置端口和凭据

# 4. 创建 .env.example
# 复制并填写 .env，不提交 .env 到 git

# 5. 初始化 Alembic
alembic init migrations

# 6. 安装 Python 依赖
pip install aiohttp asyncpg aioredis pymilvus rq alembic python-jose bcrypt

# 7. 初始化前端
cd frontend && npm create vite@latest . -- --template react-ts
npm install && npm install -D tailwindcss

# 8. 启动基础服务验证
docker-compose up -d
# 确认 PostgreSQL:5432 / Redis:6379 / Milvus:19530 均可连通
```

### 验收标准

- [ ] `docker-compose up -d` 无报错
- [ ] `python -c "import asyncpg, aioredis, pymilvus, rq"` 无 ImportError
- [ ] `cd frontend && npm run dev` 可访问 localhost:3001
- [ ] CLAUDE.md 已复制到项目根目录，docs/ 目录已创建

### 不做

- 不写任何业务逻辑
- 不配置 CI/CD（Phase 3 再做）

---

## Phase 1：核心链路跑通（第1-3周）

---

### 第1周：认证与租户基础

**目标**：企业能注册、能登录、能邀请成员、JWT 鉴权全链路通。

#### Week 1 任务（按顺序执行）

**Day 1-2：数据库 Schema + 迁移**

建立以下 4 张核心表（详见 `docs/DATABASE.md`）：

- `tenants`：企业主体
- `users`：系统用户，含 role 字段
- `invitations`：邀请 token
- `refresh_tokens`：JWT 刷新 token

```powershell
# 每张表单独一个 migration commit
alembic revision --autogenerate -m "add tenants table"
alembic upgrade head
git add -A && git commit -m "migration: add tenants table"
# ... 重复 users / invitations / refresh_tokens
```

**Day 3-4：Auth API**

实现以下端点（`api/routes/auth.py`）：

```
POST /api/auth/register     # 企业注册 → 创建 tenant + super_admin
POST /api/auth/login        # 邮箱+密码 → 返回 access_token + refresh_token
POST /api/auth/refresh      # refresh_token → 新 access_token
POST /api/auth/logout       # 吊销 refresh_token
POST /api/auth/invite       # 发送邀请（admin+ 可操作）
POST /api/auth/invite/accept # 接受邀请，激活账号
```

JWT 中间件（`api/middleware.py`）：提取 `tenant_id` 和 `user_id`，注入到 `request`。

**Day 5：验证 + Git**

```powershell
python tests/test_auth.py
# 预期：注册/登录/刷新/邀请 全部通过
git add -A && git commit -m "feat: auth system complete"
```

#### Week 1 验收标准

- [ ] `python tests/test_auth.py` 全部通过
- [ ] 可用 curl 或 Postman 完成：注册企业 → 登录 → 获取 JWT → 刷新 → 邀请成员 → 接受邀请 → 被邀成员登录
- [ ] `test_tenant_isolation.py` 中 auth 相关用例通过

#### 不做

- 不做邮件发送（邀请 URL 直接返回在 API 响应中）
- 不做前端页面
- 不做密码重置

---

### 第2周：Bot 管理 + 知识库摄取

**目标**：企业能创建 Bot，能上传文档，文档能进入向量库。

#### Week 2 任务

**Day 1-2：Bot CRUD + bots / knowledge_sources 表**

```
POST   /api/bots              # 创建 Bot（需 admin+）
GET    /api/bots              # 列出本租户所有 Bot
GET    /api/bots/{bot_id}     # 获取 Bot 详情
PUT    /api/bots/{bot_id}     # 更新配置
DELETE /api/bots/{bot_id}     # 删除（级联清理知识库）
POST   /api/bots/{bot_id}/rotate-key  # 轮换 Bot API Key
```

建表：`bots`（含 `bot_api_key`）、`knowledge_sources`

**Day 3-5：知识库摄取 Pipeline**

知识摄取全程异步，通过 RQ 队列处理：

```
用户 POST /api/bots/{bot_id}/knowledge → 立即返回 job_id
          ↓
    RQ Queue: ingestion
          ↓
    knowledge/ingestion.py
      ├── parser.py     → 解析 PDF/Excel/Word/URL
      ├── chunker.py    → 语义分块（中文300-500字/块，英文200-400词/块）
      ├── embedder.py   → 调用 text-embedding-v3
      └── vector_store.py → 写入 Milvus collection: bot_{bot_id}
          ↓
    更新 knowledge_sources.status = "ready"
```

Widget Embedding 准备：创建 `bot_api_key`（`cs_bot_` 前缀，32位随机），存 `bots` 表，用于 Widget 鉴权。

**Day 5：验证**

```powershell
python tests/test_knowledge.py
# 预期：上传文档 → 摄取完成 → Milvus 可检索到内容
```

#### Week 2 验收标准

- [ ] `python tests/test_knowledge.py` 全部通过
- [ ] 上传一份产品手册 PDF → 摄取状态变为 ready → Milvus 中能检索到相关 chunk
- [ ] Bot API Key 生成正常，形如 `cs_bot_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- [ ] 删除 Bot 后 Milvus collection 同步清理

#### 不做

- 不做 URL 爬取（Phase 3 再做）
- 不做 Graph DB（可选项，默认 Phase 2 后评估）

---

### 第3周：RAG 核心引擎 + Widget

**目标**：端到端跑通"上传文档 → Widget 对话 → 得到回答"完整链路。

#### Week 3 任务

**Day 1-3：Agentic RAG Pipeline**

按顺序实现 6 个节点，每个节点独立文件，单独测试：

```
core/rag/router.py             # 意图分类（skip / retrieve / out_of_scope）
core/rag/query_transform.py    # 默认 HyDE（首期）
core/rag/retriever.py          # Milvus vector search + BM25 hybrid
core/rag/grader.py             # Embedding 相似度评分，< 0.6 触发 re-retrieve
core/rag/generator.py          # 流式调用 Qwen，DeepSeek fallback
core/rag/hallucination_checker.py  # 验证 grounding，失败 → clarify
```

**Day 4：WebSocket 对话端点**

```
WS /api/chat/{bot_id}  # Bot API Key 鉴权（不需要 JWT）
```

流式协议（见 `docs/API_CONVENTIONS.md`）：
- 每个 token 发一帧 `{"type": "token", "content": "..."}`
- 完成发 `{"type": "done", "session_id": "..."}`
- 错误发 `{"type": "error", "code": "...", "message": "..."}`

实现语义缓存：相似度 >= 0.95 直接返回，跳过整个 RAG pipeline。

**Day 5：JS Widget + Standalone Link**

```
widget/widget.ts   # Shadow DOM 封装，嵌入代码：
# <script>window.CS_CONFIG={botId:"bot_xxx"}</script>
# <script src="https://cdn.yourproduct.com/widget.js" async></script>

GET /api/bots/{bot_id}/chat   # Standalone 独立对话页
GET /widget.js                # Widget JS 文件服务
```

**Day 5：端到端验证**

```powershell
python tests/test_rag.py
# 预期：
# - 知识库内问题 → 得到有依据的回答（Hallucination pass）
# - 知识库外问题 → 触发 clarify
# - 语义缓存命中 → 延迟 < 100ms
```

#### Week 3 验收标准

- [ ] `python tests/test_rag.py` 全部通过
- [ ] 完整演示：创建 Bot → 上传文档 → 复制 Widget 代码嵌入测试页 → 提问 → 流式收到答案
- [ ] `test_tenant_isolation.py` 中 Bot 和知识库相关用例全部通过
- [ ] 流式输出在 Postman/wscat 中正常工作

**Phase 1 里程碑**：可向种子用户演示核心功能 ✓

---

## Phase 2：外贸差异化（第4-5周）

---

### 第4周：Query Transform + 语义缓存完善 + Admin Console

**目标**：Query Transform 提升检索质量；Admin Console MVP 可用。

#### Week 4 任务

**Day 1-2：Query Transform 完整实现**

在 `core/rag/query_transform.py` 中增加全部策略：

| 策略 | 适用场景 | 实现要点 |
|------|---------|---------|
| HyDE | 模糊描述性问题（默认首次） | 生成假设文档 → embedding 检索 |
| Expansion | 精确功能性问题 | 同义词+上下位词扩展 |
| Step-Back | re-retrieve 时策略升级 | 抽象化，粒度上升再检索 |
| Decompose | 复杂多跳问题 | 拆分子查询，并行检索后合并 |

策略选择由 Router 根据 intent 决定。Re-retrieve 时按策略升级规则切换。

**Day 3：5层缓存完整实现**

```python
# cache/semantic.py   — 语义缓存，相似度 >= 0.95
# cache/session.py    — 会话上下文，TTL 30min
# cache/quota.py      — 配额计数，INCR + 定时同步
# 热块缓存在 knowledge/vector_store.py 中集成
```

**Day 4-5：Admin Console 前端 MVP**

最小可用的 4 个页面（`frontend/src/pages/`）：

| 页面 | 功能 |
|------|------|
| `Dashboard.tsx` | 会话量、解决率、无法回答率 3 个核心指标 |
| `Bots.tsx` | Bot 列表、创建、配置、复制嵌入代码 |
| `Knowledge.tsx` | 文档上传、摄取状态、手动 FAQ 编辑 |
| `Sessions.tsx` | 会话记录列表、单条对话详情、一键接管 |

**Day 5：验证**

```powershell
python tests/test_rag.py          # 确保 Query Transform 不破坏原有通过的 case
cd frontend && npx tsc --noEmit   # 前端类型检查
```

#### Week 4 验收标准

- [ ] 同一问题用 HyDE 和 Expansion 各测一次，验证检索质量有差异
- [ ] re-retrieve 成功触发并切换策略（日志可见 `strategy_upgraded: step_back`）
- [ ] Admin Console 4 个页面可正常访问和操作
- [ ] 前端 `tsc --noEmit` 无错误

---

### 第5周：询盘捕获 + 通知 + 人工接管

**目标**：外贸核心功能完整：对话 → 收集询盘 → 通知业务员 → 人工接管。

#### Week 5 任务

**Day 1-2：Lead Capture 模块**

当 Router 判断 intent = `lead_capture` 时，进入多轮收集模式：

```python
# 收集字段可由 Bot 配置（bots.lead_capture_fields JSON）
# 默认外贸字段：product_requirement, quantity, target_price, contact
```

建表：`leads`（含 `tenant_id`, `bot_id`, `session_id`, `lead_info JSON`, `status`）

端点：
```
GET  /api/leads              # 线索列表（按 intent_score 排序）
GET  /api/leads/{lead_id}    # 单条线索详情
PUT  /api/leads/{lead_id}    # 标记状态（contacted/qualified/closed）
```

前端：`Leads.tsx` 页面，支持线索列表和状态管理。

**Day 3-4：通知服务（RQ 异步）**

```python
# queue/tasks/notifications.py
# 触发时机：
# 1. Lead capture 完成 → 邮件通知
# 2. Human transfer 触发 → 邮件通知
# 3. 新会话开始（如 Bot 配置了 always_notify）

# 邮件：SMTP（先用简单配置，不依赖三方服务）
# 微信：先不做（预留接口，Phase 3 评估）
```

**Day 5：人工接管完善**

人工接管 WebSocket 协议扩展：
- `sessions.status` 字段：`active` / `transferred` / `closed`
- Admin 端 WebSocket 接管后，用户端提示"已为您接通人工客服"
- 接管中 AI 停止自动回复

#### Week 5 验收标准

- [ ] 完整演示：外贸客户询盘 → AI 多轮收集信息 → 邮件通知业务员 → 业务员在 Admin Console 接管 → 继续对话
- [ ] Lead 列表按意向度排序显示
- [ ] 接管后 AI 不再自动回复
- [ ] `test_tenant_isolation.py` leads 相关用例通过

**Phase 2 里程碑**：可让外贸种子用户真实使用 ✓

---

## Phase 3：商业化准备（第6-7周）

---

### 第6周：套餐/配额 + 支付 + 私域引流

**目标**：系统可以收费，配额正确执行。

#### Week 6 任务

**Day 1-2：套餐与配额系统**

建表：在 `tenants` 表扩展套餐字段（通过 migration 加列）：

```sql
ALTER TABLE tenants ADD COLUMN plan TEXT NOT NULL DEFAULT 'free';
ALTER TABLE tenants ADD COLUMN max_bots INT NOT NULL DEFAULT 1;
ALTER TABLE tenants ADD COLUMN monthly_quota INT NOT NULL DEFAULT 200;
```

配额检查中间件：每次对话请求前检查 Redis quota 计数，超限返回 402。

| 套餐 | max_bots | monthly_quota |
|------|---------|---------------|
| free | 1 | 200 |
| entity（实体版） | 3 | 5000 |
| trade（外贸版） | 3 | 5000 |
| pro（专业版） | 10 | unlimited(-1) |

**Day 3-4：支付接入**

微信支付 / 支付宝（选其一先做）：

```
POST /api/billing/create-order   # 创建支付订单
POST /api/billing/webhook        # 支付回调（更新 plan）
GET  /api/billing/status         # 查询当前套餐状态
```

**Day 5：私域引流组件（国内实体版功能）**

Widget 配置项增加：

```javascript
// Bot 配置中增加 private_domain_config
{
  "enabled": true,
  "trigger": "after_qa",    // 回答完问题后触发
  "message": "您好，我们有专属优惠群，加我微信发您",
  "qr_code_url": "https://...",
  "mini_program_url": "weixin://..."  // 可选
}
```

#### Week 6 验收标准

- [ ] 免费版创建第 2 个 Bot 时返回 402 Limit Exceeded
- [ ] 超过月配额后对话请求返回 429 Quota Exceeded
- [ ] 升级套餐后配额立即生效（Redis 更新）
- [ ] 私域引流组件在 Widget 中正常显示二维码

---

### 第7周：CI/CD + 性能 + 上线准备

**目标**：系统稳定，可以接第一批付费客户。

#### Week 7 任务

**Day 1：Golden Set 建立**

```python
# tests/golden_set/cases.json
# 格式：
[
  {
    "id": "gs_001",
    "bot_id": "test_bot",
    "query": "你们的最小起订量是多少",
    "language": "zh",
    "expected_contains": ["MOQ", "起订量"],
    "expected_grounded": true,
    "baseline_score": 0.85
  },
  ...
]
# 初始建立 50 条，覆盖：FAQ / 价格 / 政策 / 越界拒绝 / 中英双语
```

```powershell
python tests/test_golden_set.py
# 记录 baseline，写入 tests/golden_set/baseline.json
```

**Day 2：性能压测**

```powershell
# 安装 locust
pip install locust
# 运行压测
locust -f tests/locustfile.py --headless -u 100 -r 10 --run-time 5m
# 目标：100并发下 p95 < 5s，error rate < 1%
```

**Day 3：GitHub Actions CI/CD**

`.github/workflows/ci.yml`：

```yaml
on: [push, pull_request]
jobs:
  test:
    steps:
      - python -m pytest tests/test_auth.py tests/test_rag.py tests/test_tenant_isolation.py
      - cd frontend && npx tsc --noEmit
  deploy-staging:
    if: github.ref == 'refs/heads/main'
    steps:
      - alembic upgrade head
      - deploy to fly.io staging
  golden-set:
    needs: deploy-staging
    steps:
      - python tests/test_golden_set.py --env staging
      # 分数低于 baseline 则阻断 PR merge
```

**Day 4：监控 + 告警**

结构化日志（每次 LLM 调用记录）：

```python
logger.info("rag_call", extra={
    "tenant_id": state.tenant_id,
    "bot_id": state.bot_id,
    "latency_ms": latency,
    "tokens_used": tokens,
    "grader_score": state.grader_score,
    "cache_hit": cache_hit,
    "attempts": state.attempts,
})
```

关键告警阈值：
- p95 响应时间 > 5s → 告警
- error rate > 1% → 告警
- no_hit rate > 30%（知识库覆盖不足）→ 告警

**Day 5：最终回归测试**

```powershell
# 完整回归
python tests/test_auth.py
python tests/test_rag.py
python tests/test_tenant_isolation.py
python tests/test_golden_set.py
cd frontend && npx tsc --noEmit && npm run build
```

#### Week 7 验收标准

- [ ] 所有测试通过
- [ ] Golden Set 50 条全部 >= baseline
- [ ] locust 压测：100并发 p95 < 5s，error rate < 1%
- [ ] GitHub Actions CI 跑通（PR 可以自动触发测试）
- [ ] 部署到 fly.io/Railway staging 环境可访问

**Phase 3 里程碑**：可正式对外收费 ✓

---

## Post-MVP 路线图（Month 2+）

> 有了真实用户数据后，根据 no-hit 率和 Grader 低分率决定优先级。

### 数据飞轮（最高优先）

- RAGAS 自动评估（Weekly cron）
- no-hit 集群分析（找知识空白）
- 知识精炼工作流（人工审核后执行）
- Golden Set A/B re-index

### 功能扩展

- URL 爬取（Crawl4AI）
- Graph DB（复杂产品关系）
- 企业微信渠道接入（评估市场需求后）
- 语音客服（Fin Voice 路线）

### 技术债偿还

- Query Decomposition 完整实现
- Grader 升级为 LLM-as-Judge（当有足够数据验证必要性时）
- PostgreSQL 读副本（QPS > 1000 时）
- Milvus 集群化（collection 超过 100 时）

---

## 技术债务台账

> 每次刻意选择简化方案时，在此记录。

| 日期 | 简化内容 | 完整方案 | 触发条件 |
|------|---------|---------|---------|
| Week 3 | Grader 用 Embedding 相似度 | LLM-as-Judge | Grader 误判率 > 10% |
| Week 5 | 通知仅支持邮件 | 微信企业号 | 用户需求明确后 |
| Week 6 | 支付仅接一个渠道 | 微信+支付宝 | 上线后看用户偏好 |
| Week 7 | 日志仅结构化存文件 | Grafana + Prometheus | 日活 > 100 |
| — | URL 爬取未实现 | Crawl4AI | 用户反馈知识库维护困难 |
| — | Query Decompose 未实现 | 并行子查询 | 复杂问题 no-hit 率高 |
