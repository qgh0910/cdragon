"""LPOS 合同结构化摘要前端静态检查。"""

from pathlib import Path


INDEX_HTML = Path("src/shuyixiao_agent/static/index.html")
EXPECTED_LEGAL_TASK_TYPES = {
    "contract_review",
    "risk_identification",
    "revision_suggestions",
    "legal_research",
    "compliance_analysis",
    "review_summary",
    "legal_document_generation",
    "redline_comparison",
    "approval_flow_suggestion",
}


def _read_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def _extract_between(html: str, start_marker: str, end_marker: str) -> str:
    start = html.index(start_marker)
    end = html.index(end_marker, start)
    return html[start:end]


def _extract_legal_task_templates_block(html: str) -> str:
    return _extract_between(
        html,
        "const LEGAL_TASK_TEMPLATES = {",
        "        // 加载团队和模式信息",
    )


def _extract_function_block(html: str, function_name: str) -> str:
    start = html.index(f"function {function_name}(")
    next_function = html.index("\n        function ", start + 1)
    return html[start:next_function]


def _extract_case_block(function_block: str, case_label: str) -> str:
    start = function_block.index(f"case '{case_label}':")
    next_case = function_block.find("\n                case ", start + 1)
    end = next_case if next_case != -1 else function_block.index("\n            }", start)
    return function_block[start:end]


def test_frontend_tracks_contract_structure_summary_and_uses_it_in_legal_context():
    html = _read_html()

    assert "let parsedContractStructureSummary = null;" in html
    assert (
        "parsedContractStructureSummary = data.contract_structure_summary || null;"
        in html
    )
    assert "contract_structure_summary: parsedContractStructureSummary" in html


def test_frontend_does_not_send_server_file_path_in_legal_context_by_default():
    html = _read_html()
    start = html.index("const legalContext =")
    end = html.index("if (!task)", start)
    legal_context_block = html[start:end]

    assert "uploaded_file_id" in legal_context_block
    assert "uploaded_file_name" in legal_context_block
    assert "contract_structure:" not in legal_context_block
    assert "uploaded_file_path" not in legal_context_block


def test_frontend_parse_status_mentions_structure_summary_when_available():
    html = _read_html()

    assert "formatContractStructureSummary" in html
    assert "合同类型" in html
    assert "关键条款" in html


def test_frontend_renders_contract_parse_result_as_structured_summary_card():
    """解析成功状态不应再把所有摘要压成一行纯文本。"""
    html = _read_html()
    apply_block = _extract_function_block(html, "applyParsedContractResult")
    render_block = _extract_function_block(html, "renderParsedContractStatus")

    assert "renderParsedContractStatus(" in apply_block
    assert "parseStatus.innerHTML" in render_block
    assert 'class="legal-parse-summary"' in render_block
    assert 'class="legal-parse-summary-meta"' in render_block
    assert "合同解析成功" in render_block
    assert "escapeHtml(uploadedLegalFileName" in render_block


def test_frontend_contract_summary_multivalue_fields_render_as_lists():
    """主体、金额、期限等多值摘要应按分组列表展示，避免长句挤在一起。"""
    html = _read_html()
    render_block = _extract_function_block(html, "renderParsedContractStatus")
    section_block = _extract_function_block(html, "renderContractSummarySection")

    assert "renderContractSummarySection('主体', summary.parties)" in render_block
    assert "renderContractSummarySection('金额', summary.amount)" in render_block
    assert "renderContractSummarySection('期限', summary.term)" in render_block
    assert "<ul" in section_block
    assert "<li>" in section_block
    assert "normalizeContractSummaryValues" in section_block


def test_frontend_clears_contract_structure_summary_with_parsed_file_state():
    html = _read_html()

    assert html.count("parsedContractStructureSummary = null;") >= 6


def test_frontend_report_does_not_fall_back_to_server_file_path():
    html = _read_html()
    start = html.index("const legalFilePath =")
    end = html.index("const timestamp =", start)
    report_file_label_block = html[start:end]

    assert "uploadedLegalFilePath" not in report_file_label_block
    assert "legalFilePath" not in report_file_label_block.split("=", 1)[1]


def test_frontend_has_legal_agent_selection_dom_targets():
    """法律任务区应预留策略状态、Agent 选项、能力缺口和恢复默认控件。"""
    html = _read_html()

    for element_id in [
        "legalAgentSelection",
        "legalAgentSelectionStatus",
        "legalAgentOptions",
        "legalAgentGapWarning",
        "restoreLegalAgentDefaults",
    ]:
        assert f'id="{element_id}"' in html


def test_frontend_tracks_legal_selection_policy_state_and_selected_agents():
    """前端应显式维护策略加载三态、服务端策略和用户选择快照。"""
    html = _read_html()

    assert "let legalSelectionPolicyState = 'loading';" in html
    assert "let legalSelectionPolicy = null;" in html
    assert "let selectedLegalAgentNames = [];" in html
    for state in ["loading", "ready", "error"]:
        assert f"legalSelectionPolicyState = '{state}'" in html


def test_frontend_reads_server_selection_policy_without_template_agent_mapping():
    """Agent 默认名单必须来自 /teams.selection_policy，不应复制在模板对象里。"""
    html = _read_html()
    templates_block = _extract_legal_task_templates_block(html)

    assert "team.selection_policy" in html
    assert "team.selection_policy.task_defaults" in html
    assert "team.selection_policy.capability_gaps" in html
    assert "task_defaults" not in templates_block
    assert "selected_agent_names" not in templates_block
    assert "required_agent_names" not in templates_block


