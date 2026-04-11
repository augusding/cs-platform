# 安全规范

> 所有开发必须遵守。P0 条目上线前必须完成，P1 在 Week 7 统一实现。

---

## 沙箱架构

系统存在三类攻击面，对应三层沙箱：

| 攻击面 | 沙箱层 | 位置 |
|--------|--------|------|
| 上传文件（PDF/Excel） | 文件解析隔离 | RQ Worker 独立进程 |
| 用户对话输入 | Prompt 注入过滤 | core/engine.py 入口 |
| LLM 生成输出 | 输出内容过滤 | PostProcess 节点（Week 7） |

---

## 文件安全规则（P0，已实现）

- 单文件最大 **20MB**，超限返回 413
- 允许类型白名单：`.pdf` / `.xlsx` / `.xls` / `.docx` / `.doc`
- 保存路径：`data/uploads/{uuid}{suffix}`，绝对不含原始文件名
- 解析在 RQ Worker 独立进程执行，崩溃不影响 API 主进程
- 只提取文本，pdfplumber/openpyxl/python-docx 不执行任何宏或脚本

---

## Prompt 注入防御（P0，已实现）

`core/engine.py` 入口的 `sanitize_input()` 执行：
1. 过滤常见注入模式（ignore/forget/disregard 等）
2. 截断超长输入（2000 字符）
3. Strip HTML 标签和控制字符

System/User 角色严格分离，用户内容只放 user 角色，不能修改 system prompt。

---

## LLM 输出内容安全

| 过滤层 | 目标 | 状态 |
|--------|------|------|
| HallucinationChecker | 无依据回答 → clarify | ✅ 已实现 |
| 敏感词过滤 | 政治敏感/竞品负面 | ⏳ Week 7 |
| PII 检测 | 手机号/身份证泄露 | ⏳ Week 7 |

---

## 上线前安全检查清单

- [ ] JWT_SECRET 已从默认值更改（>= 32字符）
- [ ] .env 未提交到 git（`git log --all -- .env` 应无结果）
- [ ] API Key 未硬编码（`grep -r "sk-" --include="*.py"` 应无结果）
- [ ] test_tenant_isolation.py 全部通过
- [ ] 上传 >20MB 文件返回 413
- [ ] 上传 .exe 返回 400
- [ ] 发送 Prompt 注入 payload 被过滤
- [ ] API 限流启用，超限返回 429
- [ ] 生产环境 WIDGET_ALLOWED_ORIGINS 非 *
- [ ] 所有接口强制 HTTPS

---

## 禁止事项

- 禁止用户输入直接拼接进 system prompt
- 禁止文件解析在 API 主进程同步执行
- 禁止跳过文件类型/大小校验
- 禁止 API Key 硬编码在任何源代码文件
- 禁止在没有 tenant_id 过滤的情况下返回数据
