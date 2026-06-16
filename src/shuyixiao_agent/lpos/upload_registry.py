"""LPOS 上传文件登记表初始化。"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException

from ..auth import storage


LPOS_UPLOAD_SCHEMA_VERSION = 20
LPOS_UPLOAD_SCHEMA_NAME = "create_lpos_uploaded_files_table"
LPOS_CONTRACT_USAGE_TYPE = "lpos_contract"
FILE_ID_PATTERN = re.compile(r"^[0-9]{8}_[0-9]{6}_[a-f0-9]{12}$")


def initialize_lpos_upload_registry(db_path: str | Path | None = None) -> Path:
    """初始化 LPOS 上传文件登记表，保持幂等。"""
    normalized_path = storage.initialize_auth_storage(db_path)
    with storage.open_auth_connection(normalized_path) as connection:
        _create_lpos_uploaded_files_table(connection)
        _record_lpos_upload_migration(connection)
        connection.commit()
    return normalized_path


def register_uploaded_file(
    *,
    file_id: str,
    owner_user_id: str,
    tenant_id: str = "default",
    original_filename: str,
    stored_file_path: str,
    file_size: int,
    content_type: str | None = None,
    sha256: str | None = None,
    metadata: Dict[str, Any] | None = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    """登记 LPOS 上传文件并返回登记记录。"""
    _validate_file_id(file_id)
    initialize_lpos_upload_registry(db_path)
    now = datetime.now().isoformat(timespec="seconds")
    metadata_json = json.dumps(metadata or {}, ensure_ascii=False)

    with storage.open_auth_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO lpos_uploaded_files (
                file_id, owner_user_id, tenant_id, usage_type, original_filename,
                stored_file_path, file_size, content_type, sha256, created_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                owner_user_id,
                tenant_id,
                LPOS_CONTRACT_USAGE_TYPE,
                original_filename,
                stored_file_path,
                file_size,
                content_type,
                sha256,
                now,
                metadata_json,
            ),
        )
        connection.commit()

    created = get_uploaded_file(file_id, db_path=db_path)
    if created is None:
        raise RuntimeError("LPOS 上传文件登记后读取失败")
    return created


def get_uploaded_file(
    file_id: str,
    *,
    include_deleted: bool = False,
    db_path: str | Path | None = None,
) -> Dict[str, Any] | None:
    """按 file_id 读取 LPOS 上传文件登记记录。"""
    _validate_file_id(file_id)
    initialize_lpos_upload_registry(db_path)
    query = "SELECT * FROM lpos_uploaded_files WHERE file_id = ?"
    params: list[Any] = [file_id]
    if not include_deleted:
        query += " AND deleted_at IS NULL"

    with storage.open_auth_connection(db_path) as connection:
        row = connection.execute(query, params).fetchone()
    return _row_to_uploaded_file(row) if row else None


def resolve_uploaded_file_for_user(
    file_id: str,
    *,
    current_user: Dict[str, Any],
    tenant_id: str = "default",
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    """按当前用户权限解析 LPOS 上传文件登记记录。"""
    record = get_uploaded_file(file_id, db_path=db_path)
    if record is None or record["tenant_id"] != tenant_id:
        raise HTTPException(status_code=404, detail="上传文件不存在")

    if current_user.get("role") == "admin":
        return record

    if record["owner_user_id"] != current_user.get("id"):
        raise HTTPException(status_code=403, detail="无权访问该上传文件")

    return record


def _create_lpos_uploaded_files_table(connection) -> None:
    """创建 LPOS 上传文件登记表和索引。"""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS lpos_uploaded_files (
            file_id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            usage_type TEXT NOT NULL DEFAULT 'lpos_contract',
            original_filename TEXT NOT NULL,
            stored_file_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            content_type TEXT,
            sha256 TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            deleted_at TEXT,
            metadata_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_lpos_uploaded_files_owner_tenant
        ON lpos_uploaded_files (owner_user_id, tenant_id, usage_type);

        CREATE INDEX IF NOT EXISTS idx_lpos_uploaded_files_created_at
        ON lpos_uploaded_files (created_at);
        """
    )


def _record_lpos_upload_migration(connection) -> None:
    """记录 LPOS 上传文件表迁移。"""
    connection.execute(
        """
        INSERT OR IGNORE INTO schema_migrations (version, name)
        VALUES (?, ?)
        """,
        (LPOS_UPLOAD_SCHEMA_VERSION, LPOS_UPLOAD_SCHEMA_NAME),
    )


def _row_to_uploaded_file(row) -> Dict[str, Any]:
    """将 SQLite 行转换为上传文件登记字典。"""
    record = dict(row)
    metadata_json = record.pop("metadata_json", None)
    record["metadata"] = json.loads(metadata_json) if metadata_json else {}
    return record


def _validate_file_id(file_id: str) -> None:
    """校验 LPOS 上传文件 ID 格式。"""
    if not FILE_ID_PATTERN.match(file_id):
        raise ValueError(f"不合法的 LPOS 上传文件 ID: {file_id}")
