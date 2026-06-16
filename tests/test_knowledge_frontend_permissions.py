"""前端知识库权限 UI 与 kb_id 契约静态测试。"""

from pathlib import Path


INDEX_HTML = Path("src/shuyixiao_agent/static/index.html")


def _index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def test_frontend_no_longer_exposes_editable_tenant_inputs():
    """第 18 步后普通用户页面不应再暴露可编辑租户 ID 输入。"""
    html = _index_html()

    removed_input_ids = [
        "legalTenantId",
        "knowledgeTenantId",
        "fileUploadTenantId",
        "manageTenantId",
        "auditTenantId",
        "uploadCollection",
        "fileUploadCollection",
        "manageCollection",
    ]
    for input_id in removed_input_ids:
        assert f'id="{input_id}"' not in html


def test_knowledge_frontend_uses_kb_id_collections_api_and_grouped_display():
    """知识库列表应使用 kb_id API，并按公共/我的/公共管理分组展示。"""
    html = _index_html()

    assert "async function loadAllCollections()" in html
    assert "fetch(`${API_BASE}/api/kb/collections`)" in html
    assert "function renderKnowledgeBaseGroups(" in html
    assert "公共知识库" in html
    assert "我的知识库" in html
    assert "公共知识库管理" in html
    assert "id=\"publicKbAdminCard\"" in html
    assert "data-admin-only=\"true\"" in html
    assert "function isAdminUser()" in html
    assert "currentUser?.role === 'admin'" in html


def test_knowledge_selects_use_kb_id_values_and_scope_labels():
    """知识库下拉框 value 应使用 kb_id，展示文案包含 scope、名称和资料数量。"""
    html = _index_html()

    assert "function updateKnowledgeBaseSelects(" in html
    assert "option.value = kb.id" in html
    assert "formatKnowledgeBaseLabel(kb)" in html
    assert "scopeLabel" in html
    assert "document_count" in html
    assert 'id="uploadKbSelect"' in html
    assert 'id="fileUploadKbSelect"' in html
    assert 'id="manageKbSelect"' in html
    assert 'id="multiAgentKnowledgeBase"' in html


def test_knowledge_mutations_use_kb_id_api_routes():
    """上传、清空、文档浏览和批量删除应改用 /api/kb/collections/{kb_id}。"""
    html = _index_html()

    expected_routes = [
        "/api/kb/collections/${encodeURIComponent(kbId)}/texts",
        "/api/kb/collections/${encodeURIComponent(kbId)}/upload",
        "/api/kb/collections/${encodeURIComponent(kbId)}/clear",
        "/api/kb/collections/${encodeURIComponent(kbId)}/documents",
        "/api/kb/collections/${encodeURIComponent(kbId)}/documents/${encodeURIComponent(docId)}",
        "/api/kb/collections/${encodeURIComponent(kbId)}/documents/batch",
    ]
    for route in expected_routes:
        assert route in html

    forbidden_legacy_routes = [
        "/api/rag/upload/texts",
        "/api/rag/upload/file-from-upload",
        "/api/rag/clear/",
        "/api/rag/document/",
        "/api/rag/documents/batch",
    ]
    for route in forbidden_legacy_routes:
        assert route not in html


def test_multi_agent_frontend_sends_knowledge_base_ids_not_tenant_or_collection():
    """多智能体请求应发送 knowledge_base_ids 和 include_public_knowledge。"""
    html = _index_html()

    assert 'id="multiAgentIncludePublicKnowledge"' in html
    assert "const selectedKnowledgeBaseIds = selectedKnowledgeBaseId ? [selectedKnowledgeBaseId] : []" in html
    assert "knowledge_base_ids: selectedKnowledgeBaseIds" in html
    assert "include_public_knowledge: includePublicKnowledge" in html

    start = html.index("async function startCollaboration()")
    end = html.index("// 处理协作事件", start)
    start_collaboration = html[start:end]
    assert "tenant_id" not in start_collaboration
    assert "collection_name" not in start_collaboration
