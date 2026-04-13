"""
CS Platform 端到端自动化测试 v2
单轮用例（独立 session）+ 多轮对话（共享 session）+ 幻觉测试
用法：PYTHONIOENCODING=utf-8 python tests/e2e_auto_test.py
"""
import asyncio
import json
import sys
import os
import time
import aiohttp
import asyncpg

API_BASE = "http://localhost:8081"
DB_URL = "postgresql://cs_user:cs_pass@localhost:5432/cs_platform"
KB_FILE = os.path.join(os.path.dirname(__file__), "test_product_kb.txt")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "e2e_test_results.md")

TEST_EMAIL = "admin@example.com"
TEST_PASSWORD = "admin1234"


# ── 单轮用例 ────────────────────────────────────────────
SINGLE_TURN_CASES = [
    # L1 对话层
    {"id": "S01", "query": "你好", "category": "L1", "expected_intent": "greeting", "should_not_contain": ["转接", "人工"]},
    {"id": "S02", "query": "你是谁", "category": "L1", "expected_intent": "bot_identity", "should_not_contain": ["转接"]},
    {"id": "S03", "query": "你能做什么？", "category": "L1", "expected_intent": "capability", "should_not_contain": ["需要为您转接"]},
    {"id": "S04", "query": "你是人工还是机器人？", "category": "L1", "expected_intent": "bot_identity", "should_not_contain": ["转接人工客服"]},
    {"id": "S05", "query": "谢谢", "category": "L1", "expected_intent": "farewell", "should_not_contain": ["转接"]},

    # L2 产品咨询
    {"id": "S06", "query": "你们有哪些产品？", "category": "L2", "expected_intent": "product_info", "should_contain_any": ["StarPods", "StarWatch", "StarPower"]},
    {"id": "S07", "query": "StarPods Pro 多少钱？", "category": "L2", "expected_intent": "price_inquiry", "should_contain_any": ["45.99", "45"]},
    {"id": "S08", "query": "StarPods Pro 多少钱？批量价呢？", "category": "L2", "expected_intent": "price_inquiry", "should_contain_any": ["28", "24", "21"]},
    {"id": "S09", "query": "有没有防水的运动耳机？", "category": "L2", "expected_intent": "product_info", "should_contain_any": ["IP67", "Sport", "SS-300"]},
    {"id": "S10", "query": "SP-100 和 SL-200 有什么区别？", "category": "L2", "expected_intent": "comparison", "should_contain_any": ["SP-100", "SL-200"]},
    {"id": "S11", "query": "智能手表续航多久？", "category": "L2", "expected_intent": "product_info", "should_contain_any": ["7", "天"]},
    {"id": "S12", "query": "充电宝支持快充吗？", "category": "L2", "expected_intent": "product_info", "should_contain_any": ["PD", "QC", "22.5"]},
    {"id": "S13", "query": "交货期大概多久？", "category": "L2", "expected_intent": "availability", "should_contain_any": ["工作日", "天"]},
    {"id": "S14", "query": "怎么付款？支持信用证吗？", "category": "L2", "expected_intent": "policy_query", "should_contain_any": ["L/C", "T/T", "PayPal"]},
    {"id": "S15", "query": "可以定制 LOGO 吗？", "category": "L2", "expected_intent": "product_info", "should_contain_any": ["丝印", "UV", "激光"]},

    # L2 英文
    {"id": "S16", "query": "What products do you have?", "category": "EN", "expected_intent": "product_info", "should_contain_any": ["StarPods", "StarWatch"]},
    {"id": "S17", "query": "How much is StarPods Pro?", "category": "EN", "expected_intent": "price_inquiry", "should_contain_any": ["45.99", "45"]},
    {"id": "S18", "query": "What's your MOQ for the smartwatch?", "category": "EN", "expected_intent": "price_inquiry", "should_contain_any": ["300"]},
    {"id": "S19", "query": "Can you ship to the US?", "category": "EN", "expected_intent": "availability", "should_contain_any": ["DHL", "FedEx", "ship"]},
    {"id": "S20", "query": "Do you support OEM customization?", "category": "EN", "expected_intent": "product_info", "should_contain_any": ["OEM", "custom"]},

    # L4 异常处理
    {"id": "S21", "query": "我要投诉！你们产品质量太差了！", "category": "L4", "expected_intent": "complaint"},
    {"id": "S22", "query": "我订单号 2024001 物流到哪了？", "category": "L4", "expected_intent": ["availability", "policy_query", "follow_up", "clarification"]},

    # L5 边界
    {"id": "S23", "query": "产品坏了怎么办？", "category": "L4", "expected_intent": ["complaint", "policy_query"], "should_contain_any": ["保修", "维修", "DOA"]},
    {"id": "S24", "query": "帮我写一首诗", "category": "L5", "expected_intent": "out_of_scope"},
    {"id": "S25", "query": "你们的股票代码是多少？", "category": "L5", "expected_intent": "out_of_scope"},

    # 幻觉诱导
    {"id": "S26", "query": "SL-900 价格多少？", "category": "HALLU",
     "should_not_contain": ["SL-900的零售价", "SL-900 零售价"],
     "should_contain_any": ["没有", "不存在", "未找到", "暂时无", "确认", "团队"]},
    {"id": "S27", "query": "你们有没有VR眼镜？", "category": "HALLU",
     "should_not_contain": ["我们的VR眼镜", "VR眼镜的价格"],
     "should_contain_any": ["没有", "目前不", "不在", "暂时没", "不提供"]},
    {"id": "S28", "query": "你们的代理政策是什么？返点多少？", "category": "HALLU",
     "should_not_contain": ["返点", "独家", "区域保护"],
     "should_contain_any": ["确认", "业务团队", "联系", "了解"]},
    {"id": "S29", "query": "西班牙可以做独家代理吗？给多少返点？", "category": "HALLU",
     "should_not_contain": ["可以做独家", "返点"],
     "should_contain_any": ["确认", "业务团队", "联系"]},
    {"id": "S30", "query": "签独家代理协议的条件是什么？", "category": "HALLU",
     "should_not_contain": ["独家代理协议条款", "独家代理的条件"],
     "should_contain_any": ["确认", "业务团队", "联系"]},
]


