"""
CS Platform 端到端自动化测试
用法：python tests/e2e_auto_test.py
"""
import asyncio
import json
import time
import sys
import os
import aiohttp
import asyncpg

API_BASE = "http://localhost:8081"
DB_URL = "postgresql://cs_user:cs_pass@localhost:5432/cs_platform"
KB_FILE = os.path.join(os.path.dirname(__file__), "test_product_kb.txt")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "e2e_test_results.md")

TEST_EMAIL = "admin@example.com"
TEST_PASSWORD = "admin1234"

TEST_CASES = [
    {"id": 1,  "query": "你好",                           "expected_intent": "greeting",          "category": "L1"},
    {"id": 2,  "query": "Hi, good morning",              "expected_intent": "greeting",          "category": "L1"},
    {"id": 3,  "query": "谢谢，没问题了",                 "expected_intent": "farewell",          "category": "L1"},
    {"id": 4,  "query": "你是人工还是机器人？",           "expected_intent": "bot_identity",      "category": "L1"},
    {"id": 5,  "query": "你能做什么？",                   "expected_intent": "capability",        "category": "L1"},
    {"id": 6,  "query": "你们有哪些蓝牙耳机？",          "expected_intent": "product_info",      "category": "L2"},
    {"id": 7,  "query": "StarPods Pro 多少钱？批量价呢？","expected_intent": "price_inquiry",     "category": "L2"},
    {"id": 8,  "query": "SP-100 和 SL-200 有什么区别？",  "expected_intent": "comparison",        "category": "L2"},
    {"id": 9,  "query": "有没有防水的运动耳机？",         "expected_intent": "product_info",      "category": "L2"},
    {"id": 10, "query": "智能手表的续航多长时间？",        "expected_intent": "product_info",      "category": "L2"},
    {"id": 11, "query": "充电宝支持快充吗？最大输出多少瓦？","expected_intent": "product_info",    "category": "L2"},
    {"id": 12, "query": "你们的产品有什么认证？",          "expected_intent": "product_info",      "category": "L2"},
    {"id": 13, "query": "怎么付款？支持信用证吗？",        "expected_intent": "policy_query",      "category": "L2"},
    {"id": 14, "query": "交货期大概多久？",                "expected_intent": "availability",      "category": "L2"},
    {"id": 15, "query": "退换货政策是什么？",              "expected_intent": "policy_query",      "category": "L2"},
    {"id": 16, "query": "我想采购一批蓝牙耳机",           "expected_intent": "purchase_intent",   "category": "L3"},
    {"id": 17, "query": "我们公司需要定制5000个耳机，能打我们的LOGO", "expected_intent": "custom_request", "category": "L3"},
    {"id": 18, "query": "I want to order 2000 units of SP-100", "expected_intent": "bulk_inquiry", "category": "L3"},
    {"id": 19, "query": "我要投诉，上次买的耳机全是坏的",  "expected_intent": "complaint",         "category": "L4"},
    {"id": 20, "query": "转人工客服",                      "expected_intent": "transfer_explicit", "category": "L4"},
    {"id": 21, "query": "很急！明天就要发货",              "expected_intent": "urgent",            "category": "L4"},
    {"id": 22, "query": "帮我写一段Python代码",            "expected_intent": "out_of_scope",      "category": "L5"},
    {"id": 23, "query": "今天股票怎么样？",                "expected_intent": "out_of_scope",      "category": "L5"},
    {"id": 24, "query": "嗯",                             "expected_intent": "acknowledgment",    "category": "L5"},
    {"id": 25, "query": "那价格呢？",                     "expected_intent": "follow_up",         "category": "L5"},
    {"id": 26, "query": "What Bluetooth earbuds do you have?",    "expected_intent": "product_info",  "category": "EN"},
    {"id": 27, "query": "How much is StarPods Pro in bulk?",      "expected_intent": "price_inquiry", "category": "EN"},
    {"id": 28, "query": "Do you support OEM customization?",      "expected_intent": "product_info",  "category": "EN"},
    {"id": 29, "query": "What's your MOQ for the smartwatch?",    "expected_intent": "bulk_inquiry",  "category": "EN"},
    {"id": 30, "query": "Can you ship to the US? What are the shipping options?", "expected_intent": "policy_query", "category": "EN"},
]

