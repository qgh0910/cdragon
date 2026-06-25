"""服务器路径导入与解析权限测试。"""

from pathlib import Path

from fastapi.testclient import TestClient

from src.shuyixiao_agent import web_app
from src.shuyixiao_agent.auth import storage
from src.shuyixiao_agent.auth.password import generate_password_hash
from src.shuyixiao_agent.kb import registry


class _FakeRAGAgent:
    """避免测试触发真实向量库和嵌入服务。"""

    def add_documents_from_file(self, file_path: str, show_progress: bool = True) -> int:
        return 1

    def add_documents_from_directory(
        self,
        directory_path: str,
        glob_pattern: str = "**/*.*",
        show_progress: bool = True,
    ) -> int:
        return 2

    def get_document_count(self) -> int:
        return 3


def _configure_server_path_test_app(tmp_path, monkeypatch):
    """将路径权限测试隔离到临时认证库和上传根目录。"""
    db_path = tmp_path / "auth" / "app.sqlite3"
    upload_root = tmp_path / "uploads"
    allowed_dir = upload_root / "server-imports"
    allowed_dir.mkdir(parents=True)

    monkeypatch.setattr(storage, "DEFAULT_AUTH_DB_PATH", db_path)
    monkeypatch.setattr(web_app.settings, "initial_admin_username", "admin")
    monkeypatch.setattr(web_app.settings, "initial_admin_password", "admin-secret")
    monkeypatch.setattr(web_app.settings, "session_expire_hours", 24)
    monkeypatch.setattr(web_app.settings, "auth_cookie_secure", False)
    monkeypatch.setattr(web_app.settings, "upload_root_path", str(upload_root))
    monkeypatch.setattr(web_app, "get_rag_agent", lambda collection_name: _FakeRAGAgent())
    monkeypatch.setattr(
        web_app,
        "parse_contract_file",
        lambda file_path, **kwargs: {
            "text": Path(file_path).read_text(encoding="utf-8"),
            "document_count": 1,
            "contract_structure": None,
            "contract_structure_summary": None,
            "parse_warnings": [],
            "metadata": {"structure_status": "text_only", "document_count": 1},
        },
    )
    return TestClient(web_app.app), allowed_dir


def _login(client: TestClient, username: str, password: str):
    """登录指定测试用户。"""
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def _create_regular_user(username: str = "reviewer", password: str = "user-secret") -> None:
    """创建普通测试用户。"""
    storage.create_user(
        username=username,
        display_name="普通用户",
        password_hash=generate_password_hash(password),
        role="user",
    )


def test_regular_user_cannot_use_server_file_or_directory_paths(tmp_path, monkeypatch):
    """普通用户不得使用服务器 file_path 或 directory_path 导入/解析。"""
    client, allowed_dir = _configure_server_path_test_app(tmp_path, monkeypatch)
    source_file = allowed_dir / "contract.txt"
    source_file.write_text("合同文本", encoding="utf-8")
    _create_regular_user()
    _login(client, "reviewer", "user-secret")

    file_response = client.post(
        "/api/rag/upload/file",
        json={"file_path": str(source_file), "collection_name": "private"},
    )
    directory_response = client.post(
        "/api/rag/upload/directory",
        json={"directory_path": str(allowed_dir), "collection_name": "private"},
    )
    contract_response = client.post(
        "/api/lpos/contracts/parse",
        json={"file_path": str(source_file)},
    )

    assert file_response.status_code == 403
    assert directory_response.status_code == 403
    assert contract_response.status_code == 403


def test_admin_server_paths_must_stay_inside_upload_root_when_enabled(tmp_path, monkeypatch):
    """管理员显式开启服务器路径能力后，越界路径仍应被拒绝。"""
    client, _ = _configure_server_path_test_app(tmp_path, monkeypatch)
    monkeypatch.setattr(web_app.settings, "auth_enable_server_path_import", True)
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "contract.txt"
    outside_file.write_text("越界合同文本", encoding="utf-8")
    _login(client, "admin", "admin-secret")

    file_response = client.post(
        "/api/rag/upload/file",
        json={"file_path": str(outside_file), "collection_name": "public"},
    )
    directory_response = client.post(
        "/api/rag/upload/directory",
        json={"directory_path": str(outside_dir), "collection_name": "public"},
    )
    contract_response = client.post(
        "/api/lpos/contracts/parse",
        json={"file_path": str(outside_file)},
    )

    assert file_response.status_code in {400, 403}
    assert directory_response.status_code in {400, 403}
    assert contract_response.status_code in {400, 403}


def test_admin_can_use_server_paths_inside_upload_root_when_enabled(tmp_path, monkeypatch):
    """管理员开启开关后，可使用配置上传根目录内的服务器路径。"""
    client, allowed_dir = _configure_server_path_test_app(tmp_path, monkeypatch)
    monkeypatch.setattr(web_app.settings, "auth_enable_server_path_import", True)
    source_file = allowed_dir / "contract.txt"
    source_file.write_text("允许导入的合同文本", encoding="utf-8")
    admin_response = _login(client, "admin", "admin-secret")
    admin_user_id = admin_response.json()["user"]["id"]
    registry.register_legacy_knowledge_base(
        display_name="public",
        collection_name="public",
        created_by=admin_user_id,
    )

    file_response = client.post(
        "/api/rag/upload/file",
        json={"file_path": str(source_file), "collection_name": "public"},
    )
    directory_response = client.post(
        "/api/rag/upload/directory",
        json={"directory_path": str(allowed_dir), "collection_name": "public"},
    )
    contract_response = client.post(
        "/api/lpos/contracts/parse",
        json={"file_path": str(source_file)},
    )

    assert file_response.status_code == 200
    assert directory_response.status_code == 200
    assert contract_response.status_code == 200
    assert contract_response.json()["text"] == "允许导入的合同文本"
