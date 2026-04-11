"""成员管理路由"""
import logging
from datetime import date, datetime
from uuid import UUID

from aiohttp import web

from store.base import fetch_all, fetch_one, execute

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()

ADMIN_ROLES = {"super_admin", "admin"}
ASSIGNABLE_ROLES = {"admin", "operator", "viewer"}


def _require_admin(request: web.Request) -> None:
    if request.get("role") not in ADMIN_ROLES:
        raise web.HTTPForbidden(reason="Admin role required")


def _serialize(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _row_to_dict(row) -> dict:
    return {k: _serialize(v) for k, v in dict(row).items()}


@routes.get("/api/members")
async def list_members(request: web.Request) -> web.Response:
    tenant_id = request["tenant_id"]
    db = request.app["db"]
    rows = await fetch_all(
        db,
        """
        SELECT id, email, name, role, status, last_login_at, created_at
        FROM users
        WHERE tenant_id = $1
        ORDER BY created_at ASC
        """,
        tenant_id,
    )
    return web.json_response({
        "data": [_row_to_dict(r) for r in rows],
        "meta": {"total": len(rows)},
    })


@routes.put("/api/members/{user_id}/role")
async def update_member_role(request: web.Request) -> web.Response:
    _require_admin(request)
    tenant_id = request["tenant_id"]
    current_uid = request["user_id"]
    target_uid = request.match_info["user_id"]
    data = await request.json()
    new_role = data.get("role", "")

    if new_role not in ASSIGNABLE_ROLES:
        raise web.HTTPBadRequest(
            reason=f"Invalid role. Allowed: {sorted(ASSIGNABLE_ROLES)}"
        )
    if current_uid == target_uid:
        raise web.HTTPBadRequest(reason="Cannot change your own role")

    db = request.app["db"]
    target = await fetch_one(
        db,
        "SELECT role FROM users WHERE id = $1 AND tenant_id = $2",
        target_uid, tenant_id,
    )
    if not target:
        raise web.HTTPForbidden(reason="User not found or access denied")
    if target["role"] == "super_admin":
        raise web.HTTPForbidden(reason="Cannot change super_admin role")

    result = await execute(
        db,
        "UPDATE users SET role = $1 WHERE id = $2 AND tenant_id = $3",
        new_role, target_uid, tenant_id,
    )
    if result == "UPDATE 0":
        raise web.HTTPForbidden(reason="User not found or access denied")
    return web.json_response(
        {"data": {"user_id": target_uid, "role": new_role}}
    )


@routes.put("/api/members/{user_id}/status")
async def update_member_status(request: web.Request) -> web.Response:
    _require_admin(request)
    tenant_id = request["tenant_id"]
    current_uid = request["user_id"]
    target_uid = request.match_info["user_id"]
    data = await request.json()
    new_status = data.get("status", "")

    if new_status not in ("active", "suspended"):
        raise web.HTTPBadRequest(
            reason="Status must be 'active' or 'suspended'"
        )
    if current_uid == target_uid:
        raise web.HTTPBadRequest(reason="Cannot change your own status")

    db = request.app["db"]
    target = await fetch_one(
        db,
        "SELECT role FROM users WHERE id = $1 AND tenant_id = $2",
        target_uid, tenant_id,
    )
    if not target or target["role"] == "super_admin":
        raise web.HTTPForbidden(reason="Cannot modify this user")

    await execute(
        db,
        "UPDATE users SET status = $1 WHERE id = $2 AND tenant_id = $3",
        new_status, target_uid, tenant_id,
    )

    # 停用时吊销所有 refresh token，强制踢下线
    if new_status == "suspended":
        await execute(
            db,
            """
            UPDATE refresh_tokens SET revoked_at = NOW()
            WHERE user_id = $1 AND revoked_at IS NULL
            """,
            target_uid,
        )
    return web.json_response(
        {"data": {"user_id": target_uid, "status": new_status}}
    )


@routes.get("/api/members/invitations")
async def list_invitations(request: web.Request) -> web.Response:
    tenant_id = request["tenant_id"]
    db = request.app["db"]
    rows = await fetch_all(
        db,
        """
        SELECT id, email, role, status, expires_at, created_at
        FROM invitations
        WHERE tenant_id = $1
          AND status = 'pending'
          AND expires_at > NOW()
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    return web.json_response({"data": [_row_to_dict(r) for r in rows]})


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