# ── 多轮用例 ────────────────────────────────────────────
MULTI_TURN_CASES = [
    {
        "id": "M01",
        "name": "产品咨询追问链",
        "turns": [
            {"query": "你们有什么蓝牙耳机？", "should_contain_any": ["StarPods"]},
            {"query": "Pro 那款多少钱？", "should_contain_any": ["45", "28", "24", "21"]},
            {"query": "那运动款呢？", "should_contain_any": ["35.99", "Sport", "35"]},
            {"query": "有防水吗？", "should_contain_any": ["IP67", "防水"]},
        ],
    },
    {
        "id": "M02",
        "name": "AI追问-用户回答（上下文理解）",
        "turns": [
            {"query": "智能手表的价格？", "should_contain_any": ["89.99", "89"]},
            {"query": "大概500台", "should_contain_any": ["500", "52"],
             "should_not_contain": ["请问您想咨询的是哪款产品", "请问您需要什么产品"]},
        ],
    },
    {
        "id": "M03",
        "name": "情绪升级-主动安抚",
        "turns": [
            {"query": "你们有代理政策吗？", "should_contain_any": ["确认", "业务", "合作", "OEM", "联系"]},
            {"query": "太傻了算了", "should_contain_any": ["抱歉", "理解", "人工", "客服"]},
        ],
    },
    {
        "id": "M04",
        "name": "重复回答检测",
        "turns": [
            {"query": "你们支持区域代理吗？"},
            {"query": "我问的是能不能做代理"},
        ],
        "check_dedup": True,
    },
    {
        "id": "M05",
        "name": "Lead capture首消息预提取",
        "turns": [
            {"query": "我想订购2000台SP-100，要印我们的LOGO",
             "should_not_contain": ["请问您需要什么产品", "请问产品需求"]},
        ],
    },
    {
        "id": "M06",
        "name": "语言切换",
        "turns": [
            {"query": "你们有什么产品？", "should_contain_any": ["StarPods"]},
            {"query": "Tell me about StarPods Pro briefly", "should_contain_any": ["StarPods Pro", "ANC"]},
        ],
    },
]


# ── 工具函数 ────────────────────────────────────────────

def similarity(a: str, b: str) -> float:
    """简单 Jaccard 相似度"""
    if not a or not b:
        return 0.0
    sa = set(a)
    sb = set(b)
    return len(sa & sb) / max(len(sa | sb), 1)


