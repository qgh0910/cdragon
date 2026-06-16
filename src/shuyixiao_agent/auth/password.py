"""密码哈希与校验工具。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass


PASSWORD_ALGORITHM = "pbkdf2_sha256"
DEFAULT_PASSWORD_ITERATIONS = 310000
DEFAULT_SALT_BYTES = 32


@dataclass(frozen=True)
class PasswordHash:
    """可直接拆分保存到 users 表的密码哈希结果。"""

    password_hash: str
    salt: str
    iterations: int = DEFAULT_PASSWORD_ITERATIONS
    algorithm: str = PASSWORD_ALGORITHM


def generate_password_hash(
    password: str,
    *,
    iterations: int = DEFAULT_PASSWORD_ITERATIONS,
    salt: str | None = None,
) -> PasswordHash:
    """使用 PBKDF2-HMAC-SHA256 生成密码哈希。"""
    if not password:
        raise ValueError("password must not be empty")
    if iterations < DEFAULT_PASSWORD_ITERATIONS:
        raise ValueError("password iterations is below the minimum")

    salt_value = salt or _generate_salt()
    password_hash = _derive_password_hash(password, salt_value, iterations)
    return PasswordHash(
        password_hash=password_hash,
        salt=salt_value,
        iterations=iterations,
        algorithm=PASSWORD_ALGORITHM,
    )


def verify_password(
    password: str,
    stored_hash: PasswordHash | str,
    *,
    salt: str | None = None,
    iterations: int | None = None,
) -> bool:
    """校验明文密码是否匹配已保存的密码哈希。"""
    if isinstance(stored_hash, PasswordHash):
        salt_value = stored_hash.salt
        iterations_value = stored_hash.iterations
        hash_value = stored_hash.password_hash
    else:
        if salt is None or iterations is None:
            raise ValueError("salt and iterations are required with a raw hash")
        salt_value = salt
        iterations_value = iterations
        hash_value = stored_hash

    candidate_hash = _derive_password_hash(password, salt_value, iterations_value)
    return hmac.compare_digest(candidate_hash, hash_value)


def _generate_salt() -> str:
    """生成 URL-safe 的随机盐。"""
    return secrets.token_urlsafe(DEFAULT_SALT_BYTES)


def _derive_password_hash(password: str, salt: str, iterations: int) -> str:
    """派生 PBKDF2-HMAC-SHA256 哈希并用 base64 保存。"""
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return base64.urlsafe_b64encode(digest).decode("ascii")
