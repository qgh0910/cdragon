"""LPOS 合同上传 API 测试。"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.auth.password import generate_password_hash
from src.shuyixiao_agent.lpos import upload_registry


def _configure_lpos_contract_test_app(tmp_path, monkeypatch, *, mock_parser=True):
    """将 LPOS 合同上传测试隔离到临时认证库和上传目录。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    upload_root = tmp_path / "uploads"
    parsed_calls = []
    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    monkeypatch.setattr(web_app.settings, "upload_root_path", str(upload_root))
    if mock_parser:
        monkeypatch.setattr(
            web_app,
            "parse_contract_file",
            lambda file_path, **kwargs: parsed_calls.append({"file_path": file_path, "kwargs": kwargs})
            or {
                "text": Path(file_path).read_text(encoding="utf-8"),
                "document_count": 1,
                "contract_structure": None,
                "contract_structure_summary": None,
                "parse_warnings": [],
                "metadata": {"structure_status": "text_only", "document_count": 1},
            },
        )
    return TestClient(web_app.app), upload_root, parsed_calls


def _create_regular_user(username: str = "reviewer", password: str = "user-secret"):
    """创建普通测试用户并返回用户记录。"""
    return storage.create_user(
        username=username,
        display_name="普通用户",
        password_hash=generate_password_hash(password),
        role="user",
    )


def _login(client: TestClient, username: str, password: str):
    """登录指定测试用户。"""
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def _contract_audit_row(action: str):
    """读取指定 LPOS 合同审计事件。"""
    with storage.open_auth_connection() as connection:
        row = connection.execute(
            "SELECT * FROM audit_log WHERE action = ? ORDER BY created_at DESC LIMIT 1",
            (action,),
        ).fetchone()
    return row


def test_contract_upload_requires_login(tmp_path, monkeypatch):
    """未登录用户不能上传合同。"""
    client, _, _ = _configure_lpos_contract_test_app(tmp_path, monkeypatch)

    response = client.post(
        "/api/lpos/contracts/upload",
        files={"file": ("contract.txt", b"contract text", "text/plain")},
    )

    assert response.status_code == 401


