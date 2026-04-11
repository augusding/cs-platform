"""
Auth 系统全链路测试。
直接调用 HTTP 接口，不 mock，测真实 DB + Redis。
运行前确保：docker-compose up -d 且 python main.py serve 已启动。
"""
import asyncio
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp
import asyncpg

from config import settings

BASE = "http://localhost:8080"

TEST_EMAILS = (
    "test_a@example.com",
    "test_b@example.com",
    "member@example.com",
)
TEST_TENANT_NAMES = ("测试企业A", "测试企业B", "另一家企业")


async def cleanup_test_data() -> None:
    """删除上次测试遗留的数据，使测试可重复运行。"""
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        await conn.execute(
            "DELETE FROM tenants WHERE id IN "
            "(SELECT tenant_id FROM users WHERE email = ANY($1::text[]))",
            list(TEST_EMAILS),
        )
        await conn.execute(
            "DELETE FROM tenants WHERE name = ANY($1::text[])",
            list(TEST_TENANT_NAMES),
        )
    finally:
        await conn.close()


async def post(session, path, data=None, cookies=None, headers=None):
    resp = await session.post(
        f"{BASE}{path}",
        json=data,
        cookies=cookies,
        headers=headers,
    )
    try:
        body = await resp.json()
    except Exception:
        body = {"_raw": await resp.text()}
    return resp.status, body, resp.cookies


def decode_jwt_payload(token: str) -> dict:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


async def run_tests() -> bool:
    await cleanup_test_data()

    passed = 0
    failed = 0

    def ok(name: str) -> None:
        nonlocal passed
        passed += 1
        print(f"  PASS  {name}")

    def fail(name: str, reason: str) -> None:
        nonlocal failed
        failed += 1
        print(f"  FAIL  {name}: {reason}")

    # DummyCookieJar ensures only explicitly-passed cookies are sent,
    # so old-token revocation checks are not masked by the session jar.
    jar = aiohttp.DummyCookieJar()
    async with aiohttp.ClientSession(cookie_jar=jar) as s:

        # ── 1. 注册企业A ─────────────────────────────────
        status, body, cookies = await post(s, "/api/auth/register", {
            "company_name": "测试企业A",
            "name": "张三",
            "email": "test_a@example.com",
            "password": "testpass123",
        })
        if status == 201 and "access_token" in body.get("data", {}):
            ok("注册企业A 返回201和access_token")
        else:
            fail("注册企业A", f"status={status} body={body}")

        token_a = body.get("data", {}).get("access_token", "")

        # ── 2. 重复注册同邮箱 → 409 ──────────────────────
        status, body, _ = await post(s, "/api/auth/register", {
            "company_name": "另一家企业",
            "name": "李四",
            "email": "test_a@example.com",
            "password": "testpass123",
        })
        if status == 409:
            ok("重复注册同邮箱 返回409")
        else:
            fail("重复注册同邮箱", f"status={status}")

        # ── 3. 注册企业B ─────────────────────────────────
        status, body, _ = await post(s, "/api/auth/register", {
            "company_name": "测试企业B",
            "name": "王五",
            "email": "test_b@example.com",
            "password": "testpass456",
        })
        if status == 201:
            ok("注册企业B 返回201")
        else:
            fail("注册企业B", f"status={status}")

        token_b = body.get("data", {}).get("access_token", "")

        # ── 4. 密码错误登录 → 401 ────────────────────────
        status, body, _ = await post(s, "/api/auth/login", {
            "email": "test_a@example.com",
            "password": "wrongpassword",
        })
        if status == 401:
            ok("密码错误登录 返回401")
        else:
            fail("密码错误登录", f"status={status}")

        # ── 5. 正确登录 ───────────────────────────────────
        status, body, new_cookies = await post(s, "/api/auth/login", {
            "email": "test_a@example.com",
            "password": "testpass123",
        })
        if status == 200 and "access_token" in body.get("data", {}):
            ok("正确登录 返回200和access_token")
        else:
            fail("正确登录", f"status={status} body={body}")

        new_refresh = new_cookies.get("cs_refresh_token")

        # ── 6. 刷新 token ─────────────────────────────────
        if new_refresh:
            status, body, _ = await post(
                s, "/api/auth/refresh",
                cookies={"cs_refresh_token": new_refresh.value},
            )
            if status == 200 and "access_token" in body.get("data", {}):
                ok("刷新token 返回200和新access_token")
            else:
                fail("刷新token", f"status={status} body={body}")
        else:
            fail("刷新token", "未收到refresh cookie")

        # ── 7. 旧 refresh token 不能再用 → 401 ───────────
        if new_refresh:
            status, body, _ = await post(
                s, "/api/auth/refresh",
                cookies={"cs_refresh_token": new_refresh.value},
            )
            if status == 401:
                ok("旧refresh token已失效 返回401")
            else:
                fail("旧refresh token轮换", f"status={status} 应为401")

        # ── 8. 邀请成员（需要 admin+ JWT）────────────────
        headers_a = {"Authorization": f"Bearer {token_a}"}
        status, body, _ = await post(
            s, "/api/auth/invite",
            data={"email": "member@example.com", "role": "operator"},
            headers=headers_a,
        )
        if status == 201 and "token" in body.get("data", {}):
            ok("邀请成员 返回201和invitation token")
            invite_token = body["data"]["token"]
        else:
            fail("邀请成员", f"status={status} body={body}")
            invite_token = None

        # ── 9. 接受邀请 ───────────────────────────────────
        if invite_token:
            status, body, _ = await post(s, "/api/auth/invite/accept", {
                "token": invite_token,
                "name": "新成员",
                "password": "newpass123",
            })
            if status == 201 and "access_token" in body.get("data", {}):
                ok("接受邀请 返回201和access_token")
            else:
                fail("接受邀请", f"status={status} body={body}")

        # ── 10. 无效邀请 token → 400 ─────────────────────
        status, body, _ = await post(s, "/api/auth/invite/accept", {
            "token": "invalid_token_xxx",
            "name": "黑客",
            "password": "hacker123",
        })
        if status == 400:
            ok("无效邀请token 返回400")
        else:
            fail("无效邀请token", f"status={status}")

        # ── 11. 登出 ──────────────────────────────────────
        if new_refresh:
            status, body, _ = await post(
                s, "/api/auth/logout",
                cookies={"cs_refresh_token": new_refresh.value},
            )
            if status == 200:
                ok("登出 返回200")
            else:
                fail("登出", f"status={status}")

        # ── 12. 租户隔离：JWT tenant_id 不同，角色 super_admin ────
        if token_a and token_b:
            payload_a = decode_jwt_payload(token_a)
            payload_b = decode_jwt_payload(token_b)

            if payload_a.get("tid") != payload_b.get("tid"):
                ok("租户隔离：企业A和B的tenant_id不同")
            else:
                fail("租户隔离", "两个企业的tenant_id相同！")

            if payload_a.get("role") == "super_admin":
                ok("企业A创始人角色为super_admin")
            else:
                fail("角色验证", f"期望super_admin，实际{payload_a.get('role')}")

    print(f"\n  {passed + failed} 个测试，{passed} 通过，{failed} 失败")
    return failed == 0


if __name__ == "__main__":
    result = asyncio.run(run_tests())
    sys.exit(0 if result else 1)
