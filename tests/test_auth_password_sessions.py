"""认证密码哈希、Session token 和 CSRF token 测试。"""

from src.shuyixiao_agent.auth.password import (
    DEFAULT_PASSWORD_ITERATIONS,
    PasswordHash,
    generate_password_hash,
    verify_password,
)
from src.shuyixiao_agent.auth.sessions import (
    generate_csrf_token,
    generate_session_token,
    hash_token,
    verify_token_hash,
)


def test_generate_password_hash_uses_pbkdf2_sha256_with_random_salt():
    """密码哈希应使用 PBKDF2-HMAC-SHA256，并为同一密码生成不同盐。"""
    first = generate_password_hash("Correct Horse Battery Staple")
    second = generate_password_hash("Correct Horse Battery Staple")

    assert isinstance(first, PasswordHash)
    assert first.algorithm == "pbkdf2_sha256"
    assert first.iterations >= 310000
    assert first.iterations == DEFAULT_PASSWORD_ITERATIONS
    assert first.salt != second.salt
    assert first.password_hash != second.password_hash
    assert "Correct Horse Battery Staple" not in first.password_hash
    assert "Correct Horse Battery Staple" not in first.salt


def test_verify_password_accepts_correct_password_and_rejects_wrong_password():
    """密码校验应只接受正确明文密码。"""
    password_hash = generate_password_hash("safe-password")

    assert verify_password("safe-password", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_verify_password_accepts_stored_hash_fields():
    """密码校验应能直接使用数据库中保存的 salt/hash/iterations 字段。"""
    password_hash = generate_password_hash("database-password")

    assert (
        verify_password(
            "database-password",
            password_hash.password_hash,
            salt=password_hash.salt,
            iterations=password_hash.iterations,
        )
        is True
    )
    assert (
        verify_password(
            "database-password!",
            password_hash.password_hash,
            salt=password_hash.salt,
            iterations=password_hash.iterations,
        )
        is False
    )


def test_session_token_hashing_does_not_store_raw_token():
    """Session token 应生成明文 token，但数据库只保存 token hash。"""
    token = generate_session_token()
    token_hash = hash_token(token)

    assert len(token) >= 43
    assert token not in token_hash
    assert token_hash != token
    assert verify_token_hash(token, token_hash) is True
    assert verify_token_hash(f"{token}tampered", token_hash) is False


def test_generated_session_tokens_are_unique():
    """多次生成 Session token 不应重复。"""
    tokens = {generate_session_token() for _ in range(20)}

    assert len(tokens) == 20


def test_csrf_token_can_be_generated_hashed_and_verified():
    """CSRF token 应可生成、哈希保存并校验。"""
    csrf_token = generate_csrf_token()
    csrf_hash = hash_token(csrf_token)

    assert len(csrf_token) >= 32
    assert csrf_token not in csrf_hash
    assert verify_token_hash(csrf_token, csrf_hash) is True
    assert verify_token_hash("wrong-csrf-token", csrf_hash) is False
