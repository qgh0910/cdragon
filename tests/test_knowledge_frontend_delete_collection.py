"""知识库管理前端删除资料库入口测试。"""

from pathlib import Path


INDEX_HTML = Path("src/shuyixiao_agent/static/index.html")


def test_knowledge_tab_has_delete_collection_entry():
    """知识库危险操作区应提供基于 kb_id 的删除资料库入口。"""
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="manageKbSelect"' in html
    assert 'id="manageTenantId"' not in html
    assert 'onclick="deleteKnowledgeBaseCollection()"' in html
    assert "删除资料库" in html


def test_delete_collection_frontend_calls_collection_delete_api():
    """删除资料库前端函数应调用 kb_id collection 删除接口并刷新状态。"""
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "async function deleteKnowledgeBaseCollection()" in html
    assert "/api/kb/collections/${encodeURIComponent(kbId)}" in html
    assert "/api/rag/collection/" not in html
    assert "encodeURIComponent(kbId)" in html
    assert "loadAllCollections()" in html
    assert "multiAgentKnowledgeBase" in html
    assert "resetDeletedKnowledgeBaseSelections(kbId)" in html
