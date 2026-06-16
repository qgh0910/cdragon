"""知识库权限解析器测试。"""

import pytest
from fastapi import HTTPException

from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.kb import registry
from src.shuyixiao_agent.kb.permissions import resolve_knowledge_base


def _configure_permissions_db(tmp_path, monkeypatch):
    """将权限测试隔离到临时 SQLite 数据库。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    return db_path


def _user(user_id: str, role: str = "user") -> dict:
    """构造当前用户字典。"""
    return {
        "id": user_id,
        "username": user_id,
        "display_name": user_id,
        "role": role,
        "is_active": True,
    }


def _assert_denied(status_code: int, func, *args, **kwargs):
    """断言权限解析被拒绝。"""
    with pytest.raises(HTTPException) as exc_info:
        func(*args, **kwargs)
    assert exc_info.value.status_code == status_code


def test_public_knowledge_base_readable_by_user_but_writable_only_by_admin(tmp_path, monkeypatch):
    """公共库所有登录用户可读，写/删仅管理员可用。"""
    _configure_permissions_db(tmp_path, monkeypatch)
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="法规案例库",
        created_by="usr_admin",
    )

    resolved_for_user = resolve_knowledge_base(_user("usr_user"), public_kb["id"], "read")
    resolved_for_admin_write = resolve_knowledge_base(
        _user("usr_admin", role="admin"),
        public_kb["id"],
        "write",
    )

    assert resolved_for_user["id"] == public_kb["id"]
    assert resolved_for_user["collection_name"] == public_kb["collection_name"]
    assert resolved_for_admin_write["scope"] == "public"
    _assert_denied(403, resolve_knowledge_base, _user("usr_user"), public_kb["id"], "write")
    _assert_denied(403, resolve_knowledge_base, _user("usr_user"), public_kb["id"], "delete")


def test_user_knowledge_base_allows_owner_and_hides_from_other_users(tmp_path, monkeypatch):
    """用户库仅 owner 可读写删，其他用户和非 owner 管理员默认不可见。"""
    _configure_permissions_db(tmp_path, monkeypatch)
    owner_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id="usr_owner",
        display_name="我的合同模板",
        created_by="usr_owner",
    )
    admin_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id="usr_admin",
        display_name="管理员自己的库",
        created_by="usr_admin",
    )

    assert resolve_knowledge_base(_user("usr_owner"), owner_kb["id"], "read")["owner_user_id"] == "usr_owner"
    assert resolve_knowledge_base(_user("usr_owner"), owner_kb["id"], "write")["id"] == owner_kb["id"]
    assert resolve_knowledge_base(_user("usr_owner"), owner_kb["id"], "delete")["id"] == owner_kb["id"]
    assert resolve_knowledge_base(_user("usr_admin", role="admin"), admin_kb["id"], "write")["id"] == admin_kb["id"]

    _assert_denied(404, resolve_knowledge_base, _user("usr_other"), owner_kb["id"], "read")
    _assert_denied(404, resolve_knowledge_base, _user("usr_other"), owner_kb["id"], "write")
    _assert_denied(404, resolve_knowledge_base, _user("usr_admin", role="admin"), owner_kb["id"], "delete")


def test_deleted_or_missing_knowledge_base_returns_404(tmp_path, monkeypatch):
    """不存在或已删除的知识库应返回 404。"""
    _configure_permissions_db(tmp_path, monkeypatch)
    public_kb = registry.create_knowledge_base(
        scope="public",
        display_name="临时公共库",
        created_by="usr_admin",
    )
    registry.soft_delete_knowledge_base(public_kb["id"])

    _assert_denied(404, resolve_knowledge_base, _user("usr_admin", role="admin"), public_kb["id"], "read")
    _assert_denied(404, resolve_knowledge_base, _user("usr_admin", role="admin"), "kb_missing", "read")


def test_legacy_admin_only_is_visible_only_to_admin(tmp_path, monkeypatch):
    """legacy_admin_only 仅管理员可见和可写。"""
    _configure_permissions_db(tmp_path, monkeypatch)
    legacy_kb = registry.register_legacy_knowledge_base(
        display_name="旧资料库",
        collection_name="old_collection",
        created_by="usr_admin",
    )

    resolved = resolve_knowledge_base(_user("usr_admin", role="admin"), legacy_kb["id"], "read")

    assert resolved["scope"] == "legacy_admin_only"
    assert resolve_knowledge_base(_user("usr_admin", role="admin"), legacy_kb["id"], "write")["id"] == legacy_kb["id"]
    _assert_denied(404, resolve_knowledge_base, _user("usr_user"), legacy_kb["id"], "read")
    _assert_denied(404, resolve_knowledge_base, _user("usr_user"), legacy_kb["id"], "write")


def test_unauthorized_or_missing_kb_does_not_touch_rag_runtime(tmp_path, monkeypatch):
    """无权限或不存在 kb_id 不应触发会自动创建 collection 的 RAG 运行时。"""
    _configure_permissions_db(tmp_path, monkeypatch)
    owner_kb = registry.create_knowledge_base(
        scope="user",
        owner_user_id="usr_owner",
        display_name="私有库",
        created_by="usr_owner",
    )

    def fail_if_rag_is_touched(*args, **kwargs):
        raise AssertionError("权限解析不应调用 get_rag_agent")

    monkeypatch.setattr(
        "src.shuyixiao_agent.web_app.get_rag_agent",
        fail_if_rag_is_touched,
    )

    _assert_denied(404, resolve_knowledge_base, _user("usr_other"), owner_kb["id"], "read")
    _assert_denied(404, resolve_knowledge_base, _user("usr_other"), "kb_missing", "read")
