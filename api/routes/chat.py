"""
WebSocket 对话端点。
鉴权：Bot API Key（middleware 注入 request["bot_id"] / request["tenant_id"]）
流式协议帧：connected / token / done / error / transfer / ping / pong
"""
import json
import logging
import uuid

from aiohttp import web

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()

# 全局注册：session_id -> set of visitor WS，admin.py broadcasts here.
_visitor_sessions: dict[str, set[web.WebSocketResponse]] = {}


@routes.get("/api/chat/{bot_id}")
async def chat_ws(request: web.Request) -> web.WebSocketResponse:
    # 校验 path bot_id 与 API Key 解析出的 bot_id 一致
    # （防止用 bot A 的 key 连接 bot B 的路径）
    path_bot_id = request.match_info["bot_id"]
    key_bot_id = str(request["bot_id"])
    if path_bot_id != key_bot_id:
        raise web.HTTPForbidden(reason="bot_id mismatch with API key")

    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    db = request.app["db"]
    tenant_id = str(request["tenant_id"])

    from store.bot_store import get_bot
    bot = await get_bot(db, key_bot_id, tenant_id)
    if not bot:
        await ws.close(code=4004, message=b"Bot not found")
        return ws

    incoming_session_id = request.rel_url.query.get("session_id")
    visitor_id = request.rel_url.query.get("visitor_id") or str(uuid.uuid4())
    language = bot.get("language", "zh")

    from store.session_store import (
        get_or_create_session,
        save_message,
        get_history,
    )
    session = await get_or_create_session(
        db, incoming_session_id, tenant_id, key_bot_id, visitor_id, language
    )
    session_id = str(session["id"])

    # 注册访客 WS（供 admin.py 向接管者广播）
    _visitor_sessions.setdefault(session_id, set()).add(ws)

    await _send(ws, {
        "type": "connected",
        "session_id": session_id,
        "welcome": bot.get("welcome_message", "您好，有什么可以帮您？"),
    })

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except json.JSONDecodeError:
                await _send(ws, {"type": "error", "code": "INVALID_JSON"})
                continue

            mtype = data.get("type")
            if mtype == "pong":
                continue
            if mtype != "message":
                continue

            user_content = (data.get("content") or "").strip()
            if not user_content:
                continue

            await save_message(
                db, session_id, tenant_id, "user", user_content
            )

            # 优先从 Redis 缓存读对话历史，回退到 DB
            redis = request.app.get("redis")
            history: list[dict] = []
            if redis is not None:
                from cache.session import get_history as cache_get_history
                history = await cache_get_history(redis, session_id)
            if not history:
                history = await get_history(db, session_id, limit=6)

            async def on_token(token: str):
                await _send(ws, {"type": "token", "content": token})

            try:
                from core.engine import run_pipeline
                from core.observability import TraceContext
                ctx = TraceContext(
                    bot_id=key_bot_id,
                    tenant_id=tenant_id,
                    session_id=session_id,
                    channel="widget",
                    user_query=user_content,
                    language=language,
                )
                state = await run_pipeline(
                    user_query=user_content,
                    bot_id=key_bot_id,
                    tenant_id=tenant_id,
                    session_id=session_id,
                    language=language,
                    history=history,
                    on_token=on_token,
                    db_pool=db,
                    ctx=ctx,
                )
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                await _send(ws, {
                    "type": "error",
                    "code": "PIPELINE_ERROR",
                    "message": (
                        "服务暂时不可用，请稍后重试"
                        if language == "zh"
                        else "Service temporarily unavailable"
                    ),
                })
                continue

            await save_message(
                db, session_id, tenant_id,
                role="assistant",
                content=state.generated_answer,
                grader_score=state.grader_score,
                is_grounded=state.is_grounded,
                latency_ms=state.total_latency_ms,
            )

            # 实时推送给 admin 监听者（接管前也能看实时对话）
            try:
                from api.routes.admin import notify_admin_listeners
                await notify_admin_listeners(session_id, {
                    "type": "new_message",
                    "role": "user",
                    "content": user_content,
                    "session_id": session_id,
                })
                await notify_admin_listeners(session_id, {
                    "type": "new_message",
                    "role": "assistant",
                    "content": state.generated_answer,
                    "grader_score": state.grader_score,
                    "session_id": session_id,
                })
            except Exception as ae:
                logger.warning(f"admin notify failed: {ae}")

            # 写回 session 缓存并累加配额计数
            if redis is not None:
                from cache.session import append_turn
                from cache.quota import increment as quota_inc
                await append_turn(
                    redis, session_id, user_content, state.generated_answer
                )
                await quota_inc(redis, tenant_id)

            # Lead capture 完成时持久化 + 触发通知
            if state.lead_info.get("_complete"):
                clean_info = {
                    k: v for k, v in state.lead_info.items()
                    if not k.startswith("_")
                }
                intent_score = float(state.lead_info.get("_score", 0.5))
                try:
                    from store.lead_store import create_lead
                    lead = await create_lead(
                        db, tenant_id, key_bot_id, session_id,
                        clean_info, intent_score,
                    )
                    try:
                        import redis as redis_lib
                        from rq import Queue as RQueue
                        from config import settings as cfg
                        r = redis_lib.from_url(cfg.REDIS_URL)
                        q = RQueue("notifications", connection=r)
                        from job_queue.tasks.notifications import (
                            send_lead_notification,
                        )
                        q.enqueue(
                            send_lead_notification,
                            str(lead["id"]), tenant_id, key_bot_id,
                            job_timeout=60,
                        )
                    except Exception as ne:
                        logger.warning(
                            f"Lead notification enqueue failed: {ne}"
                        )
                except Exception as le:
                    logger.error(f"Lead save failed: {le}")

            done_payload = {
                "type": "done",
                "session_id": session_id,
                "grounded": state.is_grounded,
                "cache_hit": state.cache_hit,
                "latency_ms": state.total_latency_ms,
                "trace_id": ctx.trace_id,
            }

            if state.should_transfer:
                done_payload["transfer"] = True
                await _send(ws, {
                    "type": "transfer",
                    "message": (
                        "已为您转接人工客服，请稍候。"
                        if language == "zh"
                        else "Transferring to human agent."
                    ),
                })

                # 异步通知人工接管 + 更新 session 状态
                try:
                    import redis as redis_lib
                    from rq import Queue as RQueue
                    from config import settings as cfg
                    r = redis_lib.from_url(cfg.REDIS_URL)
                    q = RQueue("notifications", connection=r)
                    from job_queue.tasks.notifications import (
                        send_human_transfer_notification,
                    )
                    q.enqueue(
                        send_human_transfer_notification,
                        session_id, tenant_id,
                        job_timeout=30,
                    )
                except Exception as te:
                    logger.warning(
                        f"Transfer notification enqueue failed: {te}"
                    )

                from store.base import execute as db_execute
                await db_execute(
                    db,
                    "UPDATE sessions SET status='transferred' WHERE id=$1",
                    session_id,
                )

            await _send(ws, done_payload)

            # 私域引流：Bot 配置了 private_domain_config 时，每 3 条消息推一次
            private_cfg = bot.get("private_domain_config")
            if isinstance(private_cfg, str):
                try:
                    import json as _json
                    private_cfg = _json.loads(private_cfg)
                except Exception:
                    private_cfg = None
            if (
                isinstance(private_cfg, dict)
                and state.intent == "knowledge_qa"
                and state.is_grounded
                and redis is not None
            ):
                try:
                    count_key = f"pd_count:{session_id}"
                    count = await redis.incr(count_key)
                    await redis.expire(count_key, 3600)
                    if count % 3 == 0:
                        await _send(ws, {
                            "type": "private_domain",
                            "message": private_cfg.get("message", ""),
                            "qr_code_url": private_cfg.get("qr_code_url", ""),
                        })
                except Exception as pe:
                    logger.warning(f"private_domain push failed: {pe}")

        elif msg.type in (web.WSMsgType.ERROR, web.WSMsgType.CLOSE):
            break

    # 反注册访客 WS
    listeners = _visitor_sessions.get(session_id)
    if listeners:
        listeners.discard(ws)
        if not listeners:
            _visitor_sessions.pop(session_id, None)

    logger.info(f"WebSocket closed: session={session_id}")
    return ws


async def _send(ws: web.WebSocketResponse, data: dict) -> None:
    """安全发送 JSON，连接断开时静默失败"""
    try:
        if not ws.closed:
            await ws.send_json(data)
    except Exception:
        pass


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
