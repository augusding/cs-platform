"""
租户隔离回归测试（CLAUDE.md 强制要求）。
验证企业 A 的 JWT 无法访问企业 B 的资源。
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiohttp
import asyncpg

from config import settings

BASE = "http://localhost:8080"

TEST_EMAILS = (
    "tenant_iso_a@example.com",
    "tenant_iso_b@example.com",
)


async def _cleanup() -> None:
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        await conn.execute(
            "DELETE FROM tenants WHERE id IN "
            "(SELECT tenant_id FROM users WHERE email = ANY($1::text[]))",
            list(TEST_EMAILS),
        )
    finally:
        await conn.close()


async def run() -> bool:
    await _cleanup()
    passed = 0
    failed = 0

    def ok(name: str) -> None:
        nonlocal passed
        passed += 1
        print(f"  PASS  {name}")

    def fail(name: str, why: str) -> None:
        nonlocal failed
        failed += 1
        print(f"  FAIL  {name}: {why}")

    async with aiohttp.ClientSession() as s:
        # Register A and B
        ra = await s.post(f"{BASE}/api/auth/register", json={
            "company_name": "Tenant A Co",
            "name": "Alice",
            "email": TEST_EMAILS[0],
            "password": "isolation_test_pw",
        })
        body_a = await ra.json()
        if ra.status != 201:
            fail("register A", f"status={ra.status}")
            return False
        token_a = body_a["data"]["access_token"]
        ok("register tenant A")

        rb = await s.post(f"{BASE}/api/auth/register", json={
            "company_name": "Tenant B Co",
            "name": "Bob",
            "email": TEST_EMAILS[1],
            "password": "isolation_test_pw",
        })
        body_b = await rb.json()
        if rb.status != 201:
            fail("register B", f"status={rb.status}")
            return False
        token_b = body_b["data"]["access_token"]
        ok("register tenant B")

        H_a = {"Authorization": f"Bearer {token_a}"}
        H_b = {"Authorization": f"Bearer {token_b}"}

        # A creates a bot
        rc = await s.post(
            f"{BASE}/api/bots",
            json={"name": "A Secret Bot", "language": "zh"},
            headers=H_a,
        )
        if rc.status != 201:
            fail("A create bot", f"status={rc.status}")
            return False
        bot_a_id = (await rc.json())["data"]["id"]
        ok("tenant A creates bot")

        # B lists /api/bots — must not see A's bot
        rl = await s.get(f"{BASE}/api/bots", headers=H_b)
        bots_b = (await rl.json())["data"]
        if any(b["id"] == bot_a_id for b in bots_b):
            fail("cross-tenant list leak", "B sees A's bot in /api/bots")
        else:
            ok("tenant B list hides tenant A bots")

        # B tries GET /api/bots/{bot_a_id} — must fail
        rg = await s.get(f"{BASE}/api/bots/{bot_a_id}", headers=H_b)
        if rg.status == 403:
            ok("GET cross-tenant bot -> 403")
        else:
            fail("cross-tenant get", f"status={rg.status}, expected 403")

        # B tries PUT (rename) A's bot — must fail
        rp = await s.put(
            f"{BASE}/api/bots/{bot_a_id}",
            json={"name": "hacked"},
            headers=H_b,
        )
        if rp.status == 403:
            ok("PUT cross-tenant bot -> 403")
        else:
            fail("cross-tenant update", f"status={rp.status}, expected 403")

        # B tries DELETE A's bot — must fail
        rd = await s.delete(f"{BASE}/api/bots/{bot_a_id}", headers=H_b)
        if rd.status == 403:
            ok("DELETE cross-tenant bot -> 403")
        else:
            fail("cross-tenant delete", f"status={rd.status}, expected 403")

        # Admin sessions: B should see 0 rows belonging to A
        rs = await s.get(f"{BASE}/api/admin/sessions?page=1&page_size=50", headers=H_b)
        if rs.status == 200:
            data = (await rs.json())["data"]
            if all(str(row.get("bot_id")) != bot_a_id for row in data):
                ok("admin/sessions tenant-scoped")
            else:
                fail("admin/sessions leak", "B sees rows with A's bot_id")
        else:
            fail("admin/sessions", f"status={rs.status}")

        # Cleanup A's bot via A's own token
        await s.delete(f"{BASE}/api/bots/{bot_a_id}", headers=H_a)

    print(f"\n  {passed + failed} tests, {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    result = asyncio.run(run())
    sys.exit(0 if result else 1)
