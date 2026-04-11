# 数据库设计规范

> PostgreSQL 15+。所有 Schema 变更通过 Alembic 管理，禁止手动修改生产库。

---

## 迁移规则（强制）

1. **只做加法**：只添加列/表/索引，不删改已有字段（向前兼容）
2. **删除操作单独迁移**：删除旧字段/表用单独的清理 migration，至少在功能 migration 后一个 sprint 执行
3. **每张新表单独 commit**：`migration: add {table_name} table`
4. **迁移前后验证**：
   ```powershell
   alembic upgrade head
   python -c "from store.tenant_store import TenantStore; print('schema OK')"
   ```

---

## 核心表 Schema

### tenants（企业/租户）

```sql
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    plan            TEXT NOT NULL DEFAULT 'free',     -- free|entity|trade|pro
    status          TEXT NOT NULL DEFAULT 'active',   -- active|suspended|cancelled
    max_bots        INT  NOT NULL DEFAULT 1,
    monthly_quota   INT  NOT NULL DEFAULT 200,        -- -1 = unlimited
    current_month_msgs INT NOT NULL DEFAULT 0,
    master_api_key  TEXT NOT NULL UNIQUE,             -- 后台管理密钥
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_status ON tenants(status);
```

### users（用户）

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           TEXT NOT NULL UNIQUE,             -- 全局唯一（跨租户）
    password_hash   TEXT,                             -- bcrypt，邀请未激活时为 NULL
    name            TEXT NOT NULL DEFAULT '',
    role            TEXT NOT NULL DEFAULT 'operator', -- super_admin|admin|operator|viewer
    status          TEXT NOT NULL DEFAULT 'invited',  -- active|invited|suspended
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email  ON users(email);
```

### invitations（邀请）

```sql
CREATE TABLE invitations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    inviter_id  UUID NOT NULL REFERENCES users(id),
    email       TEXT NOT NULL,
    role        TEXT NOT NULL,                        -- admin|operator|viewer
    token       TEXT NOT NULL UNIQUE,                 -- 随机 64 字符
    expires_at  TIMESTAMPTZ NOT NULL,                 -- NOW() + 7 days
    status      TEXT NOT NULL DEFAULT 'pending',      -- pending|accepted|expired
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_invitations_tenant ON invitations(tenant_id);
CREATE INDEX idx_invitations_token  ON invitations(token);
```

### refresh_tokens（JWT 刷新 token）

```sql
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id   UUID NOT NULL,                        -- 冗余字段，加速查询
    token_hash  TEXT NOT NULL UNIQUE,                 -- SHA-256 哈希
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,                          -- NULL = 有效
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
```

### bots（机器人）

```sql
CREATE TABLE bots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    avatar_url          TEXT,
    welcome_message     TEXT NOT NULL DEFAULT '您好，有什么可以帮您？',
    language            TEXT NOT NULL DEFAULT 'zh',   -- zh|en|both
    style               TEXT NOT NULL DEFAULT 'friendly', -- formal|friendly|professional
    system_prompt       TEXT,                         -- 额外的 system prompt（可选）
    bot_api_key         TEXT NOT NULL UNIQUE,         -- cs_bot_ 前缀，Widget 鉴权用
    lead_capture_fields JSONB NOT NULL DEFAULT '[]',  -- 询盘收集字段配置
    private_domain_config JSONB,                      -- 私域引流配置
    status              TEXT NOT NULL DEFAULT 'active',
    created_by          UUID NOT NULL REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bots_tenant    ON bots(tenant_id);
