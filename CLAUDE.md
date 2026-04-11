# CS Platform — 通用智能客服系统

> 开发主文档。每次新会话必读，任务完成后执行 `/save-progress`。

---

## ⚠️ 平台约束（最高优先级）

**本项目运行在 Windows 11 + PowerShell 环境。**

| 需要 | 用这个替代 |
|------|-----------|
| `grep` | `Select-String` |
| `cat` | `Get-Content` |
| `kill` | `taskkill /PID <PID> /F` |
| `lsof -i:8080` | `netstat -ano \| findstr :8080` |
| Unix 路径 `~/` | 完整路径 `D:\cs-platform\` |

- Shell 命令中路径用 `\`，Python 代码中 `\` 或 `/` 均可
- 字符串用双引号 `"`，不用单引号 `'`（PowerShell 语法）
- 日志文件 FileHandler 必须加 `encoding="utf-8"`

---

## 会话续接

```powershell
Get-Content claude-progress.txt
```

了解上次进度后再开始工作。

---

## 项目定位

面向国内中小企业（外贸 + 实体）的通用智能客服 SaaS 平台。  
**技术内核**：Agentic RAG — LLM Agent 控制整个检索推理循环，not a fixed pipeline。  
**商业模式**：多租户 SaaS，企业为主体，企业下分配用户（super_admin / admin / operator / viewer）。

---

## 技术栈

| 层次 | 选型 |
|------|------|
| 后端 | Python 3.11+, aiohttp, asyncpg |
| 前端 | React 18, TypeScript, Vite, Tailwind CSS |
| 主力 LLM | Qwen-Plus (DashScope API) |
| 备用 LLM | DeepSeek（主力超时自动切换） |
| Embedding | text-embedding-v3（通义千问） |
| 向量 DB | Milvus |
| 关系 DB | PostgreSQL 15+ |
| 缓存 + 队列 | Redis + RQ (Redis Queue) |
| DB 迁移 | Alembic |

**端口**：后端 `8080`，前端 `3001`，Redis `6379`，PostgreSQL `5432`，Milvus `19530`

---

## 架构总览

```
Widget JS / Standalone Link / API
           │
           ▼
  JWT Middleware（提取 tenant_id + user_id）
           │
           ▼
  Pre-processing（语言检测 · 意图初判 · Session init）
           │
           ▼
  ┌─── Agentic RAG Pipeline ──────────────────────────────┐
  │  Router → QueryTransform → Retriever → Grader         │
  │  → Generator（流式）→ HallucinationChecker            │
  │  反馈循环：Grader 低分 → re-retrieve（最多 2 次）      │
  │  Hallucination 失败 → regenerate                      │
  └───────────────────────────────────────────────────────┘
           │
           ▼
  LeadCapture / DirectReply / HumanTransfer / Notification
```

---

## 目录结构（改文件前必须确认路径）

