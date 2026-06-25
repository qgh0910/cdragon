"""第 20 步文档同步验收测试。"""

from pathlib import Path

import pytest


ENV_EXAMPLE = Path(".env.example")
RAG_DOC = Path("docs/RAG (检索增强生成) 使用指南.md")
API_DOC = Path("docs/API 参考文档.md")
LEGAL_DOC = Path("my_docs/法律多智能体项目文档.md")


def _read_required_doc(path: Path) -> str:
    """读取必须存在的项目文档，缺失时给出清晰契约失败信息。"""
    assert path.exists(), f"文档缺失: {path}"
    return path.read_text(encoding="utf-8")


def test_env_example_documents_auth_and_startup_settings():
    """环境变量示例应覆盖登录、Session、CORS 和服务器路径开关。"""
    content = _read_required_doc(ENV_EXAMPLE)

    required_items = [
        "AUTH_SECRET_KEY",
        "INITIAL_ADMIN_USERNAME",
        "INITIAL_ADMIN_PASSWORD",
        "SESSION_EXPIRE_HOURS",
        "AUTH_COOKIE_SECURE",
        "AUTH_ALLOWED_ORIGINS",
        "AUTH_ENABLE_SERVER_PATH_IMPORT",
        "AUTH_LOGIN_RATE_LIMIT_PER_MINUTE",
        "python run_web.py",
        "/api/health",
        "不要提交真实密码",
    ]
    for item in required_items:
        assert item in content


def test_rag_guide_documents_kb_id_permissions_and_legacy_migration():
    """RAG 指南应说明 kb_id 驱动接口、权限矩阵和 legacy 迁移报告。"""
    content = _read_required_doc(RAG_DOC)

    required_items = [
        "登录与知识库权限",
        "/api/kb/collections",
        "/api/kb/collections/{kb_id}/texts",
        "/api/kb/collections/{kb_id}/upload",
        "/api/kb/collections/{kb_id}/documents",
        "/api/rag/query",
        "kb_id",
        "公共知识库",
        "用户知识库",
        "legacy_admin_only",
        "my_docs/2026-06-10-legacy-kb-migration-report.md",
        "普通用户不能使用服务器 file_path 或 directory_path",
    ]
    for item in required_items:
        assert item in content


def test_api_reference_documents_auth_kb_and_multi_agent_contracts():
    """API 参考应包含认证、知识库、RAG 查询和多智能体新请求契约。"""
    content = _read_required_doc(API_DOC)

    required_items = [
        "Web/API 登录与知识库权限接口",
        "POST /api/auth/login",
        "POST /api/auth/logout",
        "GET /api/auth/me",
        "POST /api/auth/change-password",
        "GET /api/kb/collections",
        "POST /api/kb/collections",
        "POST /api/kb/collections/{kb_id}/texts",
        "POST /api/kb/collections/{kb_id}/upload",
        "GET /api/kb/collections/{kb_id}/documents",
        "DELETE /api/kb/collections/{kb_id}/clear",
        "knowledge_base_ids",
        "include_public_knowledge",
        "legacy 兼容接口",
        "tenant_id 不再作为权限依据",
    ]
    for item in required_items:
        assert item in content


def test_legal_project_doc_documents_login_kb_scope_and_verification():
    """法律项目文档应同步登录态、知识库作用域、多智能体来源和验收命令。"""
    content = _read_required_doc(LEGAL_DOC)

    required_items = [
        "用户登录与知识库权限",
        "服务端 Session",
        "SQLite 用户/知识库元数据",
        "公共知识库",
        "用户知识库",
        "knowledge_base_ids",
        "include_public_knowledge",
        "legacy_admin_only",
        "my_docs/2026-06-10-legacy-kb-migration-report.md",
        "conda run -n cdragon python -m pytest tests/test_auth_api.py tests/test_kb_permissions.py tests/test_legacy_api_authorization.py tests/test_multi_agent_kb_authorization.py -v",
        "conda run -n cdragon python -m py_compile src/shuyixiao_agent/web_app.py src/shuyixiao_agent/config.py",
        "python run_web.py",
    ]
    for item in required_items:
        assert item in content


@pytest.mark.parametrize("path", [API_DOC, LEGAL_DOC])
def test_multi_agent_dynamic_routing_docs_are_synchronized(path):
    """API 参考和法律项目文档应同步动态路由、选择策略和法律边界。"""
    required_items = [
        "GET /api/multi-agent/teams",
        "selected_agent_names",
        "legal_task_type",
        "selection_policy",
        "risk_identification",
        "template_default",
        "user_override",
        "missing_recommended_agent_names",
        "413",
        "422",
        "默认四人",
        "不构成正式律师意见",
    ]
    content = _read_required_doc(path)

    missing_items = [item for item in required_items if item not in content]
    assert not missing_items, f"{path} 缺少动态路由文档项: {missing_items}"
