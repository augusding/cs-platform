"""
认证路由：注册 / 登录 / 刷新 / 登出 / 邀请 / 接受邀请
"""
import os
import logging
from aiohttp import web

from auth.jwt_utils import (
    sign_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from auth.password import hash_password, verify_password
from config import settings
from store import (
    tenant_store,
    user_store,
    invitation_store,
    refresh_token_store,
)

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()

REFRESH_TOKEN_COOKIE = "cs_refresh_token"


def _set_refresh_cookie(response: web.Response, token: str) -> None:
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        samesite="Lax",
        secure=False,
        path="/api/auth",
    )


def _token_response(user: dict, tenant_id: str) -> dict:
    access_token = sign_access_token(
        user_id=str(user["id"]),
        tenant_id=str(tenant_id),
        role=user["role"],
        plan=user.get("plan", "free"),
    )
    return {
        "access_token": access_token,
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
        "role": user["role"],
    }


# ── POST /api/auth/register ──────────────────────────────
@routes.post("/api/auth/register")
async def register_handler(request: web.Request) -> web.Response:
    data = await request.json()
    company_name = (data.get("company_name") or "").strip()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not all([company_name, name, email, password]):
        raise web.HTTPBadRequest(
            reason="company_name, name, email, password are required"
        )
    if len(password) < 8:
        raise web.HTTPBadRequest(reason="Password must be at least 8 characters")

    db = request.app["db"]

    existing = await user_store.get_user_by_email(db, email)
    if existing:
        raise web.HTTPConflict(reason="Email already registered")

    tenant = await tenant_store.create_tenant(db, company_name)
    pwd_hash = hash_password(password)
    user = await user_store.create_user(
        db,
        tenant_id=str(tenant["id"]),
        email=email,
        name=name,
        role="super_admin",
        password_hash=pwd_hash,
        status="active",
    )

    refresh_token = generate_refresh_token()
    token_hash = hash_refresh_token(refresh_token)
    await refresh_token_store.create_refresh_token(
        db, str(user["id"]), str(tenant["id"]), token_hash
    )

    resp_data = _token_response(user, tenant["id"])
    resp = web.json_response({"data": resp_data}, status=201)
    _set_refresh_cookie(resp, refresh_token)
    return resp


# ── POST /api/auth/login ─────────────────────────────────
@routes.post("/api/auth/login")
async def login_handler(request: web.Request) -> web.Response:
    data = await request.json()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    db = request.app["db"]
    user = await user_store.get_user_by_email(db, email)

    if not user or not user.get("password_hash"):
        raise web.HTTPUnauthorized(reason="Invalid email or password")
    if not verify_password(password, user["password_hash"]):
        raise web.HTTPUnauthorized(reason="Invalid email or password")
    if user["status"] != "active":
        raise web.HTTPForbidden(reason="Account is not active")

    await user_store.update_last_login(db, str(user["id"]))

    refresh_token = generate_refresh_token()
    token_hash = hash_refresh_token(refresh_token)
    await refresh_token_store.create_refresh_token(
        db, str(user["id"]), str(user["tenant_id"]), token_hash
    )

    resp_data = _token_response(user, user["tenant_id"])
    resp = web.json_response({"data": resp_data})
    _set_refresh_cookie(resp, refresh_token)
    return resp


# ── POST /api/auth/refresh ───────────────────────────────
@routes.post("/api/auth/refresh")
async def refresh_handler(request: web.Request) -> web.Response:
    old_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not old_token:
        raise web.HTTPUnauthorized(reason="Missing refresh token")

    db = request.app["db"]
    token_hash = hash_refresh_token(old_token)
    stored = await refresh_token_store.get_refresh_token(db, token_hash)

    if not stored:
        raise web.HTTPUnauthorized(reason="Invalid or expired refresh token")

    await refresh_token_store.revoke_refresh_token(db, token_hash)

    new_refresh = generate_refresh_token()
    new_hash = hash_refresh_token(new_refresh)
    await refresh_token_store.create_refresh_token(
        db, str(stored["user_id"]), str(stored["tenant_id"]), new_hash
    )

    user = {
        "id": stored["user_id"],
        "role": stored["role"],
        "tenant_id": stored["tenant_id"],
    }
    resp_data = _token_response(user, stored["tenant_id"])
    resp = web.json_response({"data": resp_data})
    _set_refresh_cookie(resp, new_refresh)
    return resp


