"""认证配置项测试。"""

from pathlib import Path

from src.shuyixiao_agent.config import Settings


AUTH_ENV_NAMES = [
    "AUTH_SECRET_KEY",
    "INITIAL_ADMIN_USERNAME",
    "INITIAL_ADMIN_PASSWORD",
    "SESSION_EXPIRE_HOURS",
    "AUTH_COOKIE_SECURE",
    "AUTH_ALLOWED_ORIGINS",
    "AUTH_ENABLE_SERVER_PATH_IMPORT",
    "AUTH_LOGIN_RATE_LIMIT_PER_MINUTE",
]


def _clear_auth_env(monkeypatch):
    """清理认证相关环境变量，避免本机环境影响默认值测试。"""
    for name in AUTH_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_auth_config_defaults_are_readable(monkeypatch):
    """认证配置应提供安全的默认值，并可从 Settings 读取。"""
    _clear_auth_env(monkeypatch)

    settings = Settings(_env_file=None)

    assert settings.auth_secret_key == ""
    assert settings.initial_admin_username == ""
    assert settings.initial_admin_password == ""
    assert settings.session_expire_hours == 24
    assert settings.auth_cookie_secure is False
    assert settings.auth_allowed_origins == "http://127.0.0.1:8000,http://localhost:8000"
    assert settings.auth_enable_server_path_import is False
    assert settings.auth_login_rate_limit_per_minute == 5


def test_auth_config_can_be_overridden_by_environment(monkeypatch):
    """认证配置应支持通过环境变量覆盖。"""
    monkeypatch.setenv("AUTH_SECRET_KEY", "dev-secret")
    monkeypatch.setenv("INITIAL_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "local-only-password")
    monkeypatch.setenv("SESSION_EXPIRE_HOURS", "12")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("AUTH_ALLOWED_ORIGINS", "https://example.com,https://admin.example.com")
    monkeypatch.setenv("AUTH_ENABLE_SERVER_PATH_IMPORT", "true")
    monkeypatch.setenv("AUTH_LOGIN_RATE_LIMIT_PER_MINUTE", "9")

    settings = Settings(_env_file=None)

    assert settings.auth_secret_key == "dev-secret"
    assert settings.initial_admin_username == "admin"
    assert settings.initial_admin_password == "local-only-password"
    assert settings.session_expire_hours == 12
    assert settings.auth_cookie_secure is True
    assert settings.auth_allowed_origins == "https://example.com,https://admin.example.com"
    assert settings.auth_enable_server_path_import is True
    assert settings.auth_login_rate_limit_per_minute == 9


def test_env_example_documents_auth_settings():
    """环境变量示例文件应列出全部认证配置项。"""
    env_example = Path(".env.example").read_text(encoding="utf-8")

    for name in AUTH_ENV_NAMES:
        assert name in env_example