CREATE INDEX idx_bots_api_key   ON bots(bot_api_key);
```

### knowledge_sources（知识来源）

```sql
CREATE TABLE knowledge_sources (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    bot_id      UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,              -- doc|url|faq
    name        TEXT NOT NULL,
    file_path   TEXT,                       -- 上传文件路径
    url         TEXT,                       -- URL 爬取来源
    status      TEXT NOT NULL DEFAULT 'pending', -- pending|processing|ready|failed
    chunk_count INT NOT NULL DEFAULT 0,
    error_msg   TEXT,
    created_by  UUID NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_knowledge_tenant ON knowledge_sources(tenant_id);
CREATE INDEX idx_knowledge_bot    ON knowledge_sources(bot_id, status);
```

### faq_items（手动 FAQ）

```sql
CREATE TABLE faq_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    bot_id      UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    priority    INT  NOT NULL DEFAULT 0,    -- 越高优先级越高（FAQ > 文档）
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_by  UUID NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_faq_bot ON faq_items(bot_id, is_active);
```

### sessions（会话）

```sql
CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    bot_id          UUID NOT NULL REFERENCES bots(id),
    visitor_id      TEXT NOT NULL,                    -- 匿名访客 ID（Widget 生成）
    language        TEXT NOT NULL DEFAULT 'zh',       -- 检测到的语言
    status          TEXT NOT NULL DEFAULT 'active',   -- active|transferred|closed
    transferred_to  UUID REFERENCES users(id),        -- 接管的客服 user_id
    lead_id         UUID,                             -- 关联的询盘线索
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    message_count   INT NOT NULL DEFAULT 0
);

CREATE INDEX idx_sessions_tenant ON sessions(tenant_id, status);
CREATE INDEX idx_sessions_bot    ON sessions(bot_id, started_at DESC);
```

### messages（消息）

```sql
CREATE TABLE messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id   UUID NOT NULL,                        -- 冗余字段，加速查询
    role        TEXT NOT NULL,                        -- user|assistant|human_agent
    content     TEXT NOT NULL,
    grader_score FLOAT,                               -- RAG 检索质量分
    is_grounded  BOOLEAN,                             -- 幻觉检测结果
    tokens_used  INT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);
```

### leads（询盘线索）

```sql
CREATE TABLE leads (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    bot_id      UUID NOT NULL,
    session_id  UUID REFERENCES sessions(id),
    lead_info   JSONB NOT NULL DEFAULT '{}',          -- 收集到的询盘信息
    status      TEXT NOT NULL DEFAULT 'new',          -- new|contacted|qualified|closed
    intent_score FLOAT NOT NULL DEFAULT 0.5,          -- 意向度评分（用于排序）
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_leads_tenant   ON leads(tenant_id, status);
CREATE INDEX idx_leads_intent   ON leads(tenant_id, intent_score DESC);
```

---

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 表名 | 复数蛇形 | `knowledge_sources` |
| 列名 | 蛇形 | `tenant_id`, `created_at` |
| 索引名 | `idx_{table}_{column(s)}` | `idx_bots_tenant` |
| 外键 | `{table}_{column}_fkey`（PG 自动命名） | — |
| 枚举值 | 小写字符串（TEXT 类型）| `'active'`, `'pending'` |

---

## ID 生成策略

所有主键使用 `UUID`，由 PostgreSQL `gen_random_uuid()` 生成。
- 禁止使用自增 INT（防止 ID 枚举攻击）
- 禁止在应用层生成 UUID（DB 生成更可靠）

---

## 时间戳规范

- 所有时间字段使用 `TIMESTAMPTZ`（含时区）
- 统一存储 UTC 时间，前端显示时转换为用户本地时区
- `created_at`：只写一次，禁止更新
- `updated_at`：通过 DB trigger 或应用层每次更新时设置

---

## 软删除策略

当前不实现软删除。删除操作直接硬删除。
例外：`messages` 和 `sessions` 只允许通过级联删除（删 Bot 时级联删）。
如未来需要软删除，通过 migration 加 `deleted_at TIMESTAMPTZ` 列。

---

## 敏感字段安全

| 字段 | 存储方式 |
|------|---------|
| `password_hash` | bcrypt（cost=12）明文 → 哈希，禁止存原文 |
| `token_hash`（refresh_token）| SHA-256 哈希，禁止存原始 token |
| `master_api_key` | 明文存储（但生成后只在创建时返回给用户一次） |
| `bot_api_key` | 明文存储（公开嵌入代码中，不保密） |