# ── POST /api/auth/logout ────────────────────────────────
@routes.post("/api/auth/logout")
async def logout_handler(request: web.Request) -> web.Response:
    token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if token:
        db = request.app["db"]
        token_hash = hash_refresh_token(token)
        await refresh_token_store.revoke_refresh_token(db, token_hash)

    resp = web.json_response({"data": None})
    resp.del_cookie(REFRESH_TOKEN_COOKIE, path="/api/auth")
    return resp


# ── POST /api/auth/invite ────────────────────────────────
@routes.post("/api/auth/invite")
async def invite_handler(request: web.Request) -> web.Response:
    role = request.get("role")
    if role not in ("super_admin", "admin"):
        raise web.HTTPForbidden(reason="Only admin can invite members")

    data = await request.json()
    email = (data.get("email") or "").strip().lower()
    invite_role = data.get("role") or "operator"

    if not email:
        raise web.HTTPBadRequest(reason="email is required")
    if invite_role not in ("admin", "operator", "viewer"):
        raise web.HTTPBadRequest(reason="Invalid role")

    db = request.app["db"]
    tenant_id = request["tenant_id"]
    user_id = request["user_id"]

    token = os.urandom(32).hex()
    invitation = await invitation_store.create_invitation(
        db, tenant_id, user_id, email, invite_role, token
    )

    existing = await user_store.get_user_by_email(db, email)
    if not existing:
        await user_store.create_user(
            db,
            tenant_id=tenant_id,
            email=email,
            name=email.split("@")[0],
            role=invite_role,
            status="invited",
        )

    return web.json_response({
        "data": {
            "invitation_id": str(invitation["id"]),
            "token": token,
            "email": email,
            "role": invite_role,
            "expires_at": invitation["expires_at"].isoformat(),
        }
    }, status=201)


# ── POST /api/auth/invite/accept ─────────────────────────
@routes.post("/api/auth/invite/accept")
async def accept_invite_handler(request: web.Request) -> web.Response:
    data = await request.json()
    token = data.get("token") or ""
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""

    if not all([token, name, password]):
        raise web.HTTPBadRequest(reason="token, name, password are required")
    if len(password) < 8:
        raise web.HTTPBadRequest(reason="Password must be at least 8 characters")

    db = request.app["db"]
    invitation = await invitation_store.get_invitation_by_token(db, token)
    if not invitation:
        raise web.HTTPBadRequest(reason="Invalid or expired invitation token")

    user = await user_store.get_user_by_email(db, invitation["email"])
    if not user:
        raise web.HTTPBadRequest(reason="User not found")

    pwd_hash = hash_password(password)
    await user_store.activate_user(db, str(user["id"]), pwd_hash)
    await invitation_store.accept_invitation(db, str(invitation["id"]))

    from store.base import execute as db_execute
    await db_execute(
        db,
        "UPDATE users SET name = $1 WHERE id = $2",
        name, str(user["id"]),
    )

    refresh_token = generate_refresh_token()
    token_hash = hash_refresh_token(refresh_token)
    await refresh_token_store.create_refresh_token(
        db, str(user["id"]), str(invitation["tenant_id"]), token_hash
    )

    resp_user = {**user, "role": invitation["role"]}
    resp_data = _token_response(resp_user, invitation["tenant_id"])
    resp = web.json_response({"data": resp_data}, status=201)
    _set_refresh_cookie(resp, refresh_token)
    return resp


def register(app: web.Application) -> None:
    app.router.add_routes(routes)