def check_turn(answer: str, turn: dict) -> list[dict]:
    checks = []
    answer_lc = answer.lower()
    for kw in turn.get("should_contain", []):
        checks.append({
            "type": "contain",
            "keyword": kw,
            "pass": kw.lower() in answer_lc,
        })
    for kw in turn.get("should_not_contain", []):
        checks.append({
            "type": "not_contain",
            "keyword": kw,
            "pass": kw.lower() not in answer_lc,
        })
    if turn.get("should_contain_any"):
        any_found = any(kw.lower() in answer_lc for kw in turn["should_contain_any"])
        checks.append({
            "type": "contain_any",
            "keywords": turn["should_contain_any"],
            "pass": any_found,
        })
    return checks


class E2ETest:
    def __init__(self):
        self.token = ""
        self.bot_id = ""
        self.bot_api_key = ""
        self.single_results: list[dict] = []
        self.multi_results: list[dict] = []
        self.session: aiohttp.ClientSession | None = None

    async def run(self):
        print("=" * 60)
        print("CS Platform 端到端自动化测试 v2")
        print("=" * 60)

        await self.upgrade_tenant_plan()

        async with aiohttp.ClientSession() as session:
            self.session = session
            await self.login()
            await self.create_bot()

            print("\n[Single-turn] 运行 30 个单轮用例...")
            print("-" * 80)
            for tc in SINGLE_TURN_CASES:
                r = await self._run_single(tc)
                self.single_results.append(r)
                self._print_single(r)
                await asyncio.sleep(0.3)

            print("\n[Multi-turn] 运行 6 个多轮对话...")
            print("-" * 80)
            for tc in MULTI_TURN_CASES:
                r = await self._run_multi(tc)
                self.multi_results.append(r)
                self._print_multi(r)
                await asyncio.sleep(0.5)

        self.generate_report()
        print("\n" + "=" * 60)
        print("测试完成！报告:", REPORT_FILE)
        print("=" * 60)

    async def upgrade_tenant_plan(self):
        print("\n[0] 升级租户套餐...")
        try:
            conn = await asyncpg.connect(DB_URL)
            await conn.execute("UPDATE tenants SET plan='pro', max_bots=10 WHERE plan='free'")
            await conn.close()
            print("    ok")
        except Exception as e:
            print(f"    warn: {e}")

    async def login(self):
        print("\n[1] 登录...")
        for pwd in [TEST_PASSWORD, "testpass123", "test123456", "admin123"]:
            r = await self.session.post(f"{API_BASE}/api/auth/login", json={"email": TEST_EMAIL, "password": pwd})
            if r.status == 200:
                d = await r.json()
                self.token = d["data"]["access_token"]
                print(f"    ok: {TEST_EMAIL}")
                return
        print("    FAIL: no password worked")
        sys.exit(1)

    def _h(self):
        return {"Authorization": f"Bearer {self.token}"}

    async def create_bot(self):
        print("\n[2] 获取测试 Bot...")
        r = await self.session.get(f"{API_BASE}/api/bots", headers=self._h())
        bots = (await r.json()).get("data", [])
        for b in bots:
            if "星辰" in (b.get("name") or ""):
                self.bot_id = b["id"]
                break
        if not self.bot_id and bots:
            self.bot_id = bots[0]["id"]
        if not self.bot_id:
            print("    FAIL: no bot")
            sys.exit(1)

        # Get API key
        r = await self.session.post(f"{API_BASE}/api/bots/{self.bot_id}/reveal-key", headers=self._h())
        if r.status == 200:
            d = await r.json()
            self.bot_api_key = d["data"]["bot_api_key"]
        print(f"    bot: {self.bot_id[:8]}")

    async def _run_single(self, tc: dict) -> dict:
        """单轮用例走 admin debug WS"""
        result = {
            "id": tc["id"],
            "query": tc["query"],
            "category": tc["category"],
            "expected_intent": tc.get("expected_intent", ""),
            "actual_intent": "",
            "latency_ms": 0,
            "answer": "",
            "checks": [],
            "pass": True,
            "error": "",
        }
        try:
            ws_url = f"ws://localhost:8081/api/admin/debug/{self.bot_id}?token={self.token}"
            async with self.session.ws_connect(ws_url, timeout=60) as ws:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=10)
                if msg.get("type") != "connected":
                    result["error"] = f"unexpected: {msg.get('type')}"
                    result["pass"] = False
                    return result

                await ws.send_json({"type": "message", "content": tc["query"]})

                answer_parts = []
                debug_info = {}
                while True:
                    try:
                        m = await asyncio.wait_for(ws.receive_json(), timeout=60)
                    except asyncio.TimeoutError:
                        result["error"] = "timeout"
                        break
                    if m["type"] == "token":
                        answer_parts.append(m.get("content", ""))
                    elif m["type"] == "done":
                        debug_info = m.get("debug", {})
                        result["latency_ms"] = m.get("latency_ms", 0)
                        break
                    elif m["type"] == "error":
                        result["error"] = m.get("message", "")
                        break

                result["answer"] = "".join(answer_parts)
                result["actual_intent"] = debug_info.get("intent", "")

                # 关键字检查
                result["checks"] = check_turn(result["answer"], tc)
                all_passed = all(c["pass"] for c in result["checks"])

                # 意图检查：支持 string 或 list[str]
                intent_ok = True
                expected = tc.get("expected_intent")
                if expected:
                    if isinstance(expected, str):
                        intent_ok = self._intent_match(expected, result["actual_intent"])
                    else:
                        # list: 任一匹配即可（严格或同层级宽松）
                        intent_ok = any(
                            self._intent_match(e, result["actual_intent"])
                            for e in expected
                        )
                    result["intent_ok"] = intent_ok

                result["pass"] = all_passed and intent_ok and not result["error"]
        except Exception as e:
            result["error"] = str(e)[:200]
            result["pass"] = False
        return result

    def _intent_match(self, expected: str, actual: str) -> bool:
        if expected == actual:
            return True
        groups = [
            {"greeting", "farewell", "acknowledgment", "bot_identity", "capability", "chitchat"},
            {"product_info", "price_inquiry", "availability", "how_to_use", "policy_query", "comparison"},
            {"purchase_intent", "bulk_inquiry", "custom_request", "lead_capture"},
            {"complaint", "urgent", "transfer_explicit", "transfer_implicit"},
        ]
        for g in groups:
            if expected in g and actual in g:
                return True
        return False

    def _print_single(self, r: dict):
        icon = "✓" if r["pass"] else "✗"
        intent = r.get("actual_intent", "")[:18]
        checks_brief = f"{sum(1 for c in r['checks'] if c['pass'])}/{len(r['checks'])}" if r["checks"] else "—"
        print(f"  {r['id']} [{r['category']:5s}] {icon} intent={intent:<18s} checks={checks_brief} {r['latency_ms']}ms")
        if not r["pass"]:
            failed = [c for c in r["checks"] if not c["pass"]]
            for f in failed:
                kw = f.get("keyword") or f.get("keywords", "")
                print(f"       ✗ {f['type']}: {kw}")
            if r["error"]:
                print(f"       ERROR: {r['error']}")

    async def _run_multi(self, tc: dict) -> dict:
        """多轮用例：共享同一个 WS session"""
        result = {
            "id": tc["id"],
            "name": tc["name"],
            "turns": [],
            "pass": True,
            "error": "",
        }
        try:
            ws_url = f"ws://localhost:8081/api/admin/debug/{self.bot_id}?token={self.token}"
            async with self.session.ws_connect(ws_url, timeout=60) as ws:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=10)
                if msg.get("type") != "connected":
                    result["error"] = f"unexpected: {msg.get('type')}"
                    result["pass"] = False
                    return result

                prev_answer = ""
                for i, turn in enumerate(tc["turns"]):
                    await ws.send_json({"type": "message", "content": turn["query"]})

                    answer_parts = []
                    while True:
                        try:
                            m = await asyncio.wait_for(ws.receive_json(), timeout=60)
                        except asyncio.TimeoutError:
                            break
                        if m["type"] == "token":
                            answer_parts.append(m.get("content", ""))
                        elif m["type"] == "done":
                            break
                        elif m["type"] == "error":
                            break
                        elif m["type"] == "transfer":
                            answer_parts.append(" [TRANSFER] ")
                        # ignore private_domain and other frames

                    answer = "".join(answer_parts)
                    turn_result = {
                        "turn": i + 1,
                        "query": turn["query"],
                        "answer": answer[:200],
                        "checks": check_turn(answer, turn),
                        "pass": True,
                    }
                    turn_result["pass"] = all(c["pass"] for c in turn_result["checks"])

                    # Dedup check
                    if tc.get("check_dedup") and i > 0:
                        sim = similarity(prev_answer, answer)
                        turn_result["similarity_to_prev"] = round(sim, 2)
                        if sim > 0.90:
                            turn_result["checks"].append({
                                "type": "dedup",
                                "pass": False,
                                "keyword": f"similarity={sim:.2f} > 0.9",
                            })
                            turn_result["pass"] = False

                    if not turn_result["pass"]:
                        result["pass"] = False
                    result["turns"].append(turn_result)
                    prev_answer = answer
                    await asyncio.sleep(0.3)
        except Exception as e:
            result["error"] = str(e)[:200]
            result["pass"] = False
        return result

    def _print_multi(self, r: dict):
        icon = "✓" if r["pass"] else "✗"
        turn_summary = "/".join("✓" if t["pass"] else "✗" for t in r["turns"])
        print(f"  {r['id']} {icon} {r['name']} [{turn_summary}]")
        for t in r["turns"]:
            if not t["pass"]:
                for c in t["checks"]:
                    if not c["pass"]:
                        kw = c.get("keyword") or c.get("keywords", "")
                        print(f"       T{t['turn']} ✗ {c['type']}: {kw}")
                        print(f"            answer: {t['answer'][:100]}")
        if r["error"]:
            print(f"       ERROR: {r['error']}")

    def generate_report(self):
        single_pass = sum(1 for r in self.single_results if r["pass"])
        multi_total_turns = sum(len(r["turns"]) for r in self.multi_results)
        multi_pass_turns = sum(sum(1 for t in r["turns"] if t["pass"]) for r in self.multi_results)
        multi_case_pass = sum(1 for r in self.multi_results if r["pass"])

        hallu_results = [r for r in self.single_results if r["category"] == "HALLU"]
        hallu_pass = sum(1 for r in hallu_results if r["pass"])

        lines = [
            "# E2E Test Report v2",
            f"Date: {time.strftime('%Y-%m-%d %H:%M')}",
            f"Bot ID: {self.bot_id}",
            "",
            "## Summary",
            f"- **Single-turn**: {single_pass}/{len(self.single_results)} pass ({single_pass/max(len(self.single_results),1)*100:.0f}%)",
            f"- **Multi-turn cases**: {multi_case_pass}/{len(self.multi_results)} full pass",
            f"- **Multi-turn turns**: {multi_pass_turns}/{multi_total_turns} turns pass",
            f"- **Hallucination tests**: {hallu_pass}/{len(hallu_results)} pass",
            "",
            "## Single-turn Results",
            "",
            "| ID | Category | Query | Intent | Checks | Latency | Pass |",
            "|----|---|---|---|---|---|---|",
        ]
        for r in self.single_results:
            q = r["query"][:30].replace("|", "\\|")
            ck = f"{sum(1 for c in r['checks'] if c['pass'])}/{len(r['checks'])}" if r["checks"] else "—"
            icon = "✓" if r["pass"] else "✗"
            lines.append(f"| {r['id']} | {r['category']} | {q} | {r['actual_intent']} | {ck} | {r['latency_ms']}ms | {icon} |")

        lines.extend(["", "## Multi-turn Results", ""])
        for r in self.multi_results:
            icon = "✓" if r["pass"] else "✗"
            lines.append(f"### {r['id']} {r['name']} {icon}")
            lines.append("")
            for t in r["turns"]:
                tick = "✓" if t["pass"] else "✗"
                lines.append(f"- **T{t['turn']}** {tick} `{t['query']}`")
                ans = t["answer"][:120].replace("\n", " ")
                lines.append(f"  - answer: {ans}")
                for c in t["checks"]:
                    if not c["pass"]:
                        kw = c.get("keyword") or c.get("keywords", "")
                        lines.append(f"  - FAIL {c['type']}: {kw}")
                if t.get("similarity_to_prev") is not None:
                    lines.append(f"  - similarity_to_prev: {t['similarity_to_prev']}")
            lines.append("")

        failed_single = [r for r in self.single_results if not r["pass"]]
        if failed_single:
            lines.extend(["## Failed Single-turn Cases", ""])
            for r in failed_single:
                lines.append(f"- **{r['id']}** `{r['query']}`")
                lines.append(f"  - answer: {r['answer'][:150]}")
                for c in r["checks"]:
                    if not c["pass"]:
                        kw = c.get("keyword") or c.get("keywords", "")
                        lines.append(f"  - FAIL {c['type']}: {kw}")
                if r["error"]:
                    lines.append(f"  - error: {r['error']}")
            lines.append("")

        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"\n{'=' * 60}")
        print(f"  Single-turn:  {single_pass}/{len(self.single_results)} ({single_pass/max(len(self.single_results),1)*100:.0f}%)")
        print(f"  Multi-turn:   {multi_case_pass}/{len(self.multi_results)} cases, {multi_pass_turns}/{multi_total_turns} turns")
        print(f"  Hallucination: {hallu_pass}/{len(hallu_results)}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(E2ETest().run())
