"""生产前安全检查清单。

运行：python tests/security_check.py
在 CI 或部署前执行，确保所有关键安全项达标。
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
passed = 0
failed = 0


def check(name: str, ok: bool, fix: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        if fix:
            print(f"        修复：{fix}")


# ── 1. .env 未提交到 git ────────────────────────────────
result = subprocess.run(
    ["git", "log", "--all", "--", ".env"],
    capture_output=True, text=True, cwd=ROOT,
)
check(
    ".env 未提交到 git",
    result.returncode == 0 and not result.stdout.strip(),
    "git rm --cached .env 且确认 .gitignore 包含 .env",
)

# ── 2. API Key / JWT secret 未硬编码 ───────────────────
EXCLUDE_DIRS = {".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".git"}
EXCLUDE_FILES = {"security_check.py"}  # this scanner contains the patterns
SECRETS_PATTERNS = ("sk-", "sk_live_", "Bearer sk-")
hardcoded: list[Path] = []
for p in ROOT.rglob("*.py"):
    if any(part in EXCLUDE_DIRS for part in p.parts):
        continue
    if p.name in EXCLUDE_FILES:
        continue
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if any(kw in text for kw in SECRETS_PATTERNS):
        hardcoded.append(p)
check(
    "API Key 未硬编码在 .py 文件",
    not hardcoded,
    f"发现疑似硬编码：{[str(p.relative_to(ROOT)) for p in hardcoded]}",
)

# ── 3. JWT_SECRET 已从默认值更改 ────────────────────────
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
jwt_secret = os.getenv("JWT_SECRET", "")
check(
    "JWT_SECRET 已更改为非默认值",
    jwt_secret and jwt_secret != "dev-secret-change-in-production",
    "在 .env 中设置强随机 JWT_SECRET（建议 >= 32 字符）",
)
check(
    "JWT_SECRET 长度 >= 32",
    len(jwt_secret) >= 32,
    "openssl rand -hex 32 生成长密钥",
)

# ── 4. DEBUG=false（仅警告，dev 环境可跳过） ────────────
debug = os.getenv("DEBUG", "true").lower() == "true"
check(
    "生产环境 DEBUG=false",
    not debug,
    "部署到生产前在 .env 设 DEBUG=false",
)

# ── 5. requirements.txt 固定 marshmallow 版本 ──────────
req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
check(
    "marshmallow<3.13 已固定",
    "marshmallow<3.13" in req,
    "在 requirements.txt 添加 marshmallow<3.13",
)

# ── 6. sanitize_input 已集成到 engine ──────────────────
engine = (ROOT / "core" / "engine.py").read_text(encoding="utf-8")
check(
    "sanitize_input 已集成",
    "sanitize_input(user_query)" in engine,
    "在 core/engine.py 的 run_pipeline 入口调用 sanitize_input",
)

# ── 7. 租户隔离测试存在 ─────────────────────────────────
check(
    "tests/test_tenant_isolation.py 存在",
    (ROOT / "tests" / "test_tenant_isolation.py").exists(),
)

# ── 8. RLS 迁移存在 ─────────────────────────────────────
migrations = list((ROOT / "migrations" / "versions").glob("*.py"))
rls_exists = any("enable_rls" in p.name.lower() for p in migrations)
check(
    "PostgreSQL RLS 迁移已创建",
    rls_exists,
    "生成 alembic 迁移启用 Row-Level Security",
)

# ── 9. 审计日志迁移存在 ─────────────────────────────────
audit_exists = any("audit_log" in p.name.lower() for p in migrations)
check(
    "审计日志表迁移已创建",
    audit_exists,
)

# ── 10. CORS 未设为通配（生产） ──────────────────────────
origins = os.getenv("WIDGET_ALLOWED_ORIGINS", "*")
check(
    "生产环境 WIDGET_ALLOWED_ORIGINS 非 '*'",
    origins != "*",
    "生产部署时在 .env 设置具体域名列表",
)

print(
    f"\n  安全检查：{passed + failed} 项，{passed} 通过，{failed} 问题"
)
sys.exit(0 if failed == 0 else 1)
