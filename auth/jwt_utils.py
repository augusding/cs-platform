"""
JWT 工具函数。
access_token：15分钟有效，含 tenant_id / role / plan。
refresh_token：7天有效，明文生成，SHA-256 哈希后存库。
"""
import asyncio
import hashlib
import os
import time
from jose import jwt, JWTError

from config import settings

_ALGORITHM = "HS256"


def sign_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    plan: str,
) -> str:
    """签发 access_token"""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "tid": tenant_id,
        "role": role,
        "plan": plan,
        "iat": now,
        "exp": now + settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def verify_access_token(token: str) -> dict:
    """验证并解码 access_token，失败抛 ValueError"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[_ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Token 无效或已过期: {e}")


def generate_refresh_token() -> str:
    """生成随机 refresh_token 明文（64个十六进制字符）"""
    return os.urandom(32).hex()


def hash_refresh_token(token: str) -> str:
    """SHA-256 哈希 refresh_token，存库时存哈希，不存明文"""
    return hashlib.sha256(token.encode()).hexdigest()
