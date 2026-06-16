"""认证与会话基础模块。"""

from .storage import DEFAULT_AUTH_DB_PATH, initialize_auth_storage, open_auth_connection

__all__ = [
    "DEFAULT_AUTH_DB_PATH",
    "initialize_auth_storage",
    "open_auth_connection",
]
