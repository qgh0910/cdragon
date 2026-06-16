"""知识库元数据 registry 测试。"""

import sqlite3

import pytest

from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.kb import registry


def _configure_registry_db(tmp_path, monkeypatch):
    """将知识库 registry 测试隔离到临时 SQLite 数据库。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    return db_path


def test_initialize_kb_registry_creates_knowledge_bases_table(tmp_path, monkeypatch):
    """初始化 registry 应幂等创建 knowledge_bases 表。"""
    db_path = _configure_registry_db(tmp_path, monkeypatch)

    registry.initialize_kb_registry()
    registry.initialize_kb_registry()

    with storage.open_auth_connection(db_path) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'knowledge_bases'"
        ).fetchone()
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(knowledge_bases)").fetchall()
        }

    assert table["name"] == "knowledge_bases"
    assert {
        "id",
        "scope",
        "owner_user_id",
        "display_name",
        "collection_original_name",
        "collection_name",
        "description",
        "created_by",
        "created_at",
        "updated_at",
        "deleted_at",
    }.issubset(columns)


def test_create_public_and_user_knowledge_bases(tmp_path, monkeypatch):
    """registry 应可创建公共库和用户库，并生成新命名规则下的 collection 名。"""
    _configure_registry_db(tmp_path, monkeypatch)

    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="法规案例库",
        created_by="usr_admin",
        description="公共法规、案例、企业制度",
    )
    user_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id="usr_owner",
        display_name="我的合同模板",
        created_by="usr_owner",
    )

    assert public_kb["id"].startswith("kb_")
    assert public_kb["scope"] == "public"
    assert public_kb["owner_user_id"] is None
    assert public_kb["collection_original_name"] == "public__法规案例库"
    assert public_kb["collection_name"]
    assert public_kb["description"] == "公共法规、案例、企业制度"

    assert user_kb["scope"] == "user"
    assert user_kb["owner_user_id"] == "usr_owner"
    assert user_kb["collection_original_name"] == "user__usr_owner__我的合同模板"
    assert user_kb["collection_name"] != public_kb["collection_name"]


def test_same_owner_display_name_must_be_unique_until_soft_deleted(tmp_path, monkeypatch):
    """同一 owner 下未删除知识库展示名必须唯一，软删除后可重新创建。"""
    _configure_registry_db(tmp_path, monkeypatch)
    first = registry.create_knowledge_base(
        scope="user",
        owner_user_id="usr_owner",
        display_name="合同模板",
        created_by="usr_owner",
    )

    with pytest.raises(sqlite3.IntegrityError):
        registry.create_knowledge_base(
            scope="user",
            owner_user_id="usr_owner",
            display_name="合同模板",
            created_by="usr_owner",
        )

    other_owner = registry.create_knowledge_base(
        scope="user",
        owner_user_id="usr_other",
        display_name="合同模板",
        created_by="usr_other",
    )
    registry.soft_delete_knowledge_base(first["id"])
    recreated = registry.create_knowledge_base(
        scope="user",
        owner_user_id="usr_owner",
        display_name="合同模板",
        created_by="usr_owner",
    )

    assert other_owner["owner_user_id"] == "usr_other"
    assert recreated["id"] != first["id"]


def test_soft_deleted_knowledge_base_is_hidden_by_default(tmp_path, monkeypatch):
    """软删除后默认查询和列表不再返回该知识库。"""
    _configure_registry_db(tmp_path, monkeypatch)
    kb = registry.create_knowledge_base(
        scope="public",
        display_name="待删除公共库",
        created_by="usr_admin",
    )

    registry.soft_delete_knowledge_base(kb["id"])

    assert registry.get_knowledge_base(kb["id"]) is None
    assert registry.get_knowledge_base(kb["id"], include_deleted=True)["deleted_at"]
    assert registry.list_knowledge_bases() == []


def test_legacy_admin_only_knowledge_base_can_be_registered(tmp_path, monkeypatch):
    """历史待迁移 collection 应可登记为 legacy_admin_only。"""
    _configure_registry_db(tmp_path, monkeypatch)

    legacy_kb = registry.register_legacy_knowledge_base(
        display_name="旧资料库",
        collection_name="old_collection",
        created_by="usr_admin",
        collection_original_name="old original name",
        description="待人工确认归属",
    )

    assert legacy_kb["scope"] == "legacy_admin_only"
    assert legacy_kb["owner_user_id"] is None
    assert legacy_kb["collection_name"] == "old_collection"
    assert legacy_kb["collection_original_name"] == "old original name"
    assert legacy_kb["description"] == "待人工确认归属"
    assert registry.list_knowledge_bases(scope="legacy_admin_only") == [legacy_kb]
