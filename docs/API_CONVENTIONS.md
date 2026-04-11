# API 设计规范

> 所有接口设计必须遵守。保持一致性比追求"完美设计"更重要。

---

## 基础规范

### URL 结构

```
/api/{resource}              # 列表/创建
/api/{resource}/{id}         # 单个资源 CRUD
/api/{resource}/{id}/{sub}   # 子资源

# 示例
/api/auth/register
/api/bots
/api/bots/{bot_id}
/api/bots/{bot_id}/knowledge
/api/bots/{bot_id}/rotate-key
```

### HTTP 方法

| 操作 | 方法 |
|------|------|
| 查询列表 | GET |
| 查询单个 | GET |
| 创建 | POST |
| 全量更新 | PUT |
| 部分更新 | PATCH |
| 删除 | DELETE |
| 触发动作 | POST（动词路径，如 `/rotate-key`） |

### 请求头

```
Content-Type: application/json
Authorization: Bearer {access_token}     # 标准接口
X-Bot-Key: {bot_api_key}                 # Widget/Chat 接口
```

---

## 响应格式

### 成功响应

```json
// 单个资源
{
  "data": { "id": "...", "name": "..." },
  "meta": {}
}

// 列表
{
  "data": [...],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}

// 纯操作（无返回数据）
{
  "data": null,
  "meta": { "affected": 1 }
}
```

### 错误响应

```json
{
  "error": {
    "code": "BOT_NOT_FOUND",       // 大写下划线，机器可读
    "message": "Bot 不存在或无权访问",  // 人类可读
    "detail": {}                    // 可选，调试信息（仅开发环境）
  }
}
```

### 标准错误码

| HTTP 状态 | error.code | 含义 |
|-----------|-----------|------|
| 400 | `VALIDATION_ERROR` | 请求参数不合法 |
| 401 | `UNAUTHORIZED` | 未登录或 token 失效 |
| 403 | `FORBIDDEN` | 无权限（含跨租户访问） |
| 404 | `NOT_FOUND` | 资源不存在 |
| 402 | `QUOTA_EXCEEDED` | 超过套餐限制 |
| 429 | `RATE_LIMITED` | 请求过于频繁 |
| 500 | `INTERNAL_ERROR` | 服务器错误 |
| 503 | `LLM_UNAVAILABLE` | LLM 服务不可用（含 fallback 失败） |

**注意**：跨租户访问（访问他人资源）返回 **403**，而非 404。防止通过 404/403 差异枚举资源 ID。

---

## 分页规范

```
GET /api/sessions?page=1&page_size=20&order=desc

# 固定参数名：page, page_size
# 默认：page=1, page_size=20
# 最大：page_size=100
# 排序：order=asc|desc（按 created_at）
```

---

## WebSocket 协议（对话接口）

### 连接

```
WS /api/chat/{bot_id}?key={bot_api_key}&session_id={session_id}

# session_id 可选：传入则续接已有会话；不传则创建新会话
# key 参数用于 URL 方式传 Bot API Key（不支持 header 的场景）
```

### 消息帧格式

**客户端 → 服务端**

```json
{
  "type": "message",
  "content": "你们的产品价格是多少",
  "visitor_id": "vis_xxx"          // Widget 生成的匿名访客 ID
}
```

**服务端 → 客户端**

```json
// 流式 token（Generator 流式输出）
{"type": "token", "content": "我们"}
{"type": "token", "content": "的产品"}
{"type": "token", "content": "价格..."}

// 对话完成
{
  "type": "done",
  "session_id": "sess_xxx",
  "grounded": true,
  "cache_hit": false
}

// 需要收集信息（Lead Capture 触发）
{
  "type": "lead_form",
  "fields": ["product_requirement", "quantity", "contact"],
  "prompt": "为了给您更准确的报价，请问您的需求量大概是多少？"
}

// 转人工
{
  "type": "transfer",
  "message": "已为您转接人工客服，请稍候..."
}

// 私域引流
{
  "type": "private_domain",
  "message": "有专属优惠，加我微信告诉您",
  "qr_code_url": "https://..."
}

// 错误
{
  "type": "error",
  "code": "LLM_UNAVAILABLE",
  "message": "服务暂时不可用，请稍后重试"
}

// 心跳（服务端每 30s 发送）
{"type": "ping"}
```

**客户端心跳响应**

```json
{"type": "pong"}
```

---

## 文件上传规范

```
POST /api/bots/{bot_id}/knowledge
Content-Type: multipart/form-data

# 字段：
# file: 文件内容（PDF/Excel/Word）
# name: 知识来源名称（可选，默认用文件名）

# 响应：
{
  "data": {
    "id": "ks_xxx",
    "status": "pending",        // 立即返回，后台异步处理
    "job_id": "job_xxx"
  }
}

# 进度查询：
GET /api/bots/{bot_id}/knowledge/{source_id}
# 返回 status: pending|processing|ready|failed
```

---

## 限流规范

| 接口类型 | 限流策略 |
|---------|---------|
| 对话接口（WebSocket） | 租户级：最多 5 并发 LLM 请求 |
| 知识库上传 | 租户级：每分钟 10 次 |
| Auth 接口 | IP 级：每分钟 10 次 |
| 通用 API | 租户级：每分钟 300 次 |

超限响应：HTTP 429 + `Retry-After` header

---

## 认证接口详细规范

### POST /api/auth/register

```json
// 请求
{
  "company_name": "深圳某某贸易有限公司",
  "name": "张三",
  "email": "zhang@example.com",
  "password": "至少8位，含字母和数字"
}

// 响应 201
{
  "data": {
    "tenant_id": "...",
    "user_id": "...",
    "access_token": "eyJ...",
    "expires_in": 900
  }
}
```

### POST /api/auth/login

```json
// 请求
{ "email": "zhang@example.com", "password": "..." }

// 响应 200
{
  "data": {
    "access_token": "eyJ...",
    "expires_in": 900,
    "role": "super_admin",
    "plan": "free"
  }
  // refresh_token 通过 httpOnly Cookie 设置，不在 body 中
}
```

### POST /api/auth/refresh

```
// refresh_token 从 Cookie 读取（httpOnly），不需要 body
// 响应同 login
```

---

## 开发/调试规范

### 开发环境 error detail

```python
# 仅在 DEBUG=true 时返回 detail
if settings.DEBUG:
    error_response["error"]["detail"] = {
        "traceback": traceback.format_exc()
    }
```

### 请求日志

每个请求记录：method + path + tenant_id + status_code + latency_ms

```
INFO  POST /api/bots tenant_id=abc123 status=201 latency=42ms
INFO  WS   /api/chat/bot_xxx tenant_id=abc123 grader=0.82 tokens=234 latency=1840ms
```

### API 版本

当前无版本前缀（`/api/`）。引入破坏性变更时迁移到 `/api/v2/`。不要过早版本化。