```
cs-platform/
├── api/
│   ├── app.py              # aiohttp Application 入口，注册所有路由
│   ├── middleware.py        # JWT 鉴权中间件（注入 tenant_id / user_id）
│   └── routes/
│       ├── auth.py          # 注册 / 登录 / 刷新 / 邀请
│       ├── bots.py          # Bot CRUD + API Key 管理
│       ├── chat.py          # WebSocket 对话 + 流式输出
│       ├── knowledge.py     # 知识库上传 / 状态查询
│       ├── leads.py         # 线索管理
│       └── admin.py         # Admin Console 数据接口
├── core/
│   ├── engine.py            # CSEngine 主编排器
│   └── rag/
│       ├── state.py         # RAGState dataclass（唯一状态对象）
│       ├── router.py        # 节点1：意图分类 + skip 判断
│       ├── query_transform.py # 节点2：HyDE / Step-Back / Expansion / Decompose
│       ├── retriever.py     # 节点3：hybrid search（vector + BM25）
│       ├── grader.py        # 节点4：相关度评分，触发 re-retrieve
│       ├── generator.py     # 节点5：流式生成
│       └── hallucination_checker.py # 节点6：grounding 校验
├── knowledge/
│   ├── ingestion.py         # 摄取入口（接收 RQ 任务）
│   ├── parser.py            # PDF / Excel / Word 解析
│   ├── chunker.py           # 语义分块
│   ├── embedder.py          # 调用 embedding API
│   └── vector_store.py      # Milvus 读写封装
├── cache/
│   ├── semantic.py          # 语义缓存（相似度 >= 0.95 命中）
│   ├── session.py           # 会话上下文缓存
│   └── quota.py             # 配额计数缓存（Redis INCR）
├── queue/
│   ├── worker.py            # RQ worker 入口
│   └── tasks/
│       ├── ingestion.py     # 文档摄取异步任务
│       ├── notifications.py # 邮件 / 微信推送任务
│       └── signals.py       # 飞轮信号采集任务
├── store/
│   ├── base.py              # 连接池 + 基础查询封装
│   ├── tenant_store.py
│   ├── user_store.py
│   ├── bot_store.py
│   ├── session_store.py
│   └── lead_store.py
├── auth/
│   ├── jwt_utils.py         # 签发 / 验证 / 刷新 token
│   └── invite.py            # 邀请 token 生成 + 验证
├── widget/
│   └── widget.ts            # JS Widget 源码（Shadow DOM）
├── migrations/              # Alembic 迁移文件
│   └── versions/
├── frontend/
│   └── src/
│       ├── pages/           # Dashboard / Bots / Knowledge / Sessions / Leads
│       ├── components/      # 公共组件
│       └── api/             # 前端 API 调用层
├── tests/
│   ├── test_auth.py
│   ├── test_rag.py
│   ├── test_tenant_isolation.py   # 必须：验证跨租户数据不泄露
│   └── golden_set/
│       └── cases.json             # Golden Set 标准问答（50+ 条）
├── docs/
│   ├── DEVELOPMENT_PLAN.md
│   ├── MULTI_TENANT.md
│   ├── DATABASE.md
│   ├── API_CONVENTIONS.md
│   └── TESTING.md
├── CLAUDE.md
├── .env.example
├── main.py                  # 启动入口
└── docker-compose.yml       # PostgreSQL + Redis + Milvus 本地开发环境
```

**改文件前必须确认**：前端文件在 `frontend/src/`，后端文件在项目根目录，绝对不能混淆。

---

## 服务管理

### 启动（首次或 docker 未运行时）

```powershell
cd D:\cs-platform
# 启动基础服务
docker-compose up -d
# 等待 PostgreSQL / Redis / Milvus 就绪（约 15s）
Start-Sleep 15
# 执行数据库迁移
alembic upgrade head
# 启动后端
python main.py serve
# 新终端：启动 RQ Worker
python -m rq worker ingestion notifications signals --url redis://localhost:6379
```

### 日常重启（改了 .py 文件后）

```powershell
taskkill /F /IM python.exe
Start-Sleep 2
cd D:\cs-platform
python main.py serve
```

### 端口被占用

```powershell
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

### 判断是否需要重启

| 改动类型 | 是否重启 |
|---------|---------|
| `*.py` 后端文件 | **必须重启** |
| `frontend/src/` 前端文件 | 不需要（Vite 热更新） |
| `.env` 配置文件 | **必须重启** |
| `migrations/versions/` 迁移文件 | `alembic upgrade head` + 重启 |

---

## 核心约束

1. **每个 .py 文件不超过 500 行**，超过必须拆分
2. **每个类不超过 20 个公开方法**，超过说明职责不单一
3. **所有 async 函数使用 asyncio 前必须 `import asyncio`**（历史高频 bug）
4. **RAG 节点间状态通过 `RAGState` dataclass 传递**，禁止随意用 dict 扩展
5. **所有 SQL 用参数化查询（`$1`, `$2`）**，禁止 f-string 拼接用户输入
6. **CSEngine 只做编排**，不直接操作子系统内部状态

---

## Agentic RAG — 核心状态对象

```python
# core/rag/state.py — 唯一状态定义，所有节点共享
@dataclass
class RAGState:
    # 基础标识
    session_id: str
    bot_id: str
    tenant_id: str          # 安全边界，所有节点必须携带

    # 输入
    user_query: str
    language: str           # "zh" | "en"
    history: list[dict]     # 多轮上下文，[{"role": "user/assistant", "content": "..."}]

    # Router 输出
    intent: str             # "knowledge_qa" | "lead_capture" | "out_of_scope" | "transfer"
    skip_retrieval: bool    # True → 直接走 Generator

    # QueryTransform 输出
    transformed_query: str
    sub_queries: list[str]  # Decomposition 产出
    transform_strategy: str # "hyde" | "expansion" | "step_back" | "decompose"

    # Retriever 输出
    retrieved_chunks: list[dict]  # [{"content": ..., "score": ..., "chunk_id": ...}]

    # Grader 输出
    grader_score: float     # 0.0 - 1.0
    attempts: int           # re-retrieve 次数，最多 2

    # Generator 输出
    generated_answer: str

    # HallucinationChecker 输出
    is_grounded: bool
    hallucination_action: str  # "pass" | "regenerate" | "clarify"

    # 业务输出
    lead_info: dict         # 外贸询盘收集的信息
    should_transfer: bool   # 是否需要人工接管
