"""Multi-Agent 加载与 Agent 选择状态的前端 i18n 契约测试。"""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from scripts.check_frontend_i18n import (
    extract_named_function,
    scan_named_js_functions,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GLOBAL_HTML = PROJECT_ROOT / "src/shuyixiao_agent/static/global.html"
LEGAL_TASK_TYPES = (
    "contract_review",
    "risk_identification",
    "revision_suggestions",
    "legal_research",
    "compliance_analysis",
    "review_summary",
    "legal_document_generation",
    "redline_comparison",
    "approval_flow_suggestion",
)


@pytest.fixture(scope="module")
def global_html() -> str:
    return GLOBAL_HTML.read_text(encoding="utf-8")


def extract_function(source: str, name: str) -> str:
    block = extract_named_function(source, name)
    assert block is not None, f"JS function not found: {name}"
    return block


def extract_const_object(source: str, name: str) -> str:
    declaration = re.search(rf"\bconst\s+{re.escape(name)}\s*=\s*\{{", source)
    assert declaration is not None, f"JS const object not found: {name}"

    start = source.index("{", declaration.start())
    depth = 0
    quote: str | None = None
    escaped = False
    index = start
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"`":
            quote = char
        elif char == "/" and following == "/":
            newline = source.find("\n", index + 2)
            index = len(source) if newline == -1 else newline + 1
            continue
        elif char == "/" and following == "*":
            ending = source.find("*/", index + 2)
            index = len(source) if ending == -1 else ending + 2
            continue
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
        index += 1

    pytest.fail(f"Unterminated JS const object: {name}")


def extract_switch_case(block: str, case_name: str) -> str:
    match = re.search(
        rf"case\s+['\"]{re.escape(case_name)}['\"]\s*:(.*?)"
        r"(?=\n\s*case\s+['\"]|\n\s*}\s*$)",
        block,
        re.DOTALL,
    )
    assert match is not None, f"JS switch case not found: {case_name}"
    return match.group(1)


def test_load_collaboration_data_uses_localized_loading_and_failure(global_html):
    block = extract_function(global_html, "loadCollaborationData")

    assert "t('status.loading_collaboration_data')" in block
    assert "t('error.load_collaboration_data')" in block
    assert "fetch('/api/multi-agent/teams')" in block
    assert "fetch('/api/multi-agent/modes')" in block


def test_legal_task_templates_store_description_keys(global_html):
    templates = extract_const_object(global_html, "LEGAL_TASK_TEMPLATES")
    apply_block = extract_function(global_html, "applyLegalTaskTemplate")

    assert "description:" not in templates
    for task_type in LEGAL_TASK_TYPES:
        assert (
            f"descriptionKey: 'legal_task.{task_type}.description'" in templates
        )
    assert "description.textContent = t(template.descriptionKey);" in apply_block
    assert "description.textContent = template.description;" not in apply_block


def test_agent_selection_uses_localized_status_and_preserves_button_state(global_html):
    block = extract_function(global_html, "renderLegalAgentSelection")

    assert "t('multiagent.agent_selection.loading')" in block
    assert "t('error.load_collaboration_data')" in block
    assert "t('status.selected_agents'" in block
    assert re.search(
        r"t\('status\.selected_agents',\s*\{[^}]*count:\s*"
        r"selectedLegalAgentNames\.(?:length|size)",
        block,
        re.DOTALL,
    )
    assert "restoreButton.disabled = true;" in block
    assert "restoreButton.disabled = false;" in block
    assert "if (startButton) startButton.disabled = true;" in block
    assert "if (startButton) startButton.disabled = false;" in block


def test_agent_selection_uses_localized_badges(global_html):
    block = extract_function(global_html, "renderLegalAgentSelection")

    assert "t('badge.required')" in block
    assert "t('badge.recommended')" in block
    assert "必选" not in block
    assert "推荐" not in block


def test_agent_gap_warning_uses_localized_parameterized_message(global_html):
    block = extract_function(global_html, "renderLegalAgentGapWarning")

    assert "t('warning.capability_gap'" in block
    assert re.search(r"\bagents\s*:\s*messages\.join\(", block)
    assert re.search(r"\bcount\s*:\s*missing\.length", block)
    assert "当前未选择部分推荐智能体" not in block


def test_api_and_unknown_agent_values_are_not_used_as_translation_keys(global_html):
    load_block = extract_function(global_html, "loadCollaborationData")
    selection_block = extract_function(global_html, "renderLegalAgentSelection")
    display_name_block = extract_function(global_html, "getAgentDisplayName")

    assert "collaborationTeamsData = teamsData.teams;" in load_block
    assert "collaborationModesData = modesData.modes;" in load_block
    assert "t(teamsData" not in load_block
    assert "t(modesData" not in load_block
    assert "t(agent.name" not in selection_block
    assert "escapeHtml(displayName)" in selection_block
    assert "escapeHtml(expertise || agent.description || agent.role || '')" in selection_block
    assert "const i18nKey = 'agent_' + name;" not in display_name_block
    assert re.search(r"AGENT_DISPLAY_NAMES\[name\]", display_name_block)
    assert "t(" in display_name_block
    assert re.search(r"(?:return\s+name;|:\s*name)", display_name_block)
    assert "t(team.name" not in global_html
    assert "t(mode.name" not in global_html
    assert not re.search(r"\bt\s*\(\s*selectedLegalAgentNames", global_html)


def test_contract_file_parse_localizes_validation_loading_error_and_button(global_html):
    block = extract_function(global_html, "parseLegalContractFile")

    assert "t('validation.contract_file_required')" in block
    assert "t('status.contract_parsing')" in block
    assert (
        "localizedOperationError('error.contract_parse_failed', error.message)"
        in block
    )
    assert "console.error" in block
    assert "fetch('/api/lpos/contracts/upload'" in block
    assert "formData.append('file', fileInput.files[0]);" in block
    assert "parseBtn.disabled = true;" in block
    assert "parseBtn.disabled = false;" in block
    assert "parseBtn.textContent = t('action.parse_contract_file');" in block


def test_contract_path_parse_localizes_validation_loading_and_safe_error(global_html):
    block = extract_function(global_html, "parseLegalContractFileFromPath")

    assert "t('validation.contract_path_required')" in block
    assert "t('status.contract_parsing')" in block
    assert (
        "localizedOperationError('error.contract_parse_failed', error.message)"
        in block
    )
    assert "console.error" in block
    assert "fetch('/api/lpos/contracts/parse'" in block
    assert "JSON.stringify({ file_path: filePath })" in block


def test_contract_parse_error_helper_only_exposes_detail_in_chinese(global_html):
    block = extract_function(global_html, "localizedOperationError")

    assert "currentLang === 'zh'" in block
    assert re.search(r"currentLang\s*===\s*'zh'\s*&&\s*detail", block)
    assert "String(detail)" in block
    assert "t(key)" in block


def test_parsed_contract_status_localizes_labels_and_escapes_values(global_html):
    block = extract_function(global_html, "renderParsedContractStatus")

    for key in (
        "status.contract_parse_success",
        "contract.summary.parties",
        "contract.summary.amount",
        "contract.summary.term",
        "contract.summary.type",
        "contract.summary.clauses",
        "contract.summary.document_count",
    ):
        assert f"t('{key}')" in block

    for escaped_value in (
        "uploadedLegalFileName",
        "structureStatus",
        "parsedContractText.length",
        "documentCount",
        "summary?.contract_type",
        "summary?.key_clause_summary?.length || 0",
    ):
        assert f"escapeHtml({escaped_value})" in block

    assert not re.search(r"\bt\s*\(\s*uploadedLegalFileName", block)
    assert not re.search(r"\bt\s*\(\s*summary(?:\?|\.)", block)


def test_contract_summary_helpers_localize_fixed_text_and_escape_business_values(
    global_html,
):
    format_block = extract_function(global_html, "formatContractStructureSummary")
    section_block = extract_function(global_html, "renderContractSummarySection")

    assert "t('contract.summary.type')" in format_block
    assert "t('contract.summary.clauses')" in format_block
    assert "summary.contract_type" in format_block
    assert "summary.key_clause_summary" in format_block
    assert "escapeHtml(title)" in section_block
    assert "escapeHtml(item)" in section_block
    assert "escapeHtml(hiddenCount)" in section_block
    assert not re.search(r"\bt\s*\(\s*summary(?:\?|\.)", format_block)
    assert scan_named_js_functions(
        global_html,
        [
            "renderParsedContractStatus",
            "formatContractStructureSummary",
            "renderContractSummarySection",
        ],
    ) == []


def test_start_collaboration_localizes_guards_loading_failure_and_button_restore(
    global_html,
):
    block = extract_function(global_html, "startCollaboration")

    for key in (
        "validation.task_required",
        "validation.team_required",
        "validation.agents_required",
        "action.reviewing",
        "status.collaboration_starting",
        "status.failed",
        "action.start_review",
    ):
        assert f"t('{key}')" in block

    assert "teamType === 'legal_contract_review'" in block
    assert "legalSelectionPolicyState !== 'ready'" in block
    assert "return;" in block
    assert "startBtn.disabled = true;" in block
    assert "startBtn.disabled = false;" in block
    assert (
        "localizedOperationError('status.failed', error.message)" in block
    )
    assert "console.error" in block
    assert "t('alert_collaboration_failed') + error.message" not in block
    assert "<span data-i18n=" not in block


def test_start_collaboration_preserves_request_body_header_and_stream_url(global_html):
    block = extract_function(global_html, "startCollaboration")

    assert "fetch('/api/multi-agent/collaborate/stream'" in block
    assert "'Content-Type': 'application/json'" in block
    for field in (
        "input_text: snapshot.task",
        "team_type: snapshot.teamType",
        "mode: snapshot.mode",
        "legal_task_type: snapshot.legalTaskType",
        "selected_agent_names: snapshot.selectedAgentNames",
        "enable_rag: snapshot.knowledgeBase.ids.length > 0 || snapshot.knowledgeBase.includePublicKnowledge",
        "knowledge_base_ids: snapshot.knowledgeBase.ids",
        "include_public_knowledge: snapshot.knowledgeBase.includePublicKnowledge",
        "context: legalContext",
    ):
        assert field in block

    assert not re.search(r"\blang\s*:", block)
    assert "X-User-Lang" not in block


def test_stream_parser_keeps_cross_chunk_sse_contract(global_html):
    start_block = extract_function(global_html, "startCollaboration")
    event_block = extract_function(global_html, "handleSSEEventBlock")

    for snippet in (
        "if (!response.ok)",
        "response.body.getReader()",
        "new TextDecoder()",
        "let sseBuffer = ''",
        "decoder.decode(value, { stream: true })",
        "sseBuffer += chunk",
        "sseBuffer.indexOf('\\n\\n')",
        "sseBuffer.slice(0, eventBoundary)",
        "sseBuffer = sseBuffer.slice(eventBoundary + 2)",
        "handleSSEEventBlock(eventBlock)",
        "decoder.decode()",
        "if (sseBuffer.trim())",
    ):
        assert snippet in start_block
    assert start_block.index("if (!response.ok)") < start_block.index(
        "response.body.getReader()"
    )
    assert ".filter(line => line.startsWith('data: '))" in event_block
    assert "JSON.parse(payload)" in event_block
    assert "handleCollaborationEvent(data)" in event_block


def test_collaboration_start_event_localizes_api_message(global_html):
    block = extract_function(global_html, "handleCollaborationEvent")
    start_case = extract_switch_case(block, "start")

    assert (
        "localizedOperationError('status.collaboration_starting', data.message)"
        in start_case
    )
    assert "statusDiv.textContent = data.message;" not in start_case


def test_collaboration_complete_event_localizes_status_without_translating_output(
    global_html,
):
    block = extract_function(global_html, "handleCollaborationEvent")
    complete_case = extract_switch_case(block, "complete")

    assert "requestSnapshot: currentCollaborationSnapshot" in complete_case
    assert "displayCollaborationResult(currentCollaborationResult);" in complete_case
    assert "t('status.completed')" in complete_case
    assert "t(data.final_output" not in complete_case


def test_collaboration_error_event_hides_non_localized_api_message(global_html):
    block = extract_function(global_html, "handleCollaborationEvent")
    error_case = extract_switch_case(block, "error")

    assert "localizedOperationError('status.failed', data.message)" in error_case
    assert "console.error" in error_case
    assert "statusDiv.textContent = data.message;" not in error_case


def test_team_info_event_localizes_labels_and_preserves_server_values(global_html):
    block = extract_function(global_html, "handleCollaborationEvent")
    team_info_case = extract_switch_case(block, "team_info")

    for key in (
        "team_info.experts",
        "team_info.mode",
        "team_info.participants",
        "team_info.selection_source",
        "team_info.unknown",
        "status.team_ready",
    ):
        assert f"t('{key}'" in team_info_case

    assert re.search(
        r"t\('team_info\.experts',\s*\{\s*count:\s*data\.agent_count\s*}\)",
        team_info_case,
    )
    assert "data.metadata?.agent_selection" in team_info_case
    assert "agentSelection?.selected_agent_names" in team_info_case
    assert "serverAgents.map(agent => agent.name || agent)" in team_info_case
    assert "getAgentDisplayName(name)" in team_info_case
    for server_value in (
        "data.team_name",
        "data.mode",
        "selectedAgentText",
        "selectionSource",
    ):
        assert f"escapeHtml({server_value})" in team_info_case
        assert not re.search(rf"\bt\s*\(\s*{re.escape(server_value)}", team_info_case)
    assert "DOMPurify.sanitize(teamInfoHTML)" in team_info_case


def test_collaboration_result_localizes_status_duration_and_safe_failure(
    global_html,
):
    block = extract_function(global_html, "displayCollaborationResult")

    assert "data.success ? t('result.success') : t('result.failed')" in block
    assert re.search(
        r"t\('result\.seconds',\s*\{\s*count:\s*"
        r"data\.execution_time\.toFixed\(1\)\s*}\)",
        block,
    )
    assert (
        "alert(localizedOperationError('result.failed', data.error_message));"
        in block
    )
    assert "'Collaboration failed: ' + data.error_message" not in block

    assert (
        "outputDiv.innerHTML = "
        "DOMPurify.sanitize(marked.parse(data.final_output));"
    ) in block
    assert not re.search(r"\bt\s*\(\s*data\.final_output", block)
    assert (
        "Object.keys(data.agent_contributions || {}).length" in block
    )
    assert "(data.messages || []).length" in block


def test_agent_contribution_localizes_summary_status_and_safe_failure(
    global_html,
):
    block = extract_function(global_html, "displayAgentContributions")

    assert re.search(
        r"t\('summary\.agent_contributions',\s*\{\s*count:\s*"
        r"contributionEntries\.length\s*}\)",
        block,
    )
    assert "t('status.agent_completed')" in block
    assert "t('status.agent_failed')" in block
    assert "t('error.agent_failed_safe')" in block
    assert "contribution.error_message" not in block
    assert "contribution.error" not in block

    assert "escapeHtml(agentName)" in block
    assert "escapeHtml(contribution.role" in block
    assert "contribution.response || ''" in block
    assert "DOMPurify.sanitize(marked.parse(responseText))" in block
    assert not re.search(r"\bt\s*\(\s*contribution\.response", block)


def test_collaboration_message_localizes_summary_and_escapes_business_values(
    global_html,
):
    block = extract_function(global_html, "displayCollaborationMessages")

    assert re.search(
        r"t\('summary\.messages',\s*\{\s*count:\s*messages\.length\s*}\)",
        block,
    )
    assert "escapeHtml(message.sender)" in block
    assert "escapeHtml(message.receiver)" in block
    assert "escapeHtml(message.content.substring(0, 200))" in block
    assert "message.content.length > 200" in block
    assert not re.search(r"\bt\s*\(\s*message\.(?:sender|receiver|content)", block)


def test_collaboration_toggle_uses_localized_expand_and_collapse(global_html):
    reset_block = extract_function(global_html, "resetCollaborationSection")
    toggle_block = extract_function(global_html, "toggleCollaborationSection")

    assert "button.textContent = t('action.expand');" in reset_block
    assert (
        "button.textContent = isHidden ? t('action.collapse') : "
        "t('action.expand');"
    ) in toggle_block
    assert "button.textContent = '展开';" not in reset_block
    assert "isHidden ? '收起' : '展开'" not in toggle_block


def test_copy_collaboration_result_localizes_feedback_and_preserves_output(
    global_html,
):
    block = extract_function(global_html, "copyCollaborationResult")

    assert "alert(t('toast.report_copied'));" in block
    assert "alert(t('toast.copy_failed'));" in block
    assert "console.error(t('toast.copy_failed')" in block
    assert "const result = currentCollaborationResult.final_output;" in block
    assert "navigator.clipboard.writeText(result)" in block
    assert not re.search(r"\bt\s*\(\s*(?:result|currentCollaborationResult)", block)


def test_collaboration_detail_prompts_are_localized(global_html):
    team_block = extract_function(global_html, "showTeamDetails")
    mode_block = extract_function(global_html, "showModeDetails")
    result_block = extract_function(global_html, "showCollaborationDetails")

    assert "alert(t('detail.team_console'));" in team_block
    assert "alert(t('detail.mode_console'));" in mode_block
    assert "alert(t('detail.result_console'));" in result_block
    assert "console.log(t('detail.team_console'), collaborationTeamsData);" in team_block
    assert "console.log(t('detail.mode_console'), collaborationModesData);" in mode_block
    assert "console.log(t('detail.result_console'), currentCollaborationResult);" in result_block
    assert not re.search(r"\bt\s*\(\s*team\.(?:name|description)", team_block)
    assert not re.search(r"\bt\s*\(\s*mode\.(?:name|description|use_case)", mode_block)


def test_download_report_localizes_fixed_markdown_fields(global_html):
    block = extract_function(global_html, "downloadCollaborationResult")

    expected_keys = (
        "download.report_title",
        "download.field.task",
        "download.field.team",
        "download.field.mode",
        "download.field.legal_task_type",
        "download.field.selection_source",
        "download.field.participants",
        "download.field.capability_gaps",
        "download.field.knowledge_base",
        "download.field.include_public_knowledge",
        "download.field.file",
        "download.field.uploaded_file_id",
        "download.field.has_structured_summary",
        "download.field.started_at",
        "download.field.agent_count",
        "download.field.duration",
        "download.section.final_conclusion",
        "download.section.agent_analysis",
        "download.value.yes",
        "download.value.no",
        "download.value.none",
        "download.value.not_recorded",
        "download.human_review_notice",
        "status.agent_completed",
        "status.agent_failed",
        "error.agent_failed_safe",
    )
    for key in expected_keys:
        assert f"t('{key}')" in block

    assert "t('result.seconds'" in block
    assert "data-i18n" not in block


def test_download_report_preserves_business_values_and_ascii_filename(global_html):
    block = extract_function(global_html, "downloadCollaborationResult")

    for expression in (
        "currentCollaborationResult.final_output",
        "contribution.response",
        "fileSnapshot.uploadedFileName",
        "knowledgeBaseSnapshot.displayName",
        "requestSnapshot.task",
    ):
        assert expression in block
        assert not re.search(rf"\bt\s*\(\s*{re.escape(expression)}", block)

    assert "const filename = `legal_review_report_${timestamp}.md`;" in block
    assert "a.download = filename;" in block
    assert "Object.entries(contributions)" in block


def test_download_disclaimer_preserves_english_and_russian_legal_semantics(
    global_html,
):
    catalog = json.loads(extract_const_object(global_html, "I18N"))

    assert "download.human_review_notice" in catalog
    english = catalog["download.human_review_notice"]["en"].lower()
    russian = catalog["download.human_review_notice"]["ru"].lower()
    assert "does not constitute formal legal advice" in english
    assert "human review" in english
    assert "не является официальной юридической консультацией" in russian
    assert "провер" in russian


def test_copy_detail_and_download_functions_have_no_fixed_chinese(global_html):
    assert scan_named_js_functions(
        global_html,
        [
            "copyCollaborationResult",
            "downloadCollaborationResult",
            "showTeamDetails",
            "showModeDetails",
            "showCollaborationDetails",
        ],
    ) == []


def test_language_rerender_preserves_collaboration_result_body(global_html):
    block = extract_function(global_html, "rerenderVisibleLocalizedState")

    assert "if (currentCollaborationResult)" in block
    assert "displayCollaborationResult(currentCollaborationResult, false);" in block
    assert "currentCollaborationResult.final_output" not in block
    assert not re.search(r"\bt\s*\(\s*currentCollaborationResult", block)
    assert "currentCollaborationResult =" not in block


def test_language_rerender_preserves_agent_selection_around_metadata_reload(
    global_html,
):
    block = extract_function(global_html, "rerenderVisibleLocalizedState")

    snapshot_match = re.search(
        r"const\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*"
        r"\[\.\.\.selectedLegalAgentNames\]\s*;",
        block,
    )
    assert snapshot_match is not None
    reload_position = block.index("await loadCollaborationData(")
    assert snapshot_match.start() < reload_position

    after_reload = block[reload_position:]
    snapshot_name = snapshot_match.group("name")
    assert re.search(
        rf"selectedLegalAgentNames\s*=\s*sortLegalAgentNames\("
        rf"(?:\[\.\.\.{snapshot_name}\]|{snapshot_name})\)",
        after_reload,
    )
    assert "enforceRequiredLegalAgents();" in after_reload
