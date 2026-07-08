"""可见 Tab 静态 HTML 的 i18n 标注与国内版兼容边界测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import re

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = PROJECT_ROOT / "src/shuyixiao_agent/static/index.html"
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")


EXPECTED_TABS = {
    "multiagent": (
        "tab_multiagent",
        "switchTab('multiagent')",
        "法律多智能体系统",
    ),
    "knowledge": ("tab_knowledge", "switchTab('knowledge')", "知识库管理"),
}


MULTIAGENT_TEXT_KEYS = {
    "法律多智能体系统": "multiagent.title",
    "选择法律任务，上传合同或材料，由法律多智能体团队完成审查、检索、合规分析和修改建议。": "multiagent.description",
    "法律服务团队：": "multiagent.team.label",
    "法律合同审查团队": "multiagent.team.legal_contract_review",
    "多智能体处理模式：": "multiagent.mode.label",
    "🏢 层级协作（推荐）": "mode.hierarchical.label",
    "🔄 顺序协作": "mode.sequential.label",
    "⚡ 并行协作": "mode.parallel.label",
    "🤝 对等协作": "mode.peer_to_peer.label",
    "🔀 混合模式": "mode.hybrid.label",
    "关联资料库：": "kb.selector.label",
    "不使用资料库": "kb.selector.none",
    "选择资料库后，法律依据检索员和合规审查专员会自动检索相关资料。": "kb.selector.help",
    "自动包含可读公共知识库": "kb.include_public",
    "刷新资料库": "action.refresh_knowledge_bases",
    "请选择要完成的法律任务：": "legal_task.selector.label",
    "-- 请选择法律任务 --": "legal_task.selector.placeholder",
    "合同审查": "legal_task.contract_review.label",
    "合同风险识别": "legal_task.risk_identification.label",
    "修改建议与替代条款": "legal_task.revision_suggestions.label",
    "法律依据检索": "legal_task.legal_research.label",
    "合规风险分析": "legal_task.compliance_analysis.label",
    "审查结论摘要": "legal_task.review_summary.label",
    "法律文书生成": "legal_task.legal_document_generation.label",
    "红线比对": "legal_task.redline_comparison.label",
    "法务审批流建议": "legal_task.approval_flow_suggestion.label",
    "参与智能体": "multiagent.agent_selection.title",
    "正在加载法律智能体策略...": "multiagent.agent_selection.loading",
    "恢复当前任务推荐": "action.restore_recommended_agents",
    "合同或法律材料文件：": "contract.file.label",
    "上传并解析合同文件": "action.parse_contract_file",
    "服务器路径解析": "contract.server_path.summary",
    "合同或法律材料文件路径：": "contract.server_path.label",
    "按服务器路径解析": "action.parse_contract_path",
    "法律专家团队": "multiagent.team_info.title",
    "补充说明或具体问题：": "multiagent.task.label",
    "开始多智能体审查": "action.start_review",
    "查看法律专家团队": "action.show_team",
    "查看处理模式": "action.show_mode",
    "清除审查结果": "action.clear_review_result",
    "审查进度": "result.progress.title",
    "法律专家团队加载中...": "result.progress.team_loading",
    "准备开始法律审查...": "result.progress.ready",
    "法律审查报告": "result.report.title",
    "最终审查结论": "result.final_conclusion.title",
    "复制报告": "action.copy_report",
    "下载报告": "action.download_report",
    "查看协作详情": "action.show_collaboration_details",
    "审查状态：": "result.stats.status",
    "参与专家：": "result.stats.agents",
    "协作记录：": "result.stats.messages",
    "审查耗时：": "result.stats.duration",
    "各法律专家分析": "result.contributions.title",
    "默认折叠，展开后查看各专家的完整分析过程。": "result.contributions.summary",
    "展开": "action.expand",
    "多智能体协作过程": "result.messages.title",
    "默认折叠，展开后查看专家之间的任务分发和响应记录。": "result.messages.summary",
}


MULTIAGENT_PLACEHOLDER_KEYS = {
    "legalFilePath": "contract.server_path.placeholder",
    "collaborationTask": "multiagent.task.placeholder",
}


EXPECTED_LEGAL_TASK_OPTIONS = {
    "contract_review": ("legal_task.contract_review.label", "合同审查"),
    "risk_identification": (
        "legal_task.risk_identification.label",
        "合同风险识别",
    ),
    "revision_suggestions": (
        "legal_task.revision_suggestions.label",
        "修改建议与替代条款",
    ),
    "legal_research": ("legal_task.legal_research.label", "法律依据检索"),
    "compliance_analysis": (
        "legal_task.compliance_analysis.label",
        "合规风险分析",
    ),
    "review_summary": ("legal_task.review_summary.label", "审查结论摘要"),
    "legal_document_generation": (
        "legal_task.legal_document_generation.label",
        "法律文书生成",
    ),
    "redline_comparison": ("legal_task.redline_comparison.label", "红线比对"),
    "approval_flow_suggestion": (
        "legal_task.approval_flow_suggestion.label",
        "法务审批流建议",
    ),
}


KNOWLEDGE_TEXT_KEYS = {
    "➕ 我的知识库": "knowledge.create.user.title",
    "知识库名称：": "knowledge.create.user_name_label",
    "说明：": "knowledge.common.description_label",
    "创建我的知识库": "knowledge.create.user.action",
    "🏛️ 公共知识库管理": "knowledge.create.public.title",
    "公共知识库名称：": "knowledge.create.public_name_label",
    "创建公共知识库": "knowledge.create.public.action",
    "📝 上传法律资料文本": "knowledge.upload.text.title",
    "目标知识库：": "knowledge.upload.target_label",
    "-- 请先加载或创建知识库 --": "knowledge.upload.target_placeholder",
    "法律资料内容（每行一条资料）：": "knowledge.upload.text.content_label",
    "上传法律资料文本": "knowledge.upload.text.action",
    "📁 上传法律资料文件": "knowledge.upload.file.title",
    "选择法律资料文件：": "knowledge.upload.file.file_label",
    "上传法律资料文件": "knowledge.upload.file.action",
    "ℹ️ 资料库状态": "knowledge.info.title",
    "选择资料库：": "knowledge.info.selector_label",
    "-- 请先加载资料库列表 --": "knowledge.common.load_list_placeholder",
    "刷新状态": "knowledge.info.refresh_action",
    "点击“刷新状态”查看资料库状态": "knowledge.info.empty",
    "📚 已有资料库": "knowledge.list.title",
    "管理可供法律审查调用的法规、案例、合同模板和企业制度资料库。": "knowledge.list.description",
    "刷新资料库列表": "knowledge.list.refresh_action",
    "🧾 上传审计记录": "knowledge.audit.title",
    "查看上传审计": "knowledge.audit.load_action",
    "🗑️ 危险操作": "knowledge.danger.title",
    "选择知识库：": "knowledge.danger.selector_label",
    "-- 请选择可管理知识库 --": "knowledge.danger.selector_placeholder",
    "清空资料库": "knowledge.danger.clear_action",
    "删除资料库": "knowledge.danger.delete_action",
    "⚠️ 清空资料库会删除库内资料但保留资料库；删除资料库会移除库本身并从列表中消失，操作不可恢复。": "knowledge.danger.warning",
    "📄 浏览资料库内容": "knowledge.documents.title",
    "查看资料库：": "knowledge.documents.selector_label",
    "加载资料列表": "knowledge.documents.load_action",
    "刷新": "knowledge.documents.refresh_action",
    "删除选中资料": "knowledge.documents.delete_selected_action",
}


KNOWLEDGE_PLACEHOLDER_KEYS = {
    "createUserKbName": "knowledge.create.user_name_placeholder",
    "createUserKbDescription": "knowledge.create.user_description_placeholder",
    "createPublicKbName": "knowledge.create.public_name_placeholder",
    "createPublicKbDescription": "knowledge.create.public_description_placeholder",
    "textContent": "knowledge.upload.text.content_placeholder",
}


EXPECTED_SCOPE_IDS = {
    "knowledgeTab": {
        "batchDeleteBtn",
        "browserCollection",
        "collectionsList",
        "createPublicKbDescription",
        "createPublicKbName",
        "createPublicKbResult",
        "createUserKbDescription",
        "createUserKbName",
        "createUserKbResult",
        "docBrowser",
        "docStats",
        "fileUploadKbSelect",
        "infoCollection",
        "knowledgeInfo",
        "knowledgeTab",
        "manageKbSelect",
        "publicKbAdminCard",
        "ragUploadFile",
        "textContent",
        "uploadAuditList",
        "uploadFileResult",
        "uploadKbSelect",
        "uploadTextResult",
    },
    "multiagentTab": {
        "agentContributionsCard",
        "agentContributionsList",
        "agentContributionsSummary",
        "agentContributionsToggle",
        "agentCount",
        "collaborationFinalOutput",
        "collaborationMessagesCard",
        "collaborationMode",
        "collaborationProgressCard",
        "collaborationResultCard",
        "collaborationStartBtn",
        "collaborationStatus",
        "collaborationSuccess",
        "collaborationTask",
        "collaborationTeam",
        "collaborationTeamInfo",
        "collaborationTime",
        "legalAgentGapWarning",
        "legalAgentOptions",
        "legalAgentSelection",
        "legalAgentSelectionStatus",
        "legalContractFile",
        "legalFileParseBtn",
        "legalFileParseStatus",
        "legalFilePath",
        "legalFileSection",
        "legalTaskDescription",
        "legalTaskSection",
        "legalTaskType",
        "messageCount",
        "messagesList",
        "messagesSummary",
        "messagesToggle",
        "multiAgentIncludePublicKnowledge",
        "multiAgentKnowledgeBase",
        "multiagentTab",
        "restoreLegalAgentDefaults",
        "teamAgents",
        "teamDescription",
        "teamInfoCard",
        "teamUseCases",
    },
}


EXPECTED_SCOPE_ONCLICKS = {
    "knowledgeTab": {
        "batchDeleteDocuments()",
        "clearKnowledgeBase()",
        "createPublicKnowledgeBase()",
        "createUserKnowledgeBase()",
        "deleteKnowledgeBaseCollection()",
        "getKnowledgeInfo()",
        "loadAllCollections()",
        "loadDocuments()",
        "loadUploadAudit()",
        "refreshDocuments()",
        "uploadFile()",
        "uploadTexts()",
    },
    "multiagentTab": {
        "clearCollaborationResult()",
        "copyCollaborationResult()",
        "downloadCollaborationResult()",
        "loadAllCollections()",
        "parseLegalContractFile()",
        "parseLegalContractFileFromPath()",
        "restoreLegalAgentDefaults()",
        "showCollaborationDetails()",
        "showModeDetails()",
        "showTeamDetails()",
        "startCollaboration()",
        "toggleCollaborationSection('agentContributionsList', 'agentContributionsToggle')",
        "toggleCollaborationSection('messagesList', 'messagesToggle')",
    },
}


@dataclass
class HtmlNode:
    tag: str
    attrs: dict[str, str | None]
    line: int = 0
    parent: HtmlNode | None = None
    children: list[HtmlNode] = field(default_factory=list)
    direct_text: list[str] = field(default_factory=list)


class DomParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = HtmlNode("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = HtmlNode(tag, dict(attrs), self.getpos()[0], self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID_ELEMENTS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = HtmlNode(tag, dict(attrs), self.getpos()[0], self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data):
        self.stack[-1].direct_text.append(data)


def _walk(node: HtmlNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def _normalized_text(node: HtmlNode) -> str:
    return " ".join(" ".join(node.direct_text).split())


def _find_by_id(root: HtmlNode, node_id: str) -> HtmlNode:
    return next(node for node in _walk(root) if node.attrs.get("id") == node_id)


@pytest.fixture(scope="module")
def index_source() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dom(index_source: str) -> HtmlNode:
    parser = DomParser()
    parser.feed(index_source)
    return parser.root


def _assert_text_markers(
    scope: HtmlNode, expected: dict[str, str], scope_name: str
) -> None:
    errors: list[str] = []
    for text, key in expected.items():
        matches = [node for node in _walk(scope) if _normalized_text(node) == text]
        if not matches:
            errors.append(f"{scope_name}: missing static node {text!r}")
            continue
        for node in matches:
            actual = node.attrs.get("data-i18n")
            if actual != key:
                errors.append(
                    f"{scope_name}:{node.line} <{node.tag}> {text!r}: "
                    f"expected data-i18n={key!r}, got {actual!r}"
                )
    assert errors == []


def _assert_static_text_inventory(scope: HtmlNode, expected: dict[str, str]) -> None:
    actual = {
        text
        for node in _walk(scope)
        if (text := _normalized_text(node)) and CJK_PATTERN.search(text)
    }
    assert actual == set(expected)


def _assert_placeholder_markers(
    scope: HtmlNode, expected: dict[str, str], scope_name: str
) -> None:
    errors: list[str] = []
    for node_id, key in expected.items():
        node = _find_by_id(scope, node_id)
        actual = node.attrs.get("data-i18n-placeholder")
        if actual != key:
            errors.append(
                f"{scope_name}:{node.line} #{node_id} placeholder "
                f"{node.attrs.get('placeholder')!r}: expected "
                f"data-i18n-placeholder={key!r}, got {actual!r}"
            )
    assert errors == []


def test_visible_tabs_keep_dom_contract_and_add_exact_i18n_keys(dom: HtmlNode):
    tabs = next(
        node
        for node in _walk(dom)
        if "tabs" in (node.attrs.get("class") or "").split()
    )
    buttons = {
        node.attrs["data-tab"]: node
        for node in _walk(tabs)
        if node.attrs.get("data-tab")
    }

    assert set(buttons) == set(EXPECTED_TABS)
    for tab_name, (key, onclick, text) in EXPECTED_TABS.items():
        button = buttons[tab_name]
        assert button.attrs.get("onclick") == onclick
        assert _normalized_text(button) == text
        assert button.attrs.get("data-i18n") == key


def test_multiagent_static_text_has_exact_i18n_keys(dom: HtmlNode):
    scope = _find_by_id(dom, "multiagentTab")
    _assert_static_text_inventory(scope, MULTIAGENT_TEXT_KEYS)
    _assert_text_markers(scope, MULTIAGENT_TEXT_KEYS, "#multiagentTab")


def test_legal_task_option_values_map_one_to_one_to_exact_keys(dom: HtmlNode):
    selector = _find_by_id(dom, "legalTaskType")
    options = {
        node.attrs["value"]: node
        for node in _walk(selector)
        if node.tag == "option" and node.attrs.get("value")
    }

    assert set(options) == set(EXPECTED_LEGAL_TASK_OPTIONS)
    for value, (key, text) in EXPECTED_LEGAL_TASK_OPTIONS.items():
        assert _normalized_text(options[value]) == text
        assert options[value].attrs.get("data-i18n") == key


def test_multiagent_placeholders_have_exact_i18n_keys(dom: HtmlNode):
    _assert_placeholder_markers(
        _find_by_id(dom, "multiagentTab"),
        MULTIAGENT_PLACEHOLDER_KEYS,
        "#multiagentTab",
    )


def test_knowledge_static_text_has_exact_i18n_keys(dom: HtmlNode):
    scope = _find_by_id(dom, "knowledgeTab")
    cards = [
        node
        for node in _walk(scope)
        if "rag-card" in (node.attrs.get("class") or "").split()
    ]
    # 当前源码实际为 9 张卡片；计划中的“10 个卡片标题”与 DOM 不一致。
    assert len(cards) == 9
    _assert_static_text_inventory(scope, KNOWLEDGE_TEXT_KEYS)
    _assert_text_markers(scope, KNOWLEDGE_TEXT_KEYS, "#knowledgeTab")


def test_knowledge_placeholders_have_exact_i18n_keys(dom: HtmlNode):
    _assert_placeholder_markers(
        _find_by_id(dom, "knowledgeTab"),
        KNOWLEDGE_PLACEHOLDER_KEYS,
        "#knowledgeTab",
    )


def test_data_i18n_is_only_applied_to_leaf_nodes(dom: HtmlNode):
    marked = []
    for scope_id in ("multiagentTab", "knowledgeTab"):
        scope = _find_by_id(dom, scope_id)
        marked.extend(node for node in _walk(scope) if node.attrs.get("data-i18n"))

    errors = [
        f"line {node.line} <{node.tag}> data-i18n={node.attrs['data-i18n']!r} "
        "must not contain functional child elements"
        for node in marked
        if node.children
    ]
    assert errors == []


def test_dom_ids_data_tabs_and_onclick_handlers_keep_baseline(dom: HtmlNode):
    for scope_id in ("knowledgeTab", "multiagentTab"):
        scope = _find_by_id(dom, scope_id)
        assert {node.attrs["id"] for node in _walk(scope) if node.attrs.get("id")} == (
            EXPECTED_SCOPE_IDS[scope_id]
        )
        assert {
            node.attrs["onclick"]
            for node in _walk(scope)
            if node.attrs.get("onclick")
        } == EXPECTED_SCOPE_ONCLICKS[scope_id]

    tabs = {
        node.attrs["data-tab"]: node.attrs.get("onclick")
        for node in _walk(dom)
        if node.attrs.get("data-tab") in EXPECTED_TABS
    }
    assert tabs == {
        tab_name: contract[1] for tab_name, contract in EXPECTED_TABS.items()
    }


def test_domestic_index_does_not_embed_global_language_runtime(index_source: str):
    assert "const I18N" not in index_source
    assert "langSelect" not in index_source
    assert "setLanguage" not in index_source