```

### 节点职责边界（违反视为架构破坏）

| 节点 | 可写字段 | 禁止操作 |
|------|---------|---------|
| Router | `intent`, `skip_retrieval` | 访问 Vector DB |
| QueryTransform | `transformed_query`, `sub_queries`, `transform_strategy` | 直接检索 |
| Retriever | `retrieved_chunks` | 评分，生成 |
| Grader | `grader_score`, `attempts` | 修改 chunks，生成回答 |
| Generator | `generated_answer`（流式更新） | 校验，修改 chunks |
| HallucinationChecker | `is_grounded`, `hallucination_action` | 直接修改 answer |

### Re-retrieve 策略升级

```
首次 HyDE 失败       → Step-Back
首次 Expansion 失败  → Step-Back
Decompose 子查询失败 → Expansion 重试
attempts >= 2        → hallucination_action = "clarify" → Human Transfer
```

---

## 多租户隔离原则（强制 — 所有接口和 SQL 必须遵守）

> 详见 `docs/MULTI_TENANT.md`

**核心规则（此处不得简化）**：

```
tenant_id 从 JWT 提取，禁止信任前端传值。
所有业务表必须有 tenant_id TEXT NOT NULL 字段。
所有列表查询默认附带 WHERE tenant_id = $1。
更新/删除必须 WHERE id = $1 AND tenant_id = $2，0行返回 403。
Milvus collection 命名：bot_{bot_id}（天然隔离）。
Redis key 前缀：{tenant_id}:{bot_id}:*
```

### 新功能强制检查清单

- [ ] 表结构有 `tenant_id TEXT NOT NULL`？
- [ ] 建表时创建了 tenant_id 索引？
- [ ] API 从 JWT 提取 tenant_id，不接受前端传值？
- [ ] 列表查询带 `WHERE tenant_id = $1`？
- [ ] 删除/更新带 tenant_id 条件，0行返回 403？
- [ ] Milvus collection 用 `bot_{bot_id}` 命名？
- [ ] Redis key 带 `{tenant_id}:{bot_id}:` 前缀？

---

## 缓存操作规范

> 详见 `docs/CACHE.md`（如存在）

### Key 命名规范

```
语义缓存   semantic:{bot_id}:{embedding_hex[:16]}   TTL 86400s
Embedding  embed:{sha256(text)[:16]}                TTL 永久
会话上下文 session:{session_id}:ctx                 TTL 1800s（30min空闲）
配额计数   quota:{tenant_id}:{YYYY-MM}:msgs         TTL 月底重置
热块缓存   chunks:{bot_id}:{chunk_id}               TTL 3600s
```

### 禁止

- 禁止在 route handler 里直接操作 Redis，必须通过 `cache/` 模块
- 禁止缓存跨 bot_id 的数据
- 禁止配额直接写 DB（走 Redis INCR，每 5min 同步）
- 禁止知识库更新后不 invalidate 对应语义缓存

---

## ⚠️ 开发规范（强制执行）

### 修改后必须验证（不验证不准报完成）

```powershell
# Python 文件语法检查
python -c "import ast; ast.parse(open('改动的文件').read()); print('OK')"