def test_contract_upload_saves_under_user_scope_and_registers_file(tmp_path, monkeypatch):
    """合同上传后应保存到当前用户目录并写入 registry。"""
    client, upload_root, _ = _configure_lpos_contract_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/lpos/contracts/upload",
        data={"parse_after_upload": "false"},
        files={"file": ("contract.txt", b"contract text", "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    stored_path = Path(body["stored_file_path"])
    assert stored_path.is_file()
    assert stored_path.is_relative_to(upload_root / "users" / user["id"] / "lpos" / "contracts")

    record = upload_registry.get_uploaded_file(body["file_id"])
    assert record["owner_user_id"] == user["id"]
    assert record["original_filename"] == "contract.txt"
    assert record["stored_file_path"] == str(stored_path)
    audit_row = _contract_audit_row("contract_upload")
    assert audit_row["actor_user_id"] == user["id"]
    assert audit_row["resource_id"] == body["file_id"]
    assert audit_row["status"] == "success"


def test_regular_user_cannot_parse_another_users_file_id(tmp_path, monkeypatch):
    """普通用户不能通过 file_id 解析其他用户登记的合同。"""
    client, upload_root, _ = _configure_lpos_contract_test_app(tmp_path, monkeypatch)
    owner = _create_regular_user("owner", "owner-secret")
    _create_regular_user("reviewer", "user-secret")
    stored_path = (
        upload_root
        / "users"
        / owner["id"]
        / "lpos"
        / "contracts"
        / "20260616_120000_abcdef123456.txt"
    )
    stored_path.parent.mkdir(parents=True)
    stored_path.write_text("owner contract", encoding="utf-8")
    upload_registry.register_uploaded_file(
        file_id="20260616_120000_abcdef123456",
        owner_user_id=owner["id"],
        tenant_id="default",
        original_filename="owner.txt",
        stored_file_path=str(stored_path),
        file_size=14,
        content_type="text/plain",
    )
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/lpos/contracts/parse",
        json={"file_id": "20260616_120000_abcdef123456"},
    )

    assert response.status_code == 403
    audit_row = _contract_audit_row("contract_parse_forbidden")
    detail = json.loads(audit_row["detail_json"])
    assert audit_row["actor_user_id"] is not None
    assert audit_row["status"] == "failed"
    assert detail["target_owner_user_id"] == owner["id"]
    assert "stored_file_path" not in detail


def test_admin_can_parse_registered_file_owned_by_another_user(tmp_path, monkeypatch):
    """管理员可以解析已登记的其他用户 LPOS 合同文件。"""
    client, upload_root, _ = _configure_lpos_contract_test_app(tmp_path, monkeypatch)
    _login(client, "admin", "admin-secret")
    owner = _create_regular_user("owner", "owner-secret")
    stored_path = (
        upload_root
        / "users"
        / owner["id"]
        / "lpos"
        / "contracts"
        / "20260616_120000_abcdef123456.txt"
    )
    stored_path.parent.mkdir(parents=True)
    stored_path.write_text("owner contract", encoding="utf-8")
    upload_registry.register_uploaded_file(
        file_id="20260616_120000_abcdef123456",
        owner_user_id=owner["id"],
        tenant_id="default",
        original_filename="owner.txt",
        stored_file_path=str(stored_path),
        file_size=14,
        content_type="text/plain",
    )

    response = client.post(
        "/api/lpos/contracts/parse",
        json={"file_id": "20260616_120000_abcdef123456"},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "owner contract"
    audit_row = _contract_audit_row("contract_parse_text_only")
    detail = json.loads(audit_row["detail_json"])
    assert detail["admin_user_id"] == audit_row["actor_user_id"]
    assert detail["target_owner_user_id"] == owner["id"]


def test_contract_parse_response_includes_structure_summary_by_default(tmp_path, monkeypatch):
    """解析接口默认返回结构化结果，并隐藏完整条款正文。"""
    client, upload_root, _ = _configure_lpos_contract_test_app(
        tmp_path,
        monkeypatch,
        mock_parser=False,
    )
    user = _create_regular_user("reviewer")
    stored_path = (
        upload_root
        / "users"
        / user["id"]
        / "lpos"
        / "contracts"
        / "20260616_120000_abcdef123456.txt"
    )
    stored_path.parent.mkdir(parents=True)
    stored_path.write_text(
        "采购合同\n甲方：A公司\n乙方：B公司\n第一条 付款\n按期付款。",
        encoding="utf-8",
    )
    upload_registry.register_uploaded_file(
        file_id="20260616_120000_abcdef123456",
        owner_user_id=user["id"],
        tenant_id="default",
        original_filename="contract.txt",
        stored_file_path=str(stored_path),
        file_size=50,
        content_type="text/plain",
    )
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/lpos/contracts/parse",
        json={"file_id": "20260616_120000_abcdef123456"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["contract_structure_summary"]["contract_type"] == "采购合同"
    assert body["metadata"]["structure_status"] == "success"
    assert "content" not in body["contract_structure"]["clauses"][0]
    assert "page_index" not in body
    audit_row = _contract_audit_row("contract_parse_success")
    detail = json.loads(audit_row["detail_json"])
    assert audit_row["actor_user_id"] == user["id"]
    assert detail["structure_status"] == "success"
    assert detail["clause_count"] == 1
    assert "contract_text" not in detail


def test_contract_parse_empty_text_returns_422(tmp_path, monkeypatch):
    """文件存在但无法抽取有效文本时返回 422。"""
    client, upload_root, _ = _configure_lpos_contract_test_app(
        tmp_path,
        monkeypatch,
        mock_parser=False,
    )
    user = _create_regular_user("reviewer")
    stored_path = (
        upload_root
        / "users"
        / user["id"]
        / "lpos"
        / "contracts"
        / "20260616_120000_abcdef123456.txt"
    )
    stored_path.parent.mkdir(parents=True)
    stored_path.write_text("   ", encoding="utf-8")
    upload_registry.register_uploaded_file(
        file_id="20260616_120000_abcdef123456",
        owner_user_id=user["id"],
        tenant_id="default",
        original_filename="empty.txt",
        stored_file_path=str(stored_path),
        file_size=3,
        content_type="text/plain",
    )
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/lpos/contracts/parse",
        json={"file_id": "20260616_120000_abcdef123456"},
    )

    assert response.status_code == 422
    audit_row = _contract_audit_row("contract_parse_failed")
    assert audit_row["actor_user_id"] == user["id"]
    assert audit_row["status"] == "failed"


def test_contract_parse_missing_registered_file_records_failed_audit(tmp_path, monkeypatch):
    """登记存在但物理文件缺失时应返回 404 并记录失败审计。"""
    client, upload_root, _ = _configure_lpos_contract_test_app(tmp_path, monkeypatch)
    user = _create_regular_user("reviewer")
    missing_path = (
        upload_root
        / "users"
        / user["id"]
        / "lpos"
        / "contracts"
        / "20260616_120000_abcdef123456.txt"
    )
    upload_registry.register_uploaded_file(
        file_id="20260616_120000_abcdef123456",
        owner_user_id=user["id"],
        tenant_id="default",
        original_filename="missing.txt",
        stored_file_path=str(missing_path),
        file_size=10,
        content_type="text/plain",
    )
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/lpos/contracts/parse",
        json={"file_id": "20260616_120000_abcdef123456"},
    )

    assert response.status_code == 404
    audit_row = _contract_audit_row("contract_parse_failed")
    detail = json.loads(audit_row["detail_json"])
    assert audit_row["status"] == "failed"
    assert detail["error_code"] == "http_404"
    assert str(upload_root) not in audit_row["detail_json"]


def test_contract_parse_uses_threadpool_and_forwards_structure_options(tmp_path, monkeypatch):
    """解析路由应在线程池执行同步解析并透传结构化选项。"""
    client, upload_root, parsed_calls = _configure_lpos_contract_test_app(tmp_path, monkeypatch)
    threadpool_calls = []

    async def fake_run_in_threadpool(function, *args, **kwargs):
        threadpool_calls.append({"function": function, "args": args, "kwargs": kwargs})
        return function(*args, **kwargs)

    monkeypatch.setattr(web_app, "run_in_threadpool", fake_run_in_threadpool, raising=False)
    user = _create_regular_user("reviewer")
    stored_path = (
        upload_root
        / "users"
        / user["id"]
        / "lpos"
        / "contracts"
        / "20260616_120000_abcdef123456.txt"
    )
    stored_path.parent.mkdir(parents=True)
    stored_path.write_text("合同正文", encoding="utf-8")
    upload_registry.register_uploaded_file(
        file_id="20260616_120000_abcdef123456",
        owner_user_id=user["id"],
        tenant_id="default",
        original_filename="contract.txt",
        stored_file_path=str(stored_path),
        file_size=12,
        content_type="text/plain",
    )
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/lpos/contracts/parse",
        json={
            "file_id": "20260616_120000_abcdef123456",
            "parse_structure": False,
            "include_clause_content": True,
            "include_page_index": True,
        },
    )

    assert response.status_code == 200
    assert len(threadpool_calls) == 1
    assert parsed_calls[0]["kwargs"] == {
        "file_id": "20260616_120000_abcdef123456",
        "original_filename": "contract.txt",
        "parse_structure": False,
        "include_clause_content": True,
        "include_page_index": True,
    }


