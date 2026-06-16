"""认证依赖与当前用户解析。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import Cookie, HTTPException, status

from . import storage
from .sessions import hash_token


AUTH_COOKIE_NAME = "lpos_session"


def resolve_user_from_session_token(session_token: str | None) -> Dict[str, Any]:
    """根据 Session token 返回当前用户，供依赖和 API 边界复用。"""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或会话已失效",
        )

    session_hash = hash_token(session_token)
    session = storage.get_session_by_hash(session_hash)
    if not session or session.get("revoked_at"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或会话已失效",
        )

    expires_at = datetime.fromisoformat(session["expires_at"])
    if expires_at <= datetime.now(expires_at.tzinfo):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或会话已失效",
        )

    user = storage.get_user_by_id(session["user_id"])
    if not user or not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
        )

    return user


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> Dict[str, Any]:
    """根据 HttpOnly Cookie 中的 Session token 返回当前用户。"""
    return resolve_user_from_session_token(session_token)


def require_active_user(current_user: Dict[str, Any] = None) -> Dict[str, Any]:
    """占位式活跃用户依赖，供后续步骤复用。"""
    if current_user is None:
        return get_current_user()
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
        )
    return current_user


def require_admin(current_user: Dict[str, Any] = None) -> Dict[str, Any]:
    """管理员依赖，供后续步骤复用。"""
    user = require_active_user(current_user)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