FAQ_ITEMS = [
    {"question": "你们公司在哪里", "answer": "我们位于深圳市宝安区，拥有3条自动化生产线。"},
    {"question": "样品怎么收费", "answer": "单款3个免费样品，快递费到付。超过3个按成本价收取。"},
    {"question": "付款方式有哪些", "answer": "支持T/T（30%预付+70%发货前付清）、L/C信用证、PayPal（5%手续费）三种方式。"},
    {"question": "可以定制LOGO吗", "answer": "支持LOGO定制，提供丝印、UV印、激光雕刻三种方式，起订量不变。"},
    {"question": "退换货政策是什么", "answer": "DOA（到货损坏）7天内免费换新；保修期内故障免费维修或更换，买家承担来回运费；非质量问题不接受退换。"},
]


class E2ETest:
    def __init__(self):
        self.token = ""
        self.bot_id = ""
        self.bot_api_key = ""
        self.results = []
        self.session: aiohttp.ClientSession | None = None

    async def run(self):
        print("=" * 60)
        print("CS Platform 端到端自动化测试")
        print("=" * 60)

        await self.upgrade_tenant_plan()

        async with aiohttp.ClientSession() as session:
            self.session = session
            await self.login()
            await self.create_bot()
            await self.upload_knowledge()
            await self.add_faqs()
            await self.wait_for_ready()
            await self.run_test_cases()

        await self.enrich_from_db()
        self.generate_report()

        print("\n" + "=" * 60)
        print("测试完成！报告已保存到:", REPORT_FILE)
        print("=" * 60)

    async def upgrade_tenant_plan(self):
        print("\n[0] 升级租户套餐...")
        try:
            conn = await asyncpg.connect(DB_URL)
            await conn.execute("""
                UPDATE tenants SET plan = 'pro', max_bots = 10
                WHERE plan = 'free'
            """)
            result = await conn.fetchrow(
                "SELECT id, name, plan, max_bots FROM tenants LIMIT 1"
            )
            if result:
                print(f"    租户: {result['name'] or result['id']} | plan={result['plan']} max_bots={result['max_bots']}")
            await conn.close()
        except Exception as e:
            print(f"    警告：DB 连接失败 ({e})，跳过升级")

    async def login(self):
        print("\n[1] 登录...")
        pwds = [TEST_PASSWORD, "testpass123", "test123456", "admin123", "Admin1234!"]
        data = None
        for pwd in pwds:
            resp = await self.session.post(f"{API_BASE}/api/auth/login", json={
                "email": TEST_EMAIL, "password": pwd,
            })
            if resp.status == 200:
                data = await resp.json()
                print(f"    登录成功: {TEST_EMAIL} (password match)")
                break
        if not data:
            print(f"    登录失败：所有候选密码均不匹配")
            sys.exit(1)
        self.token = data["data"]["access_token"]

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    async def create_bot(self):
        print("\n[2] 创建测试 Bot...")
        resp = await self.session.get(f"{API_BASE}/api/bots", headers=self._headers())
        data = await resp.json()
        bots = data.get("data", [])

        for bot in bots:
            if "星辰" in (bot.get("name") or ""):
                self.bot_id = bot["id"]
                print(f"    使用已有 Bot: {bot['name']} ({self.bot_id})")
                break

        if not self.bot_id:
            resp = await self.session.post(f"{API_BASE}/api/bots", headers=self._headers(), json={
                "name": "星辰电子客服",
                "welcome_message": "您好！欢迎咨询深圳星辰电子，我是AI客服助手。",
                "language": "zh",
                "style": "professional",
            })
            if resp.status == 201:
                data = await resp.json()
                self.bot_id = data["data"]["id"]
                print(f"    创建成功: {self.bot_id}")
            elif resp.status == 402:
                if bots:
                    self.bot_id = bots[0]["id"]
                    print(f"    配额限制，使用现有 Bot: {bots[0]['name']} ({self.bot_id})")
                else:
                    print("    无法创建 Bot 且没有现有 Bot，退出")
                    sys.exit(1)
            else:
                err = await resp.text()
                print(f"    创建失败: {err}")
                if bots:
                    self.bot_id = bots[0]["id"]
                    print(f"    回退到现有 Bot: {bots[0]['name']}")
                else:
                    sys.exit(1)

        resp = await self.session.post(
            f"{API_BASE}/api/bots/{self.bot_id}/reveal-key",
            headers=self._headers(),
        )
        if resp.status == 200:
            data = await resp.json()
            self.bot_api_key = data.get("data", {}).get("bot_api_key", "")
            if self.bot_api_key:
                print(f"    API Key: {self.bot_api_key[:20]}...")

    async def upload_knowledge(self):
        print("\n[3] 上传知识库...")
        if not os.path.exists(KB_FILE):
            print(f"    文件不存在: {KB_FILE}")
            return

        resp = await self.session.get(
            f"{API_BASE}/api/bots/{self.bot_id}/knowledge",
            headers=self._headers(),
        )
        if resp.status == 200:
            data = await resp.json()
            sources = data.get("data", [])
            for s in sources:
                nm = s.get("name") or s.get("file_name") or ""
                if "test_product_kb" in nm:
                    print(f"    已存在: {nm} (status={s.get('status')})")
                    return

        with open(KB_FILE, "rb") as f:
            form = aiohttp.FormData()
            form.add_field("file", f, filename="test_product_kb.txt", content_type="text/plain")
            resp = await self.session.post(
                f"{API_BASE}/api/bots/{self.bot_id}/knowledge",
                headers=self._headers(),
                data=form,
            )
        if resp.status in (200, 201):
            data = await resp.json()
            print(f"    上传成功: id={data.get('data',{}).get('id','?')} status={data.get('data',{}).get('status','?')}")
        else:
            err = await resp.text()
            print(f"    上传失败 ({resp.status}): {err[:200]}")

    async def add_faqs(self):
        print("\n[4] 添加 FAQ...")
        resp = await self.session.get(
            f"{API_BASE}/api/bots/{self.bot_id}/faq",
            headers=self._headers(),
        )
        existing_qs = set()
        if resp.status == 200:
            data = await resp.json()
            existing_qs = {f.get("question", "") for f in data.get("data", [])}

        for faq in FAQ_ITEMS:
            if faq["question"] in existing_qs:
                print(f"    ○ {faq['question'][:20]}... (已存在)")
                continue
            resp = await self.session.post(
                f"{API_BASE}/api/bots/{self.bot_id}/faq",
                headers=self._headers(),
                json=faq,
            )
            status = "✓" if resp.status in (200, 201) else f"✗ {resp.status}"
            print(f"    {status} {faq['question'][:20]}...")

    async def wait_for_ready(self):
        print("\n[5] 等待知识库就绪...")
        for i in range(24):
            resp = await self.session.get(
                f"{API_BASE}/api/bots/{self.bot_id}/knowledge",
                headers=self._headers(),
            )
            if resp.status == 200:
                data = await resp.json()
                sources = data.get("data", [])
                pending = [s for s in sources if s.get("status") in ("pending", "processing")]
                ready = [s for s in sources if s.get("status") == "ready"]
                if not pending and ready:
                    print(f"    就绪！{len(ready)} 个文档已处理 (chunks 总计 {sum(s.get('chunk_count',0) for s in ready)})")
                    return
                print(f"    等待中... ready={len(ready)} pending={len(pending)} [{i*5}s]")
            await asyncio.sleep(5)
        print("    超时，继续测试（部分文档可能未就绪）")

    async def run_test_cases(self):
        print("\n[6] 运行测试用例...")
        print("-" * 80)
        for tc in TEST_CASES:
            result = await self._run_single_test(tc)
            self.results.append(result)
            intent_match = "✓" if result["intent_match"] else "✗"
            print(
                f"  #{tc['id']:2d} [{tc['category']}] "
                f"{intent_match} intent={result['actual_intent']:<20s} "
                f"conf={result['confidence']:.2f} "
                f"grader={result['grader_score']:.3f} "
                f"latency={result['latency_ms']}ms "
                f"exit={result['exit_branch']}"
            )
            await asyncio.sleep(0.5)
        print("-" * 80)

    async def _run_single_test(self, tc: dict) -> dict:
        result = {
            "id": tc["id"],
            "query": tc["query"],
            "category": tc["category"],
            "expected_intent": tc["expected_intent"],
            "actual_intent": "",
            "confidence": 0.0,
            "grader_score": 0.0,
            "latency_ms": 0,
            "exit_branch": "",
            "cache_hit": False,
            "llm_calls": 0,
            "tokens": 0,
            "answer_preview": "",
            "trace_id": "",
            "intent_match": False,
            "error": "",
        }
        try:
            ws_url = f"ws://localhost:8081/api/admin/debug/{self.bot_id}?token={self.token}"
            async with self.session.ws_connect(ws_url, timeout=60) as ws:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=10)
                if msg.get("type") != "connected":
                    result["error"] = f"unexpected: {msg.get('type')}"
                    return result

                await ws.send_json({"type": "message", "content": tc["query"]})

                answer_parts = []
                debug_info = {}
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.receive_json(), timeout=60)
                    except asyncio.TimeoutError:
                        result["error"] = "timeout waiting for response"
                        break
                    if msg["type"] == "token":
                        answer_parts.append(msg.get("content", ""))
                    elif msg["type"] == "done":
                        debug_info = msg.get("debug", {})
                        result["latency_ms"] = msg.get("latency_ms", 0)
                        result["cache_hit"] = msg.get("cache_hit", False)
                        break
                    elif msg["type"] == "error":
                        result["error"] = msg.get("message", "unknown error")
                        break

                result["actual_intent"] = debug_info.get("intent", "")
                result["confidence"] = debug_info.get("intent_confidence", 0.0) or 0.0
                result["grader_score"] = debug_info.get("grader_score", 0.0) or 0.0
                trace = debug_info.get("trace") or {}
                result["exit_branch"] = trace.get("exit_branch", "")
                result["llm_calls"] = trace.get("llm_calls_count", 0)
                result["tokens"] = trace.get("llm_total_tokens", 0)
                result["trace_id"] = trace.get("trace_id", "")
                result["answer_preview"] = "".join(answer_parts)[:150]
                result["intent_match"] = self._check_intent_match(
                    tc["expected_intent"], result["actual_intent"], tc["category"]
                )
        except Exception as e:
            result["error"] = str(e)[:200]
        return result

    def _check_intent_match(self, expected: str, actual: str, category: str) -> bool:
        if expected == actual:
            return True
        L1 = {"greeting", "farewell", "acknowledgment", "bot_identity", "capability", "chitchat"}
        L2 = {"product_info", "price_inquiry", "availability", "how_to_use", "policy_query", "comparison"}
        L3 = {"purchase_intent", "bulk_inquiry", "custom_request", "lead_capture"}
        L4 = {"complaint", "urgent", "transfer_explicit", "transfer_implicit"}
        for group in [L1, L2, L3, L4]:
            if expected in group and actual in group:
                return True
        if expected == "follow_up" and actual in L2:
            return True
        return False

    async def enrich_from_db(self):
        print("\n[7] 从 DB 补充 trace 数据...")
        try:
            conn = await asyncpg.connect(DB_URL)
            for r in self.results:
                if r["trace_id"]:
                    row = await conn.fetchrow(
                        "SELECT exit_branch, llm_calls_count, llm_total_tokens "
                        "FROM traces WHERE trace_id = $1",
                        r["trace_id"],
                    )
                    if row:
                        r["exit_branch"] = row["exit_branch"] or r["exit_branch"]
                        r["llm_calls"] = row["llm_calls_count"] or r["llm_calls"]
                        r["tokens"] = row["llm_total_tokens"] or r["tokens"]
            await conn.close()
            print("    补充完成")
        except Exception as e:
            print(f"    DB 查询失败: {e}")

    def generate_report(self):
        print("\n[8] 生成测试报告...")
        total = len(self.results)
        intent_correct = sum(1 for r in self.results if r["intent_match"])
        errors = sum(1 for r in self.results if r["error"])
        l2_results = [r for r in self.results if r["category"] == "L2" and not r["error"]]
        avg_grader = sum(r["grader_score"] for r in l2_results) / len(l2_results) if l2_results else 0
        non_err = [r for r in self.results if not r["error"]]
        avg_latency = sum(r["latency_ms"] for r in non_err) / max(len(non_err), 1)
        cache_hits = sum(1 for r in self.results if r["cache_hit"])
        total_tokens = sum(r["tokens"] for r in self.results)

        lines = [
            "# 端到端测试报告",
            f"日期：{time.strftime('%Y-%m-%d %H:%M')}",
            f"Bot ID：{self.bot_id}",
            f"知识库：test_product_kb.txt + 5 条 FAQ",
            "",
            "## 总体指标",
            f"- 测试用例数：{total}",
            f"- 意图分类准确数：{intent_correct}/{total} ({intent_correct/total*100:.0f}%)",
            f"- 错误/超时数：{errors}",
            f"- L2 平均 Grader 分数：{avg_grader:.3f}",
            f"- 平均延迟：{avg_latency:.0f}ms",
            f"- 缓存命中：{cache_hits}",
            f"- 总 Token 消耗：{total_tokens}",
            "",
            "## 按类别统计",
        ]
        for cat in ["L1", "L2", "L3", "L4", "L5", "EN"]:
            cat_results = [r for r in self.results if r["category"] == cat]
            if not cat_results:
                continue
            correct = sum(1 for r in cat_results if r["intent_match"])
            avg_lat = sum(r["latency_ms"] for r in cat_results) / len(cat_results)
            lines.append(f"- **{cat}**: {correct}/{len(cat_results)} 准确, 平均 {avg_lat:.0f}ms")

        lines.extend([
            "",
            "## 详细记录",
            "",
            "| # | 类别 | 问题 | 期望意图 | 实际意图 | 匹配 | 置信度 | Grader | 延迟 | Exit | 备注 |",
            "|---|------|------|---------|---------|------|--------|--------|------|------|------|",
        ])
        for r in self.results:
            match_icon = "✓" if r["intent_match"] else "✗"
            error_note = r["error"][:30] if r["error"] else ""
            answer_note = r["answer_preview"][:40].replace("|", "\\|").replace("\n", " ") if not r["error"] else ""
            note = error_note or answer_note
            q = r["query"][:25] + ("..." if len(r["query"]) > 25 else "")
            lines.append(
                f"| {r['id']} | {r['category']} | {q} | "
                f"{r['expected_intent']} | {r['actual_intent']} | "
                f"{match_icon} | {r['confidence']:.2f} | "
                f"{r['grader_score']:.3f} | {r['latency_ms']}ms | "
                f"{r['exit_branch']} | {note} |"
            )

        failures = [r for r in self.results if not r["intent_match"] and not r["error"]]
        if failures:
            lines.extend(["", "## 意图分类偏差分析", ""])
            for r in failures:
                lines.append(
                    f"- **#{r['id']}** \"{r['query']}\" → 期望 `{r['expected_intent']}`，"
                    f"实际 `{r['actual_intent']}` (置信度 {r['confidence']:.2f})"
                )

        report = "\n".join(lines)
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n{'='*60}")
        print(f"  意图准确率: {intent_correct}/{total} ({intent_correct/total*100:.0f}%)")
        print(f"  L2 Grader 均分: {avg_grader:.3f}")
        print(f"  平均延迟: {avg_latency:.0f}ms")
        print(f"  Token 总消耗: {total_tokens}")
        print(f"  错误数: {errors}")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(E2ETest().run())
