# 多租户隔离规范

> 所有业务接口和 SQL 必须遵守。违反此文件规则视为 P0 安全 Bug。

---

## 实体层级

```
Tenant（企业）
├── Users（用户，4种角色）
│   ├── super_admin  — 所有者，全权限（含套餐支付）
│   ├── admin        — 管理员（Bot/知识库/成员管理）
│   ├── operator     — 客服坐席（会话监控/接管）
│   └── viewer       — 只读观察
├── Bots（机器人）
│   ├── KnowledgeSources（知识来源）
│   └── Sessions → Messages
└── Leads（询盘线索）
```

---

## 隔离维度

**`tenant_id` 是唯一的隔离维度**。

- 从 JWT sub_claim 中提取 user_id，通过 DB 查找对应 tenant_id
- tenant_id 由服务端注入，**禁止信任任何前端传入的 tenant_id**
- Bot API Key 鉴权时，通过 `bot_api_key` 查找 `bot_id` 和 `tenant_id`

---

## 各模块隔离标准

| 模块 | 表 | 隔离字段 | 默认查询条件 |
|------|---|---------|------------|
| 企业 | tenants | 自身 | — |
| 用户 | users | tenant_id | `WHERE tenant_id = $1` |
| 邀请 | invitations | tenant_id | `WHERE tenant_id = $1` |
| Bot | bots | tenant_id | `WHERE tenant_id = $1` |
| 知识来源 | knowledge_sources | tenant_id | `WHERE tenant_id = $1` |
| 会话 | sessions | tenant_id | `WHERE tenant_id = $1` |
| 消息 | messages | 通过 session JOIN | `JOIN sessions WHERE sessions.tenant_id = $1` |
| 线索 | leads | tenant_id | `WHERE tenant_id = $1` |
| 刷新 token | refresh_tokens | tenant_id | `WHERE tenant_id = $1 AND user_id = $2` |
| Milvus | — | collection = `bot_{bot_id}` | 天然隔离（不同 Bot 不同 collection） |
| Redis | — | key 前缀 `{tenant_id}:{bot_id}:` | 命名空间隔离 |

---

## JWT 提取模式（标准实现）

```python
# api/middleware.py

async def jwt_middleware(app, handler):
    async def middleware(request):
        # 1. 跳过公开路由
        public_paths = ["/api/auth/register", "/api/auth/login",
                        "/api/auth/refresh", "/widget.js"]
        if request.path in public_paths:
            return await handler(request)

        # 2. Bot API Key 路由（Widget 用，不需要 JWT）
        if request.path.startswith("/api/chat/"):
            bot_api_key = request.headers.get("X-Bot-Key") or \
                          request.rel_url.query.get("key")
            if not bot_api_key:
                raise web.HTTPUnauthorized(reason="Missing bot API key")
            bot = await bot_store.get_by_api_key(bot_api_key)
            if not bot:
                raise web.HTTPUnauthorized(reason="Invalid bot API key")
            request["bot_id"] = bot["id"]
            request["tenant_id"] = bot["tenant_id"]
            return await handler(request)

        # 3. 标准 JWT 路由
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise web.HTTPUnauthorized(reason="Missing token")

        token = auth_header[7:]
        payload = jwt_utils.verify_access_token(token)  # 失败抛 401

        request["user_id"] = payload["sub"]
        request["tenant_id"] = payload["tid"]
        request["role"] = payload["role"]
        request["plan"] = payload["plan"]

        return await handler(request)
    return middleware
```

---

## 标准 SQL 模式

### 列表查询

```python
# 正确 ✓
rows = await db.fetch(
    "SELECT * FROM bots WHERE tenant_id = $1 ORDER BY created_at DESC",
    request["tenant_id"]
)

# 错误 ✗（缺少 tenant_id 过滤）
rows = await db.fetch("SELECT * FROM bots")
```

### 创建

```python
# 正确 ✓ — tenant_id 从 request 注入，不接受前端传值
await db.execute(
    "INSERT INTO bots (id, tenant_id, name, ...) VALUES ($1, $2, $3, ...)",
    new_id, request["tenant_id"], data["name"]
)
```

### 更新