# 前端类型检查
cd frontend && npx tsc --noEmit

# RAG 核心改动后
python tests/test_rag.py

# 认证改动后
python tests/test_auth.py

# 租户隔离改动后（必须）
python tests/test_tenant_isolation.py

# 上线前 Golden Set 回归
python tests/test_golden_set.py
# 预期：所有 case 分数 >= baseline（baseline 在 tests/golden_set/baseline.json 中）

# 数据库迁移后
alembic upgrade head
python -c "from store.tenant_store import TenantStore; print('schema OK')"
```

### 高频 bug 检查清单（每次提交前核对）

- [ ] 新文件 import 了所有用到的模块（`asyncio`, `json`, `time`）？
- [ ] JWT 中间件正确注入 `request['tenant_id']` 和 `request['user_id']`？
- [ ] 新路由在 `app.py` 或对应路由文件的 `register()` 中注册？
- [ ] 新 Alembic migration 只做加法（不删改已有列）？
- [ ] Redis key 带 tenant_id/bot_id 前缀？
- [ ] 流式输出处理了 HallucinationChecker 中断信号？
- [ ] RQ task 设置了 `job_timeout`（文档摄取建议 600s）？
- [ ] RAGState 字段变更同步更新了所有引用节点？

### 修复 bug 的正确流程

1. **先复现**：用用户描述的步骤复现问题，截图或记录错误信息
2. **定位根因**：读代码找到具体出错的行，不猜，不假设
3. **最小修改**：只改必要代码，不顺手重构
4. **验证修复**：跑验证命令，确认修复生效
5. **回归检查**：确认没有破坏多租户隔离和 RAG 核心流程
6. **不得声称"已修复"除非验证命令通过**

---

## 任务管理规范

### 每个会话限 2-3 个任务

不要在一个会话中做超过 3 个任务。每个任务完成并测试通过后 `git commit`，再做下一个。

### 提示模板

```
本次会话只做以下任务：
1. [具体任务]
2. [具体任务]
每个任务完成并验证通过后 git commit，再做下一个。不要跳跃。
```

### 大任务拆分原则

- 超过 5 个文件的改动 → 拆成 2-3 批
- 每批有明确的验收标准（测试命令通过）
- 每批完成后 `git commit`

---

## Git 规范

```powershell
git add -A && git commit -m "feat: xxx" && git push origin main
```

### Commit Message 规范

| 前缀 | 用途 |
|------|------|
| `feat:` | 新功能 |
| `fix:` | 修复 bug |
| `refactor:` | 重构 |
| `migration:` | 数据库迁移（单独 commit） |
| `chore:` | 依赖/配置杂项 |
| `test:` | 测试相关 |
| `perf:` | 性能优化 |

**迁移 commit 必须单独提交**：`migration: add {table_name} table`

---

## 常见错误速查

| 症状 | 根因 | 修复 |
|------|------|------|
| `NameError: asyncio` | 文件缺少 import asyncio | 文件顶部加 `import asyncio` |
| 前端 405 错误 | 路由未注册 | 检查 `register()` 是否调用 |
| JWT 验证失败 | secret 不匹配或 token 过期 | 检查 `.env` 中 `JWT_SECRET` |
| Milvus 查无结果 | collection 不存在 | 检查知识库摄取状态 |
| Redis INCR 配额不准 | 同步任务未执行 | 手动触发 `queue/tasks/signals.py:sync_quota` |
| 流式输出中断 | WebSocket 心跳未清理 session | 检查 `cache/session.py` 心跳逻辑 |
| RQ 任务卡死 | 未设 job_timeout | enqueue 时传 `job_timeout=600` |
| **跨租户数据泄露** | SQL 缺 tenant_id 过滤 | **审查所有受影响查询，P0 紧急修复** |
| Windows 编码乱码 | 日志未指定 UTF-8 | `FileHandler(encoding="utf-8")` |
| Milvus 连接失败 | docker-compose 未启动 | `docker-compose up -d` |
| asyncpg 连接超时 | 连接池耗尽 | 检查是否有连接未释放 |
