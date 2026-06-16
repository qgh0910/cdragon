"""认证 SQLite 存储基础测试。"""

import sqlite3
from pathlib import Path

from src.shuyixiao_agent.auth.storage import (
    DEFAULT_AUTH_DB_PATH,
    initialize_auth_storage,
    open_auth_connection,
)


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    """读取指定表的列名集合。"""
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _table_names(connection: sqlite3.Connection) -> set[str]:
    """读取数据库中的业务表名。"""
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    return {row["name"] for row in rows}


def test_default_auth_database_path_is_data_app_sqlite():
    """默认认证数据库路径应落在 data/app/app.sqlite3。"""
    assert DEFAULT_AUTH_DB_PATH.parts[-3:] == ("data", "app", "app.sqlite3")


def test_initialize_auth_storage_creates_required_tables(tmp_path):
    """初始化认证存储时应创建用户、会话、审计和迁移表。"""
    db_path = tmp_path / "nested" / "app.sqlite3"

    initialized_path = initialize_auth_storage(db_path)

    assert initialized_path == db_path
    assert db_path.exists()

    with open_auth_connection(db_path) as connection:
        assert _table_names(connection) == {
            "schema_migrations",
            "users",
            "sessions",
            "audit_log",
        }
        assert _table_columns(connection, "users") >= {
            "id",
            "username",
            "display_name",
            "password_salt",
            "password_hash",
            "password_iterations",
            "role",
            "is_active",
            "must_change_password",
            "created_at",
            "updated_at",
            "last_login_at",
        }
        assert _table_columns(connection, "sessions") >= {
            "id_hash",
            "user_id",
            "csrf_token_hash",
            "created_at",
            "expires_at",
            "revoked_at",
            "user_agent",
            "ip_address",
        }
        assert _table_columns(connection, "audit_log") >= {
            "id",
            "actor_user_id",
            "action",
            "resource_type",
            "resource_id",
            "scope",
            "status",
            "detail_json",
            "ip_address",
            "created_at",
        }
        assert _table_columns(connection, "schema_migrations") >= {
            "version",
            "name",
            "applied_at",
        }


def test_initialize_auth_storage_is_idempotent_and_preserves_data(tmp_path):
    """重复初始化不应重复迁移记录，也不应破坏已有数据。"""
    db_path = tmp_path / "app.sqlite3"
    initialize_auth_storage(db_path)

    with open_auth_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO users (
                id, username, display_name, password_salt, password_hash,
                password_iterations, role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("usr_test", "alice", "Alice", "salt", "hash", 310000, "admin"),
        )
        connection.commit()

    initialize_auth_storage(db_path)

    with open_auth_connection(db_path) as connection:
        migration_rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        user_count = connection.execute(
            "SELECT COUNT(*) AS count FROM users WHERE username = ?",
            ("alice",),
        ).fetchone()["count"]

    assert [dict(row) for row in migration_rows] == [
        {"version": 1, "name": "create_auth_core_tables"}
    ]
    assert user_count == 1


def test_open_auth_connection_enables_sqlite_pragmas(tmp_path):
    """认证数据库连接应启用 foreign keys、WAL 和 busy timeout。"""
    db_path = tmp_path / "app.sqlite3"
    initialize_auth_storage(db_path)

    with open_auth_connection(db_path) as connection:
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]

    assert foreign_keys == 1
    assert journal_mode.lower() == "wal"
    assert busy_timeout >= 5000


def test_sessions_enforce_user_foreign_key(tmp_path):
    """sessions.user_id 应受 users.id 外键约束保护。"""
    db_path = tmp_path / "app.sqlite3"
    initialize_auth_storage(db_path)

    with open_auth_connection(db_path) as connection:
        try:
            connection.execute(
                """
                INSERT INTO sessions (
                    id_hash, user_id, csrf_token_hash, created_at, expires_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "session_hash",
                    "usr_missing",
                    "csrf_hash",
                    "2026-06-10T00:00:00",
                    "2026-06-11T00:00:00",
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            foreign_key_failed = True
        else:
            foreign_key_failed = False

    assert foreign_key_failed is True
