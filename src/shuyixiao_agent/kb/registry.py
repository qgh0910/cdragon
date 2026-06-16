"""知识库元数据 registry。"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..auth import storage


KB_SCHEMA_VERSION = 2
KB_SCHEMA_NAME = "create_knowledge_bases_table"
VALID_SCOPES = {"public", "user", "legacy_admin_only"}


def initialize_kb_registry(db_path: str | Path | None = None) -> Path:
    """初始化知识库元数据表，保持幂等。"""
    normalized_path = storage.initialize_auth_storage(db_path)
    with storage.open_auth_connection(normalized_path) as connection:
        _create_knowledge_bases_table(connection)
        _record_kb_migration(connection)
        connection.commit()
    return normalized_path


def create_knowledge_base(
    *,
    scope: str,
    display_name: str,
    created_by: str,
    owner_user_id: str | None = None,
    description: str | None = None,
    collection_original_name: str | None = None,
    collection_name: str | None = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    """创建公共库、用户库或历史待迁移库元数据。"""
    normalized_scope = _validate_scope(scope)
    normalized_display_name = _validate_display_name(display_name)
    normalized_owner_user_id = _validate_owner(normalized_scope, owner_user_id)
    original_name = collection_original_name or _build_collection_original_name(
        normalized_scope,
        normalized_display_name,
        normalized_owner_user_id,
        collection_name,
    )
    normalized_collection_name = collection_name or build_normalized_collection_name(original_name)

    initialize_kb_registry(db_path)
    kb_id = f"kb_{uuid.uuid4().hex[:12]}"
    now = _now()
    with storage.open_auth_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO knowledge_bases (
                id, scope, owner_user_id, display_name, collection_original_name,
                collection_name, description, created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kb_id,
                normalized_scope,
                normalized_owner_user_id,
                normalized_display_name,
                original_name,
                normalized_collection_name,
                description,
                created_by,
                now,
                now,
            ),
        )
        connection.commit()

    created = get_knowledge_base(kb_id, db_path=db_path)
    if created is None:
        raise RuntimeError("知识库元数据创建后读取失败")
    return created


def register_legacy_knowledge_base(
    *,
    display_name: str,
    collection_name: str,
    created_by: str,
    collection_original_name: str | None = None,
    description: str | None = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    """登记历史待迁移 Chroma collection。"""
    return create_knowledge_base(
        scope="legacy_admin_only",
        display_name=display_name,
        created_by=created_by,
        description=description,
        collection_original_name=collection_original_name or collection_name,
        collection_name=collection_name,
        db_path=db_path,
    )


def get_knowledge_base(
    kb_id: str,
    *,
    include_deleted: bool = False,
    db_path: str | Path | None = None,
) -> Dict[str, Any] | None:
    """按 ID 读取知识库元数据。"""
    initialize_kb_registry(db_path)
    query = "SELECT * FROM knowledge_bases WHERE id = ?"
    params: list[Any] = [kb_id]
    if not include_deleted:
        query += " AND deleted_at IS NULL"

    with storage.open_auth_connection(db_path) as connection:
        row = connection.execute(query, params).fetchone()
    return dict(row) if row else None


def list_knowledge_bases(
    *,
    scope: str | None = None,
    owner_user_id: str | None = None,
    include_deleted: bool = False,
    db_path: str | Path | None = None,
) -> List[Dict[str, Any]]:
    """列出知识库元数据；权限过滤由后续 permissions 模块负责。"""
    initialize_kb_registry(db_path)
    clauses: list[str] = []
    params: list[Any] = []

    if scope is not None:
        clauses.append("scope = ?")
        params.append(_validate_scope(scope))
    if owner_user_id is not None:
        clauses.append("owner_user_id = ?")
        params.append(owner_user_id)
    if not include_deleted:
        clauses.append("deleted_at IS NULL")

    query = "SELECT * FROM knowledge_bases"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at ASC, id ASC"

    with storage.open_auth_connection(db_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def soft_delete_knowledge_base(
    kb_id: str,
    *,
    db_path: str | Path | None = None,
) -> bool:
    """软删除知识库元数据，返回是否命中未删除记录。"""
    initialize_kb_registry(db_path)
    now = _now()
    with storage.open_auth_connection(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE knowledge_bases
            SET deleted_at = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (now, now, kb_id),
        )
        connection.commit()
    return cursor.rowcount > 0


def build_normalized_collection_name(name: str) -> str:
    """将内部原始名转换为 ChromaDB 合法 collection 名。"""
    if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,510}[a-zA-Z0-9]$", name):
        return name

    name_hash = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    safe_prefix = re.sub(r"[^a-zA-Z0-9._-]", "", name).strip("._-")
    if not safe_prefix or len(safe_prefix) < 2:
        safe_prefix = "kb"
    else:
        safe_prefix = safe_prefix[:20]

    normalized_name = f"{safe_prefix}_{name_hash}"
    if not re.match(r"^[a-zA-Z0-9]", normalized_name):
        normalized_name = f"kb_{normalized_name}"
    if not re.match(r"[a-zA-Z0-9]$", normalized_name):
        normalized_name = f"{normalized_name}_kb"
    if len(normalized_name) < 3:
        normalized_name = f"kb_{name_hash}_default"
    if len(normalized_name) > 512:
        normalized_name = normalized_name[:512].rstrip("._-")
    return normalized_name


def _create_knowledge_bases_table(connection: sqlite3.Connection) -> None:
    """创建知识库元数据表和索引。"""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            id TEXT PRIMARY KEY,
            scope TEXT NOT NULL CHECK (scope IN ('public', 'user', 'legacy_admin_only')),
            owner_user_id TEXT,
            display_name TEXT NOT NULL,
            collection_original_name TEXT NOT NULL,
            collection_name TEXT NOT NULL,
            description TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            deleted_at TEXT,
            CHECK (
                (scope = 'user' AND owner_user_id IS NOT NULL)
                OR (scope IN ('public', 'legacy_admin_only') AND owner_user_id IS NULL)
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_kb_active_display_owner
        ON knowledge_bases (
            scope,
            COALESCE(owner_user_id, '__none__'),
            display_name
        )
        WHERE deleted_at IS NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_kb_active_collection_name
        ON knowledge_bases (collection_name)
        WHERE deleted_at IS NULL;

        CREATE INDEX IF NOT EXISTS idx_kb_scope_owner_deleted
        ON knowledge_bases (scope, owner_user_id, deleted_at);
        """
    )