def test_frontend_blocks_legal_start_until_selection_policy_ready_only_for_legal_team():
    """法律策略未就绪时 startCollaboration 应提前 return，非法律团队不受影响。"""
    html = _read_html()
    start_block = _extract_function_block(html, "startCollaboration")
    assert "teamType === 'legal_contract_review'" in start_block
    legal_guard_start = start_block.index("teamType === 'legal_contract_review'")
    fetch_start = start_block.index("fetch('/api/multi-agent/collaborate/stream'")
    legal_guard_block = start_block[legal_guard_start:fetch_start]

    assert "legalSelectionPolicyState !== 'ready'" in legal_guard_block
    assert "return;" in legal_guard_block
    assert "teamType === 'legal_contract_review'" in legal_guard_block


def test_frontend_legal_task_options_match_template_task_types():
    """九个法律 task type 应同时存在于 select option 和模板对象中。"""
    html = _read_html()
    select_block = _extract_between(
        html,
        '<select id="legalTaskType"',
        '<div id="legalTaskDescription"',
    )
    templates_block = _extract_legal_task_templates_block(html)

    for task_type in EXPECTED_LEGAL_TASK_TYPES:
        assert f'value="{task_type}"' in select_block
        assert f"{task_type}:" in templates_block

    assert select_block.count("<option value=") == len(EXPECTED_LEGAL_TASK_TYPES) + 1


def test_frontend_builds_frozen_request_snapshot_and_payload_uses_selected_agents():
    """发起协作时应冻结请求快照，并从快照发送显式 Agent 选择。"""
    html = _read_html()
    start_block = _extract_function_block(html, "startCollaboration")
    complete_block = _extract_case_block(
        _extract_function_block(html, "handleCollaborationEvent"),
        "complete",
    )

    assert "let currentCollaborationSnapshot = null;" in html
    assert "function buildCollaborationSnapshot(" in html
    assert "Object.freeze" in html
    assert "const snapshot = buildCollaborationSnapshot(" in start_block
    assert "currentCollaborationSnapshot = snapshot;" in start_block
    assert "selected_agent_names: snapshot.selectedAgentNames" in start_block
    assert "requestSnapshot: currentCollaborationSnapshot" in complete_block


def test_frontend_checks_stream_response_status_before_reading_body():
    """SSE 响应必须先处理非 2xx，再读取 response.body。"""
    html = _read_html()
    start_block = _extract_function_block(html, "startCollaboration")

    assert "response.body.getReader()" in start_block
    assert "if (!response.ok)" in start_block
    assert start_block.index("if (!response.ok)") < start_block.index(
        "response.body.getReader()"
    )


def test_frontend_sse_parser_buffers_cross_chunk_events():
    """SSE 解析应保留跨 chunk buffer，并按空行事件边界解析。"""
    html = _read_html()
    start_block = _extract_function_block(html, "startCollaboration")

    assert "let sseBuffer = '';" in start_block
    assert "decoder.decode(value, { stream: true })" in start_block
    assert "sseBuffer += chunk" in start_block
    assert "sseBuffer.indexOf('\\n\\n')" in start_block
    assert "sseBuffer.slice(0, eventBoundary)" in start_block
    assert "sseBuffer = sseBuffer.slice(eventBoundary + 2)" in start_block
    assert "if (sseBuffer.trim())" in start_block


def test_frontend_uses_server_agents_selection_metadata_and_contribution_status():
    """页面结果应展示服务端实际参与者、选择 metadata 和贡献状态。"""
    html = _read_html()
    event_block = _extract_function_block(html, "handleCollaborationEvent")
    team_info_block = _extract_case_block(event_block, "team_info")
    contribution_block = _extract_function_block(html, "displayAgentContributions")

    assert "data.agents" in team_info_block
    assert "data.metadata?.agent_selection" in team_info_block
    assert "selected_agent_names" in team_info_block
    assert "selection_source" in team_info_block
    assert "contribution.status" in contribution_block
    assert "status === 'failed'" in contribution_block
    assert "failed" in contribution_block


def test_frontend_report_uses_snapshot_and_server_selection_metadata():
    """导出报告只应使用请求快照和服务端权威选择 metadata。"""
    html = _read_html()
    report_block = _extract_function_block(html, "downloadCollaborationResult")

    assert "currentCollaborationResult.requestSnapshot" in report_block
    assert "currentCollaborationResult.metadata?.agent_selection" in report_block
    assert "requestSnapshot.task" in report_block
    assert "agentSelection.legal_task_type" in report_block
    assert "agentSelection.selection_source" in report_block
    assert "agentSelection.selected_agent_names" in report_block
    assert "agentSelection.capability_gaps" in report_block
    assert "不构成正式律师意见" in report_block


def test_frontend_report_does_not_read_current_form_or_unsafe_contract_fields():
    """报告不得回读当前表单，也不得包含路径、完整结构或 pageindex。"""
    html = _read_html()
    report_block = _extract_function_block(html, "downloadCollaborationResult")

    forbidden_snippets = [
        "document.getElementById('collaborationTask')",
        "document.getElementById('collaborationTeam')",
        "document.getElementById('collaborationMode')",
        "document.getElementById('multiAgentKnowledgeBase')",
        "uploaded_file_path",
        "uploadedLegalFilePath",
        "contract_structure:",
        "parsedContractStructureSummary",
        "pageindex",
        "pageIndex",
    ]
    for snippet in forbidden_snippets:
        assert snippet not in report_block