```python
# 正确 ✓ — WHERE 条件同时包含 id 和 tenant_id
result = await db.execute(
    "UPDATE bots SET name = $1 WHERE id = $2 AND tenant_id = $3",
    data["name"], bot_id, request["tenant_id"]
)
if result == "UPDATE 0":
    raise web.HTTPForbidden(reason="Bot not found or access denied")
```

### 删除

```python
# 正确 ✓
result = await db.execute(
    "DELETE FROM bots WHERE id = $1 AND tenant_id = $2",
    bot_id, request["tenant_id"]
)
if result == "DELETE 0":
    raise web.HTTPForbidden(reason="Not found or access denied")  # 403 而非 404（防止枚举）
```

---

## 角色权限矩阵

```python
# auth/permissions.py

PERMISSIONS = {
    "super_admin": ["*"],  # 全权限
    "admin": [
        "bot:create", "bot:read", "bot:update", "bot:delete",
        "knowledge:write", "member:invite", "member:remove",
        "session:read", "session:transfer",
        "lead:read", "lead:update",
        "analytics:read",
    ],
    "operator": [
        "bot:read",
        "session:read", "session:transfer",
        "lead:read",
        "analytics:read",
    ],
    "viewer": [
        "bot:read",
        "session:read",
        "analytics:read",
    ],
}

def require_permission(perm: str):
    """路由装饰器：检查当前用户是否有指定权限"""
    async def decorator(request):
        role = request["role"]
        allowed = PERMISSIONS.get(role, [])
        if "*" not in allowed and perm not in allowed:
            raise web.HTTPForbidden(reason=f"Role '{role}' lacks permission '{perm}'")
    return decorator
```

---

## Milvus 隔离规范

```python
# knowledge/vector_store.py

# collection 命名：bot_{bot_id}（不含 tenant_id，因为 bot_id 全局唯一）
COLLECTION_NAME = lambda bot_id: f"bot_{bot_id.replace('-', '_')}"

# 检索时：collection 已天然隔离，但仍需传 bot_id 做二次校验
async def search(bot_id: str, tenant_id: str, query_vector: list, top_k: int = 10):
    # 先验证 bot 属于该 tenant
    bot = await bot_store.get(bot_id, tenant_id)  # 含 tenant_id 过滤
    if not bot:
        raise PermissionError("Bot not found or access denied")

    collection_name = COLLECTION_NAME(bot_id)
    # ... 执行检索
```

---

## Redis 隔离规范

```python
# cache/base.py

class CacheKey:
    @staticmethod
    def semantic(bot_id: str, embedding_prefix: str) -> str:
        return f"semantic:{bot_id}:{embedding_prefix}"

    @staticmethod
    def session(session_id: str) -> str:
        return f"session:{session_id}:ctx"

    @staticmethod
    def quota(tenant_id: str, month: str) -> str:
        return f"quota:{tenant_id}:{month}:msgs"

    @staticmethod
    def chunk(bot_id: str, chunk_id: str) -> str:
        return f"chunks:{bot_id}:{chunk_id}"
```

---

## 租户隔离测试（tests/test_tenant_isolation.py）

以下场景必须测试并通过：

```python
# 1. 用户 A 无法访问 用户 B 的 Bot
# 2. 用户 A 无法访问 用户 B 的知识库
# 3. 用户 A 无法访问 用户 B 的会话记录
# 4. 用户 A 无法访问 用户 B 的线索
# 5. 用户 A 的 Bot API Key 无法检索 用户 B 的知识库
# 6. 伪造 tenant_id 请求被拒绝
# 7. 越权删除（删除他人 Bot）返回 403 而非 500
```

---

## 禁止事项

- **禁止**只按 `id` 删除/更新数据（必须附带 `tenant_id`）
- **禁止**信任前端传入的 `tenant_id`（从 JWT 的 `tid` claim 提取）
- **禁止**用 `user_id` 替代 `tenant_id` 做隔离（user_id 是操作人，tenant_id 是归属）
- **禁止**在 Milvus 检索前不验证 bot 归属
- **禁止**Redis key 不带 tenant_id 或 bot_id 前缀
- **禁止**在没有 `WHERE tenant_id = $1` 的情况下返回数据列表
