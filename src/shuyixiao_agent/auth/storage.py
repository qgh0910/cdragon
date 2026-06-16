"""认证 SQLite 存储初始化。"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict
from pathlib import Path

from .password import PasswordHash


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AUTH_DB_PATH = PROJECT_ROOT / "data" / "app" / "app.sqlite3"
BUSY_TIMEOUT_MS = 5000
CORE_SCHEMA_VERSION = 1
CORE_SCHEMA_NAME = "create_auth_core_tables"


def _normalize_db_path(db_path: str | Path | None = None) -> Path:
    """标准化认证数据库路径。"""
    return Path(db_path or DEFAULT_AUTH_DB_PATH).expanduser()


def _configure_connection(connection: sqlite3.Connection) -> None:
    """为认证数据库连接启用必要 SQLite PRAGMA。"""
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    connection.execute("PRAGMA journal_mode=WAL")


def open_auth_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """打开认证 SQLite 连接，并启用外键、WAL 和 busy timeout。"""
    normalized_path = _normalize_db_path(db_path)
    normalized_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(normalized_path)
    _configure_connection(connection)
    return connection


def initialize_auth_storage(db_path: str | Path | None = None) -> Path:
    """初始化认证数据库，幂等创建基础表结构。"""
    normalized_path = _normalize_db_path(db_path)

    with open_auth_connection(normalized_path) as connection:
        _ensure_schema_migrations_table(connection)
        if not _is_migration_applied(connection, CORE_SCHEMA_VERSION):
            _create_core_tables(connection)
            _record_migration(connection, CORE_SCHEMA_VERSION, CORE_SCHEMA_NAME)
        connection.commit()

    return normalized_path


def count_users(db_path: str | Path | None = None) -> int:
    """返回用户数量。"""
    initialize_auth_storage(db_path)
    with open_auth_connection(db_path) as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return int(row["count"])


def create_user(
    *,
    username: str,
    display_name: str,
    password_hash: PasswordHash,
    role: str = "user",
    is_active: bool = True,
    must_change_password: bool = False,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    """创建用户并返回用户记录。"""
    initialize_auth_storage(db_path)
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat(timespec="seconds")
    with open_auth_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO users (
                id, username, display_name, password_salt, password_hash,
                password_iterations, role, is_active, must_change_password,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                display_name,
                password_hash.salt,
                password_hash.password_hash,
                password_hash.iterations,
                role,
                int(is_active),
                int(must_change_password),
                now,
                now,
            ),
        )
        connection.commit()
    return get_user_by_id(user_id, db_path=db_path)


def get_user_by_username(
    username: str,
    db_path: str | Path | None = None,
) -> Dict[str, Any] | None:
    """按用户名读取用户。"""
    initialize_auth_storage(db_path)
    with open_auth_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_id(
    user_id: str,
    db_path: str | Path | None = None,
) -> Dict[str, Any] | None:
    """按用户 ID 读取用户。"""
    initialize_auth_storage(db_path)
    with open_auth_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return _row_to_user(row) if row else None


def update_user_password(
    user_id: str,
    password_hash: PasswordHash,
    *,
    must_change_password: bool = False,
    db_path: str | Path | None = None,
) -> None:
    """更新用户密码哈希。"""
    now = datetime.now().isoformat(timespec="seconds")
    with open_auth_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE users
            SET password_salt = ?,
                password_hash = ?,
                password_iterations = ?,
                must_change_password = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                password_hash.salt,
                password_hash.password_hash,
                password_hash.iterations,
                int(must_change_password),
                now,
                user_id,
            ),
        )
        connection.commit()


def mark_user_login(user_id: str, db_path: str | Path | None = None) -> None:
    """记录用户最近登录时间。"""
    now = datetime.now().isoformat(timespec="seconds")
    with open_auth_connection(db_path) as connection:
        connection.execute(
            "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (now, now, user_id),
        )
        connection.commit()


def create_session(
    *,
    id_hash: str,
    user_id: str,
    csrf_token_hash: str,
    expires_at: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    """创建服务端 Session 记录。"""
    created_at = datetime.now().isoformat(timespec="seconds")
    with open_auth_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO sessions (
                id_hash, user_id, csrf_token_hash, created_at, expires_at,
                user_agent, ip_address
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_hash,
                user_id,
                csrf_token_hash,
                created_at,
                expires_at,
                user_agent,
                ip_address,
            ),
        )
        connection.commit()


def get_session_by_hash(
    id_hash: str,
    db_path: str | Path | None = None,
) -> Dict[str, Any] | None:
    """按 Session token hash 读取 Session。"""
    initialize_auth_storage(db_path)
    with open_auth_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM sessions WHERE id_hash = ?",
            (id_hash,),
        ).fetchone()
    return dict(row) if row else None


def revoke_session(id_hash: str, db_path: str | Path | None = None) -> None:
    """撤销指定 Session。"""
    revoked_at = datetime.now().isoformat(timespec="seconds")
    with open_auth_connection(db_path) as connection:
        connection.execute(
            "UPDATE sessions SET revoked_at = ? WHERE id_hash = ?",
            (revoked_at, id_hash),
        )
        connection.commit()


def _row_to_user(row: sqlite3.Row) -> Dict[str, Any]:
    """将 SQLite 用户行转换为普通字典并规范布尔字段。"""
    user = dict(row)
    user["is_active"] = bool(user["is_active"])
    user["must_change_password"] = bool(user["must_change_password"])
    return user


def _ensure_schema_migrations_table(connection: sqlite3.Connection) -> None:
    """创建迁移记录表。"""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _is_migration_applied(connection: sqlite3.Connection, version: int) -> bool:
    """检查指定迁移是否已经执行。"""
    row = connection.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ?",
        (version,),
    ).fetchone()
    return row is not None


def _record_migration(connection: sqlite3.Connection, version: int, name: str) -> None:
    """记录已执行迁移。"""
    connection.execute(
        """
        INSERT OR IGNORE INTO schema_migrations (version, name)
        VALUES (?, ?)
        """,
        (version, name),
    )


def _create_core_tables(connection: sqlite3.Connection) -> None:
    """创建认证核心表。"""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            password_iterations INTEGER NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_login_at TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            csrf_token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            user_agent TEXT,
            ip_address TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            actor_user_id TEXT,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            scope TEXT,
            status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
            detail_json TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
        CREATE INDEX IF NOT EXISTS idx_audit_log_actor_user_id ON audit_log(actor_user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
        """
    )
