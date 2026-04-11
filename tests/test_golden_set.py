"""
Golden Set 回归测试。

前提：python main.py serve 已启动。

用法（自动模式）— 自动登录 + 创建临时 bot + 运行所有用例 + 清理：
    python tests/test_golden_set.py --email test_a@example.com --password testpass123

用法（手动模式）— 复用现有 bot 及其 API Key：
    python tests/test_golden_set.py --bot-id UUID --bot-key cs_bot_...
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp

BASE = "http://localhost:8080"
GOLDEN_SET_PATH = Path(__file__).parent / "golden_set" / "cases.json"
BASELINE_PATH = Path(__file__).parent / "golden_set" / "baseline.json"


async def _login(session: aiohttp.ClientSession, email: str, password: str) -> str:
    r = await session.post(
        f"{BASE}/api/auth/login",
        json={"email": email, "password": password},
    )
    body = await r.json()
    return body["data"]["access_token"]


async def _create_temp_bot(
    session: aiohttp.ClientSession, token: str
) -> tuple[str, str]:
    """返回 (bot_id, bot_api_key)"""
    H = {"Authorization": f"Bearer {token}"}
    r = await session.post(
        f"{BASE}/api/bots",
        json={"name": "Golden Set Bot", "language": "zh"},
        headers=H,
    )
    bot_id = (await r.json())["data"]["id"]
    r = await session.post(f"{BASE}/api/bots/{bot_id}/rotate-key", headers=H)
    bot_key = (await r.json())["data"]["bot_api_key"]
    return bot_id, bot_key


async def _delete_bot(
    session: aiohttp.ClientSession, token: str, bot_id: str
) -> None:
    H = {"Authorization": f"Bearer {token}"}
    await session.delete(f"{BASE}/api/bots/{bot_id}", headers=H)


async def run_case(
    case: dict, bot_id: str, bot_key: str
) -> dict:
    """运行单个测试用例，返回结果字典"""
    result = {
        "id": case["id"],
        "passed": False,
        "score": 0.0,
        "answer": "",
        "grounded": False,
        "transferred": False,
        "cache_hit": False,
        "fail_reasons": [],
    }

    ws_url = (
        f"ws://localhost:8080/api/chat/{bot_id}"
        f"?key={bot_key}&visitor_id=gs_{case['id']}"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                connected = await asyncio.wait_for(ws.receive(), timeout=10)
                if connected.type != aiohttp.WSMsgType.TEXT:
                    result["fail_reasons"].append(
                        f"Expected connected frame, got {connected.type}"
                    )
                    return result
                conn_data = json.loads(connected.data)
                if conn_data.get("type") != "connected":
                    result["fail_reasons"].append(
                        f"First frame type={conn_data.get('type')}"
                    )
                    return result

                await ws.send_json(
                    {"type": "message", "content": case["query"]}
                )

                answer_parts: list[str] = []
                while True:
                    msg = await asyncio.wait_for(ws.receive(), timeout=60)
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        break
                    frame = json.loads(msg.data)
                    ftype = frame.get("type")
                    if ftype == "token":
                        answer_parts.append(frame.get("content", ""))
                    elif ftype == "transfer":
                        result["transferred"] = True
                    elif ftype == "done":
                        result["grounded"] = frame.get("grounded", False)
                        result["cache_hit"] = frame.get("cache_hit", False)
                        if frame.get("transfer"):
                            result["transferred"] = True
                        break
                    elif ftype == "error":
                        result["fail_reasons"].append(
                            f"Error frame: {frame}"
                        )
                        break

                result["answer"] = "".join(answer_parts)
    except Exception as e:
        result["fail_reasons"].append(f"Exception: {e}")
        return result

    # ── 评分 ─────────────────────────────────────────────
    answer_lower = result["answer"].lower()
    score = 0.0

    if "expected_grounded" in case:
        if result["grounded"] == case["expected_grounded"]:
            score += 0.3
        else:
            result["fail_reasons"].append(
                f"grounded={result['grounded']}, expected={case['expected_grounded']}"
            )

    contains_list = case.get("expected_contains", [])
    if contains_list:
        # 命中任意一个关键词即视为通过（OR 匹配，对生成式答案更合理）
        if any(kw.lower() in answer_lower for kw in contains_list):
            score += 0.4
        else:
            result["fail_reasons"].append(
                f"None of expected keywords present: {contains_list}"
            )
    else:
        score += 0.4

    for kw in case.get("expected_not_contains", []):
        if kw.lower() in answer_lower:
            result["fail_reasons"].append(f"Should not contain: {kw}")
            score -= 0.2

    if "expected_transfer" in case:
        if result["transferred"] == case["expected_transfer"]:
            score += 0.3
        else:
            result["fail_reasons"].append(
                f"transferred={result['transferred']}, expected={case['expected_transfer']}"
            )
    else:
        score += 0.3

    if case.get("expected_no_transfer") and result["transferred"]:
        result["fail_reasons"].append("Unexpected transfer")
        score -= 0.2

    result["score"] = max(0.0, min(1.0, score))
    result["passed"] = result["score"] >= 0.6 and not result["fail_reasons"]
    return result


async def run_all(bot_id: str, bot_key: str) -> bool:
    cases = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    results = []
    passed = 0
    failed = 0
    total_score = 0.0

    for case in cases:
        result = await run_case(case, bot_id, bot_key)
        results.append(result)
        total_score += result["score"]
        status = "PASS" if result["passed"] else "FAIL"
        query_preview = case["query"][:40].replace("\n", " ")
        print(f"  {status}  [{case['id']}] score={result['score']:.2f}  {query_preview}")
        if not result["passed"]:
            failed += 1
            for r in result["fail_reasons"][:3]:
                print(f"           - {r}")
        else:
            passed += 1

    avg = total_score / max(len(cases), 1)
    print(
        f"\n  {len(cases)} 个用例  {passed} 通过  {failed} 失败  平均分 {avg:.2f}"
    )

    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text())
        baseline_avg = baseline.get("avg_score", 0)
        delta = avg - baseline_avg
        tag = "OK" if delta >= -0.05 else "REGRESSED"
        print(
            f"  baseline={baseline_avg:.2f}  current={avg:.2f}  delta={delta:+.2f}  {tag}"
        )
        if delta < -0.05:
            return False
    else:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(
            json.dumps(
                {"avg_score": avg, "total": len(cases), "passed": passed},
                indent=2,
            )
        )
        print(f"  baseline saved: avg={avg:.2f}")

    return failed == 0


async def main_async(args: argparse.Namespace) -> bool:
    if args.bot_id and args.bot_key:
        return await run_all(args.bot_id, args.bot_key)

    if not (args.email and args.password):
        print("Provide either --bot-id+--bot-key or --email+--password", file=sys.stderr)
        return False

    async with aiohttp.ClientSession() as s:
        token = await _login(s, args.email, args.password)
        bot_id, bot_key = await _create_temp_bot(s, token)
        print(f"  Temporary bot created: {bot_id}")
        try:
            return await run_all(bot_id, bot_key)
        finally:
            await _delete_bot(s, token, bot_id)
            print("  Temporary bot cleaned up")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot-id")
    parser.add_argument("--bot-key")
    parser.add_argument("--email")
    parser.add_argument("--password")
    args = parser.parse_args()

    ok = asyncio.run(main_async(args))
    sys.exit(0 if ok else 1)
