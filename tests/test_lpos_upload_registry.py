"""LPOS 上传文件 registry 测试。"""

import pytest
from fastapi import HTTPException

from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.lpos import upload_registry


def test_initialize_lpos_upload_registry_creates_required_table(tmp_path, monkeypatch):
    """初始化 LPOS registry 应幂等创建上传文件登记表和索引。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)

    upload_registry.initialize_lpos_upload_registry()
    upload_registry.initialize_lpos_upload_registry()

    with storage.open_auth_connection(db_path) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'lpos_uploaded_files'"
        ).fetchone()
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(lpos_uploaded_files)").fetchall()
        }
        indexes = {
            row["name"]
            for row in connection.execute("PRAGMA index_list(lpos_uploaded_files)").fetchall()
        }

    assert table["name"] == "lpos_uploaded_files"
    assert {
        "file_id",
        "owner_user_id",
        "tenant_id",
        "usage_type",
        "original_filename",
        "stored_file_path",
        "file_size",
        "content_type",
        "sha256",
        "created_at",
        "deleted_at",
        "metadata_json",
    }.issubset(columns)
    assert "idx_lpos_uploaded_files_owner_tenant" in indexes
    assert "idx_lpos_uploaded_files_created_at" in indexes


def test_register_and_get_uploaded_file_preserves_metadata(tmp_path, monkeypatch):
    """上传文件登记后应能按 file_id 读取并保留 metadata。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)

    created = upload_registry.register_uploaded_file(
        file_id="20260616_120000_abcdef123456",
        owner_user_id="usr_owner",
        tenant_id="default",
        original_filename="采购合同.pdf",
        stored_file_path=str(
            tmp_path
            / "uploads"
            / "users"
            / "usr_owner"
            / "lpos"
            / "contracts"
            / "20260616_120000_abcdef123456.pdf"
        ),
        file_size=1234,
        content_type="application/pdf",
        sha256="hash123",
        metadata={"source": "unit-test"},
    )

    loaded = upload_registry.get_uploaded_file(created["file_id"])

    assert loaded["file_id"] == created["file_id"]
    assert loaded["owner_user_id"] == "usr_owner"
    assert loaded["tenant_id"] == "default"
    assert loaded["usage_type"] == "lpos_contract"
    assert loaded["original_filename"] == "采购合同.pdf"
    assert loaded["metadata"]["source"] == "unit-test"


def test_resolve_uploaded_file_for_user_enforces_owner_and_admin_access(tmp_path, monkeypatch):
    """普通用户只能读取自己文件，管理员可跨用户读取。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    stored_path = (
        tmp_path
        / "uploads"
        / "users"
        / "usr_owner"
        / "lpos"
        / "contracts"
        / "20260616_120000_abcdef123456.txt"
    )
    stored_path.parent.mkdir(parents=True)
    stored_path.write_text("合同文本", encoding="utf-8")

    upload_registry.register_uploaded_file(
        file_id="20260616_120000_abcdef123456",
        owner_user_id="usr_owner",
        tenant_id="default",
        original_filename="合同.txt",
        stored_file_path=str(stored_path),
        file_size=12,
        content_type="text/plain",
    )

    owner_record = upload_registry.resolve_uploaded_file_for_user(
        "20260616_120000_abcdef123456",
        current_user={"id": "usr_owner", "role": "user"},
        tenant_id="default",
    )
    admin_record = upload_registry.resolve_uploaded_file_for_user(
        "20260616_120000_abcdef123456",
        current_user={"id": "usr_admin", "role": "admin"},
        tenant_id="default",
    )

    assert owner_record["stored_file_path"] == str(stored_path)
    assert admin_record["owner_user_id"] == "usr_owner"

    with pytest.raises(HTTPException) as forbidden:
        upload_registry.resolve_uploaded_file_for_user(
            "20260616_120000_abcdef123456",
            current_user={"id": "usr_other", "role": "user"},
            tenant_id="default",
        )
    assert forbidden.value.status_code == 403