def _record_kb_migration(connection: sqlite3.Connection) -> None:
    """记录 knowledge_bases 表迁移。"""
    connection.execute(
        """
        INSERT OR IGNORE INTO schema_migrations (version, name)
        VALUES (?, ?)
        """,
        (KB_SCHEMA_VERSION, KB_SCHEMA_NAME),
    )


def _validate_scope(scope: str) -> str:
    """校验知识库 scope。"""
    normalized_scope = scope.strip()
    if normalized_scope not in VALID_SCOPES:
        raise ValueError(f"不支持的知识库 scope: {scope}")
    return normalized_scope


def _validate_display_name(display_name: str) -> str:
    """校验展示名。"""
    normalized_display_name = display_name.strip()
    if not normalized_display_name:
        raise ValueError("知识库展示名不能为空")
    return normalized_display_name


def _validate_owner(scope: str, owner_user_id: str | None) -> str | None:
    """校验 owner 与 scope 的组合。"""
    normalized_owner = owner_user_id.strip() if owner_user_id else None
    if scope == "user" and not normalized_owner:
        raise ValueError("用户知识库必须提供 owner_user_id")
    if scope in {"public", "legacy_admin_only"} and normalized_owner:
        raise ValueError("公共库和历史待迁移库不能设置 owner_user_id")
    return normalized_owner


def _build_collection_original_name(
    scope: str,
    display_name: str,
    owner_user_id: str | None,
    collection_name: str | None,
) -> str:
    """按新 registry 命名规则构造内部原始 collection 名。"""
    if scope == "public":
        return f"public__{display_name}"
    if scope == "user":
        return f"user__{owner_user_id}__{display_name}"
    return collection_name or f"legacy_admin_only__{display_name}"


def _now() -> str:
    """返回 SQLite 记录使用的时间字符串。"""
    return datetime.now().isoformat(timespec="seconds")
