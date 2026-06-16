"""Session token 与 CSRF token 工具。"""

from __future__ import annotations

import hashlib
import hmac
import secrets


SESSION_TOKEN_BYTES = 32
CSRF_TOKEN_BYTES = 32


def generate_session_token() -> str:
    """生成用于 Cookie 的高熵 Session token 明文。"""
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def generate_csrf_token() -> str:
    """生成返回给前端的 CSRF token 明文。"""
    return secrets.token_urlsafe(CSRF_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """生成 token 的 SHA-256 哈希，数据库只保存该值。"""
    if not token:
        raise ValueError("token must not be empty")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """常量时间校验 token 明文是否匹配已保存哈希。"""
    if not token or not token_hash:
        return False
    return hmac.compare_digest(hash_token(token), token_hash)
