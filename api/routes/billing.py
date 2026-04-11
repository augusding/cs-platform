"""计费路由：套餐查询 + 创建订单 + 支付回调 + 开发模拟支付"""
import logging
import xml.etree.ElementTree as ET

from aiohttp import web

from config import settings
from store.plan_store import (
    PLAN_CONFIG,
    get_tenant_plan,
    create_order,
    confirm_order,
)

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()

_PLAN_LABELS = {
    "free": "体验版",
    "entity": "实体版",
    "trade": "外贸版",
    "pro": "专业版",
}


@routes.get("/api/billing/plans")
async def list_plans(request: web.Request) -> web.Response:
    plans = [
        {
            "id": k,
            "name": _PLAN_LABELS.get(k, k),
            "price_yuan": v["price_fen"] / 100,
            "price_fen": v["price_fen"],
            "max_bots": v["max_bots"],
            "monthly_quota": v["monthly_quota"],
        }
        for k, v in PLAN_CONFIG.items()
    ]
    return web.json_response({"data": plans})


@routes.get("/api/billing/status")
async def billing_status(request: web.Request) -> web.Response:
    db = request.app["db"]
    info = await get_tenant_plan(db, request["tenant_id"])
    if info.get("plan_expires_at"):
        info["plan_expires_at"] = info["plan_expires_at"].isoformat()
    return web.json_response({"data": info})


@routes.post("/api/billing/create-order")
async def create_order_handler(request: web.Request) -> web.Response:
    data = await request.json()
    plan = data.get("plan")
    if plan not in PLAN_CONFIG or plan == "free":
        raise web.HTTPBadRequest(reason="Invalid plan")

    db = request.app["db"]
    order = await create_order(db, request["tenant_id"], plan)

    has_wechat = bool(settings.WECHAT_PAY_MCH_ID)
    return web.json_response(
        {
            "data": {
                "order_id": str(order["id"]),
                "out_trade_no": order["out_trade_no"],
                "amount_yuan": order["amount_fen"] / 100,
                "pay_params": None,
                "manual_note": (
                    None
                    if has_wechat
                    else "微信支付未配置，请使用模拟支付或联系客服"
                ),
            }
        },
        status=201,
    )


@routes.post("/api/billing/webhook")
async def wechat_webhook(request: web.Request) -> web.Response:
    """微信支付回调（公开，验签由 WeChat 签名承担；MVP 版暂未实现验签）"""
    body = await request.read()
    try:
        root = ET.fromstring(body)
        result_code = root.findtext("result_code", "")
        out_trade_no = root.findtext("out_trade_no", "")
        transaction_id = root.findtext("transaction_id", "")
        if result_code == "SUCCESS" and out_trade_no:
            db = request.app["db"]
            await confirm_order(db, out_trade_no, transaction_id)
    except Exception as e:
        logger.error(f"WeChat webhook parse error: {e}")
    return web.Response(
        text="<xml><return_code>SUCCESS</return_code><return_msg>OK</return_msg></xml>",
        content_type="text/xml",
    )


@routes.post("/api/billing/simulate-pay")
async def simulate_pay(request: web.Request) -> web.Response:
    """开发环境模拟支付；生产（DEBUG=false）返回 404。"""
    if not settings.DEBUG:
        raise web.HTTPNotFound()

    data = await request.json()
    out_trade_no = (data.get("out_trade_no") or "").strip()
    if not out_trade_no:
        raise web.HTTPBadRequest(reason="out_trade_no required")

    db = request.app["db"]

    # 先校验订单归属本租户，再确认支付（避免跨租户升级别人的套餐）
    from store.base import fetch_one as _fetch_one
    owner = await _fetch_one(
        db,
        "SELECT tenant_id FROM orders WHERE out_trade_no = $1",
        out_trade_no,
    )
    if not owner:
        raise web.HTTPBadRequest(reason="Order not found")
    if str(owner["tenant_id"]) != str(request["tenant_id"]):
        raise web.HTTPForbidden(reason="Order belongs to a different tenant")

    tenant_id = await confirm_order(db, out_trade_no, f"SIM_{out_trade_no}")
    if not tenant_id:
        raise web.HTTPBadRequest(reason="Order already paid")

    from store.audit_store import log_action
    await log_action(
        db, tenant_id, "plan.upgrade", "tenant", tenant_id,
        user_id=request.get("user_id"),
        after={"out_trade_no": out_trade_no, "method": "simulate"},
        ip=request.remote,
    )

    return web.json_response(
        {"data": {"message": "Simulated", "tenant_id": tenant_id}}
    )


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
