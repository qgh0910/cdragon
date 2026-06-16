"""知识库权限解析器。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException, status

from . import registry


VALID_ACTIONS = {"read", "write", "delete"}


def resolve_knowledge_base(
    current_user: Dict[str, Any],
    kb_id: str,
    action: str,
    *,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    """解析知识库并校验当前用户对指定动作的权限。"""
    user = _require_authenticated_user(current_user)
    normalized_action = _validate_action(action)
    knowledge_base = registry.get_knowledge_base(kb_id, db_path=db_path)
    if knowledge_base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")

    if _is_allowed(user, knowledge_base, normalized_action):
        return knowledge_base

    raise HTTPException(
        status_code=_denied_status_code(knowledge_base),
        detail="无权访问该知识库",
    )


def _require_authenticated_user(current_user: Dict[str, Any]) -> Dict[str, Any]:
    """校验当前用户字典。"""
    if not current_user or not current_user.get("id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或会话已失效")
    if current_user.get("is_active") is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return current_user


def _validate_action(action: str) -> str:
    """校验权限动作。"""
    normalized_action = action.strip().lower()
    if normalized_action not in VALID_ACTIONS:
        raise ValueError(f"不支持的知识库权限动作: {action}")
    return normalized_action


def _is_allowed(user: Dict[str, Any], knowledge_base: Dict[str, Any], action: str) -> bool:
    """根据知识库 scope 判断动作是否允许。"""
    scope = knowledge_base.get("scope")
    role = user.get("role")
    user_id = user.get("id")

    if scope == "public":
        return action == "read" or role == "admin"

    if scope == "user":
        return knowledge_base.get("owner_user_id") == user_id

    if scope == "legacy_admin_only":
        return role == "admin"

    return False


def _denied_status_code(knowledge_base: Dict[str, Any]) -> int:
    """返回符合资源枚举控制的拒绝状态码。"""
    if knowledge_base.get("scope") == "public":
        return status.HTTP_403_FORBIDDEN
    return status.HTTP_404_NOT_FOUND