def test_contract_upload_uses_threadpool_and_returns_structure_fields(tmp_path, monkeypatch):
    """上传后立即解析应使用线程池，并返回与解析接口一致的结构字段。"""
    client, _, parsed_calls = _configure_lpos_contract_test_app(tmp_path, monkeypatch)
    threadpool_calls = []

    async def fake_run_in_threadpool(function, *args, **kwargs):
        threadpool_calls.append({"function": function, "args": args, "kwargs": kwargs})
        return function(*args, **kwargs)

    monkeypatch.setattr(web_app, "run_in_threadpool", fake_run_in_threadpool, raising=False)
    _create_regular_user("reviewer")
    _login(client, "reviewer", "user-secret")

    response = client.post(
        "/api/lpos/contracts/upload",
        data={
            "parse_after_upload": "true",
            "parse_structure": "false",
            "include_clause_content": "true",
            "include_page_index": "true",
        },
        files={"file": ("contract.txt", b"contract text", "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["parsed"] is True
    assert body["contract_structure"] is None
    assert body["contract_structure_summary"] is None
    assert body["parse_warnings"] == []
    assert len(threadpool_calls) == 1
    assert parsed_calls[0]["kwargs"]["parse_structure"] is False
    assert parsed_calls[0]["kwargs"]["include_clause_content"] is True
    assert parsed_calls[0]["kwargs"]["include_page_index"] is True
