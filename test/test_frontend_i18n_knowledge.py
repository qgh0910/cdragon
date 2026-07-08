"""Knowledge 可见动态路径的前端 i18n 契约测试。"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from scripts.check_frontend_i18n import (
    extract_named_function,
    scan_named_js_functions,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GLOBAL_HTML = PROJECT_ROOT / "src/shuyixiao_agent/static/global.html"
KNOWLEDGE_FUNCTIONS = (
    "createKnowledgeBase",
    "createUserKnowledgeBase",
    "createPublicKnowledgeBase",
    "uploadTexts",
    "renderRagFileUploadSuccess",
    "uploadFile",
    "getKnowledgeInfo",
    "loadMappings",
    "loadUploadAudit",
    "clearKnowledgeBase",
    "deleteKnowledgeBaseCollection",
    "resetDeletedKnowledgeBaseSelections",
    "syncKnowledgeBaseSelection",
    "loadDocuments",
    "refreshDocuments",
    "viewDocument",
    "closeDocModal",
    "deleteCurrentDoc",
    "deleteDocumentById",
    "getKnowledgeBaseScopeLabel",
    "formatKnowledgeBaseLabel",
    "renderKnowledgeBaseGroups",
    "loadAllCollections",
    "updateKnowledgeBaseSelects",
    "selectKnowledgeBase",
    "toggleDocSelection",
    "updateBatchDeleteButton",
    "batchDeleteDocuments",
)


@pytest.fixture(scope="module")
def global_html() -> str:
    return GLOBAL_HTML.read_text(encoding="utf-8")


def extract_function(source: str, name: str) -> str:
    block = extract_named_function(source, name)
    assert block is not None, f"JS function not found: {name}"
    return block


def assert_uses_keys(block: str, *keys: str) -> None:
    for key in keys:
        assert f"t('{key}'" in block


def test_create_upload_and_info_use_localized_fixed_ui(global_html):
    create_block = extract_function(global_html, "createKnowledgeBase")
    text_block = extract_function(global_html, "uploadTexts")
    file_block = extract_function(global_html, "uploadFile")
    success_block = extract_function(global_html, "renderRagFileUploadSuccess")
    info_block = extract_function(global_html, "getKnowledgeInfo")

    assert_uses_keys(
        create_block,
        "validation.knowledge_name_required",
        "status.knowledge_creating",
        "error.knowledge_create_failed",
        "toast.knowledge_created",
    )
    assert_uses_keys(
        text_block,
        "validation.knowledge_text_required",
        "validation.knowledge_write_target_required",
        "status.knowledge_uploading",
        "toast.knowledge_upload_success",
    )
    assert_uses_keys(
        file_block,
        "validation.knowledge_file_required",
        "validation.knowledge_write_target_required",
        "status.knowledge_uploading",
        "error.knowledge_upload_failed",
    )
    assert_uses_keys(
        success_block,
        "toast.knowledge_upload_success",
        "knowledge.field.knowledge_base",
        "knowledge.field.file_name",
    )
    assert_uses_keys(
        info_block,
        "validation.knowledge_read_target_required",
        "status.loading",
        "knowledge.info.id",
        "knowledge.info.name",
        "knowledge.info.scope",
        "knowledge.info.internal_collection",
        "knowledge.info.description",
        "error.knowledge_info_failed",
    )

    assert "display_name: displayName" in create_block
    assert "escapeHtml(data.collection.display_name)" in create_block
    assert "escapeHtml(data.display_name" in success_block
    assert "escapeHtml(data.original_filename)" in success_block
    assert "escapeHtml(collection.display_name)" in info_block
    assert "escapeHtml(collection.description)" in info_block
    for expression in (
        "data.collection.display_name",
        "data.display_name",
        "data.original_filename",
        "collection.display_name",
        "collection.description",
    ):
        assert not re.search(rf"\bt\s*\(\s*{re.escape(expression)}", global_html)


def test_knowledge_labels_do_not_translate_user_names(global_html):
    scope_block = extract_function(global_html, "getKnowledgeBaseScopeLabel")
    label_block = extract_function(global_html, "formatKnowledgeBaseLabel")

    assert_uses_keys(
        scope_block,
        "knowledge.scope.public",
        "knowledge.scope.user",
        "knowledge.scope.legacy_admin_only",
        "knowledge.scope.unknown",
    )
    assert_uses_keys(
        label_block,
        "knowledge.document_count.loaded",
        "knowledge.document_count.not_loaded",
    )
    assert "kb.display_name" in label_block
    assert "kb.document_count ?? kb.total_documents" in label_block
    assert not re.search(r"\bt\s*\(\s*kb\.(?:display_name|name)", label_block)


def test_groups_and_selects_localize_labels_and_preserve_selection(global_html):
    groups_block = extract_function(global_html, "renderKnowledgeBaseGroups")
    selects_block = extract_function(global_html, "updateKnowledgeBaseSelects")

    assert_uses_keys(
        groups_block,
        "knowledge.group.visible_count",
        "knowledge.group.public_title",
        "knowledge.group.public_empty",
        "knowledge.group.mine_title",
        "knowledge.group.mine_empty",
        "knowledge.group.public_admin_notice",
        "knowledge.action.manage",
    )
    assert "collections.filter(kb => kb.scope === 'public')" in groups_block
    assert "collections.filter(kb => kb.scope === 'user')" in groups_block
    assert "includeAdminActions && isAdminUser()" in groups_block
    assert "escapeHtml(kb.display_name)" in groups_block
    assert "escapeHtml(kb.id)" in groups_block
    assert not re.search(r"\bt\s*\(\s*kb\.(?:display_name|id)", groups_block)

    assert_uses_keys(
        selects_block,
        "knowledge.selector.none",
        "knowledge.selector.readable_placeholder",
        "knowledge.selector.writable_placeholder",
        "knowledge.selector.manageable_placeholder",
        "knowledge.status.selects_updated",
    )
    assert "'browserCollection'" in selects_block
    assert "'multiAgentKnowledgeBase'" in selects_block
    assert "const currentValue = select.value;" in selects_block
    assert "items.some(kb => kb.id === currentValue)" in selects_block
    assert "select.value = currentValue;" in selects_block
    assert "option.value = kb.id;" in selects_block
    assert "option.textContent = formatKnowledgeBaseLabel(kb);" in selects_block


def test_collection_mapping_and_audit_shells_are_localized(global_html):
    collections_block = extract_function(global_html, "loadAllCollections")
    mappings_block = extract_function(global_html, "loadMappings")
    audit_block = extract_function(global_html, "loadUploadAudit")

    assert_uses_keys(
        collections_block,
        "status.loading",
        "knowledge.group.empty",
        "error.knowledge_list_failed",
    )
    assert "knowledgeBases = data.collections || [];" in collections_block
    assert "renderKnowledgeBaseGroups(knowledgeBases);" in collections_block
    assert "updateKnowledgeBaseSelects(knowledgeBases);" in collections_block

    assert_uses_keys(
        mappings_block,
        "status.loading",
        "knowledge.mapping.empty",
        "knowledge.mapping.count",
        "knowledge.document_count.loaded",
        "knowledge.document_count.not_loaded",
        "error.knowledge_mapping_failed",
    )
    assert "escapeHtml(mapping.display_name)" in mappings_block
    assert "escapeHtml(mapping.original_collection_name)" in mappings_block
    assert "escapeHtml(mapping.internal_collection_name)" in mappings_block

    assert_uses_keys(
        audit_block,
        "status.loading",
        "knowledge.audit.empty",
        "knowledge.audit.recent_count",
        "knowledge.audit.status",
        "knowledge.audit.type",
        "knowledge.audit.knowledge_base",
        "knowledge.audit.scope",
        "knowledge.audit.time",
        "knowledge.audit.error",
        "knowledge.audit.text_material",
        "knowledge.value.no_knowledge_base",
        "error.knowledge_audit_failed",
    )
    for value in (
        "fileName",
        "record.status",
        "record.usage_type",
        "collectionName",
        "record.scope",
        "record.uploaded_at",
        "record.error_message",
        "record.file_id",
        "record.kb_id",
    ):
        assert f"escapeHtml({value}" in audit_block
        assert not re.search(rf"\bt\s*\(\s*{re.escape(value)}", audit_block)


def test_clear_and_collection_delete_use_parameterized_localized_prompts(
    global_html,
):
    clear_block = extract_function(global_html, "clearKnowledgeBase")
    delete_block = extract_function(global_html, "deleteKnowledgeBaseCollection")

    assert_uses_keys(
        clear_block,
        "validation.knowledge_manage_target_required",
        "confirm.knowledge_clear",
        "toast.knowledge_cleared",
        "error.knowledge_clear_failed",
    )
    assert re.search(
        r"t\('confirm\.knowledge_clear',\s*\{\s*name:\s*kb\.display_name\s*}\)",
        clear_block,
    )
    assert_uses_keys(
        delete_block,
        "validation.knowledge_manage_target_required",
        "confirm.knowledge_delete",
        "confirm.knowledge_delete_name",
        "validation.knowledge_delete_name_mismatch",
        "toast.knowledge_deleted",
        "status.knowledge_deleted",
        "error.knowledge_delete_failed",
    )
    assert re.search(
        r"t\('confirm\.knowledge_delete',\s*\{\s*name:\s*kb\.display_name\s*}\)",
        delete_block,
    )
    assert re.search(
        r"t\('confirm\.knowledge_delete_name',\s*\{\s*name:\s*kb\.display_name\s*}\)",
        delete_block,
    )
    assert "typedName !== kb.display_name" in delete_block
    assert not re.search(r"\bt\s*\(\s*kb\.display_name", clear_block + delete_block)


def test_document_browser_localizes_fixed_labels_without_translating_documents(
    global_html,
):
    load_block = extract_function(global_html, "loadDocuments")
    view_block = extract_function(global_html, "viewDocument")

    assert_uses_keys(
        load_block,
        "validation.knowledge_read_target_required",
        "status.loading",
        "knowledge.documents.knowledge_base",
        "knowledge.documents.total",
        "knowledge.documents.showing",
        "knowledge.documents.empty",
        "knowledge.documents.document_id",
        "knowledge.action.view",
        "knowledge.action.delete",
        "error.knowledge_documents_failed",
    )
    assert_uses_keys(
        view_block,
        "status.loading",
        "knowledge.documents.document_id",
        "knowledge.documents.metadata",
        "error.knowledge_document_failed",
    )
    assert "escapeHtml(data.display_name || kbId)" in load_block
    assert "escapeHtml(shortText)" in load_block
    assert "escapeHtml(doc.text)" in view_block
    assert "JSON.stringify(doc.metadata, null, 2)" in view_block
    for expression in (
        "data.display_name",
        "shortText",
        "doc.text",
        "doc.metadata",
    ):
        assert not re.search(
            rf"\bt\s*\(\s*{re.escape(expression)}", load_block + view_block
        )


def test_document_delete_and_batch_actions_use_localized_params(global_html):
    current_block = extract_function(global_html, "deleteCurrentDoc")
    direct_block = extract_function(global_html, "deleteDocumentById")
    button_block = extract_function(global_html, "updateBatchDeleteButton")
    batch_block = extract_function(global_html, "batchDeleteDocuments")

    for block in (current_block, direct_block):
        assert_uses_keys(
            block,
            "confirm.document_delete",
            "toast.document_deleted",
            "error.document_delete_failed",
        )
    assert_uses_keys(button_block, "knowledge.action.delete_selected")
    assert re.search(
        r"t\('knowledge\.action\.delete_selected',\s*\{\s*count:\s*selectedDocIds\.size\s*}\)",
        button_block,
    )
    assert_uses_keys(
        batch_block,
        "validation.documents_required",
        "validation.knowledge_manage_target_required",
        "confirm.documents_batch_delete",
        "toast.documents_batch_deleted",
        "error.documents_batch_delete_failed",
    )
    assert re.search(
        r"t\('confirm\.documents_batch_delete',\s*\{\s*count:\s*selectedDocIds\.size\s*}\)",
        batch_block,
    )
    for name in ("success_count", "failed_count", "remaining_count"):
        assert f"data.{name}" in batch_block
        assert not re.search(rf"\bt\s*\(\s*data\.{name}", batch_block)


def test_knowledge_routes_ids_and_permission_branches_remain_unchanged(global_html):
    create_block = extract_function(global_html, "createKnowledgeBase")
    text_block = extract_function(global_html, "uploadTexts")
    file_block = extract_function(global_html, "uploadFile")
    info_block = extract_function(global_html, "getKnowledgeInfo")
    clear_block = extract_function(global_html, "clearKnowledgeBase")
    delete_block = extract_function(global_html, "deleteKnowledgeBaseCollection")
    documents_block = extract_function(global_html, "loadDocuments")
    batch_block = extract_function(global_html, "batchDeleteDocuments")
    groups_block = extract_function(global_html, "renderKnowledgeBaseGroups")
    selects_block = extract_function(global_html, "updateKnowledgeBaseSelects")

    assert "fetch(`${API_BASE}/api/kb/collections`," in create_block
    assert "scope," in create_block
    assert "display_name: displayName" in create_block
    assert "/collections/${encodeURIComponent(kbId)}/texts" in text_block
    assert "/collections/${encodeURIComponent(kbId)}/upload" in file_block
    assert "/collections/${encodeURIComponent(kbId)}`" in info_block
    assert "/collections/${encodeURIComponent(kbId)}/clear" in clear_block
    assert "`${API_BASE}/api/kb/collections/${encodeURIComponent(kbId)}`" in delete_block
    assert "/collections/${encodeURIComponent(kbId)}/documents?limit=${limit}" in documents_block
    assert "/collections/${encodeURIComponent(kbId)}/documents/batch" in batch_block
    assert "doc_ids: Array.from(selectedDocIds)" in batch_block

    assert "includeAdminActions && isAdminUser()" in groups_block
    assert "collections.filter(canWriteKnowledgeBase)" in selects_block
    assert "collections.filter(canManageKnowledgeBase)" in selects_block
    assert "kb.scope === 'user' || (kb.scope === 'public' && isAdminUser())" in global_html


def test_all_scoped_knowledge_functions_have_no_fixed_chinese(global_html):
    assert scan_named_js_functions(global_html, KNOWLEDGE_FUNCTIONS) == []


def test_language_rerender_captures_and_restores_knowledge_selection(global_html):
    block = extract_function(global_html, "rerenderVisibleLocalizedState")

    capture_position = block.index("captureKnowledgeSelectValues();")
    groups_position = block.index("renderKnowledgeBaseGroups(knowledgeBases || []);")
    selects_position = block.index("updateKnowledgeBaseSelects(knowledgeBases || []);")
    restore_position = block.index("restoreKnowledgeSelectValues(")
    assert capture_position < groups_position < selects_position < restore_position


def test_knowledge_selection_helpers_restore_only_existing_options(global_html):
    capture_block = extract_function(global_html, "captureKnowledgeSelectValues")
    restore_block = extract_function(global_html, "restoreKnowledgeSelectValues")

    for select_id in (
        "browserCollection",
        "multiAgentKnowledgeBase",
        "uploadKbSelect",
        "fileUploadKbSelect",
        "infoCollection",
        "manageKbSelect",
    ):
        assert f"'{select_id}'" in capture_block

    assert "select.value" in capture_block
    assert re.search(
        r"Array\.from\(select\.options\)\.some\("
        r"option\s*=>\s*option\.value\s*===\s*value\)",
        restore_block,
    )
    assert "select.value = value;" in restore_block
