#!/usr/bin/env python3
"""
生成国际版前端 HTML：盖亚国际世界模型法律智能体系统
基于 index.html，添加三语支持（中文/英文/俄语，默认英文）
全面清理所有中文文本，替换为英文。
"""
import re

INDEX_PATH = "src/shuyixiao_agent/static/index.html"
OUTPUT_PATH = "src/shuyixiao_agent/static/global.html"


class BuildRuleError(RuntimeError):
    """构建规则未按预期唯一命中。"""


def replace_once(content: str, old: str, new: str, rule_name: str) -> str:
    """仅在规则唯一命中时执行替换。"""
    count = content.count(old)
    if count != 1:
        raise BuildRuleError(f"{rule_name}: expected 1 match, got {count}")
    return content.replace(old, new, 1)


# ============================================================
# 三语翻译字典
# ============================================================
I18N = {
    # 页面标题
    "page_title": {
        "en": "Gaia International World Model Legal Intelligence System",
        "zh": "盖亚国际世界模型法律智能体系统",
        "ru": "Международная система юридического интеллекта Gaia World Model",
    },
    # 登录页标题
    "login_title": {
        "en": "Login to Gaia International World Model Legal Intelligence System",
        "zh": "登录盖亚国际世界模型法律智能体系统",
        "ru": "Вход в Международную систему юридического интеллекта Gaia World Model",
    },
    "login_subtitle": {
        "en": "Please use your registered account to access the contract review, knowledge base, and multi-agent workstation.",
        "zh": "请使用已开通的账号进入合同审查、知识库和多智能体工作台。",
        "ru": "Пожалуйста, используйте зарегистрированную учетную запись для доступа к проверке контрактов, базе знаний и мультиагентной рабочей станции.",
    },
    "login_username": {
        "en": "Username",
        "zh": "用户名",
        "ru": "Имя пользователя",
    },
    "login_password": {
        "en": "Password",
        "zh": "密码",
        "ru": "Пароль",
    },
    "login_button": {
        "en": "Login",
        "zh": "登录",
        "ru": "Войти",
    },
    # Header
    "header_title": {
        "en": "Gaia International World Model Legal Intelligence System",
        "zh": "盖亚国际世界模型法律智能体系统",
        "ru": "Международная система юридического интеллекта Gaia World Model",
    },
    "user_label": {
        "en": "Logged In",
        "zh": "已登录",
        "ru": "В системе",
    },
    "logout_button": {
        "en": "Logout",
        "zh": "退出",
        "ru": "Выйти",
    },
    # Tabs
    "tab_multiagent": {
        "en": "Multi-Agent System",
        "zh": "法律多智能体系统",
        "ru": "Мультиагентная система",
    },
    "tab_knowledge": {
        "en": "Knowledge Base",
        "zh": "知识库管理",
        "ru": "База знаний",
    },
    # Language switcher
    "lang_label": {
        "en": "Language",
        "zh": "语言",
        "ru": "Язык",
    },
    # Multi-agent tab
    "team_label": {
        "en": "Team:",
        "zh": "团队：",
        "ru": "Команда:",
    },
    "mode_label": {
        "en": "Mode:",
        "zh": "模式：",
        "ru": "Режим:",
    },
    "legal_task_label": {
        "en": "Legal Task:",
        "zh": "法律任务：",
        "ru": "Юридическая задача:",
    },
    "kb_label": {
        "en": "Knowledge Base:",
        "zh": "知识库：",
        "ru": "База знаний:",
    },
    "include_public_kb": {
        "en": "Include Public KB",
        "zh": "包含公共知识库",
        "ru": "Вкл. публичную БЗ",
    },
    "contract_file_label": {
        "en": "Contract File:",
        "zh": "合同文件：",
        "ru": "Файл контракта:",
    },
    "or_label": {
        "en": "or",
        "zh": "或",
        "ru": "или",
    },
    "server_path_label": {
        "en": "Server Path:",
        "zh": "服务器路径：",
        "ru": "Путь на сервере:",
    },
    "parse_contract_btn": {
        "en": "Parse Contract",
        "zh": "解析合同",
        "ru": "Разобрать контракт",
    },
    "task_input_placeholder": {
        "en": "Enter your task description...",
        "zh": "请输入任务描述...",
        "ru": "Введите описание задачи...",
    },
    "start_collaboration_btn": {
        "en": "Start Multi-Agent Review",
        "zh": "开始多智能体审查",
        "ru": "Начать мультиагентную проверку",
    },
    "reviewing_text": {
        "en": "Reviewing...",
        "zh": "审查中...",
        "ru": "Проверка...",
    },
    "initializing_text": {
        "en": "Initializing legal multi-agent review...",
        "zh": "正在初始化法律多智能体审查...",
        "ru": "Инициализация мультиагентной юридической проверки...",
    },
    # Knowledge base tab
    "kb_create_user_title": {
        "en": "Create User Knowledge Base",
        "zh": "创建用户知识库",
        "ru": "Создать пользовательскую БЗ",
    },
    "kb_create_public_title": {
        "en": "Admin: Create Public Knowledge Base",
        "zh": "管理员：创建公共知识库",
        "ru": "Админ: Создать публичную БЗ",
    },
    "kb_upload_text_title": {
        "en": "Upload Text",
        "zh": "上传文本",
        "ru": "Загрузить текст",
    },
    "kb_upload_file_title": {
        "en": "File Upload",
        "zh": "文件上传",
        "ru": "Загрузка файла",
    },
    "kb_info_title": {
        "en": "Knowledge Base Info",
        "zh": "知识库信息",
        "ru": "Информация о БЗ",
    },
    "kb_list_title": {
        "en": "All Knowledge Bases",
        "zh": "所有知识库列表",
        "ru": "Все базы знаний",
    },
    "kb_audit_title": {
        "en": "Upload Audit",
        "zh": "上传审计",
        "ru": "Аудит загрузок",
    },
    "kb_manage_title": {
        "en": "Knowledge Base Management",
        "zh": "知识库管理",
        "ru": "Управление БЗ",
    },
    "kb_doc_browser_title": {
        "en": "Document Browser",
        "zh": "文档浏览器",
        "ru": "Просмотр документов",
    },
    "kb_name_placeholder": {
        "en": "Knowledge Base Name",
        "zh": "知识库名称",
        "ru": "Название базы знаний",
    },
    "kb_desc_placeholder": {
        "en": "Description (optional)",
        "zh": "描述（可选）",
        "ru": "Описание (необязательно)",
    },
    "kb_create_btn": {
        "en": "Create",
        "zh": "创建",
        "ru": "Создать",
    },
    "kb_upload_btn": {
        "en": "Upload",
        "zh": "上传",
        "ru": "Загрузить",
    },
    "kb_select_placeholder": {
        "en": "Select Knowledge Base",
        "zh": "选择知识库",
        "ru": "Выберите базу знаний",
    },
    "kb_refresh_btn": {
        "en": "Refresh",
        "zh": "刷新",
        "ru": "Обновить",
    },
    "kb_delete_btn": {
        "en": "Delete Selected",
        "zh": "删除选中",
        "ru": "Удалить выбранное",
    },
    # Quick tasks
    "quick_tasks_label": {
        "en": "Quick Tasks:",
        "zh": "快速任务：",
        "ru": "Быстрые задачи:",
    },
    # Legal task templates
    "task_contract_review": {
        "en": "Contract Review",
        "zh": "合同审查",
        "ru": "Проверка контракта",
    },
    "task_risk_identification": {
        "en": "Risk Identification",
        "zh": "合同风险识别",
        "ru": "Выявление рисков",
    },
    "task_revision_suggestions": {
        "en": "Revision Suggestions",
        "zh": "修改建议与替代条款",
        "ru": "Предложения по изменению",
    },
    "task_legal_research": {
        "en": "Legal Research",
        "zh": "法律依据检索",
        "ru": "Юридический поиск",
    },
    "task_compliance_analysis": {
        "en": "Compliance Analysis",
        "zh": "合规风险分析",
        "ru": "Анализ соответствия",
    },
    "task_review_summary": {
        "en": "Review Summary",
        "zh": "审查结论摘要",
        "ru": "Резюме проверки",
    },
    "task_legal_document": {
        "en": "Legal Document Generation",
        "zh": "法律文书生成",
        "ru": "Создание документа",
    },
    "task_redline": {
        "en": "Redline Comparison",
        "zh": "红线比对",
        "ru": "Сравнение версий",
    },
    "task_approval_flow": {
        "en": "Approval Flow",
        "zh": "法务审批流建议",
        "ru": "Процесс утверждения",
    },
    # Agent display names
    "agent_contract_reviewer": {
        "en": "Contract Review Coordinator",
        "zh": "合同审查协调员",
        "ru": "Координатор проверки контрактов",
    },
    "agent_clause_risk_analyzer": {
        "en": "Clause Risk Analyst",
        "zh": "条款风险分析师",
        "ru": "Аналитик рисков положений",
    },
    "agent_legal_researcher": {
        "en": "Legal Researcher",
        "zh": "法律依据检索员",
        "ru": "Юридический исследователь",
    },
    "agent_drafting_specialist": {
        "en": "Legal Drafting Specialist",
        "zh": "法律文书起草专家",
        "ru": "Специалист по составлению документов",
    },
    "agent_compliance_checker": {
        "en": "Compliance Reviewer",
        "zh": "合规审查专员",
        "ru": "Специалист по соответствию",
    },
    "agent_audit_recorder": {
        "en": "Audit Recorder",
        "zh": "审计留痕记录员",
        "ru": "Аудитор",
    },
    # Collaboration modes
    "mode_sequential": {
        "en": "Sequential",
        "zh": "顺序协作",
        "ru": "Последовательный",
    },
    "mode_parallel": {
        "en": "Parallel",
        "zh": "并行协作",
        "ru": "Параллельный",
    },
    "mode_hierarchical": {
        "en": "Hierarchical",
        "zh": "层级协作",
        "ru": "Иерархический",
    },
    "mode_peer_to_peer": {
        "en": "Peer-to-Peer",
        "zh": "对等协作",
        "ru": "Одноранговый",
    },
    "mode_hybrid": {
        "en": "Hybrid",
        "zh": "混合模式",
        "ru": "Гибридный",
    },
    # Common
    "loading_text": {
        "en": "Loading...",
        "zh": "加载中...",
        "ru": "Загрузка...",
    },
    "error_text": {
        "en": "Error",
        "zh": "错误",
        "ru": "Ошибка",
    },
    "success_text": {
        "en": "Success",
        "zh": "成功",
        "ru": "Успешно",
    },
    "confirm_text": {
        "en": "Confirm",
        "zh": "确认",
        "ru": "Подтвердить",
    },
    "cancel_text": {
        "en": "Cancel",
        "zh": "取消",
        "ru": "Отмена",
    },
    "close_text": {
        "en": "Close",
        "zh": "关闭",
        "ru": "Закрыть",
    },
    "export_btn": {
        "en": "Export Report",
        "zh": "导出报告",
        "ru": "Экспорт отчета",
    },
    "copy_btn": {
        "en": "Copy",
        "zh": "复制",
        "ru": "Копировать",
    },
    "download_btn": {
        "en": "Download",
        "zh": "下载",
        "ru": "Скачать",
    },
    "clear_btn": {
        "en": "Clear",
        "zh": "清除",
        "ru": "Очистить",
    },
    # JS alert messages
    "alert_enter_task": {
        "en": "Please enter a task description",
        "zh": "请输入任务描述",
        "ru": "Пожалуйста, введите описание задачи",
    },
    "alert_select_team": {
        "en": "Please select a collaboration team",
        "zh": "请选择协作团队",
        "ru": "Пожалуйста, выберите команду",
    },
    "alert_policy_not_ready": {
        "en": "Legal agent policy is not yet loaded, please try again later",
        "zh": "法律智能体策略尚未加载完成，请稍后重试",
        "ru": "Политика юридических агентов еще не загружена, попробуйте позже",
    },
    "alert_collaboration_failed": {
        "en": "Collaboration failed: ",
        "zh": "协作失败: ",
        "ru": "Ошибка collaboration: ",
    },
    # Collaboration status
    "status_team_ready": {
        "en": "Legal expert team assembled, starting review...",
        "zh": "法律专家团队已组建，开始审查...",
        "ru": "Команда юридических экспертов собрана, начинаем проверку...",
    },
    "status_preparing": {
        "en": "Preparing legal multi-agent review...",
        "zh": "正在准备法律多智能体审查...",
        "ru": "Подготовка мультиагентной юридической проверки...",
    },
    # Team info
    "team_members_label": {
        "en": "Team Members:",
        "zh": "团队成员：",
        "ru": "Члены команды:",
    },
    "team_use_cases_label": {
        "en": "Use Cases:",
        "zh": "适用场景：",
        "ru": "Сценарии использования:",
    },
    "processing_mode_label": {
        "en": "Processing Mode:",
        "zh": "处理模式:",
        "ru": "Режим обработки:",
    },
    "actual_participants_label": {
        "en": "Actual Participants:",
        "zh": "实际参与:",
        "ru": "Фактические участники:",
    },
    "selection_source_label": {
        "en": "Selection Source:",
        "zh": "选择来源:",
        "ru": "Источник выбора:",
    },
    # Legal agent selection
    "legal_agent_selection_label": {
        "en": "Legal Agent Selection",
        "zh": "法律智能体选择",
        "ru": "Выбор юридических агентов",
    },
    "restore_defaults_btn": {
        "en": "Restore Defaults",
        "zh": "恢复默认",
        "ru": "Восстановить по умолчанию",
    },
    # Document modal
    "doc_modal_title": {
        "en": "Document Details",
        "zh": "资料详情",
        "ru": "Детали документа",
    },
    # Collaboration result
    "collab_result_title": {
        "en": "Review Results",
        "zh": "审查结果",
        "ru": "Результаты проверки",
    },
    "agent_contributions_title": {
        "en": "Agent Contributions",
        "zh": "Agent 贡献",
        "ru": "Вклад агентов",
    },
    "messages_title": {
        "en": "Message Records",
        "zh": "消息记录",
        "ru": "Записи сообщений",
    },
    "execution_stats_title": {
        "en": "Execution Statistics",
        "zh": "执行统计",
        "ru": "Статистика выполнения",
    },
    "expand_text": {
        "en": "Expand",
        "zh": "展开",
        "ru": "Развернуть",
    },
    "collapse_text": {
        "en": "Collapse",
        "zh": "折叠",
        "ru": "Свернуть",
    },
    # Footer / disclaimer
    "disclaimer_text": {
        "en": "This output does not constitute formal legal advice. Please consult a qualified lawyer for legal decisions.",
        "zh": "本输出不构成正式法律意见，法律决策请咨询合格律师。",
        "ru": "Данный вывод не является официальной юридической консультацией. Для принятия юридических решений обратитесь к квалифицированному юристу.",
    },
}


# P1b 可见 Tab 静态资产。保留上方旧扁平 key，避免影响既有生成规则。
P1B_STATIC_I18N = {
    "auth.session_expired": {
        "en": "Your session has expired. Please sign in again.",
        "zh": "登录状态已失效，请重新登录。",
        "ru": "Срок действия сеанса истёк. Войдите снова.",
    },
    "auth.logged_out": {
        "en": "You have signed out.",
        "zh": "已退出登录。",
        "ru": "Вы вышли из системы.",
    },
    "error.request_failed_http": {
        "en": "Request failed (HTTP {status})",
        "zh": "请求失败（HTTP {status}）",
        "ru": "Ошибка запроса (HTTP {status})",
    },
    "error.read_response_failed": {
        "en": "Failed to read the error response:",
        "zh": "读取错误响应失败：",
        "ru": "Не удалось прочитать ответ с ошибкой:",
    },
    "multiagent.title": {
        "en": "Legal Multi-Agent System",
        "zh": "法律多智能体系统",
        "ru": "Юридическая мультиагентная система",
    },
    "lang.option.en": {
        "en": "English",
        "zh": "English",
        "ru": "English",
    },
    "lang.option.zh": {
        "en": "中文",
        "zh": "中文",
        "ru": "中文",
    },
    "lang.option.ru": {
        "en": "Русский",
        "zh": "Русский",
        "ru": "Русский",
    },
    "multiagent.description": {
        "en": "Select a legal task and upload a contract or supporting material. The legal multi-agent team will review it, research legal authorities, analyze compliance, and propose revisions.",
        "zh": "选择法律任务，上传合同或材料，由法律多智能体团队完成审查、检索、合规分析和修改建议。",
        "ru": "Выберите юридическую задачу и загрузите договор или материалы. Команда агентов проведёт проверку, поиск правовых оснований, анализ соответствия и предложит изменения.",
    },
    "multiagent.team.label": {
        "en": "Legal service team:",
        "zh": "法律服务团队：",
        "ru": "Команда юридической службы:",
    },
    "multiagent.team.legal_contract_review": {
        "en": "Legal Contract Review Team",
        "zh": "法律合同审查团队",
        "ru": "Команда проверки юридических договоров",
    },
    "multiagent.mode.label": {
        "en": "Multi-agent processing mode:",
        "zh": "多智能体处理模式：",
        "ru": "Режим работы агентов:",
    },
    "multiagent.agent_selection.title": {
        "en": "Participating agents",
        "zh": "参与智能体",
        "ru": "Участвующие агенты",
    },
    "multiagent.agent_selection.loading": {
        "en": "Loading legal agent policy...",
        "zh": "正在加载法律智能体策略...",
        "ru": "Загрузка политики юридических агентов...",
    },
    "status.loading_collaboration_data": {
        "en": "Loading collaboration teams and modes...",
        "zh": "正在加载协作团队和处理模式...",
        "ru": "Загрузка команд и режимов взаимодействия...",
    },
    "error.load_collaboration_data": {
        "en": "Failed to load collaboration data. Legal collaboration cannot be started safely.",
        "zh": "协作数据加载失败，无法安全发起法律协作。",
        "ru": "Не удалось загрузить данные взаимодействия. Безопасный запуск юридической работы невозможен.",
    },
    "action.retry": {
        "en": "Retry",
        "zh": "重试",
        "ru": "Повторить",
    },
    "badge.required": {
        "en": "Required",
        "zh": "必选",
        "ru": "Обязательный",
    },
    "badge.recommended": {
        "en": "Recommended",
        "zh": "推荐",
        "ru": "Рекомендуемый",
    },
    "status.selected_agents": {
        "en": "Selected agents: {count}",
        "zh": "已选择 {count} 个智能体",
        "ru": "Выбрано агентов: {count}",
    },
    "warning.capability_gap": {
        "en": "{count} recommended agent(s) are not selected: {agents}.",
        "zh": "当前有 {count} 个推荐智能体未选择：{agents}。",
        "ru": "Не выбрано рекомендуемых агентов: {count}. {agents}.",
    },
    "warning.capability_gap_default": {
        "en": "The corresponding professional capability may be missing",
        "zh": "可能缺少对应专业能力",
        "ru": "Возможно отсутствие соответствующей профессиональной компетенции",
    },
    "multiagent.team_info.title": {
        "en": "Legal Expert Team",
        "zh": "法律专家团队",
        "ru": "Команда юридических экспертов",
    },
    "multiagent.task.label": {
        "en": "Additional instructions or specific questions:",
        "zh": "补充说明或具体问题：",
        "ru": "Дополнительные указания или конкретные вопросы:",
    },
    "multiagent.task.placeholder": {
        "en": "Add review priorities, such as payment terms, liability for breach, data compliance, intellectual property ownership, or dispute resolution. Selecting a legal task fills in a standard prompt that you can still edit.",
        "zh": "你可以补充审查重点，例如：重点关注付款条款、违约责任、数据合规、知识产权归属、争议解决方式等。选择法律任务后，系统会自动填充标准提示词，你仍然可以继续修改。",
        "ru": "Укажите приоритеты проверки: условия оплаты, ответственность за нарушение, соответствие требованиям к данным, права на интеллектуальную собственность или разрешение споров. После выбора задачи стандартный запрос можно редактировать.",
    },
    "mode.hierarchical.label": {
        "en": "🏢 Hierarchical collaboration (recommended)",
        "zh": "🏢 层级协作（推荐）",
        "ru": "🏢 Иерархическое взаимодействие (рекомендуется)",
    },
    "mode.sequential.label": {
        "en": "🔄 Sequential collaboration",
        "zh": "🔄 顺序协作",
        "ru": "🔄 Последовательное взаимодействие",
    },
    "mode.parallel.label": {
        "en": "⚡ Parallel collaboration",
        "zh": "⚡ 并行协作",
        "ru": "⚡ Параллельное взаимодействие",
    },
    "mode.peer_to_peer.label": {
        "en": "🤝 Peer-to-peer collaboration",
        "zh": "🤝 对等协作",
        "ru": "🤝 Равноправное взаимодействие",
    },
    "mode.hybrid.label": {
        "en": "🔀 Hybrid mode",
        "zh": "🔀 混合模式",
        "ru": "🔀 Гибридный режим",
    },
    "kb.selector.label": {
        "en": "Related knowledge base:",
        "zh": "关联资料库：",
        "ru": "Связанная база знаний:",
    },
    "kb.selector.none": {
        "en": "Do not use a knowledge base",
        "zh": "不使用资料库",
        "ru": "Не использовать базу знаний",
    },
    "kb.selector.help": {
        "en": "After a knowledge base is selected, the legal researcher and compliance reviewer will automatically retrieve relevant material.",
        "zh": "选择资料库后，法律依据检索员和合规审查专员会自动检索相关资料。",
        "ru": "После выбора базы знаний агент правового поиска и специалист по соответствию автоматически найдут относящиеся материалы.",
    },
    "kb.include_public": {
        "en": "Automatically include accessible public knowledge bases",
        "zh": "自动包含可读公共知识库",
        "ru": "Автоматически включать доступные публичные базы знаний",
    },
    "legal_task.selector.label": {
        "en": "Select the legal task to perform:",
        "zh": "请选择要完成的法律任务：",
        "ru": "Выберите юридическую задачу:",
    },
    "legal_task.selector.placeholder": {
        "en": "-- Select a legal task --",
        "zh": "-- 请选择法律任务 --",
        "ru": "-- Выберите юридическую задачу --",
    },
    "legal_task.contract_review.label": {
        "en": "Contract review",
        "zh": "合同审查",
        "ru": "Проверка договора",
    },
    "legal_task.contract_review.description": {
        "en": "Review the contract as a whole and identify material legal issues.",
        "zh": "全面审查合同并识别重要法律问题。",
        "ru": "Комплексная проверка договора и выявление существенных юридических вопросов.",
    },
    "legal_task.risk_identification.label": {
        "en": "Contract risk identification",
        "zh": "合同风险识别",
        "ru": "Выявление рисков договора",
    },
    "legal_task.risk_identification.description": {
        "en": "Identify and prioritize legal, commercial, and performance risks in the contract.",
        "zh": "识别合同中的法律、商业和履约风险并确定优先级。",
        "ru": "Выявление и приоритизация юридических, коммерческих и исполнительских рисков договора.",
    },
    "legal_task.revision_suggestions.label": {
        "en": "Revision suggestions and alternative clauses",
        "zh": "修改建议与替代条款",
        "ru": "Предложения по изменению и альтернативные условия",
    },
    "legal_task.revision_suggestions.description": {
        "en": "Provide actionable revisions and alternative clause language for identified issues.",
        "zh": "针对已识别问题提供可执行的修改建议和替代条款。",
        "ru": "Подготовка практических изменений и альтернативных формулировок для выявленных проблем.",
    },
    "legal_task.legal_research.label": {
        "en": "Legal authority research",
        "zh": "法律依据检索",
        "ru": "Поиск правовых оснований",
    },
    "legal_task.legal_research.description": {
        "en": "Research relevant laws, regulations, cases, and internal rules, with source references where available.",
        "zh": "检索相关法律、法规、案例和内部制度，并尽可能标注来源。",
        "ru": "Поиск применимых законов, нормативных актов, судебной практики и внутренних правил с указанием источников, если они доступны.",
    },
    "legal_task.compliance_analysis.label": {
        "en": "Compliance risk analysis",
        "zh": "合规风险分析",
        "ru": "Анализ рисков соответствия",
    },
    "legal_task.compliance_analysis.description": {
        "en": "Analyze regulatory and internal compliance risks raised by the transaction and contract.",
        "zh": "分析交易和合同涉及的监管及内部合规风险。",
        "ru": "Анализ регуляторных и внутренних рисков соответствия, связанных со сделкой и договором.",
    },
    "legal_task.review_summary.label": {
        "en": "Review conclusion summary",
        "zh": "审查结论摘要",
        "ru": "Краткое заключение по проверке",
    },
    "legal_task.review_summary.description": {
        "en": "Summarize key findings, risk levels, and recommended next steps.",
        "zh": "汇总关键发现、风险等级和建议的下一步行动。",
        "ru": "Краткое изложение основных выводов, уровней риска и рекомендуемых дальнейших действий.",
    },
    "legal_task.legal_document_generation.label": {
        "en": "Legal document generation",
        "zh": "法律文书生成",
        "ru": "Подготовка юридического документа",
    },
    "legal_task.legal_document_generation.description": {
        "en": "Draft a legal document based on the provided facts, requirements, and applicable authority.",
        "zh": "根据提供的事实、要求和适用依据起草法律文书。",
        "ru": "Подготовка юридического документа на основе предоставленных фактов, требований и применимых правовых оснований.",
    },
    "legal_task.redline_comparison.label": {
        "en": "Redline comparison",
        "zh": "红线比对",
        "ru": "Сравнение редакций",
    },
    "legal_task.redline_comparison.description": {
        "en": "Compare contract versions and explain the legal effect of material changes.",
        "zh": "比较合同版本并说明重大变更的法律影响。",
        "ru": "Сравнение редакций договора и объяснение юридических последствий существенных изменений.",
    },
    "legal_task.approval_flow_suggestion.label": {
        "en": "Legal approval workflow suggestion",
        "zh": "法务审批流建议",
        "ru": "Рекомендации по юридическому согласованию",
    },
    "legal_task.approval_flow_suggestion.description": {
        "en": "Recommend review roles, approval steps, escalation conditions, and required supporting material.",
        "zh": "建议审查角色、审批步骤、升级条件和所需支持材料。",
        "ru": "Рекомендации по ролям, этапам согласования, условиям эскалации и необходимым материалам.",
    },
    "contract.file.label": {
        "en": "Contract or legal material file:",
        "zh": "合同或法律材料文件：",
        "ru": "Файл договора или юридических материалов:",
    },
    "contract.server_path.summary": {
        "en": "Parse from a server path",
        "zh": "服务器路径解析",
        "ru": "Разбор по пути на сервере",
    },
    "contract.server_path.label": {
        "en": "Contract or legal material file path:",
        "zh": "合同或法律材料文件路径：",
        "ru": "Путь к файлу договора или юридических материалов:",
    },
    "contract.server_path.placeholder": {
        "en": "Enter a server-accessible file path, for example: C:/Users/.../contract.pdf or /mnt/c/Users/.../contract.txt",
        "zh": "请输入服务器可访问的文件路径，例如：C:/Users/.../contract.pdf 或 /mnt/c/Users/.../contract.txt",
        "ru": "Введите доступный серверу путь к файлу, например: C:/Users/.../contract.pdf или /mnt/c/Users/.../contract.txt",
    },
    "action.refresh_knowledge_bases": {
        "en": "Refresh knowledge bases",
        "zh": "刷新资料库",
        "ru": "Обновить базы знаний",
    },
    "action.restore_recommended_agents": {
        "en": "Restore recommendations for this task",
        "zh": "恢复当前任务推荐",
        "ru": "Восстановить рекомендации для этой задачи",
    },
    "action.parse_contract_file": {
        "en": "Upload and parse contract file",
        "zh": "上传并解析合同文件",
        "ru": "Загрузить и разобрать файл договора",
    },
    "action.parse_contract_path": {
        "en": "Parse from server path",
        "zh": "按服务器路径解析",
        "ru": "Разобрать по пути на сервере",
    },
    "validation.contract_file_required": {
        "en": "Select a contract or legal material file.",
        "zh": "请选择合同或法律材料文件。",
        "ru": "Выберите файл договора или юридических материалов.",
    },
    "validation.contract_path_required": {
        "en": "Enter the path to a contract or legal material file.",
        "zh": "请输入合同或法律材料文件路径。",
        "ru": "Введите путь к файлу договора или юридических материалов.",
    },
    "status.contract_parsing": {
        "en": "Parsing the contract...",
        "zh": "正在解析合同……",
        "ru": "Выполняется разбор договора...",
    },
    "status.contract_parse_success": {
        "en": "Contract parsed successfully",
        "zh": "合同解析成功",
        "ru": "Договор успешно разобран",
    },
    "error.contract_parse_failed": {
        "en": "Contract parsing failed.",
        "zh": "合同解析失败。",
        "ru": "Не удалось разобрать договор.",
    },
    "contract.summary.type": {
        "en": "Contract type",
        "zh": "合同类型",
        "ru": "Тип договора",
    },
    "contract.summary.parties": {
        "en": "Parties",
        "zh": "主体",
        "ru": "Стороны",
    },
    "contract.summary.amount": {
        "en": "Amount",
        "zh": "金额",
        "ru": "Сумма",
    },
    "contract.summary.term": {
        "en": "Term",
        "zh": "期限",
        "ru": "Срок",
    },
    "contract.summary.clauses": {
        "en": "Key clauses",
        "zh": "关键条款",
        "ru": "Ключевые условия",
    },
    "contract.summary.document_count": {
        "en": "Document segments",
        "zh": "文档片段",
        "ru": "Фрагменты документа",
    },
    "contract.summary.file": {
        "en": "File",
        "zh": "文件",
        "ru": "Файл",
    },
    "contract.summary.character_count": {
        "en": "Characters read",
        "zh": "已读取字符",
        "ru": "Прочитано символов",
    },
    "contract.summary.effective_date": {
        "en": "Effective date",
        "zh": "生效日期",
        "ru": "Дата вступления в силу",
    },
    "contract.summary.structured": {
        "en": "Structured summary",
        "zh": "结构化摘要",
        "ru": "Структурированное резюме",
    },
    "contract.summary.clause_count": {
        "en": "Clause count",
        "zh": "条款数量",
        "ru": "Количество условий",
    },
    "contract.summary.warning_count": {
        "en": "Parsing notes",
        "zh": "解析提示",
        "ru": "Примечания к разбору",
    },
    "contract.summary.unrecognized": {
        "en": "Not identified",
        "zh": "未识别",
        "ru": "Не определено",
    },
    "contract.summary.items": {
        "en": "{count} item(s)",
        "zh": "{count} 项",
        "ru": "Элементов: {count}",
    },
    "contract.summary.more_items": {
        "en": "{count} more item(s); review them in the report.",
        "zh": "另有 {count} 项，建议在审查报告中复核。",
        "ru": "Ещё элементов: {count}; проверьте их в отчёте.",
    },
    "contract.summary.no_structured": {
        "en": "No structured summary was identified. You can continue the multi-agent review, subject to professional review.",
        "zh": "未识别结构化摘要，仍可继续发起多智能体审查并由专业人员复核。",
        "ru": "Структурированное резюме не сформировано. Можно продолжить мультиагентную проверку с последующей проверкой специалистом.",
    },
    "validation.task_required": {
        "en": "Enter a task description.",
        "zh": "请输入任务描述。",
        "ru": "Введите описание задачи.",
    },
    "validation.team_required": {
        "en": "Select a collaboration team.",
        "zh": "请选择协作团队。",
        "ru": "Выберите команду для совместной работы.",
    },
    "validation.agents_required": {
        "en": "Select at least one legal agent.",
        "zh": "请至少选择一个法律智能体。",
        "ru": "Выберите хотя бы одного юридического агента.",
    },
    "status.collaboration_starting": {
        "en": "Starting the legal multi-agent review...",
        "zh": "正在启动法律多智能体审查……",
        "ru": "Запуск юридической мультиагентной проверки...",
    },
    "status.team_ready": {
        "en": "The legal expert team is ready and has started the review.",
        "zh": "法律专家团队已组建，开始审查。",
        "ru": "Команда юридических экспертов сформирована и приступила к проверке.",
    },
    "status.completed": {
        "en": "The legal multi-agent review is complete.",
        "zh": "法律多智能体审查已完成。",
        "ru": "Юридическая мультиагентная проверка завершена.",
    },
    "status.failed": {
        "en": "The legal multi-agent review failed.",
        "zh": "法律多智能体审查失败。",
        "ru": "Не удалось выполнить юридическую мультиагентную проверку.",
    },
    "action.reviewing": {
        "en": "Reviewing...",
        "zh": "审查中……",
        "ru": "Выполняется проверка...",
    },
    "team_info.experts": {
        "en": "{count} expert(s)",
        "zh": "{count} 位专家",
        "ru": "Экспертов: {count}",
    },
    "team_info.mode": {
        "en": "Processing mode",
        "zh": "处理模式",
        "ru": "Режим обработки",
    },
    "team_info.participants": {
        "en": "Actual participants",
        "zh": "实际参与",
        "ru": "Фактические участники",
    },
    "team_info.selection_source": {
        "en": "Selection source",
        "zh": "选择来源",
        "ru": "Источник выбора",
    },
    "team_info.unknown": {
        "en": "Not provided",
        "zh": "未提供",
        "ru": "Не указано",
    },
    "action.start_review": {
        "en": "Start multi-agent review",
        "zh": "开始多智能体审查",
        "ru": "Начать мультиагентную проверку",
    },
    "action.show_team": {
        "en": "View legal expert team",
        "zh": "查看法律专家团队",
        "ru": "Посмотреть команду юридических экспертов",
    },
    "action.show_mode": {
        "en": "View processing mode",
        "zh": "查看处理模式",
        "ru": "Посмотреть режим обработки",
    },
    "action.clear_review_result": {
        "en": "Clear review result",
        "zh": "清除审查结果",
        "ru": "Очистить результат проверки",
    },
    "action.copy_report": {
        "en": "Copy report",
        "zh": "复制报告",
        "ru": "Копировать отчёт",
    },
    "action.download_report": {
        "en": "Download report",
        "zh": "下载报告",
        "ru": "Скачать отчёт",
    },
    "action.show_collaboration_details": {
        "en": "View collaboration details",
        "zh": "查看协作详情",
        "ru": "Посмотреть сведения о взаимодействии",
    },
    "action.expand": {
        "en": "Expand",
        "zh": "展开",
        "ru": "Развернуть",
    },
    "action.collapse": {
        "en": "Collapse",
        "zh": "收起",
        "ru": "Свернуть",
    },
    "result.success": {
        "en": "Success",
        "zh": "成功",
        "ru": "Успешно",
    },
    "result.failed": {
        "en": "Failed",
        "zh": "失败",
        "ru": "Ошибка",
    },
    "result.seconds": {
        "en": "{count} s",
        "zh": "{count} 秒",
        "ru": "{count} с",
    },
    "summary.agent_contributions": {
        "en": "Collapsed by default. {count} legal expert(s) participated; expand to view the full analysis.",
        "zh": "默认折叠，共 {count} 位法律专家参与分析，展开后查看完整过程。",
        "ru": "По умолчанию свёрнуто. В анализе участвовало экспертов: {count}. Разверните, чтобы просмотреть полный процесс.",
    },
    "summary.messages": {
        "en": "Collapsed by default. {count} collaboration record(s); expand to view task distribution and responses.",
        "zh": "默认折叠，共 {count} 条协作记录，展开后查看任务分发和响应过程。",
        "ru": "По умолчанию свёрнуто. Записей взаимодействия: {count}. Разверните, чтобы просмотреть распределение задач и ответы.",
    },
    "status.agent_completed": {
        "en": "Completed",
        "zh": "完成",
        "ru": "Завершено",
    },
    "status.agent_failed": {
        "en": "Failed",
        "zh": "失败",
        "ru": "Ошибка",
    },
    "error.agent_failed_safe": {
        "en": "This agent did not complete successfully. Internal error details are hidden. Review the other expert outputs and obtain human review.",
        "zh": "该智能体执行失败，内部异常已隐藏。请结合其他专家结果并进行人工复核。",
        "ru": "Агент не завершил выполнение. Внутренние сведения об ошибке скрыты. Проверьте результаты других экспертов и выполните ручную проверку.",
    },
    "toast.report_copied": {
        "en": "Review report copied to the clipboard.",
        "zh": "审查报告已复制到剪贴板。",
        "ru": "Отчёт о проверке скопирован в буфер обмена.",
    },
    "toast.copy_failed": {
        "en": "Copy failed. Please copy the report manually.",
        "zh": "复制失败，请手动复制报告。",
        "ru": "Не удалось скопировать отчёт. Скопируйте его вручную.",
    },
    "detail.team_console": {
        "en": "Team details are available in the console.",
        "zh": "团队详情已在控制台输出。",
        "ru": "Сведения о команде доступны в консоли.",
    },
    "detail.mode_console": {
        "en": "Mode details are available in the console.",
        "zh": "模式详情已在控制台输出。",
        "ru": "Сведения о режиме доступны в консоли.",
    },
    "detail.result_console": {
        "en": "Collaboration details are available in the console.",
        "zh": "完整协作结果已在控制台输出。",
        "ru": "Сведения о взаимодействии доступны в консоли.",
    },
    "download.report_title": {
        "en": "Legal Multi-Agent Review Report",
        "zh": "法律多智能体审查报告",
        "ru": "Отчёт о юридической мультиагентной проверке",
    },
    "download.field.task": {"en": "Review task", "zh": "审查任务", "ru": "Задача проверки"},
    "download.field.team": {"en": "Legal service team", "zh": "法律服务团队", "ru": "Команда юридической службы"},
    "download.field.mode": {"en": "Processing mode", "zh": "处理模式", "ru": "Режим обработки"},
    "download.field.legal_task_type": {"en": "Legal task type", "zh": "法律任务类型", "ru": "Тип юридической задачи"},
    "download.field.selection_source": {"en": "Selection source", "zh": "选择来源", "ru": "Источник выбора"},
    "download.field.participants": {"en": "Participating agents", "zh": "实际参与智能体", "ru": "Участвующие агенты"},
    "download.field.capability_gaps": {"en": "Capability gap notice", "zh": "能力缺口提示", "ru": "Предупреждение о пробелах в компетенциях"},
    "download.field.knowledge_base": {"en": "Related knowledge base", "zh": "关联资料库", "ru": "Связанная база знаний"},
    "download.field.include_public_knowledge": {"en": "Include public knowledge", "zh": "包含公共知识库", "ru": "Использовать общедоступную базу знаний"},
    "download.field.file": {"en": "Contract or material file", "zh": "合同或材料文件", "ru": "Файл договора или материала"},
    "download.field.uploaded_file_id": {"en": "Uploaded file ID", "zh": "上传文件 ID", "ru": "ID загруженного файла"},
    "download.field.has_structured_summary": {"en": "Structured summary available", "zh": "是否包含结构化摘要", "ru": "Доступно структурированное резюме"},
    "download.field.started_at": {"en": "Started at", "zh": "发起时间", "ru": "Время запуска"},
    "download.field.agent_count": {"en": "Expert count", "zh": "参与专家数", "ru": "Количество экспертов"},
    "download.field.duration": {"en": "Review duration", "zh": "审查耗时", "ru": "Длительность проверки"},
    "download.section.final_conclusion": {"en": "Final Review Conclusion", "zh": "最终审查结论", "ru": "Итоговое заключение проверки"},
    "download.section.agent_analysis": {"en": "Legal Expert Analysis", "zh": "各法律专家分析", "ru": "Анализ юридических экспертов"},
    "download.value.yes": {"en": "Yes", "zh": "是", "ru": "Да"},
    "download.value.no": {"en": "No", "zh": "否", "ru": "Нет"},
    "download.value.none": {"en": "None", "zh": "无", "ru": "Нет"},
    "download.value.not_recorded": {"en": "Not recorded", "zh": "未记录", "ru": "Не указано"},
    "download.human_review_notice": {
        "en": "This report was generated with legal multi-agent assistance and does not constitute formal legal advice. A qualified professional must conduct human review against the facts, evidence, and applicable law.",
        "zh": "本报告由法律多智能体系统辅助生成，不构成正式律师意见或法律意见；必须由具备资质的专业人员结合事实、证据和适用法律进行人工复核。",
        "ru": "Этот отчёт подготовлен при содействии юридической мультиагентной системы и не является официальной юридической консультацией. Квалифицированный специалист должен проверить его вручную с учётом фактов, доказательств и применимого права.",
    },
    "result.progress.title": {
        "en": "Review progress",
        "zh": "审查进度",
        "ru": "Ход проверки",
    },
    "result.progress.team_loading": {
        "en": "Loading legal expert team...",
        "zh": "法律专家团队加载中...",
        "ru": "Загрузка команды юридических экспертов...",
    },
    "result.progress.ready": {
        "en": "Ready to start legal review...",
        "zh": "准备开始法律审查...",
        "ru": "Готово к началу юридической проверки...",
    },
    "result.report.title": {
        "en": "Legal Review Report",
        "zh": "法律审查报告",
        "ru": "Отчёт о юридической проверке",
    },
    "result.final_conclusion.title": {
        "en": "Final review conclusion",
        "zh": "最终审查结论",
        "ru": "Итоговое заключение проверки",
    },
    "result.stats.status": {
        "en": "Review status:",
        "zh": "审查状态：",
        "ru": "Статус проверки:",
    },
    "result.stats.agents": {
        "en": "Participating experts:",
        "zh": "参与专家：",
        "ru": "Участвующие эксперты:",
    },
    "result.stats.messages": {
        "en": "Collaboration records:",
        "zh": "协作记录：",
        "ru": "Записи взаимодействия:",
    },
    "result.stats.duration": {
        "en": "Review duration:",
        "zh": "审查耗时：",
        "ru": "Длительность проверки:",
    },
    "result.contributions.title": {
        "en": "Legal expert analyses",
        "zh": "各法律专家分析",
        "ru": "Анализ юридических экспертов",
    },
    "result.contributions.summary": {
        "en": "Collapsed by default. Expand to view each expert's complete analysis.",
        "zh": "默认折叠，展开后查看各专家的完整分析过程。",
        "ru": "По умолчанию свёрнуто. Разверните, чтобы посмотреть полный анализ каждого эксперта.",
    },
    "result.messages.title": {
        "en": "Multi-agent collaboration process",
        "zh": "多智能体协作过程",
        "ru": "Процесс взаимодействия агентов",
    },
    "result.messages.summary": {
        "en": "Collapsed by default. Expand to view task delegation and responses between experts.",
        "zh": "默认折叠，展开后查看专家之间的任务分发和响应记录。",
        "ru": "По умолчанию свёрнуто. Разверните, чтобы посмотреть распределение задач и ответы экспертов.",
    },
    "knowledge.create.user.title": {
        "en": "➕ My Knowledge Base",
        "zh": "➕ 我的知识库",
        "ru": "➕ Моя база знаний",
    },
    "knowledge.create.user_name_label": {
        "en": "Knowledge base name:",
        "zh": "知识库名称：",
        "ru": "Название базы знаний:",
    },
    "knowledge.create.user_name_placeholder": {
        "en": "For example: My contract templates",
        "zh": "例如：我的合同模板",
        "ru": "Например: мои шаблоны договоров",
    },
    "knowledge.common.description_label": {
        "en": "Description:",
        "zh": "说明：",
        "ru": "Описание:",
    },
    "knowledge.create.user_description_placeholder": {
        "en": "Optional, for example: Frequently used personal contract templates and review rules",
        "zh": "可选，例如：个人常用合同模板和审查规则",
        "ru": "Необязательно, например: часто используемые шаблоны договоров и правила проверки",
    },
    "knowledge.create.user.action": {
        "en": "Create my knowledge base",
        "zh": "创建我的知识库",
        "ru": "Создать мою базу знаний",
    },
    "knowledge.create.public.title": {
        "en": "🏛️ Public Knowledge Base Management",
        "zh": "🏛️ 公共知识库管理",
        "ru": "🏛️ Управление публичными базами знаний",
    },
    "knowledge.create.public_name_label": {
        "en": "Public knowledge base name:",
        "zh": "公共知识库名称：",
        "ru": "Название публичной базы знаний:",
    },
    "knowledge.create.public_name_placeholder": {
        "en": "For example: Laws and cases",
        "zh": "例如：法规案例库",
        "ru": "Например: законы и судебная практика",
    },
    "knowledge.create.public_description_placeholder": {
        "en": "Optional, for example: Laws, cases, and compliance rules available to all users",
        "zh": "可选，例如：全员可检索的法规、案例和合规规则",
        "ru": "Необязательно, например: законы, судебная практика и правила соответствия, доступные всем пользователям",
    },
    "knowledge.create.public.action": {
        "en": "Create public knowledge base",
        "zh": "创建公共知识库",
        "ru": "Создать публичную базу знаний",
    },
    "knowledge.upload.text.title": {
        "en": "📝 Upload Legal Material Text",
        "zh": "📝 上传法律资料文本",
        "ru": "📝 Загрузить текст юридических материалов",
    },
    "knowledge.upload.target_label": {
        "en": "Target knowledge base:",
        "zh": "目标知识库：",
        "ru": "Целевая база знаний:",
    },
    "knowledge.upload.target_placeholder": {
        "en": "-- Load or create a knowledge base first --",
        "zh": "-- 请先加载或创建知识库 --",
        "ru": "-- Сначала загрузите или создайте базу знаний --",
    },
    "knowledge.upload.text.content_label": {
        "en": "Legal material content (one item per line):",
        "zh": "法律资料内容（每行一条资料）：",
        "ru": "Содержание юридических материалов (один материал на строку):",
    },
    "knowledge.upload.text.content_placeholder": {
        "en": "Enter laws, contract clauses, case summaries, or company policies to add to the knowledge base...",
        "zh": "输入要加入资料库的法规条文、合同条款、案例摘要或企业制度...",
        "ru": "Введите нормы права, условия договоров, обзоры дел или корпоративные политики для добавления в базу знаний...",
    },
    "knowledge.upload.text.action": {
        "en": "Upload legal material text",
        "zh": "上传法律资料文本",
        "ru": "Загрузить текст юридических материалов",
    },
    "knowledge.upload.file.title": {
        "en": "📁 Upload Legal Material File",
        "zh": "📁 上传法律资料文件",
        "ru": "📁 Загрузить файл юридических материалов",
    },
    "knowledge.upload.file.file_label": {
        "en": "Select a legal material file:",
        "zh": "选择法律资料文件：",
        "ru": "Выберите файл юридических материалов:",
    },
    "knowledge.upload.file.action": {
        "en": "Upload legal material file",
        "zh": "上传法律资料文件",
        "ru": "Загрузить файл юридических материалов",
    },
    "knowledge.info.title": {
        "en": "ℹ️ Knowledge Base Status",
        "zh": "ℹ️ 资料库状态",
        "ru": "ℹ️ Состояние базы знаний",
    },
    "knowledge.info.selector_label": {
        "en": "Select a knowledge base:",
        "zh": "选择资料库：",
        "ru": "Выберите базу знаний:",
    },
    "knowledge.common.load_list_placeholder": {
        "en": "-- Load the knowledge base list first --",
        "zh": "-- 请先加载资料库列表 --",
        "ru": "-- Сначала загрузите список баз знаний --",
    },
    "knowledge.info.refresh_action": {
        "en": "Refresh status",
        "zh": "刷新状态",
        "ru": "Обновить состояние",
    },
    "knowledge.info.empty": {
        "en": "Click “Refresh status” to view the knowledge base status",
        "zh": "点击“刷新状态”查看资料库状态",
        "ru": "Нажмите «Обновить состояние», чтобы посмотреть состояние базы знаний",
    },
    "knowledge.list.title": {
        "en": "📚 Existing Knowledge Bases",
        "zh": "📚 已有资料库",
        "ru": "📚 Существующие базы знаний",
    },
    "knowledge.list.description": {
        "en": "Manage knowledge bases containing laws, cases, contract templates, and company policies for legal review.",
        "zh": "管理可供法律审查调用的法规、案例、合同模板和企业制度资料库。",
        "ru": "Управляйте базами законов, судебной практики, шаблонов договоров и корпоративных правил для юридической проверки.",
    },
    "knowledge.list.refresh_action": {
        "en": "Refresh knowledge base list",
        "zh": "刷新资料库列表",
        "ru": "Обновить список баз знаний",
    },
    "knowledge.audit.title": {
        "en": "🧾 Upload Audit Records",
        "zh": "🧾 上传审计记录",
        "ru": "🧾 Журнал загрузок",
    },
    "knowledge.audit.load_action": {
        "en": "View upload audit",
        "zh": "查看上传审计",
        "ru": "Посмотреть журнал загрузок",
    },
    "knowledge.danger.title": {
        "en": "🗑️ Destructive Operations",
        "zh": "🗑️ 危险操作",
        "ru": "🗑️ Опасные операции",
    },
    "knowledge.danger.selector_label": {
        "en": "Select a knowledge base:",
        "zh": "选择知识库：",
        "ru": "Выберите базу знаний:",
    },
    "knowledge.danger.selector_placeholder": {
        "en": "-- Select a manageable knowledge base --",
        "zh": "-- 请选择可管理知识库 --",
        "ru": "-- Выберите доступную для управления базу знаний --",
    },
    "knowledge.danger.clear_action": {
        "en": "Clear knowledge base",
        "zh": "清空资料库",
        "ru": "Очистить базу знаний",
    },
    "knowledge.danger.delete_action": {
        "en": "Delete knowledge base",
        "zh": "删除资料库",
        "ru": "Удалить базу знаний",
    },
    "knowledge.danger.warning": {
        "en": "⚠️ Clearing removes all material but keeps the knowledge base. Deleting removes the knowledge base itself from the list. These operations cannot be undone.",
        "zh": "⚠️ 清空资料库会删除库内资料但保留资料库；删除资料库会移除库本身并从列表中消失，操作不可恢复。",
        "ru": "⚠️ Очистка удаляет все материалы, но сохраняет базу знаний. Удаление убирает саму базу из списка. Эти операции необратимы.",
    },
    "knowledge.documents.title": {
        "en": "📄 Browse Knowledge Base Content",
        "zh": "📄 浏览资料库内容",
        "ru": "📄 Просмотр содержимого базы знаний",
    },
    "knowledge.documents.selector_label": {
        "en": "View knowledge base:",
        "zh": "查看资料库：",
        "ru": "Просмотреть базу знаний:",
    },
    "knowledge.documents.load_action": {
        "en": "Load document list",
        "zh": "加载资料列表",
        "ru": "Загрузить список материалов",
    },
    "knowledge.documents.refresh_action": {
        "en": "Refresh",
        "zh": "刷新",
        "ru": "Обновить",
    },
    "knowledge.documents.delete_selected_action": {
        "en": "Delete selected material",
        "zh": "删除选中资料",
        "ru": "Удалить выбранные материалы",
    },
    "disclaimer.report": {
        "en": "This report is generated with legal multi-agent assistance and does not constitute formal legal or attorney advice. A qualified professional must review it against the facts, evidence, and applicable law.",
        "zh": "本报告由法律多智能体系统辅助生成，不构成正式律师意见或法律意见；请由具备资质的专业人员结合事实、证据和适用法律进行人工复核。",
        "ru": "Этот отчёт подготовлен с помощью юридической мультиагентной системы и не является официальным заключением адвоката или юридической консультацией. Квалифицированный специалист должен вручную проверить его с учётом фактов, доказательств и применимого права.",
    },
}

I18N.update(P1B_STATIC_I18N)


# P1b Knowledge 动态路径资产。用户资料库名、文件名和审计字段值不进入字典。
P1B_KNOWLEDGE_I18N = {
    "validation.knowledge_name_required": {"en": "Enter a knowledge base name.", "zh": "请输入知识库名称。", "ru": "Введите название базы знаний."},
    "validation.knowledge_text_required": {"en": "Enter legal material content.", "zh": "请输入法律资料内容。", "ru": "Введите содержание юридического материала."},
    "validation.knowledge_file_required": {"en": "Select a file to upload.", "zh": "请选择要上传的文件。", "ru": "Выберите файл для загрузки."},
    "validation.knowledge_write_target_required": {"en": "Select a writable knowledge base.", "zh": "请先选择可写入的知识库。", "ru": "Выберите базу знаний с правом записи."},
    "validation.knowledge_read_target_required": {"en": "Select a knowledge base.", "zh": "请先选择一个资料库。", "ru": "Выберите базу знаний."},
    "validation.knowledge_manage_target_required": {"en": "Select a knowledge base to manage.", "zh": "请先选择要管理的知识库。", "ru": "Выберите базу знаний для управления."},
    "validation.knowledge_delete_name_mismatch": {"en": "The name does not match. Deletion was cancelled.", "zh": "资料库名称不一致，已取消删除。", "ru": "Название не совпадает. Удаление отменено."},
    "validation.documents_required": {"en": "Select documents to delete.", "zh": "请先选择要删除的资料。", "ru": "Выберите материалы для удаления."},
    "status.loading": {"en": "Loading...", "zh": "加载中...", "ru": "Загрузка..."},
    "status.knowledge_creating": {"en": "Creating knowledge base...", "zh": "正在创建知识库...", "ru": "Создание базы знаний..."},
    "status.knowledge_uploading": {"en": "Uploading materials...", "zh": "正在上传资料...", "ru": "Загрузка материалов..."},
    "status.knowledge_deleted": {"en": "Knowledge base deleted. Reload the list or select another base.", "zh": "资料库已删除，请重新加载列表或选择其他资料库。", "ru": "База знаний удалена. Обновите список или выберите другую базу."},
    "toast.knowledge_created": {"en": "Knowledge base created:", "zh": "已创建知识库：", "ru": "База знаний создана:"},
    "toast.knowledge_upload_success": {"en": "Uploaded {count} chunks; total: {total}", "zh": "成功上传 {count} 条资料片段；资料总数：{total}", "ru": "Загружено фрагментов: {count}; всего: {total}"},
    "toast.knowledge_cleared": {"en": "Knowledge base cleared.", "zh": "资料库已清空。", "ru": "База знаний очищена."},
    "toast.knowledge_deleted": {"en": "Knowledge base deleted: {name}", "zh": "资料库已删除：{name}", "ru": "База знаний удалена: {name}"},
    "toast.document_deleted": {"en": "Document deleted.", "zh": "资料已删除。", "ru": "Материал удалён."},
    "toast.documents_batch_deleted": {"en": "Batch deletion complete. Success: {success}; failed: {failed}; remaining: {remaining}", "zh": "批量删除完成。成功：{success}；失败：{failed}；剩余资料：{remaining}", "ru": "Пакетное удаление завершено. Успешно: {success}; ошибок: {failed}; осталось: {remaining}"},
    "confirm.knowledge_clear": {"en": "Clear knowledge base “{name}”? This cannot be undone.", "zh": "确定要清空资料库“{name}”吗？此操作不可恢复。", "ru": "Очистить базу знаний «{name}»? Это действие необратимо."},
    "confirm.knowledge_delete": {"en": "Delete knowledge base “{name}”? Linked reviews will need another selection.", "zh": "确定要删除资料库“{name}”吗？已关联的审查需要重新选择资料库。", "ru": "Удалить базу знаний «{name}»? Для связанных проверок потребуется новый выбор."},
    "confirm.knowledge_delete_name": {"en": "Enter the knowledge base name to confirm deletion: {name}", "zh": "请再次输入资料库名称以确认删除：{name}", "ru": "Введите название базы знаний для подтверждения удаления: {name}"},
    "confirm.document_delete": {"en": "Delete this document? This cannot be undone.", "zh": "确定要删除这条资料吗？此操作不可恢复。", "ru": "Удалить этот материал? Это действие необратимо."},
    "confirm.documents_batch_delete": {"en": "Delete {count} selected documents? This cannot be undone.", "zh": "确定要删除选中的 {count} 条资料吗？此操作不可恢复。", "ru": "Удалить выбранные материалы ({count})? Это действие необратимо."},
    "error.knowledge_create_failed": {"en": "Failed to create the knowledge base.", "zh": "创建知识库失败。", "ru": "Не удалось создать базу знаний."},
    "error.knowledge_upload_failed": {"en": "Failed to upload materials.", "zh": "上传资料失败。", "ru": "Не удалось загрузить материалы."},
    "error.knowledge_info_failed": {"en": "Failed to load knowledge base information.", "zh": "获取资料库信息失败。", "ru": "Не удалось загрузить сведения о базе знаний."},
    "error.knowledge_mapping_failed": {"en": "Failed to load name mappings.", "zh": "加载名称对照失败。", "ru": "Не удалось загрузить сопоставления имён."},
    "error.knowledge_audit_failed": {"en": "Failed to load upload audit records.", "zh": "加载上传审计记录失败。", "ru": "Не удалось загрузить журнал загрузок."},
    "error.knowledge_clear_failed": {"en": "Failed to clear the knowledge base.", "zh": "清空资料库失败。", "ru": "Не удалось очистить базу знаний."},
    "error.knowledge_delete_failed": {"en": "Failed to delete the knowledge base.", "zh": "删除资料库失败。", "ru": "Не удалось удалить базу знаний."},
    "error.knowledge_list_failed": {"en": "Failed to load knowledge bases.", "zh": "加载资料库列表失败。", "ru": "Не удалось загрузить список баз знаний."},
    "error.knowledge_documents_failed": {"en": "Failed to load documents.", "zh": "加载资料列表失败。", "ru": "Не удалось загрузить материалы."},
    "error.knowledge_document_failed": {"en": "Failed to load the document.", "zh": "加载资料详情失败。", "ru": "Не удалось загрузить материал."},
    "error.document_delete_failed": {"en": "Failed to delete the document.", "zh": "删除资料失败。", "ru": "Не удалось удалить материал."},
    "error.documents_batch_delete_failed": {"en": "Failed to delete selected documents.", "zh": "批量删除资料失败。", "ru": "Не удалось удалить выбранные материалы."},
    "knowledge.scope.public": {"en": "Public", "zh": "公共", "ru": "Публичная"},
    "knowledge.scope.user": {"en": "Mine", "zh": "我的", "ru": "Моя"},
    "knowledge.scope.legacy_admin_only": {"en": "Migration review required", "zh": "迁移待确认", "ru": "Требуется проверка миграции"},
    "knowledge.scope.unknown": {"en": "Unknown", "zh": "未知", "ru": "Неизвестно"},
    "knowledge.document_count.loaded": {"en": "{count} documents", "zh": "{count} 条资料", "ru": "Материалов: {count}"},
    "knowledge.document_count.not_loaded": {"en": "Document count not loaded", "zh": "资料数未加载", "ru": "Количество материалов не загружено"},
    "knowledge.field.knowledge_base": {"en": "Knowledge base", "zh": "知识库", "ru": "База знаний"},
    "knowledge.field.file_name": {"en": "File name", "zh": "文件名称", "ru": "Имя файла"},
    "knowledge.info.id": {"en": "Knowledge base ID", "zh": "知识库 ID", "ru": "ID базы знаний"},
    "knowledge.info.name": {"en": "Knowledge base name", "zh": "知识库名称", "ru": "Название базы знаний"},
    "knowledge.info.scope": {"en": "Scope", "zh": "范围", "ru": "Область"},
    "knowledge.info.internal_collection": {"en": "Internal collection", "zh": "内部集合", "ru": "Внутренняя коллекция"},
    "knowledge.info.description": {"en": "Description", "zh": "说明", "ru": "Описание"},
    "knowledge.mapping.empty": {"en": "No name mappings.", "zh": "暂无名称对照记录。", "ru": "Сопоставления имён отсутствуют."},
    "knowledge.mapping.count": {"en": "{count} name mappings", "zh": "共 {count} 条名称对照", "ru": "Сопоставлений имён: {count}"},
    "knowledge.audit.empty": {"en": "No upload audit records.", "zh": "暂无上传审计记录。", "ru": "Записи журнала загрузок отсутствуют."},
    "knowledge.audit.recent_count": {"en": "Recent upload records: {count}", "zh": "最近 {count} 条上传记录", "ru": "Последних записей загрузки: {count}"},
    "knowledge.audit.status": {"en": "Status", "zh": "状态", "ru": "Статус"},
    "knowledge.audit.type": {"en": "Type", "zh": "类型", "ru": "Тип"},
    "knowledge.audit.knowledge_base": {"en": "Knowledge base", "zh": "资料库", "ru": "База знаний"},
    "knowledge.audit.scope": {"en": "Scope", "zh": "范围", "ru": "Область"},
    "knowledge.audit.time": {"en": "Time", "zh": "时间", "ru": "Время"},
    "knowledge.audit.error": {"en": "Error", "zh": "错误", "ru": "Ошибка"},
    "knowledge.audit.text_material": {"en": "Text material", "zh": "文本资料", "ru": "Текстовый материал"},
    "knowledge.value.no_knowledge_base": {"en": "No linked knowledge base", "zh": "未关联资料库", "ru": "База знаний не связана"},
    "knowledge.group.visible_count": {"en": "Visible knowledge bases: {count}", "zh": "共 {count} 个可见知识库", "ru": "Доступных баз знаний: {count}"},
    "knowledge.group.public_title": {"en": "Public knowledge bases", "zh": "公共知识库", "ru": "Публичные базы знаний"},
    "knowledge.group.public_empty": {"en": "No public knowledge bases.", "zh": "暂无公共知识库。", "ru": "Публичные базы знаний отсутствуют."},
    "knowledge.group.mine_title": {"en": "My knowledge bases", "zh": "我的知识库", "ru": "Мои базы знаний"},
    "knowledge.group.mine_empty": {"en": "No personal knowledge bases.", "zh": "暂无我的知识库，请先创建或联系管理员。", "ru": "Личные базы знаний отсутствуют."},
    "knowledge.group.public_admin_notice": {"en": "Admins can create, upload, clear, or delete public knowledge bases.", "zh": "管理员可创建、上传、清空或删除公共知识库。", "ru": "Администраторы могут создавать, загружать, очищать и удалять публичные базы знаний."},
    "knowledge.group.empty": {"en": "No knowledge bases found.", "zh": "暂无资料库。", "ru": "Базы знаний не найдены."},
    "knowledge.action.manage": {"en": "Manage", "zh": "管理", "ru": "Управлять"},
    "knowledge.action.view": {"en": "View", "zh": "查看", "ru": "Просмотр"},
    "knowledge.action.delete": {"en": "Delete", "zh": "删除", "ru": "Удалить"},
    "knowledge.action.delete_selected": {"en": "Delete selected ({count})", "zh": "删除选中资料（{count}）", "ru": "Удалить выбранные ({count})"},
    "knowledge.selector.none": {"en": "No single knowledge base", "zh": "不指定单个知识库", "ru": "Без отдельной базы знаний"},
    "knowledge.selector.readable_placeholder": {"en": "-- Select a knowledge base --", "zh": "-- 请选择资料库 --", "ru": "-- Выберите базу знаний --"},
    "knowledge.selector.writable_placeholder": {"en": "-- Select a writable knowledge base --", "zh": "-- 请选择可写入知识库 --", "ru": "-- Выберите базу знаний с правом записи --"},
    "knowledge.selector.manageable_placeholder": {"en": "-- Select a manageable knowledge base --", "zh": "-- 请选择可管理知识库 --", "ru": "-- Выберите базу знаний для управления --"},
    "knowledge.status.selects_updated": {"en": "Knowledge base selectors updated: {count}", "zh": "已更新知识库下拉选择框，数量：{count}", "ru": "Списки баз знаний обновлены: {count}"},
    "knowledge.status.selected": {"en": "Knowledge base selected: {name}", "zh": "已选择知识库：{name}", "ru": "Выбрана база знаний: {name}"},
    "knowledge.documents.knowledge_base": {"en": "Knowledge base", "zh": "资料库", "ru": "База знаний"},
    "knowledge.documents.total": {"en": "Total documents", "zh": "资料总数", "ru": "Всего материалов"},
    "knowledge.documents.showing": {"en": "Showing", "zh": "显示", "ru": "Показано"},
    "knowledge.documents.empty": {"en": "This knowledge base has no documents.", "zh": "该资料库暂无资料。", "ru": "В этой базе знаний нет материалов."},
    "knowledge.documents.document_id": {"en": "Document ID", "zh": "资料编号", "ru": "ID материала"},
    "knowledge.documents.metadata": {"en": "Metadata", "zh": "资料属性", "ru": "Метаданные"},
}

I18N.update(P1B_KNOWLEDGE_I18N)


# ============================================================
# 生成 i18n JavaScript 代码
# ============================================================
def generate_i18n_js():
    """生成 i18n 字典的 JavaScript 代码"""
    import json
    return f"""        // ==================== i18n Internationalization ====================
        const I18N = {json.dumps(I18N, ensure_ascii=False, indent=12)};
        
        const SUPPORTED_FRONTEND_LANGS = new Set(['en', 'zh', 'ru']);

        function normalizeFrontendLang(lang) {{
            return SUPPORTED_FRONTEND_LANGS.has(lang) ? lang : 'en';
        }}

        let currentLang = normalizeFrontendLang(localStorage.getItem('gaia_lang'));
        localStorage.setItem('gaia_lang', currentLang);
        
        function t(key, params = {{}}) {{
            const entry = I18N[key];
            if (!entry) return key;
            let value = entry[currentLang] || entry.en || entry.zh || key;
            Object.entries(params).forEach(([name, rawValue]) => {{
                value = value.split(`{{${{name}}}}`).join(String(rawValue));
            }});
            return value;
        }}
        
        function setLanguage(lang) {{
            const previousLang = currentLang;
            const normalizedLang = normalizeFrontendLang(lang);
            currentLang = normalizedLang;
            localStorage.setItem('gaia_lang', normalizedLang);
            applyTranslations();
            document.dispatchEvent(new CustomEvent('languagechange', {{
                detail: {{ lang: normalizedLang, previousLang }}
            }}));
        }}
        
        function applyTranslations() {{
            // Update text-only elements with data-i18n attribute
            document.querySelectorAll('[data-i18n]').forEach(el => {{
                const key = el.getAttribute('data-i18n');
                el.textContent = t(key);
            }});

            // Update placeholder-only elements separately
            document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {{
                const key = el.getAttribute('data-i18n-placeholder');
                el.placeholder = t(key);
            }});
            
            // Update document title
            document.title = t('page_title');
            
            // Update language selector
            const langSelect = document.getElementById('langSelect');
            if (langSelect) langSelect.value = currentLang;
        }}
        
        // Initialize on DOM ready
        document.addEventListener('DOMContentLoaded', () => {{
            applyTranslations();
        }});
"""


# ============================================================
# 生成语言切换器 HTML
# ============================================================
LANG_SWITCHER_HTML = """                <div class="lang-switcher">
                    <select id="langSelect" onchange="setLanguage(this.value)" style="padding: 4px 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.3); background: rgba(255,255,255,0.15); color: white; font-size: 13px; cursor: pointer;">
                        <option value="en" data-i18n="lang.option.en">English</option>
                        <option value="zh" data-i18n="lang.option.zh">中文</option>
                        <option value="ru" data-i18n="lang.option.ru">Русский</option>
                    </select>
                </div>"""


# ============================================================
# 全面中文→英文替换映射表
# ============================================================
def _get_chinese_replacements():
    """返回所有中文→英文的替换映射。"""
    return [
        # ===== CSS 注释 =====
        ("/* 聊天区域 */", "/* Chat Area */"),
        ("/* RAG 区域 */", "/* RAG Area */"),
        ("/* 文档浏览器样式 */", "/* Document Browser Styles */"),
        ("/* 模态框样式 */", "/* Modal Styles */"),
        
        ("<h3>➕ 我的知识库</h3>", "<h3>➕ My Knowledge Base</h3>"),
        ("<label>知识库名称：</label>", "<label>Knowledge Base Name:</label>"),
        ("<label>说明：</label>", "<label>Description:</label>"),
        ('<input type="text" id="createUserKbName" placeholder="例如：我的合同模板">', '<input type="text" id="createUserKbName" placeholder="e.g., My Contract Templates">'),
        ('<button class="btn btn-primary" onclick="createUserKnowledgeBase()" style="width: 100%;">创建我的知识库</button>', '<button class="btn btn-primary" onclick="createUserKnowledgeBase()" style="width: 100%;">Create My Knowledge Base</button>'),
        
        # ===== Knowledge Base Tab =====
        ("<h3>🏛️ 公共知识库管理</h3>", "<h3>🏛️ Public Knowledge Base Management</h3>"),
        ("<label>公共知识库名称：</label>", "<label>Public KB Name:</label>"),
        ('<input type="text" id="createPublicKbName" placeholder="例如：法规案例库">', '<input type="text" id="createPublicKbName" placeholder="e.g., Legal Case Library">'),
        ('<button class="btn btn-primary" onclick="createPublicKnowledgeBase()" style="width: 100%;">创建公共知识库</button>', '<button class="btn btn-primary" onclick="createPublicKnowledgeBase()" style="width: 100%;">Create Public Knowledge Base</button>'),
        ("<h3>📝 上传法律资料文本</h3>", "<h3>📝 Upload Legal Material Text</h3>"),
        ("<label>目标知识库：</label>", "<label>Target Knowledge Base:</label>"),
        ('<option value="">-- 请先加载或创建知识库 --</option>', '<option value="">-- Please load or create a knowledge base first --</option>'),
        ("<label>法律资料内容（每行一条资料）：</label>", "<label>Legal Material Content (one item per line):</label>"),
        ('<button class="btn btn-primary" onclick="uploadTexts()" style="width: 100%;">上传法律资料文本</button>', '<button class="btn btn-primary" onclick="uploadTexts()" style="width: 100%;">Upload Legal Material Text</button>'),
        ("<h3>📁 上传法律资料文件</h3>", "<h3>📁 Upload Legal Material File</h3>"),
        ("<label>选择法律资料文件：</label>", "<label>Select Legal Material File:</label>"),
        ('<button class="btn btn-primary" onclick="uploadFile()" style="width: 100%;">上传法律资料文件</button>', '<button class="btn btn-primary" onclick="uploadFile()" style="width: 100%;">Upload Legal Material File</button>'),
        ("<h3>ℹ️ 资料库状态</h3>", "<h3>ℹ️ Knowledge Base Status</h3>"),
        ("<label>选择资料库：</label>", "<label>Select Knowledge Base:</label>"),
        ('<option value="">-- 请先加载资料库列表 --</option>', '<option value="">-- Please load knowledge base list first --</option>'),
        ('<button class="btn btn-secondary" onclick="getKnowledgeInfo()" style="width: 100%; margin-bottom: 16px;">刷新状态</button>', '<button class="btn btn-secondary" onclick="getKnowledgeInfo()" style="width: 100%; margin-bottom: 16px;">Refresh Status</button>'),
        ('<div class="alert alert-info">点击\u201c刷新状态\u201d查看资料库状态</div>', '<div class="alert alert-info">Click "Refresh Status" to view knowledge base status</div>'),
        ("<h3>📚 已有资料库</h3>", "<h3>📚 Existing Knowledge Bases</h3>"),
        ('<button class="btn btn-secondary" onclick="loadAllCollections()" style="width: 100%; margin-bottom: 16px;">刷新资料库列表</button>', '<button class="btn btn-secondary" onclick="loadAllCollections()" style="width: 100%; margin-bottom: 16px;">Refresh Knowledge Base List</button>'),
        ("<h3>🧾 上传审计记录</h3>", "<h3>🧾 Upload Audit Records</h3>"),
        ('<button class="btn btn-secondary" onclick="loadUploadAudit()" style="width: 100%; margin-bottom: 16px;">查看上传审计</button>', '<button class="btn btn-secondary" onclick="loadUploadAudit()" style="width: 100%; margin-bottom: 16px;">View Upload Audit</button>'),
        ("<h3>🗑️ 危险操作</h3>", "<h3>🗑️ Dangerous Operations</h3>"),
        ("<label>选择知识库：</label>", "<label>Select Knowledge Base:</label>"),
        ('<option value="">-- 请选择可管理知识库 --</option>', '<option value="">-- Select a manageable knowledge base --</option>'),
        ('<button class="btn btn-danger" onclick="clearKnowledgeBase()" style="width: 100%; margin-bottom: 12px;">清空资料库</button>', '<button class="btn btn-danger" onclick="clearKnowledgeBase()" style="width: 100%; margin-bottom: 12px;">Clear Knowledge Base</button>'),
        ('<button class="btn btn-danger" onclick="deleteKnowledgeBaseCollection()" style="width: 100%; margin-bottom: 12px;">删除资料库</button>', '<button class="btn btn-danger" onclick="deleteKnowledgeBaseCollection()" style="width: 100%; margin-bottom: 12px;">Delete Knowledge Base</button>'),
        ("<h3>📄 浏览资料库内容</h3>", "<h3>📄 Browse Knowledge Base Content</h3>"),
        ("<label>查看资料库：</label>", "<label>View Knowledge Base:</label>"),
        ('<button class="btn btn-secondary" onclick="loadDocuments()" style="flex: 1;">加载资料列表</button>', '<button class="btn btn-secondary" onclick="loadDocuments()" style="flex: 1;">Load Document List</button>'),
        ('<span data-i18n="kb_delete_btn">Delete Selected</span>资料', '<span data-i18n="kb_delete_btn">Delete Selected</span>'),
        
        # ===== Simple Chat Tab =====
        ("<label>Agent 类型：</label>", "<label>Agent Type:</label>"),
        ('<option value="simple">简单对话</option>', '<option value="simple">Simple Chat</option>'),
        ('<option value="tool">工具调用</option>', '<option value="tool">Tool Use</option>'),
        ('<button class="btn btn-danger" onclick="clearChatHistory()">清除历史</button>', '<button class="btn btn-danger" onclick="clearChatHistory()">Clear History</button>'),
        ("<h3>开始对话</h3>", "<h3>Start Chat</h3>"),
        ("<p>选择 Agent 类型，然后输入您的问题开始对话</p>", "<p>Select an Agent type and enter your question to start chatting</p>"),
        ('<textarea id="userInput" placeholder="输入您的问题..." rows="1"></textarea>', '<textarea id="userInput" placeholder="Enter your question..." rows="1"></textarea>'),
        ('<button id="sendBtn" onclick="sendMessage()">发送</button>', '<button id="sendBtn" onclick="sendMessage()">Send</button>'),
        
        # ===== RAG Tab =====
        ("<label>资料库：</label>", "<label>Knowledge Base:</label>"),
        ('<option value="">-- 请选择资料库 --</option>', '<option value="">-- Select Knowledge Base --</option>'),
        ("<label>资料检索方式：</label>", "<label>Retrieval Method:</label>"),
        ('<option value="hybrid">混合检索</option>', '<option value="hybrid">Hybrid Search</option>'),
        ('<option value="vector">向量检索</option>', '<option value="vector">Vector Search</option>'),
        ('<option value="keyword">关键词检索</option>', '<option value="keyword">Keyword Search</option>'),
        ('<label for="optimizeQuery">查询优化</label>', '<label for="optimizeQuery">Query Optimization</label>'),
        ('<label for="useHistory">使用历史</label>', '<label for="useHistory">Use History</label>'),
        ('<button class="btn btn-danger" onclick="clearRagHistory()">清除历史</button>', '<button class="btn btn-danger" onclick="clearRagHistory()">Clear History</button>'),
        ("<h3>RAG 问答</h3>", "<h3>RAG Q&A</h3>"),
        ("<p>基于资料库的智能问答，支持多种检索方式</p>", "<p>Knowledge base powered Q&A with multiple retrieval methods</p>"),
        ('<textarea id="ragInput" placeholder="输入您的问题..." rows="1"></textarea>', '<textarea id="ragInput" placeholder="Enter your question..." rows="1"></textarea>'),
        ('<button id="ragSendBtn" onclick="sendRagQuery()">发送</button>', '<button id="ragSendBtn" onclick="sendRagQuery()">Send</button>'),
        
        # ===== Knowledge Base Tab =====
        ('<div class="alert alert-info">点击"Refresh Status"查看资料库状态</div>', '<div class="alert alert-info">Click "Refresh Status" to view knowledge base status</div>'),
        ('<button class="btn btn-secondary" onclick="refreshDocuments()">刷新</button>', '<button class="btn btn-secondary" onclick="refreshDocuments()">Refresh</button>'),
        ("公共知识库管理：管理员可创建、上传、清空或删除公共知识库", "Public Knowledge Base Management: Admins can create, upload, clear, or delete public knowledge bases"),
        ("输入要加入资料库的法规条文、合同条款、案例摘要或企业制度", "Enter legal provisions, contract clauses, case summaries, or enterprise policies to add to the knowledge base"),
        ("可选，例如：全员可检索的法规、案例和合规规则", "Optional, e.g., publicly searchable laws, cases, and compliance rules"),
        ("可选，例如：个人常用合同模板和审查规则", "Optional, e.g., personal contract templates and review rules"),
        ("例如: 用户偏好, Python, 编程", "e.g., User preferences, Python, Programming"),
        ("例如：10年Python和架构设计经验", "e.g., 10 years of Python and architecture design experience"),
        ("输入消息... (AI会基于存储的记忆回答)", "Enter message... (AI will answer based on stored memories)"),
        
        # ===== Routing Agent Tab =====
        ('<h3>🎯 Routing Agent - 智能路由</h3>', '<h3>🎯 Routing Agent - Smart Routing</h3>'),
        ("根据任务类型智能选择最合适的处理器，实现精准、高效的任务分发", "Intelligently selects the most suitable processor based on task type for precise and efficient task distribution"),
        ("混合路由结合规则、关键词和LLM的优势，平衡效率和准确性", "Hybrid routing combines the strengths of rules, keywords, and LLM, balancing efficiency and accuracy"),
        ('<option value="hybrid">🔄 混合路由（推荐）</option>', '<option value="hybrid">🔄 Hybrid Routing (Recommended)</option>'),
        ('<option value="llm_based">🤖 LLM路由</option>', '<option value="llm_based">🤖 LLM Routing</option>'),
        ('<option value="keyword">🔍 关键词路由</option>', '<option value="keyword">🔍 Keyword Routing</option>'),
        ('<option value="rule_based">📏 规则路由</option>', '<option value="rule_based">📏 Rule-Based Routing</option>'),
        ('<strong style="font-size: 13px; color: #495057;">💡 路由原因：</strong>', '<strong style="font-size: 13px; color: #495057;">💡 Routing Reason:</strong>'),
        ("🗑️ 清除结果", "🗑️ Clear Results"),
        ("📋 复制结果", "📋 Copy Results"),
        ("💾 下载结果", "💾 Download Results"),
        ("展开全部", "Expand All"),
        ('<label id="routingInputLabel">输入任务：</label>', '<label id="routingInputLabel">Enter Task:</label>'),
        ('<option value="">-- 加载中 --</option>', '<option value="">-- Loading --</option>'),
        ("当前场景下的所有可用路由和说明", "All available routes and descriptions for the current scenario"),
        ('<h4 style="margin-bottom: 12px; color: #495057;">场景信息</h4>', '<h4 style="margin-bottom: 12px; color: #495057;">Scenario Info</h4>'),
        ('<label>选择场景：</label>', '<label>Select Scenario:</label>'),
        ('<label>路由策略：</label>', '<label>Routing Strategy:</label>'),
        ('<strong>💡 策略说明：</strong>', '<strong>💡 Strategy Description:</strong>'),
        
        # ===== Other hidden tab content =====
        ("同时执行多个任务，通过并行处理提高效率、获得多角度视角，提升结果质量", "Execute multiple tasks simultaneously, improving efficiency through parallel processing, gaining multi-angle perspectives, and enhancing result quality"),
        ("将复杂任务分解为多个步骤，每个步骤专注于特定目标，前一步的输出作为下一步的输入，实现模块化、高质量的输出", "Decompose complex tasks into multiple steps, each focusing on a specific goal, with the output of the previous step serving as input for the next, achieving modular, high-quality output"),
        ("通过自我批判和迭代改进来提升输出质量。系统先生成初始响应，然后进行反思，基于反思进行改进，可进行多轮迭代直到达到质量要求", "Improve output quality through self-critique and iterative refinement. The system generates an initial response, then reflects on it, improves based on reflection, and can iterate multiple rounds until quality requirements are met"),
        ("智能分析目标并制定详细的执行计划。系统会将复杂目标分解为可执行的子任务，制定合理的执行顺序，并支持动态调整和进度监控", "Intelligently analyze goals and create detailed execution plans. The system decomposes complex goals into executable subtasks, establishes reasonable execution order, and supports dynamic adjustment and progress monitoring"),
        ("智能选择和执行工具来完成复杂任务。系统会分析用户需求，自动选择最合适的工具，并支持多工具协作完成复杂任务", "Intelligently select and execute tools to complete complex tasks. The system analyzes user needs, automatically selects the most suitable tools, and supports multi-tool collaboration for complex tasks"),
        ("智能记忆管理系统 - 让AI拥有记忆能力，记住过去的对话、学习用户偏好、提供个性化服务", "Intelligent Memory Management System - Give AI memory capabilities to remember past conversations, learn user preferences, and provide personalized services"),
        ("选择资料库后，法律依据检索员和合规审查专员会自动检索相关资料", "After selecting a knowledge base, the Legal Researcher and Compliance Checker will automatically search relevant materials"),
        ("提示：如果输入的是任务描述，系统会先生成初始内容再进行反思；如果输入的是已有内容，系统会直接对其进行反思和改进", "Tip: If the input is a task description, the system will first generate initial content then reflect; if the input is existing content, the system will directly reflect and improve it"),
        ("默认折叠，展开后查看专家之间的任务分发和响应记录", "Collapsed by default, expand to view task distribution and response records between experts"),
        ("默认折叠，展开后查看各专家的完整分析过程", "Collapsed by default, expand to view complete analysis from each expert"),
        
        # ===== Agent descriptions =====
        ("🧠 Memory Management Agent - 记忆管理", "🧠 Memory Management Agent - Memory Management"),
        ("🚀 Parallelization Agent - 并行化智能体", "🚀 Parallelization Agent - Parallelization Agent"),
        ("🔧 Tool Use Agent - 工具使用智能体", "🔧 Tool Use Agent - Tool Use Agent"),
        
        # ===== Legal task descriptions =====
        ("识别合同基础信息，包括合同类型、合同主体、金额、期限、付款安排、违约责任和争议解决条款", "Identify basic contract information including contract type, parties, amount, term, payment arrangements, breach liability, and dispute resolution clauses"),
        ("识别高风险、中风险、低风险条款，并标记风险所在条款和原文位置", "Identify high, medium, and low risk clauses, and mark the clause and original text location of each risk"),
        ("输出合同总体风险等级、是否建议签署、优先处理事项和谈判建议", "Output overall contract risk level, signing recommendation, priority items, and negotiation suggestions"),
        ("识别法律风险、商业风险、履约风险、付款风险、责任风险和争议解决风险", "Identify legal risks, commercial risks, performance risks, payment risks, liability risks, and dispute resolution risks"),
        ("识别数据安全、隐私保护、劳动用工、广告宣传、金融、知识产权、反垄断等合规风险", "Identify compliance risks in data security, privacy protection, labor, advertising, finance, intellectual property, antitrust, etc."),
        ("检索相关法律法规、司法解释、监管规则、案例和企业知识库", "Search relevant laws, regulations, judicial interpretations, regulatory rules, cases, and enterprise knowledge bases"),
        ("根据合同类型、行业、交易场景和主体类型识别适用监管规则", "Identify applicable regulatory rules based on contract type, industry, transaction scenario, and party types"),
        ("给出后续处理建议，例如补充材料、人工复核、进入审批或重新谈判", "Provide follow-up recommendations such as supplementing materials, manual review, entering approval, or renegotiation"),
        ("如信息不足，请列出需要用户补充的关键事实和证据", "If information is insufficient, list key facts and evidence the user needs to provide"),
        ("如信息不足，请列出需要用户补充的背景信息", "If information is insufficient, list background information the user needs to provide"),
        ("识别合同中可能违反企业红线、审批规则或标准模板的条款", "Identify clauses that may violate enterprise redlines, approval rules, or standard templates"),
        ("识别合同类型、交易金额、主体类型、业务场景和关键风险", "Identify contract type, transaction amount, party types, business scenario, and key risks"),
        ("判断是否需要法务、合规、财务、业务负责人或外部律师参与审批", "Determine whether legal, compliance, finance, business leaders, or external counsel need to participate in approval"),
        ("输出进入审批、退回修改、补充材料或人工复核的建议", "Output recommendations for entering approval, returning for revision, supplementing materials, or manual review"),
        ("输出是否建议签署、需修改后签署或不建议签署", "Output signing recommendation: sign, sign after revision, or do not sign"),
        ("说明这些依据如何适用于当前合同审查任务", "Explain how these references apply to the current contract review task"),
        
        # ===== Legal task template descriptions (JS) =====
        ("description: '完整审查合同风险并输出标准审查报告'", "description: 'Complete contract risk review with standard report'"),
        ("description: '只识别合同条款风险和风险等级'", "description: 'Identify clause-level risks and risk levels'"),
        ("description: '根据合同风险生成修改建议和替代条款'", "description: 'Generate revision suggestions and alternative clauses based on risks'"),
        ("description: '检索相关法律法规、案例、监管规则和企业知识库'", "description: 'Search relevant laws, cases, regulations and enterprise knowledge bases'"),
        ("description: '分析合同和业务安排中的监管合规风险'", "description: 'Analyze regulatory compliance risks in contracts and business arrangements'"),
        ("description: '输出面向决策的合同审查结论'", "description: 'Output decision-oriented contract review conclusions'"),
        ("description: '根据事实、诉求和证据生成法律文书初稿'", "description: 'Generate legal document drafts based on facts, claims and evidence'"),
        ("description: '将合同与企业红线规则或标准模板进行比对'", "description: 'Compare contracts against enterprise redline rules or standard templates'"),
        ("description: '根据风险等级和业务场景给出审批流建议'", "description: 'Provide approval flow suggestions based on risk levels and business scenarios'"),
        
        # ===== Legal task template names (JS) =====
        ("name: '合同审查'", "name: 'Contract Review'"),
        ("name: '合同风险识别'", "name: 'Risk Identification'"),
        ("name: '修改建议与替代条款'", "name: 'Revision Suggestions'"),
        ("name: '法律依据检索'", "name: 'Legal Research'"),
        ("name: '合规风险分析'", "name: 'Compliance Analysis'"),
        ("name: '审查结论摘要'", "name: 'Review Summary'"),
        ("name: '法律文书生成'", "name: 'Legal Document Generation'"),
        ("name: '红线比对'", "name: 'Redline Comparison'"),
        ("name: '法务审批流建议'", "name: 'Approval Flow Suggestion'"),
        
        # ===== Agent display names (JS) =====
        ("'合同审查协调员'", "'Contract Review Coordinator'"),
        ("'条款风险分析师'", "'Clause Risk Analyst'"),
        ("'法律依据检索员'", "'Legal Researcher'"),
        ("'法律文书起草专家'", "'Legal Drafting Specialist'"),
        ("'合规审查专员'", "'Compliance Reviewer'"),
        ("'审计留痕记录员'", "'Audit Recorder'"),
        
        # ===== JS alerts/confirms =====
        ("alert('请先选择一个资料库！');", "alert('Please select a knowledge base first!');"),
        ("alert('请先选择要清空的知识库');", "alert('Please select a knowledge base to clear first');"),
        ("alert('请先选择要删除的知识库');", "alert('Please select a knowledge base to delete first');"),
        ("alert('资料库名称不一致，已取消删除');", "alert('Knowledge base name mismatch, deletion cancelled');"),
        ("alert('✓ 资料库已清空');", "alert('Knowledge base cleared');"),
        ("alert(`✗ 清空失败: ${data.detail}`);", "alert(`Clear failed: ${data.detail}`);"),
        ("alert(`✗ 清空失败: ${error.message}`);", "alert(`Clear failed: ${error.message}`);"),
        ("alert(`✓ 资料库已删除：${kb.display_name}`);", "alert(`Knowledge base deleted: ${kb.display_name}`);"),
        ("alert(`✗ 删除失败: ${data.detail}`);", "alert(`Delete failed: ${data.detail}`);"),
        ("alert(`✗ 删除失败: ${error.message}`);", "alert(`Delete failed: ${error.message}`);"),
        ("alert('✓ 资料已删除');", "alert('Document deleted');"),
        ("alert('清除失败: ' + error.message);", "alert('Clear failed: ' + error.message);"),
        ("alert('请先选择要删除的资料');", "alert('Please select documents to delete first');"),
        ("alert('请先选择要管理的知识库');", "alert('Please select a knowledge base to manage first');"),
        ("alert('审查报告已复制到剪贴板')", "alert('Review report copied to clipboard')"),
        ("alert('计划信息已复制到剪贴板')", "alert('Plan info copied to clipboard')"),
        ("alert('加载计划失败: ' + error.message)", "alert('Failed to load plan: ' + error.message)"),
        ("alert('存储记忆失败，请重试')", "alert('Failed to store memory, please retry')"),
        ("alert('✅ 结果已复制到剪贴板')", "alert('Results copied to clipboard')"),
        ("alert('没有可执行的计划')", "alert('No executable plan')"),
        ("alert('删除计划失败: ' + error.message)", "alert('Failed to delete plan: ' + error.message)"),
        ("alert('没有可下载的结果')", "alert('No downloadable results')"),
        ("alert('没有可复制的结果')", "alert('No results to copy')"),
        ("alert('执行失败: ' + error.message)", "alert('Execution failed: ' + error.message)"),
        ("alert('检索记忆失败，请重试')", "alert('Failed to retrieve memory, please retry')"),
        ("alert('请输入目标描述')", "alert('Please enter a goal description')"),
        ("alert(`✗ 批量删除失败: ${error.message}`)", "alert(`Batch delete failed: ${error.message}`)"),
        ("alert('模式详情已在控制台输出')", "alert('Mode details output to console')"),
        ("alert('执行结果已复制到剪贴板')", "alert('Execution results copied to clipboard')"),
        ("alert('复制失败，请手动复制')", "alert('Copy failed, please copy manually')"),
        ("alert('获取计划列表失败: ' + error.message)", "alert('Failed to get plan list: ' + error.message)"),
        ("alert('请先选择一个场景')", "alert('Please select a scenario first')"),
        ("alert('请输入内容')", "alert('Please enter content')"),
        ("alert('流式执行失败: ' + error.message)", "alert('Stream execution failed: ' + error.message)"),
        ("alert('请输入合同或法律材料文件路径')", "alert('Please enter contract or legal material file path')"),
        ("alert('请输入记忆内容')", "alert('Please enter memory content')"),
        ("alert('反思执行失败: ' + error.message)", "alert('Reflection execution failed: ' + error.message)"),
        ("alert('计划已删除')", "alert('Plan deleted')"),
        ("alert('创建规划失败: ' + error.message)", "alert('Failed to create plan: ' + error.message)"),
        ("alert('协作失败: ' + data.error_message)", "alert('Collaboration failed: ' + data.error_message)"),
        ("alert(`执行出错: ${data.message}`)", "alert(`Execution error: ${data.message}`)"),
        ("alert(`执行失败: ${error.message}`)", "alert(`Execution failed: ${error.message}`)"),
        ("alert('✅ 记忆已存储！')", "alert('Memory stored!')"),
        ("alert('团队详情已在控制台输出')", "alert('Team details output to console')"),
        ("alert('执行计划失败: ' + error.message)", "alert('Failed to execute plan: ' + error.message)"),
        ("alert(`流式执行失败: ${error.message}`)", "alert(`Stream execution failed: ${error.message}`)"),
        ("alert(`获取工具列表失败: ${error.message}`)", "alert(`Failed to get tool list: ${error.message}`)"),
        ("alert('结果已复制到剪贴板！')", "alert('Results copied to clipboard!')"),
        ("alert(`获取工具历史失败: ${error.message}`)", "alert(`Failed to get tool history: ${error.message}`)"),
        ("alert('请输入查询内容')", "alert('Please enter query content')"),
        ("alert('获取场景失败: ' + error.message)", "alert('Failed to get scenario: ' + error.message)"),
        ("alert('执行失败: ' + (data.error_message || '未知错误')", "alert('Execution failed: ' + (data.error_message || 'Unknown error')"),
        ("alert('创建计划失败: ' + (data.error_message || '未知错误')", "alert('Failed to create plan: ' + (data.error_message || 'Unknown error')"),
        ("alert('请选择合同或法律材料文件')", "alert('Please select a contract or legal material file')"),
        
        # ===== JS confirm messages =====
        ("confirm(`确定要Clear KB\"${kb.display_name}\"吗？此操作不可恢复！`)", "confirm(`Are you sure you want to clear KB \"${kb.display_name}\"? This action cannot be undone!`)"),
        ("confirm('确定要删除这个计划吗？')", "confirm('Are you sure you want to delete this plan?')"),
        ("confirm('确定要清除对话历史吗？')", "confirm('Are you sure you want to clear chat history?')"),
        ("confirm('确定要清除 RAG 对话历史吗？')", "confirm('Are you sure you want to clear RAG chat history?')"),
        ("confirm('确定要删除这条资料吗？此操作不可恢复！')", "confirm('Are you sure you want to delete this document? This action cannot be undone!')"),
        
        # ===== JS innerHTML status messages =====
        ("'<div class=\"alert alert-info\">正在创建知识库...</div>'", "'<div class=\"alert alert-info\">Creating knowledge base...</div>'"),
        ("'<div class=\"alert alert-info\">正在上传资料...</div>'", "'<div class=\"alert alert-info\">Uploading materials...</div>'"),
        ("'<div class=\"alert alert-info\">加载中...</div>'", "'<div class=\"alert alert-info\">Loading...</div>'"),
        ("'<div class=\"alert alert-info\">暂无名称对照记录</div>'", "'<div class=\"alert alert-info\">No name mapping records</div>'"),
        ("'<div class=\"alert alert-error\">请输入法律资料内容</div>'", "'<div class=\"alert alert-error\">Please enter legal material content</div>'"),
        ("'<div class=\"alert alert-error\">请先选择可写入的知识库</div>'", "'<div class=\"alert alert-error\">Please select a writable knowledge base first</div>'"),
        ("'<div class=\"alert alert-error\">请选择要上传的文件</div>'", "'<div class=\"alert alert-error\">Please select a file to upload</div>'"),
        ("'<div class=\"alert alert-error\">请先选择一个资料库</div>'", "'<div class=\"alert alert-error\">Please select a knowledge base first</div>'"),
        ("'<div class=\"alert alert-info\">资料库已删除，请重新加载资料库列表</div>'", "'<div class=\"alert alert-info\">Knowledge base deleted, please reload the list</div>'"),
        ("'<div class=\"alert alert-info\">该资料库暂无资料</div>'", "'<div class=\"alert alert-info\">This knowledge base has no documents</div>'"),
        ("'<div class=\"alert alert-info\">暂无资料库，请先上传法律资料</div>'", "'<div class=\"alert alert-info\">No knowledge bases found, please upload legal materials first</div>'"),
        
        # ===== JS textContent =====
        ("submitBtn.textContent = '登录';", "submitBtn.textContent = 'Login';"),
        ("sendBtn.textContent = '发送';", "sendBtn.textContent = 'Send';"),
        
        # ===== JS DOM innerHTML =====
        ("innerHTML = '<span>🚀 执行并行任务</span>'", "innerHTML = '<span>🚀 Execute Parallel Tasks</span>'"),
        ("innerHTML = '<span>⏳ 正在执行反思...</span>'", "innerHTML = '<span>⏳ Executing reflection...</span>'"),
        ("innerHTML = '<span>▶️ 运行提示链</span>'", "innerHTML = '<span>▶️ Run Prompt Chain</span>'"),
        ("innerHTML = '<span>⏳ 执行中...</span>'", "innerHTML = '<span>⏳ Executing...</span>'"),
        ("innerHTML = '<strong>示例任务：</strong> '", "innerHTML = '<strong>Sample Tasks:</strong> '"),
        ("innerHTML = '<span>💭 开始反思与改进</span>'", "innerHTML = '<span>💭 Start Reflection & Improvement</span>'"),
        ("innerHTML = '<span>🚀 执行路由</span>'", "innerHTML = '<span>🚀 Execute Route</span>'"),
        
        # ===== JS console =====
        ("console.error('注销失败:', error);", "console.error('Logout failed:', error);"),
        ("console.error('检查登录态失败:', error);", "console.error('Login check failed:', error);"),
        ("console.error('初始化应用失败:', error);", "console.error('App initialization failed:', error);"),
        ("console.log(`已同步知识库选择: ${kbId}`);", "console.log(`Knowledge base selection synced: ${kbId}`);"),
        ("console.log('[loadAllCollections] 开始加载...');", "console.log('[loadAllCollections] Loading...');"),
        ("console.log('[loadAllCollections] 正在获取collections列表...');", "console.log('[loadAllCollections] Fetching collections...');"),
        ("console.log('响应状态:', response.status);", "console.log('Response status:', response.status);"),
        ("console.log('成功获取collections:', data);", "console.log('Collections fetched:', data);"),
        ("console.error('获取collections失败:', data);", "console.error('Failed to fetch collections:', data);"),
        ("console.error('加载collections异常:', error);", "console.error('Collections load error:', error);"),
        ("console.log(`已更新知识库下拉选择框，数量: ${collections.length}`);", "console.log(`Knowledge base dropdown updated, count: ${collections.length}`);"),
        ("console.log('已加载提示链类型:', chainTypes);", "console.log('Prompt chain types loaded:', chainTypes);"),
        ("console.error('加载提示链类型失败:', error);", "console.error('Failed to load prompt chain types:', error);"),
        ("console.error('解析SSE数据失败:', e);", "console.error('SSE data parse failed:', e);"),
        ("console.error('执行失败:', error);", "console.error('Execution failed:', error);"),
        ("console.error('复制失败:', err);", "console.error('Copy failed:', err);"),
        ("console.log('已下载结果到:', filename);", "console.log('Results downloaded to:', filename);"),
        ("console.log('已加载路由场景:', routingScenarios);", "console.log('Routing scenarios loaded:', routingScenarios);"),
        ("console.error('加载路由场景失败:', error);", "console.error('Failed to load routing scenarios:', error);"),
        ("console.error('加载路由失败:', error);", "console.error('Failed to load routing:', error);"),
        ("console.error('执行路由失败:', error);", "console.error('Route execution failed:', error);"),
        ("console.log('已加载并行化场景:', parallelScenarios);", "console.log('Parallelization scenarios loaded:', parallelScenarios);"),
        ("console.error('加载并行化场景失败:', error);", "console.error('Failed to load parallelization scenarios:', error);"),
        
        # ===== JS other strings =====
        ("'当前用户'", "'Current User'"),
        ("currentUser.role === 'admin' ? '管理员' : '用户'", "currentUser.role === 'admin' ? 'Admin' : 'User'"),
        ("'协作失败: ' + error.message", "'Collaboration failed: ' + error.message"),
        ("法律智能体策略加载失败，无法安全发起法律协作", "Legal agent strategy failed to load, cannot safely initiate legal collaboration"),
        ("本报告由法律多智能体系统辅助生成，不构成正式律师意见；请由具备资质的专业人员结合事实、证据和适用法律进行人工复核", "This report is AI-assisted and does not constitute formal legal opinion; please have qualified professionals review based on facts, evidence, and applicable law"),
        ("该智能体执行失败，内部异常已隐藏。请结合其他专家结果并进行人工复核", "This agent execution failed, internal exception hidden. Please combine with other expert results and conduct manual review"),
        ("未识别结构化摘要，仍可继续发起多智能体审查并由人工复核", "No structured summary identified, you can still proceed with multi-agent review and manual verification"),
        ("完整协作结果已在控制台输出，可以按 F12 查看", "Complete collaboration results output to console, press F12 to view"),
        ("此操作会移除资料库本身，并从资料库列表中消失；已关联该资料库的多智能体审查需要重新选择资料库", "This will remove the knowledge base itself from the list; multi-agent reviews linked to this knowledge base will need to reselect"),
        ("选择法律任务，上传合同或材料，由法律多智能体团队完成审查、检索、合规分析和修改建议", "Select a legal task, upload contracts or materials, and the legal multi-agent team will complete review, research, compliance analysis, and revision suggestions"),
        ("管理可供法律审查调用的法规、案例、合同模板和企业制度资料库", "Manage the knowledge base of laws, cases, contract templates, and enterprise policies available for legal review"),
        ("⚠️ 清空资料库会删除库内资料但保留资料库；删除资料库会移除库本身并从列表中消失，操作不可恢复。", "⚠️ Clearing a knowledge base deletes its documents but keeps the base; deleting a knowledge base removes it entirely from the list. These actions cannot be undone."),
        ("种法律任务策略，可按本次需求调整参与智能体", " legal task strategies, adjust participating agents as needed"),
        ("条协作记录，展开后查看任务分发和响应过程", " collaboration records, expand to view task distribution and response process"),
        ("位法律专家参与分析，展开后查看完整过程", " legal experts participated, expand to view complete process"),
        ("系统会自动分析目标并制定详细的执行计划", "The system will automatically analyze the goal and create a detailed execution plan"),
        ("系统会自动选择合适的工具来完成您的任务", "The system will automatically select the appropriate tools to complete your task"),
        ("法律智能体策略尚未加载完成，请稍后重试", "Legal agent policy is not yet loaded, please try again later"),
        ("简化实现：使用alert显示统计信息", "Simplified implementation: use alert to display statistics"),
        ("暂无我的知识库，请先创建或联系管理员", "No personal knowledge bases, please create one or contact admin"),
        ("对合同条款和业务安排进行合规风险映射", "Map compliance risks for contract clauses and business arrangements"),
        ("并行内容生成 - 同时生成文档各章节", "Parallel content generation - generate document sections simultaneously"),
        ("更新反思策略信息（显示/隐藏专家设置", "Update reflection strategy info (show/hide expert settings"),
        ("多角度分析 - 从多个角度分析问题", "Multi-angle analysis - analyze problems from multiple perspectives"),
        ("确保improvements是数组", "Ensure improvements is an array"),
        ("撰写一篇关于人工智能未来发展的文章", "Write an article about the future development of artificial intelligence"),
        ("读取config.json文件内容", "Read config.json file content"),
        ("研究深度学习在自然语言处理中的应用", "Research deep learning applications in natural language processing"),
        ("登录盖亚国际世界模型法律智能体系统", "Login to Gaia International World Model Legal Intelligence System"),
        ("alert('请输入任务')", "alert('Please enter a task')"),
        ("确定要清空资料库\u201c${kb.display_name}\u201d吗？此操作不可恢复！", "Are you sure you want to clear knowledge base \u201c${kb.display_name}\u201d? This action cannot be undone!"),
        ("确定要删除资料库\u201c${kb.display_name}\u201d吗？", "Are you sure you want to delete knowledge base \u201c${kb.display_name}\u201d?"),
        ("alert('请输入任务描述或初始内容')", "alert('Please enter a task description or initial content')"),
        ("alert('请输入任务')", "alert('Please enter a task')"),
        ('<input type="text" id="createUserKbName" placeholder="例如：我的合同模板">', '<input type="text" id="createUserKbName" placeholder="e.g., My Contract Templates">'),
        ('<button class="btn btn-primary" onclick="createUserKnowledgeBase()" style="width: 100%;">创建我的知识库</button>', '<button class="btn btn-primary" onclick="createUserKnowledgeBase()" style="width: 100%;">Create My Knowledge Base</button>'),
        ("alert(`已选择知识库: ${kb.display_name}`)", "alert(`Knowledge base selected: ${kb.display_name}`)"),
        ("`确定要<span data-i18n=\"kb_delete_btn\">Delete Selected</span>的 ${selectedDocIds.size} 条资料吗？此操作不可恢复！`", "`Are you sure you want to delete ${selectedDocIds.size} documents? This action cannot be undone!`"),
        ("`✓ 批量删除完成\\n成功: ${data.success_count}\\n失败: ${data.failed_count}\\n剩余资料: ${data.remaining_count}`", "`✓ Batch delete complete\\nSuccess: ${data.success_count}\\nFailed: ${data.failed_count}\\nRemaining: ${data.remaining_count}`"),
        ("`✗ 批量删除失败: ${data.detail}`", "`✗ Batch delete failed: ${data.detail}`"),
        
        # ===== Placeholders
        ('placeholder="输入您的问题..."', 'placeholder="Enter your question..."'),
        ('placeholder="输入消息..."', 'placeholder="Enter message..."'),
        ('placeholder="例如：帮我写一个Python排序函数"', 'placeholder="e.g., Write a Python sorting function for me"'),
        ('placeholder="请先选择一个场景..."', 'placeholder="Please select a scenario first..."'),
        ('placeholder="例如：资深Python开发工程师"', 'placeholder="e.g., Senior Python Developer"'),
        
        # ===== Server path =====
        ('<summary style="cursor: pointer; color: #166534; font-size: 13px;">服务器路径解析</summary>', '<summary style="cursor: pointer; color: #166534; font-size: 13px;">Server Path Resolution</summary>'),
        ('placeholder="请输入服务器可访问的文件路径，例如：C:/Users/.../contract.pdf 或 /mnt/c/Users/.../contract.txt"', 'placeholder="Enter server-accessible file path, e.g., C:/Users/.../contract.pdf or /mnt/c/Users/.../contract.txt"'),
        
        # ===== Status messages in JS =====
        ("**执行状态**: ${data.success ? '✅ 成功完成' : '❌ 执行失败'}", "**Execution Status**: ${data.success ? '✅ Completed Successfully' : '❌ Execution Failed'}"),
        ("**任务统计**:", "**Task Statistics**:"),
        ("**执行时间**: ${formatDuration(data.total_duration)}", "**Execution Time**: ${formatDuration(data.total_duration)}"),
        ("**详细日志**: 共 ${data.execution_log?.length || 0} 条记录", "**Detailed Log**: ${data.execution_log?.length || 0} records total"),
        ("*计划执行完成时间: ${new Date().toLocaleString()}*`;", "*Plan execution completed at: ${new Date().toLocaleString()}*`;"),
        
        # ===== Step text =====
        ("document.getElementById('currentStep').textContent = '准备执行...';", "document.getElementById('currentStep').textContent = 'Preparing...';"),
        ("document.getElementById('currentStep').textContent = `步骤 ${data.step}: ${data.name}`;", "document.getElementById('currentStep').textContent = `Step ${data.step}: ${data.name}`;"),
        
        # ===== Batch delete button =====
        ('btn.textContent = `<span data-i18n="kb_delete_btn">Delete Selected</span>资料 (${selectedDocIds.size})`;', 'btn.textContent = `<span data-i18n="kb_delete_btn">Delete Selected</span> (${selectedDocIds.size})`;'),
        
        # ===== JS comments =====
        ("// ==================== i18n 国际化 ====================", "// ==================== i18n Internationalization ===================="),
        ("// 配置 marked", "// Configure marked"),
        ("// 切换标签页", "// Switch tabs"),
        
        # ===== HTML comments =====
        ("<!-- 智能对话标签页 -->", "<!-- Smart Chat Tab -->"),
        ("<!-- RAG 问答标签页 -->", "<!-- RAG Q&A Tab -->"),
        ("<!-- 知识库管理标签页 -->", "<!-- Knowledge Base Management Tab -->"),
        ("<!-- Multi-Agent Collaboration 标签页 -->", "<!-- Multi-Agent Collaboration Tab -->"),
        ("<!-- Memory Management Agent 内容 -->", "<!-- Memory Management Agent Content -->"),
        ("<!-- Parallelization Agent 标签页 -->", "<!-- Parallelization Agent Tab -->"),
        ("<!-- Reflection Agent 标签页 -->", "<!-- Reflection Agent Tab -->"),
        ("<!-- Prompt Chaining 标签页 -->", "<!-- Prompt Chaining Tab -->"),
        ("<!-- Tool Use Agent 标签页 -->", "<!-- Tool Use Agent Tab -->"),
        ("<!-- Planning Agent 标签页 -->", "<!-- Planning Agent Tab -->"),
        ("<!-- Routing Agent 标签页 -->", "<!-- Routing Agent Tab -->"),
        ("<!-- 创建用户知识库 -->", "<!-- Create User Knowledge Base -->"),
        ("<!-- 管理员公共知识库 -->", "<!-- Admin Public Knowledge Base -->"),
        ("<!-- 上传文本 -->", "<!-- Upload Text -->"),
        ("<!-- 文件上传 -->", "<!-- File Upload -->"),
        ("<!-- 知识库信息 -->", "<!-- Knowledge Base Info -->"),
        ("<!-- 所有知识库列表 -->", "<!-- All Knowledge Bases List -->"),
        ("<!-- 上传审计 -->", "<!-- Upload Audit -->"),
        ("<!-- 知识库管理 -->", "<!-- Knowledge Base Management -->"),
        ("<!-- 文档浏览器 -->", "<!-- Document Browser -->"),
        ("<!-- 场景和策略选择 -->", "<!-- Scenario and Strategy Selection -->"),
        ("<!-- 场景信息 -->", "<!-- Scenario Info -->"),
        ("<!-- 专家设置（仅在expert策略时显示） -->", "<!-- Expert Settings (only shown for expert strategy) -->"),
        ("<!-- 元数据将通过 JavaScript 填充 -->", "<!-- Metadata will be populated by JavaScript -->"),
        ("<!-- 内容将通过 JavaScript 填充 -->", "<!-- Content will be populated by JavaScript -->"),
        
        # ===== Iteration messages =====
        ("`<strong>第 ${data.iteration} 轮反思完成</strong><br>`", "`<strong>Reflection round ${data.iteration} complete</strong><br>`"),
        ("`<strong>第 ${data.iteration} 轮改进完成</strong><br>`", "`<strong>Improvement round ${data.iteration} complete</strong><br>`"),
        ("`<strong>初始内容已生成</strong><br><div style=\"", "`<strong>Initial content generated</strong><br><div style=\""),
        
        # ===== Misc =====
        ("📜 查看完整历史", "📜 View Full History"),
        ("📁 读取配置文件", "📁 Read Config File"),
        ("<span>🚀 执行路由</span>", "<span>🚀 Execute Route</span>"),
    ]


def _clean_remaining_chinese(content: str) -> str:
    """清理所有残留的中文文本，替换为英文。"""
    replacements = _get_chinese_replacements()
    
    applied = 0
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            applied += 1
    
    print(f"   中文清理: 应用了 {applied}/{len(replacements)} 条替换规则")
    return content


def _apply_p1b_shared_i18n(content: str) -> str:
    """国际化可见共享路径，并保持国内版源文件不变。"""
    replacements = (
        (
            """            const lang = localStorage.getItem('gaia_lang');
            if (lang) {
                headers.set('X-User-Lang', lang);
            }""",
            """            const lang = normalizeFrontendLang(localStorage.getItem('gaia_lang'));
            headers.set('X-User-Lang', lang);""",
            "p1b.shared.api_fetch_language",
        ),
        (
            "showLoginScreen('登录状态已失效，请重新登录。');",
            "showLoginScreen(t('auth.session_expired'));",
            "p1b.shared.session_expired",
        ),
        (
            "showLoginScreen('已退出登录。');",
            "showLoginScreen(t('auth.logged_out'));",
            "p1b.shared.logged_out",
        ),
        (
            "selectedKnowledgeBaseId ? knowledgeBaseSelect.selectedOptions?.[0]?.text || selectedKnowledgeBaseId : '未关联资料库'",
            "selectedKnowledgeBaseId ? knowledgeBaseSelect.selectedOptions?.[0]?.text || selectedKnowledgeBaseId : t('knowledge.value.no_knowledge_base')",
            "p1b.shared.snapshot_no_knowledge_base",
        ),
        (
            "let message = `请求失败（HTTP ${response.status}）`;",
            "let message = t('error.request_failed_http', { status: response.status });",
            "p1b.shared.stream_http_error",
        ),
        (
            "console.warn('读取错误响应失败:', error);",
            "console.warn(t('error.read_response_failed'), error);",
            "p1b.shared.stream_read_error",
        ),
    )
    for old, new, rule_name in replacements:
        content = replace_once(content, old, new, rule_name)
    return content


def _apply_p1b_multiagent_selection_i18n(content: str) -> str:
    """国际化 Multi-Agent 加载、任务描述和 Agent 选择状态。"""
    agent_names = """        const AGENT_DISPLAY_NAMES = {
            contract_reviewer: '合同审查协调员',
            clause_risk_analyzer: '条款风险分析师',
            legal_researcher: '法律依据检索员',
            drafting_specialist: '法律文书起草专家',
            compliance_checker: '合规审查专员',
            audit_recorder: '审计留痕记录员'
        };"""
    localized_agent_names = """        const AGENT_DISPLAY_NAMES = {
            contract_reviewer: 'agent_contract_reviewer',
            clause_risk_analyzer: 'agent_clause_risk_analyzer',
            legal_researcher: 'agent_legal_researcher',
            drafting_specialist: 'agent_drafting_specialist',
            compliance_checker: 'agent_compliance_checker',
            audit_recorder: 'agent_audit_recorder'
        };

        function getAgentDisplayName(name) {
            const i18nKey = AGENT_DISPLAY_NAMES[name];
            return i18nKey ? t(i18nKey) : name;
        }"""
    content = replace_once(
        content,
        agent_names,
        localized_agent_names,
        "p1b.multiagent.selection.agent_display_names",
    )

    task_descriptions = {
        "完整审查合同风险并输出标准审查报告": "contract_review",
        "只识别合同条款风险和风险等级": "risk_identification",
        "根据合同风险生成修改建议和替代条款": "revision_suggestions",
        "检索相关法律法规、案例、监管规则和企业知识库": "legal_research",
        "分析合同和业务安排中的监管合规风险": "compliance_analysis",
        "输出面向决策的合同审查结论": "review_summary",
        "根据事实、诉求和证据生成法律文书初稿": "legal_document_generation",
        "将合同与企业红线规则或标准模板进行比对": "redline_comparison",
        "根据风险等级和业务场景给出审批流建议": "approval_flow_suggestion",
    }
    for description, task_type in task_descriptions.items():
        content = replace_once(
            content,
            f"description: '{description}'",
            f"descriptionKey: 'legal_task.{task_type}.description'",
            f"p1b.multiagent.selection.task_description.{task_type}",
        )
    content = replace_once(
        content,
        "description.textContent = template.description;",
        "description.textContent = t(template.descriptionKey);",
        "p1b.multiagent.selection.task_description.render",
    )

    content = replace_once(
        content,
        """        async function loadCollaborationData() {
            legalSelectionPolicyState = 'loading';
            legalSelectionPolicy = null;
            renderLegalAgentSelection();""",
        """        async function loadCollaborationData() {
            legalSelectionPolicyState = 'loading';
            legalSelectionPolicy = null;
            renderLegalAgentSelection(t('status.loading_collaboration_data'));""",
        "p1b.multiagent.selection.load.start",
    )
    content = replace_once(
        content,
        """                if (teamsData.success) {
                    collaborationTeamsData = teamsData.teams;
                } else {
                    legalSelectionPolicyState = 'error';
                }""",
        """                if (teamsData.success) {
                    collaborationTeamsData = teamsData.teams;
                } else {
                    legalSelectionPolicyState = 'error';
                    renderLegalAgentSelection(t('error.load_collaboration_data'));
                }""",
        "p1b.multiagent.selection.load.response_error",
    )
    content = replace_once(
        content,
        """            } catch (error) {
                console.error('加载协作数据失败:', error);
                legalSelectionPolicyState = 'error';
                legalSelectionPolicy = null;
                renderLegalAgentSelection();
            }""",
        """            } catch (error) {
                console.error(t('error.load_collaboration_data'), error);
                legalSelectionPolicyState = 'error';
                legalSelectionPolicy = null;
                renderLegalAgentSelection(t('error.load_collaboration_data'));
            }""",
        "p1b.multiagent.selection.load.exception",
    )

    content = replace_once(
        content,
        "function renderLegalAgentSelection() {",
        "function renderLegalAgentSelection(feedbackMessage = '') {",
        "p1b.multiagent.selection.render.signature",
    )
    content = replace_once(
        content,
        "status.textContent = '正在加载法律智能体策略...';",
        "status.textContent = feedbackMessage || t('multiagent.agent_selection.loading');",
        "p1b.multiagent.selection.render.loading",
    )
    content = replace_once(
        content,
        """status.innerHTML = '法律智能体策略加载失败，无法安全发起法律协作。<button class="btn btn-sm btn-outline" onclick="loadCollaborationData()" type="button" style="margin-left: 8px;">重试</button>';""",
        """status.innerHTML = DOMPurify.sanitize(`${escapeHtml(feedbackMessage || t('error.load_collaboration_data'))}<button class="btn btn-sm btn-outline legal-agent-retry" type="button" style="margin-left: 8px;">${escapeHtml(t('action.retry'))}</button>`);
                status.querySelector('.legal-agent-retry')?.addEventListener('click', loadCollaborationData);""",
        "p1b.multiagent.selection.render.error",
    )
    content = replace_once(
        content,
        """status.textContent = `已加载 ${Object.keys(legalSelectionPolicy.task_defaults || {}).length} 种法律任务策略，可按本次需求调整参与智能体。`;""",
        """status.textContent = t('status.selected_agents', {
                count: selectedLegalAgentNames.length
            });""",
        "p1b.multiagent.selection.render.selected_status",
    )
    content = replace_once(
        content,
        """            options.innerHTML = agents.map(agent => {
                const displayName = AGENT_DISPLAY_NAMES[agent.name] || agent.name;""",
        """            options.innerHTML = DOMPurify.sanitize(agents.map(agent => {
                const displayName = getAgentDisplayName(agent.name);""",
        "p1b.multiagent.selection.render.options_start",
    )
    content = replace_once(
        content,
        """required ? '<span style="background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 10px; font-size: 11px;">必选</span>' : '',""",
        """required ? `<span style="background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 10px; font-size: 11px;">${escapeHtml(t('badge.required'))}</span>` : '',""",
        "p1b.multiagent.selection.render.required_badge",
    )
    content = replace_once(
        content,
        """recommended ? '<span style="background: #e0f2fe; color: #075985; padding: 2px 6px; border-radius: 10px; font-size: 11px;">推荐</span>' : ''""",
        """recommended ? `<span style="background: #e0f2fe; color: #075985; padding: 2px 6px; border-radius: 10px; font-size: 11px;">${escapeHtml(t('badge.recommended'))}</span>` : ''""",
        "p1b.multiagent.selection.render.recommended_badge",
    )
    content = replace_once(
        content,
        """<input type="checkbox" value="${escapeAttr(agent.name)}" ${checked ? 'checked' : ''} ${required ? 'disabled' : ''} onchange="toggleLegalAgent('${escapeAttr(agent.name)}', this.checked)">""",
        """<input type="checkbox" value="${escapeAttr(agent.name)}" data-agent-name="${escapeAttr(agent.name)}" ${checked ? 'checked' : ''} ${required ? 'disabled' : ''}>""",
        "p1b.multiagent.selection.render.checkbox_handler",
    )
    content = replace_once(
        content,
        """            }).join('');

            renderLegalAgentGapWarning();""",
        """            }).join(''));
            options.querySelectorAll('input[data-agent-name]').forEach(input => {
                input.addEventListener('change', () => {
                    toggleLegalAgent(input.dataset.agentName, input.checked);
                });
            });

            renderLegalAgentGapWarning();""",
        "p1b.multiagent.selection.render.options_sanitize",
    )

    content = replace_once(
        content,
        "const displayName = AGENT_DISPLAY_NAMES[name] || name;",
        "const displayName = getAgentDisplayName(name);",
        "p1b.multiagent.selection.gap.display_name",
    )
    content = replace_once(
        content,
        """const gapMessage = legalSelectionPolicy.capability_gaps?.[name] || '可能缺少对应专业能力';""",
        """const gapMessage = legalSelectionPolicy.capability_gaps?.[name] || t('warning.capability_gap_default');""",
        "p1b.multiagent.selection.gap.default",
    )
    content = replace_once(
        content,
        """            warning.textContent = `当前未选择部分推荐智能体：${messages.join('；')}。`;""",
        """            warning.textContent = t('warning.capability_gap', {
                agents: messages.join('; '),
                count: missing.length
            });""",
        "p1b.multiagent.selection.gap.message",
    )

    content = replace_once(
        content,
        """            team.agents.forEach(agent => {
                const displayName = AGENT_DISPLAY_NAMES[agent.name] || agent.name;""",
        """            team.agents.forEach(agent => {
                const displayName = getAgentDisplayName(agent.name);""",
        "p1b.multiagent.selection.team.display_name",
    )
    content = replace_once(
        content,
        """let agentsHTML = '<div style="margin-bottom: 8px; font-weight: 600; color: #495057;">团队成员：</div><div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px;">';""",
        """let agentsHTML = `<div style="margin-bottom: 8px; font-weight: 600; color: #495057;">${escapeHtml(t('team_members_label'))}</div><div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px;">`;""",
        "p1b.multiagent.selection.team.members_label",
    )
    content = replace_once(
        content,
        """<div style="font-weight: 600; font-size: 13px; color: #495057; margin-bottom: 4px;">${displayName}</div>
                        <div style="font-size: 11px; color: #6c757d;">${agent.expertise.join(', ')}</div>""",
        """<div style="font-weight: 600; font-size: 13px; color: #495057; margin-bottom: 4px;">${escapeHtml(displayName)}</div>
                        <div style="font-size: 11px; color: #6c757d;">${escapeHtml(Array.isArray(agent.expertise) ? agent.expertise.join(', ') : '')}</div>""",
        "p1b.multiagent.selection.team.agent_data_escape",
    )
    content = replace_once(
        content,
        "document.getElementById('teamAgents').innerHTML = agentsHTML;",
        "document.getElementById('teamAgents').innerHTML = DOMPurify.sanitize(agentsHTML);",
        "p1b.multiagent.selection.team.agents_sanitize",
    )
    content = replace_once(
        content,
        """let useCasesHTML = '<div style="margin-bottom: 8px; font-weight: 600; color: #495057;">适用场景：</div><div style="display: flex; flex-wrap: wrap; gap: 8px;">';""",
        """let useCasesHTML = `<div style="margin-bottom: 8px; font-weight: 600; color: #495057;">${escapeHtml(t('team_use_cases_label'))}</div><div style="display: flex; flex-wrap: wrap; gap: 8px;">`;""",
        "p1b.multiagent.selection.team.use_cases_label",
    )
    content = replace_once(
        content,
        """useCasesHTML += `<span style="background: #e7f3ff; color: #004085; padding: 4px 12px; border-radius: 12px; font-size: 13px;">${useCase}</span>`;""",
        """useCasesHTML += `<span style="background: #e7f3ff; color: #004085; padding: 4px 12px; border-radius: 12px; font-size: 13px;">${escapeHtml(useCase)}</span>`;""",
        "p1b.multiagent.selection.team.use_case_escape",
    )
    content = replace_once(
        content,
        "document.getElementById('teamUseCases').innerHTML = useCasesHTML;",
        "document.getElementById('teamUseCases').innerHTML = DOMPurify.sanitize(useCasesHTML);",
        "p1b.multiagent.selection.team.use_cases_sanitize",
    )
    return content


def _apply_p1b_contract_parse_i18n(content: str) -> str:
    """国际化合同解析流程，并隔离非中文界面的后端错误详情。"""
    content = replace_once(
        content,
        """        async function parseLegalContractFile() {""",
        """        function localizedOperationError(key, detail) {
            return currentLang === 'zh' && detail ? String(detail) : t(key);
        }

        async function parseLegalContractFile() {""",
        "p1b.multiagent.contract.error_helper",
    )
    content = replace_once(
        content,
        "alert('请选择合同或法律材料文件');",
        "alert(t('validation.contract_file_required'));",
        "p1b.multiagent.contract.file_required",
    )
    content = replace_once(
        content,
        "parseStatus.textContent = '正在上传并解析合同文件...';",
        "parseStatus.textContent = t('status.contract_parsing');",
        "p1b.multiagent.contract.file_loading",
    )
    content = replace_once(
        content,
        "parseBtn.textContent = '上传解析中...';",
        "parseBtn.textContent = t('status.contract_parsing');",
        "p1b.multiagent.contract.button_loading",
    )
    content = replace_once(
        content,
        """                    parseStatus.textContent = `合同上传解析失败：${error.message}`;""",
        """                    parseStatus.textContent = localizedOperationError('error.contract_parse_failed', error.message);""",
        "p1b.multiagent.contract.file_error_ui",
    )
    content = replace_once(
        content,
        """            } catch (error) {
                parsedContractText = '';
                parsedContractStructureSummary = null;
                uploadedLegalFileId = '';
                uploadedLegalFileName = '';
                if (parseStatus) {
                    parseStatus.style.display = 'block';
                    parseStatus.style.color = '#b91c1c';
                    parseStatus.textContent = localizedOperationError('error.contract_parse_failed', error.message);
                }
            } finally {""",
        """            } catch (error) {
                console.error(t('error.contract_parse_failed'), error?.name || 'Error');
                parsedContractText = '';
                parsedContractStructureSummary = null;
                uploadedLegalFileId = '';
                uploadedLegalFileName = '';
                if (parseStatus) {
                    parseStatus.style.display = 'block';
                    parseStatus.style.color = '#b91c1c';
                    parseStatus.textContent = localizedOperationError('error.contract_parse_failed', error.message);
                }
            } finally {""",
        "p1b.multiagent.contract.file_error_log",
    )
    content = replace_once(
        content,
        "parseBtn.textContent = '上传并解析合同文件';",
        "parseBtn.textContent = t('action.parse_contract_file');",
        "p1b.multiagent.contract.button_restore",
    )
    content = replace_once(
        content,
        "alert('请输入合同或法律材料文件路径');",
        "alert(t('validation.contract_path_required'));",
        "p1b.multiagent.contract.path_required",
    )
    content = replace_once(
        content,
        "parseStatus.textContent = '正在按服务器路径解析合同文件...';",
        "parseStatus.textContent = t('status.contract_parsing');",
        "p1b.multiagent.contract.path_loading",
    )
    content = replace_once(
        content,
        """                    parseStatus.textContent = `合同解析失败：${error.message}`;""",
        """                    parseStatus.textContent = localizedOperationError('error.contract_parse_failed', error.message);""",
        "p1b.multiagent.contract.path_error_ui",
    )
    content = replace_once(
        content,
        """            } catch (error) {
                parsedContractText = '';
                parsedContractStructureSummary = null;
                uploadedLegalFileId = '';
                uploadedLegalFileName = '';
                if (parseStatus) {
                    parseStatus.style.display = 'block';
                    parseStatus.style.color = '#b91c1c';
                    parseStatus.textContent = localizedOperationError('error.contract_parse_failed', error.message);
                }
            }
        }

        function applyParsedContractResult""",
        """            } catch (error) {
                console.error(t('error.contract_parse_failed'), error?.name || 'Error');
                parsedContractText = '';
                parsedContractStructureSummary = null;
                uploadedLegalFileId = '';
                uploadedLegalFileName = '';
                if (parseStatus) {
                    parseStatus.style.display = 'block';
                    parseStatus.style.color = '#b91c1c';
                    parseStatus.textContent = localizedOperationError('error.contract_parse_failed', error.message);
                }
            }
        }

        function applyParsedContractResult""",
        "p1b.multiagent.contract.path_error_log",
    )
    content = replace_once(
        content,
        "throw new Error(data.detail || '合同解析失败');",
        "throw new Error(data.detail || t('error.contract_parse_failed'));",
        "p1b.multiagent.contract.response_error",
    )

    old_render_status = """        function renderParsedContractStatus(parseStatus, data, documentCount) {
            const summary = parsedContractStructureSummary;
            const summarySections = summary ? [
                renderContractSummarySection('主体', summary.parties),
                renderContractSummarySection('金额', summary.amount),
                renderContractSummarySection('期限', summary.term),
                renderContractSummarySection('生效日期', summary.effective_date)
            ].filter(Boolean).join('') : '';
            const structureSummary = formatContractStructureSummary(summary, summarySections);
            const structureStatus = data.metadata?.structure_status || (summary ? 'success' : 'text_only');
            const parseWarnings = normalizeContractSummaryValues(data.parse_warnings);
            const warningHtml = parseWarnings.length ? `
                <div class="legal-parse-summary-note">
                    ${parseWarnings.map(warning => escapeHtml(warning)).join('<br>')}
                </div>
            ` : '';
            const fileNameHtml = uploadedLegalFileName ? `
                <div class="legal-parse-summary-file">文件：${escapeHtml(uploadedLegalFileName)}</div>
            ` : '';

            parseStatus.innerHTML = `
                <div class="legal-parse-summary">
                    <div class="legal-parse-summary-header">
                        <div>
                            <div class="legal-parse-summary-title">合同解析成功</div>
                            ${fileNameHtml}
                        </div>
                        <div class="legal-parse-summary-value">${escapeHtml(structureStatus)}</div>
                    </div>
                    <div class="legal-parse-summary-meta">
                        <div class="legal-parse-summary-meta-item">
                            <div class="legal-parse-summary-label">已读取字符</div>
                            <div class="legal-parse-summary-value">${escapeHtml(parsedContractText.length)}</div>
                        </div>
                        <div class="legal-parse-summary-meta-item">
                            <div class="legal-parse-summary-label">文档片段</div>
                            <div class="legal-parse-summary-value">${escapeHtml(documentCount)}</div>
                        </div>
                        <div class="legal-parse-summary-meta-item">
                            <div class="legal-parse-summary-label">合同类型</div>
                            <div class="legal-parse-summary-value">${escapeHtml(summary?.contract_type || '未识别')}</div>
                        </div>
                        <div class="legal-parse-summary-meta-item">
                            <div class="legal-parse-summary-label">关键条款</div>
                            <div class="legal-parse-summary-value">${escapeHtml(summary?.key_clause_summary?.length || 0)} 项</div>
                        </div>
                    </div>
                    ${structureSummary || '<div class="legal-parse-summary-note">未识别结构化摘要，仍可继续发起多智能体审查并由人工复核。</div>'}
                    ${warningHtml}
                </div>
            `;
        }"""
    new_render_status = """        function renderParsedContractStatus(parseStatus, data, documentCount) {
            const summary = parsedContractStructureSummary;
            const summarySections = summary ? [
                renderContractSummarySection(t('contract.summary.parties'), summary.parties),
                renderContractSummarySection(t('contract.summary.amount'), summary.amount),
                renderContractSummarySection(t('contract.summary.term'), summary.term),
                renderContractSummarySection(t('contract.summary.effective_date'), summary.effective_date)
            ].filter(Boolean).join('') : '';
            const structureSummary = formatContractStructureSummary(summary, summarySections);
            const structureStatus = data.metadata?.structure_status || (summary ? 'success' : 'text_only');
            const parseWarnings = normalizeContractSummaryValues(data.parse_warnings);
            const warningHtml = parseWarnings.length ? `
                <div class="legal-parse-summary-note">
                    ${parseWarnings.map(warning => escapeHtml(warning)).join('<br>')}
                </div>
            ` : '';
            const fileNameHtml = uploadedLegalFileName ? `
                <div class="legal-parse-summary-file">${escapeHtml(t('contract.summary.file'))}: ${escapeHtml(uploadedLegalFileName)}</div>
            ` : '';
            const contractTypeHtml = summary?.contract_type
                ? escapeHtml(summary?.contract_type)
                : escapeHtml(t('contract.summary.unrecognized'));

            parseStatus.innerHTML = DOMPurify.sanitize(`
                <div class="legal-parse-summary">
                    <div class="legal-parse-summary-header">
                        <div>
                            <div class="legal-parse-summary-title">${escapeHtml(t('status.contract_parse_success'))}</div>
                            ${fileNameHtml}
                        </div>
                        <div class="legal-parse-summary-value">${escapeHtml(structureStatus)}</div>
                    </div>
                    <div class="legal-parse-summary-meta">
                        <div class="legal-parse-summary-meta-item">
                            <div class="legal-parse-summary-label">${escapeHtml(t('contract.summary.character_count'))}</div>
                            <div class="legal-parse-summary-value">${escapeHtml(parsedContractText.length)}</div>
                        </div>
                        <div class="legal-parse-summary-meta-item">
                            <div class="legal-parse-summary-label">${escapeHtml(t('contract.summary.document_count'))}</div>
                            <div class="legal-parse-summary-value">${escapeHtml(documentCount)}</div>
                        </div>
                        <div class="legal-parse-summary-meta-item">
                            <div class="legal-parse-summary-label">${escapeHtml(t('contract.summary.type'))}</div>
                            <div class="legal-parse-summary-value">${contractTypeHtml}</div>
                        </div>
                        <div class="legal-parse-summary-meta-item">
                            <div class="legal-parse-summary-label">${escapeHtml(t('contract.summary.clauses'))}</div>
                            <div class="legal-parse-summary-value">${escapeHtml(summary?.key_clause_summary?.length || 0)}</div>
                        </div>
                    </div>
                    ${structureSummary || `<div class="legal-parse-summary-note">${escapeHtml(t('contract.summary.no_structured'))}</div>`}
                    ${warningHtml}
                </div>
            `);
        }"""
    content = replace_once(
        content,
        old_render_status,
        new_render_status,
        "p1b.multiagent.contract.render_status",
    )

    old_format_summary = """        function formatContractStructureSummary(summary, sectionHtml = '') {
            if (!summary) return '';

            const clauseCount = Number(summary.clause_count || 0);
            const warningCount = Number(summary.warning_count || 0);
            const overviewItems = [
                `合同类型：${summary.contract_type || '未识别'}`,
                `条款数量：${Number.isFinite(clauseCount) ? clauseCount : 0} 项`,
                `关键条款：${summary.key_clause_summary?.length || 0} 项`
            ];
            if (warningCount > 0) {
                overviewItems.push(`解析提示：${warningCount} 项`);
            }

            const overviewHtml = renderContractSummarySection('结构化摘要', overviewItems);
            const gridHtml = sectionHtml ? `<div class="legal-parse-summary-grid">${sectionHtml}</div>` : '';
            return `${overviewHtml}${gridHtml}`;
        }"""
    new_format_summary = """        function formatContractStructureSummary(summary, sectionHtml = '') {
            if (!summary) return '';

            const clauseCount = Number(summary.clause_count || 0);
            const warningCount = Number(summary.warning_count || 0);
            const overviewItems = [
                `${t('contract.summary.type')}: ${summary.contract_type || t('contract.summary.unrecognized')}`,
                `${t('contract.summary.clause_count')}: ${t('contract.summary.items', { count: Number.isFinite(clauseCount) ? clauseCount : 0 })}`,
                `${t('contract.summary.clauses')}: ${t('contract.summary.items', { count: summary.key_clause_summary?.length || 0 })}`
            ];
            if (warningCount > 0) {
                overviewItems.push(`${t('contract.summary.warning_count')}: ${t('contract.summary.items', { count: warningCount })}`);
            }

            const overviewHtml = renderContractSummarySection(t('contract.summary.structured'), overviewItems);
            const gridHtml = sectionHtml ? `<div class="legal-parse-summary-grid">${sectionHtml}</div>` : '';
            return `${overviewHtml}${gridHtml}`;
        }"""
    content = replace_once(
        content,
        old_format_summary,
        new_format_summary,
        "p1b.multiagent.contract.format_summary",
    )
    content = replace_once(
        content,
        """            const hiddenHtml = hiddenCount > 0 ? `<li>另有 ${escapeHtml(hiddenCount)} 项，建议在审查报告中复核</li>` : '';""",
        """            const hiddenHtml = hiddenCount > 0
                ? `<li>${escapeHtml(t('contract.summary.more_items', { count: escapeHtml(hiddenCount) }))}</li>`
                : '';""",
        "p1b.multiagent.contract.hidden_summary_items",
    )
    return content


def _apply_p1b_collaboration_stream_i18n(content: str) -> str:
    """国际化协作发起和流式状态，不改变请求或 SSE 协议。"""
    content = replace_once(
        content,
        """            if (!task) {
                alert('请输入任务描述');
                return;
            }""",
        """            if (!task) {
                alert(t('validation.task_required'));
                return;
            }""",
        "p1b.multiagent.collaboration.task_required",
    )
    content = replace_once(
        content,
        """            if (!teamType) {
                alert('请选择协作团队');
                return;
            }""",
        """            if (!teamType) {
                alert(t('validation.team_required'));
                return;
            }""",
        "p1b.multiagent.collaboration.team_required",
    )
    content = replace_once(
        content,
        """            if (teamType === 'legal_contract_review' && legalSelectionPolicyState !== 'ready') {
                renderLegalAgentSelection();
                alert('法律智能体策略尚未加载完成，请稍后重试');
                return;
            }

            const snapshot = buildCollaborationSnapshot();""",
        """            if (teamType === 'legal_contract_review' && legalSelectionPolicyState !== 'ready') {
                renderLegalAgentSelection();
                alert(t('alert_policy_not_ready'));
                return;
            }
            if (teamType === 'legal_contract_review' && !selectedLegalAgentNames.length) {
                alert(t('validation.agents_required'));
                return;
            }

            const snapshot = buildCollaborationSnapshot();""",
        "p1b.multiagent.collaboration.agent_required",
    )
    content = replace_once(
        content,
        "startBtn.textContent = '审查中...';",
        "startBtn.textContent = t('action.reviewing');",
        "p1b.multiagent.collaboration.button_loading",
    )
    content = replace_once(
        content,
        "document.getElementById('collaborationStatus').textContent = '正在初始化法律多智能体审查...';",
        "document.getElementById('collaborationStatus').textContent = t('status.collaboration_starting');",
        "p1b.multiagent.collaboration.initial_status",
    )
    content = replace_once(
        content,
        """            } catch (error) {
                console.error('协作失败:', error);
                alert('协作失败: ' + error.message);
                document.getElementById('collaborationStatus').textContent = '协作失败: ' + error.message;
            } finally {
                startBtn.disabled = false;
                startBtn.textContent = '开始多智能体审查';
            }""",
        """            } catch (error) {
                console.error(t('status.failed'), error?.name || 'Error');
                const failureMessage = localizedOperationError('status.failed', error.message);
                alert(failureMessage);
                document.getElementById('collaborationStatus').textContent = failureMessage;
            } finally {
                startBtn.disabled = false;
                startBtn.textContent = t('action.start_review');
            }""",
        "p1b.multiagent.collaboration.failure_and_restore",
    )

    old_event_handler = """        function handleCollaborationEvent(data) {
            const statusDiv = document.getElementById('collaborationStatus');

            switch (data.type) {
                case 'start':
                    statusDiv.textContent = data.message;
                    break;

                case 'team_info':
                    const agentSelection = data.metadata?.agent_selection || null;
                    const serverAgents = data.agents || [];
                    const selectedAgentNames = agentSelection?.selected_agent_names
                        || serverAgents.map(agent => agent.name || agent)
                        || [];
                    const selectionSource = agentSelection?.selection_source || '未记录';
                    const selectedAgentText = selectedAgentNames.length
                        ? selectedAgentNames.map(name => AGENT_DISPLAY_NAMES[name] || name).join('、')
                        : '服务端未返回参与名单';
                    const teamInfoHTML = `
                        <div style="font-weight: 600; margin-bottom: 8px;">法律专家团队: ${data.team_name} (${data.agent_count} 位专家)</div>
                        <div style="font-size: 13px; color: #6c757d;">处理模式: ${data.mode}</div>
                        <div style="font-size: 13px; color: #6c757d; margin-top: 6px;">实际参与: ${escapeHtml(selectedAgentText)}</div>
                        <div style="font-size: 12px; color: #6c757d; margin-top: 4px;">选择来源: ${escapeHtml(selectionSource)}</div>
                    `;
                    document.getElementById('collaborationTeamInfo').innerHTML = teamInfoHTML;
                    statusDiv.textContent = '法律专家团队已组建，开始审查...';
                    break;

                case 'complete':
                    currentCollaborationResult = {...data, requestSnapshot: currentCollaborationSnapshot};
                    displayCollaborationResult(currentCollaborationResult);
                    statusDiv.textContent = '法律多智能体审查已完成！';
                    break;

                case 'error':
                    statusDiv.textContent = data.message;
                    statusDiv.style.color = '#dc3545';
                    break;
            }
        }"""
    old_event_handler = old_event_handler.replace(
        "const statusDiv = document.getElementById('collaborationStatus');\n\n            switch",
        "const statusDiv = document.getElementById('collaborationStatus');\n            \n            switch",
    ).replace(
        "break;\n\n                case",
        "break;\n                    \n                case",
    )
    new_event_handler = """        function handleCollaborationEvent(data) {
            const statusDiv = document.getElementById('collaborationStatus');

            switch (data.type) {
                case 'start':
                    statusDiv.textContent = localizedOperationError('status.collaboration_starting', data.message);
                    break;

                case 'team_info':
                    const agentSelection = data.metadata?.agent_selection || null;
                    const serverAgents = data.agents || [];
                    const selectedAgentNames = agentSelection?.selected_agent_names
                        || serverAgents.map(agent => agent.name || agent)
                        || [];
                    const selectionSource = agentSelection?.selection_source || t('team_info.unknown');
                    const selectedAgentText = selectedAgentNames.length
                        ? selectedAgentNames.map(name => getAgentDisplayName(name)).join(', ')
                        : t('team_info.unknown');
                    const safeTeamName = data.team_name
                        ? escapeHtml(data.team_name)
                        : escapeHtml(t('team_info.unknown'));
                    const safeMode = data.mode
                        ? escapeHtml(data.mode)
                        : escapeHtml(t('team_info.unknown'));
                    const teamInfoHTML = `
                        <div style="font-weight: 600; margin-bottom: 8px;">${safeTeamName} (${escapeHtml(t('team_info.experts', { count: data.agent_count }))})</div>
                        <div style="font-size: 13px; color: #6c757d;">${escapeHtml(t('team_info.mode'))}: ${safeMode}</div>
                        <div style="font-size: 13px; color: #6c757d; margin-top: 6px;">${escapeHtml(t('team_info.participants'))}: ${escapeHtml(selectedAgentText)}</div>
                        <div style="font-size: 12px; color: #6c757d; margin-top: 4px;">${escapeHtml(t('team_info.selection_source'))}: ${escapeHtml(selectionSource)}</div>
                    `;
                    document.getElementById('collaborationTeamInfo').innerHTML = DOMPurify.sanitize(teamInfoHTML);
                    statusDiv.textContent = t('status.team_ready');
                    break;

                case 'complete':
                    currentCollaborationResult = {...data, requestSnapshot: currentCollaborationSnapshot};
                    displayCollaborationResult(currentCollaborationResult);
                    statusDiv.textContent = t('status.completed');
                    break;

                case 'error':
                    console.error(t('status.failed'), data.message);
                    statusDiv.textContent = localizedOperationError('status.failed', data.message);
                    statusDiv.style.color = '#dc3545';
                    break;
            }
        }"""
    content = replace_once(
        content,
        old_event_handler,
        new_event_handler,
        "p1b.multiagent.collaboration.event_handler",
    )
    return content


def _apply_p1b_collaboration_result_i18n(content: str) -> str:
    """国际化协作结果壳层，并保留模型与业务内容的净化边界。"""
    content = replace_once(
        content,
        "alert('协作失败: ' + data.error_message);",
        "alert(localizedOperationError('result.failed', data.error_message));",
        "p1b.multiagent.result.safe_failure",
    )
    content = replace_once(
        content,
        "document.getElementById('collaborationSuccess').textContent = data.success ? '成功' : '失败';",
        "document.getElementById('collaborationSuccess').textContent = data.success ? t('result.success') : t('result.failed');",
        "p1b.multiagent.result.status",
    )
    content = replace_once(
        content,
        "document.getElementById('collaborationTime').textContent = data.execution_time.toFixed(1) + 's';",
        "document.getElementById('collaborationTime').textContent = t('result.seconds', { count: data.execution_time.toFixed(1) });",
        "p1b.multiagent.result.duration",
    )
    content = replace_once(
        content,
        "if (button) button.textContent = '展开';",
        "if (button) button.textContent = t('action.expand');",
        "p1b.multiagent.result.reset_expand",
    )
    content = replace_once(
        content,
        "button.textContent = isHidden ? '收起' : '展开';",
        "button.textContent = isHidden ? t('action.collapse') : t('action.expand');",
        "p1b.multiagent.result.toggle",
    )
    content = replace_once(
        content,
        "summary.textContent = `默认折叠，共 ${contributionEntries.length} 位法律专家参与分析，展开后查看完整过程。`;",
        "summary.textContent = t('summary.agent_contributions', { count: contributionEntries.length });",
        "p1b.multiagent.result.contribution_summary",
    )
    content = replace_once(
        content,
        """                const statusLabel = status === 'failed' ? '失败' : '完成';
                const statusColor = status === 'failed' ? '#b91c1c' : '#166534';
                const responseText = status === 'failed'
                    ? '该智能体执行失败，内部异常已隐藏。请结合其他专家结果并进行人工复核。'
                    : (contribution.response || '');""",
        """                const statusLabel = status === 'failed'
                    ? t('status.agent_failed')
                    : t('status.agent_completed');
                const statusColor = status === 'failed' ? '#b91c1c' : '#166534';
                const responseText = status === 'failed'
                    ? t('error.agent_failed_safe')
                    : (contribution.response || '');""",
        "p1b.multiagent.result.contribution_status",
    )
    content = replace_once(
        content,
        '<h5 style="margin: 0; color: #495057;">${agentName}</h5>',
        '<h5 style="margin: 0; color: #495057;">${escapeHtml(agentName)}</h5>',
        "p1b.multiagent.result.contribution_agent_name",
    )
    content = replace_once(
        content,
        '<div style="font-size: 12px; color: #6c757d;">${contribution.role} · <span style="color: ${statusColor};">${statusLabel}</span></div>',
        '<div style="font-size: 12px; color: #6c757d;">${escapeHtml(contribution.role || \'\')} · <span style="color: ${statusColor};">${statusLabel}</span></div>',
        "p1b.multiagent.result.contribution_role",
    )
    content = replace_once(
        content,
        "summary.textContent = `默认折叠，共 ${messages.length} 条协作记录，展开后查看任务分发和响应过程。`;",
        "summary.textContent = t('summary.messages', { count: messages.length });",
        "p1b.multiagent.result.message_summary",
    )
    content = replace_once(
        content,
        '<span style="font-weight: 600; color: #495057;">${icon} ${message.sender} → ${message.receiver}</span>',
        '<span style="font-weight: 600; color: #495057;">${icon} ${escapeHtml(message.sender)} → ${escapeHtml(message.receiver)}</span>',
        "p1b.multiagent.result.message_participants",
    )
    content = replace_once(
        content,
        '<div style="color: #6c757d;">${message.content.substring(0, 200)}${message.content.length > 200 ? \'...\' : \'\'}</div>',
        '<div style="color: #6c757d;">${escapeHtml(message.content.substring(0, 200))}${message.content.length > 200 ? \'...\' : \'\'}</div>',
        "p1b.multiagent.result.message_content",
    )
    return content


def _apply_p1b_collaboration_report_i18n(content: str) -> str:
    """国际化复制、详情提示和下载报告的固定壳层。"""
    content = replace_once(
        content,
        """            navigator.clipboard.writeText(result).then(() => {
                alert('审查报告已复制到剪贴板');
            }).catch(err => {
                console.error('复制失败:', err);
            });""",
        """            navigator.clipboard.writeText(result).then(() => {
                alert(t('toast.report_copied'));
            }).catch(err => {
                console.error(t('toast.copy_failed'), err);
                alert(t('toast.copy_failed'));
            });""",
        "p1b.multiagent.report.copy_feedback",
    )

    old_download = r"""        function downloadCollaborationResult() {
            if (!currentCollaborationResult) return;

            const requestSnapshot = currentCollaborationResult.requestSnapshot || {};
            const agentSelection = currentCollaborationResult.metadata?.agent_selection || {};
            const knowledgeBaseSnapshot = requestSnapshot.knowledgeBase || {};
            const fileSnapshot = requestSnapshot.file || {};
            const selectedAgentNames = agentSelection.selected_agent_names || requestSnapshot.selectedAgentNames || [];
            const capabilityGaps = agentSelection.capability_gaps || [];
            const contributions = currentCollaborationResult.agent_contributions || {};
            const legalFilePath = fileSnapshot.uploadedFileName || '未上传或未解析文件';
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `legal_review_report_${timestamp}.md`;
            const selectedAgentText = selectedAgentNames.length
                ? selectedAgentNames.map(name => AGENT_DISPLAY_NAMES[name] || name).join('、')
                : '未记录';
            const gapText = capabilityGaps.length
                ? capabilityGaps.map(gap => {
                    if (typeof gap === 'string') return gap;
                    const agentName = gap.agent_name || gap.agentName || '未知智能体';
                    return `${AGENT_DISPLAY_NAMES[agentName] || agentName}：${gap.message || '可能缺少对应专业能力'}`;
                }).join('；')
                : '无';

            let content = `# 法律多智能体审查报告\n\n`;
            content += `**审查任务**: ${requestSnapshot.task || '未记录'}\n\n`;
            content += `**法律服务团队**: ${requestSnapshot.teamDisplayName || requestSnapshot.teamType || '未记录'}\n`;
            content += `**处理模式**: ${requestSnapshot.modeDisplayName || requestSnapshot.mode || '未记录'}\n`;
            content += `**法律任务类型**: ${agentSelection.legal_task_type || requestSnapshot.legalTaskType || '未记录'}\n`;
            content += `**选择来源**: ${agentSelection.selection_source || '未记录'}\n`;
            content += `**实际参与智能体**: ${selectedAgentText}\n`;
            content += `**能力缺口提示**: ${gapText}\n`;
            content += `**关联资料库**: ${knowledgeBaseSnapshot.displayName || '未关联资料库'}\n`;
            content += `**包含公共知识库**: ${knowledgeBaseSnapshot.includePublicKnowledge ? '是' : '否'}\n`;
            content += `**合同或材料文件**: ${legalFilePath}\n`;
            if (fileSnapshot.uploadedFileId) {
                content += `**上传文件ID**: ${fileSnapshot.uploadedFileId}\n`;
            }
            content += `**是否包含结构化摘要**: ${fileSnapshot.hasContractStructureSummary ? '是' : '否'}\n`;
            content += `**发起时间**: ${requestSnapshot.startedAt || '未记录'}\n`;
            content += `**参与专家数**: ${Object.keys(contributions).length}\n`;
            content += `**审查耗时**: ${Number(currentCollaborationResult.execution_time || 0).toFixed(1)}s\n\n`;
            content += `> 本报告由法律多智能体系统辅助生成，不构成正式律师意见；请由具备资质的专业人员结合事实、证据和适用法律进行人工复核。\n\n`;
            content += `---\n\n`;
            content += `## 最终审查结论\n\n${currentCollaborationResult.final_output}\n\n`;
            content += `---\n\n`;
            content += `## 各法律专家分析\n\n`;
<P1B_SOURCE_INDENT>
            for (const [agentName, contribution] of Object.entries(contributions)) {
                const status = contribution.status || 'completed';
                const statusLabel = status === 'failed' ? '失败' : '完成';
                content += `### ${AGENT_DISPLAY_NAMES[agentName] || agentName} (${contribution.role || 'unknown'} · ${statusLabel})\n\n`;
                if (status === 'failed') {
                    content += `该智能体执行失败，内部异常已隐藏。请结合其他专家结果并进行人工复核。\n\n`;
                    continue;
                }
                content += `${contribution.response || ''}\n\n`;
            }
<P1B_SOURCE_INDENT>
            const blob = new Blob([content], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        }""".replace("<P1B_SOURCE_INDENT>", "            ")
    new_download = r"""        function downloadCollaborationResult() {
            if (!currentCollaborationResult) return;

            const requestSnapshot = currentCollaborationResult.requestSnapshot || {};
            const agentSelection = currentCollaborationResult.metadata?.agent_selection || {};
            const knowledgeBaseSnapshot = requestSnapshot.knowledgeBase || {};
            const fileSnapshot = requestSnapshot.file || {};
            const selectedAgentNames = agentSelection.selected_agent_names || requestSnapshot.selectedAgentNames || [];
            const capabilityGaps = agentSelection.capability_gaps || [];
            const contributions = currentCollaborationResult.agent_contributions || {};
            const notRecorded = t('download.value.not_recorded');
            const legalFilePath = fileSnapshot.uploadedFileName || notRecorded;
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `legal_review_report_${timestamp}.md`;
            const selectedAgentText = selectedAgentNames.length
                ? selectedAgentNames.map(name => getAgentDisplayName(name)).join(', ')
                : notRecorded;
            const gapText = capabilityGaps.length
                ? capabilityGaps.map(gap => {
                    if (typeof gap === 'string') return gap;
                    const agentName = gap.agent_name || gap.agentName || notRecorded;
                    return `${getAgentDisplayName(agentName)}: ${gap.message || t('warning.capability_gap_default')}`;
                }).join('; ')
                : t('download.value.none');

            let content = `# ${t('download.report_title')}\n\n`;
            content += `**${t('download.field.task')}**: ${requestSnapshot.task || notRecorded}\n\n`;
            content += `**${t('download.field.team')}**: ${requestSnapshot.teamDisplayName || requestSnapshot.teamType || notRecorded}\n`;
            content += `**${t('download.field.mode')}**: ${requestSnapshot.modeDisplayName || requestSnapshot.mode || notRecorded}\n`;
            content += `**${t('download.field.legal_task_type')}**: ${agentSelection.legal_task_type || requestSnapshot.legalTaskType || notRecorded}\n`;
            content += `**${t('download.field.selection_source')}**: ${agentSelection.selection_source || notRecorded}\n`;
            content += `**${t('download.field.participants')}**: ${selectedAgentText}\n`;
            content += `**${t('download.field.capability_gaps')}**: ${gapText}\n`;
            content += `**${t('download.field.knowledge_base')}**: ${knowledgeBaseSnapshot.displayName || t('download.value.none')}\n`;
            content += `**${t('download.field.include_public_knowledge')}**: ${knowledgeBaseSnapshot.includePublicKnowledge ? t('download.value.yes') : t('download.value.no')}\n`;
            content += `**${t('download.field.file')}**: ${legalFilePath}\n`;
            if (fileSnapshot.uploadedFileId) {
                content += `**${t('download.field.uploaded_file_id')}**: ${fileSnapshot.uploadedFileId}\n`;
            }
            content += `**${t('download.field.has_structured_summary')}**: ${fileSnapshot.hasContractStructureSummary ? t('download.value.yes') : t('download.value.no')}\n`;
            content += `**${t('download.field.started_at')}**: ${requestSnapshot.startedAt || notRecorded}\n`;
            content += `**${t('download.field.agent_count')}**: ${Object.keys(contributions).length}\n`;
            content += `**${t('download.field.duration')}**: ${t('result.seconds', { count: Number(currentCollaborationResult.execution_time || 0).toFixed(1) })}\n\n`;
            content += `> ${t('download.human_review_notice')}\n\n`;
            content += `---\n\n`;
            content += `## ${t('download.section.final_conclusion')}\n\n${currentCollaborationResult.final_output}\n\n`;
            content += `---\n\n`;
            content += `## ${t('download.section.agent_analysis')}\n\n`;

            for (const [agentName, contribution] of Object.entries(contributions)) {
                const status = contribution.status || 'completed';
                const statusLabel = status === 'failed'
                    ? t('status.agent_failed')
                    : t('status.agent_completed');
                content += `### ${getAgentDisplayName(agentName)} (${contribution.role || notRecorded} · ${statusLabel})\n\n`;
                if (status === 'failed') {
                    content += `${t('error.agent_failed_safe')}\n\n`;
                    continue;
                }
                content += `${contribution.response || ''}\n\n`;
            }

            const blob = new Blob([content], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        }"""
    content = replace_once(
        content,
        old_download,
        new_download,
        "p1b.multiagent.report.download",
    )

    content = replace_once(
        content,
        """<div style="font-weight: 600; margin-bottom: 6px;">成员 (${team.agents.length}):</div>""",
        """<div style="font-weight: 600; margin-bottom: 6px;">${escapeHtml(t('team_members_label'))} (${team.agents.length}):</div>""",
        "p1b.multiagent.detail.team_members",
    )
    content = replace_once(
        content,
        """            alert('团队详情已在控制台输出');
            console.log('协作团队:', collaborationTeamsData);""",
        """            alert(t('detail.team_console'));
            console.log(t('detail.team_console'), collaborationTeamsData);""",
        "p1b.multiagent.detail.team_console",
    )
    content = replace_once(
        content,
        """            alert('模式详情已在控制台输出');
            console.log('协作模式:', collaborationModesData);""",
        """            alert(t('detail.mode_console'));
            console.log(t('detail.mode_console'), collaborationModesData);""",
        "p1b.multiagent.detail.mode_console",
    )
    content = replace_once(
        content,
        """            console.log('完整协作结果:', currentCollaborationResult);
            alert('完整协作结果已在控制台输出，可以按 F12 查看');""",
        """            console.log(t('detail.result_console'), currentCollaborationResult);
            alert(t('detail.result_console'));""",
        "p1b.multiagent.detail.result_console",
    )
    return content


def _replace_js_function_text(
    content: str,
    function_name: str,
    old: str,
    new: str,
    rule_name: str,
) -> str:
    """只在指定顶层 JS 函数内执行唯一替换。"""
    start_pattern = re.compile(
        rf"^        (?:async )?function {re.escape(function_name)}\(", re.MULTILINE
    )
    start_match = start_pattern.search(content)
    if not start_match:
        raise BuildRuleError(f"{rule_name}: JS function not found: {function_name}")
    next_match = re.compile(
        r"^        (?:async )?function [A-Za-z_$][A-Za-z0-9_$]*\(", re.MULTILINE
    ).search(content, start_match.end())
    end = next_match.start() if next_match else len(content)
    block = content[start_match.start():end]
    updated_block = replace_once(block, old, new, rule_name)
    return replace_once(
        content,
        block,
        updated_block,
        f"{rule_name}.function_block",
    )


def _apply_p1b_knowledge_i18n(content: str) -> str:
    """国际化 Knowledge 可见动态路径，不改 API、权限或业务值。"""
    rules = {
        "createKnowledgeBase": [
            ("resultDiv.innerHTML = '<div class=\"alert alert-error\">请输入知识库名称</div>';", "resultDiv.innerHTML = `<div class=\"alert alert-error\">${escapeHtml(t('validation.knowledge_name_required'))}</div>`;", "name_required"),
            ("resultDiv.innerHTML = '<div class=\"alert alert-info\">正在创建知识库...</div>';", "resultDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.knowledge_creating'))}</div>`;", "creating"),
            ("throw new Error(data.detail || '创建知识库失败');", "if (data.detail) console.error('Knowledge base creation failed:', data.detail);\n                    throw new Error(currentLang === 'zh' && data.detail ? data.detail : t('error.knowledge_create_failed'));", "create_error"),
            ("resultDiv.innerHTML = `<div class=\"alert alert-success\">✓ 已创建知识库：${escapeHtml(data.collection.display_name)}</div>`;", "resultDiv.innerHTML = `<div class=\"alert alert-success\">✓ ${escapeHtml(t('toast.knowledge_created'))} ${escapeHtml(data.collection.display_name)}</div>`;", "created"),
            ("resultDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${error.message}</div>`;", "console.error('Knowledge base creation failed:', error);\n                const message = currentLang === 'zh' && error.message ? error.message : t('error.knowledge_create_failed');\n                resultDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "catch"),
        ],
        "uploadTexts": [
            ("resultDiv.innerHTML = '<div class=\"alert alert-error\">请输入法律资料内容</div>';", "resultDiv.innerHTML = `<div class=\"alert alert-error\">${escapeHtml(t('validation.knowledge_text_required'))}</div>`;", "text_required"),
            ("resultDiv.innerHTML = '<div class=\"alert alert-error\">请先选择可写入的知识库</div>';", "resultDiv.innerHTML = `<div class=\"alert alert-error\">${escapeHtml(t('validation.knowledge_write_target_required'))}</div>`;", "target_required"),
            ("resultDiv.innerHTML = '<div class=\"alert alert-info\">正在上传资料...</div>';", "resultDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.knowledge_uploading'))}</div>`;", "uploading"),
            ("let successMsg = `✓ 成功上传 ${data.chunks_added} 条资料片段<br>资料总数: ${data.total_documents}<br>`;\n                    successMsg += `知识库: <strong>${escapeHtml(data.display_name || '已授权知识库')}</strong>`;", "let successMsg = `✓ ${escapeHtml(t('toast.knowledge_upload_success', { count: data.chunks_added, total: data.total_documents }))}<br>`;\n                    successMsg += `${escapeHtml(t('knowledge.field.knowledge_base'))}: <strong>${escapeHtml(data.display_name || t('knowledge.value.no_knowledge_base'))}</strong>`;", "success"),
            ("resultDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${data.detail}</div>`;", "if (data.detail) console.error('Text upload failed:', data.detail);\n                    const message = currentLang === 'zh' && data.detail ? data.detail : t('error.knowledge_upload_failed');\n                    resultDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "response_error"),
            ("resultDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${error.message}</div>`;", "console.error('Text upload failed:', error);\n                const message = currentLang === 'zh' && error.message ? error.message : t('error.knowledge_upload_failed');\n                resultDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "catch"),
        ],
        "renderRagFileUploadSuccess": [
            ("let successMsg = `✓ 成功上传 ${data.chunks_added} 条资料片段<br>资料总数: ${data.total_documents}<br>`;\n            successMsg += `知识库: <strong>${escapeHtml(data.display_name || '已授权知识库')}</strong><br>`;", "let successMsg = `✓ ${escapeHtml(t('toast.knowledge_upload_success', { count: data.chunks_added, total: data.total_documents }))}<br>`;\n            successMsg += `${escapeHtml(t('knowledge.field.knowledge_base'))}: <strong>${escapeHtml(data.display_name || t('knowledge.value.no_knowledge_base'))}</strong><br>`;", "summary"),
            ("successMsg += `文件名称: <strong>${escapeHtml(data.original_filename)}</strong><br>`;", "successMsg += `${escapeHtml(t('knowledge.field.file_name'))}: <strong>${escapeHtml(data.original_filename)}</strong><br>`;", "file_name"),
        ],
        "uploadFile": [
            ("resultDiv.innerHTML = '<div class=\"alert alert-error\">请选择要上传的文件</div>';", "resultDiv.innerHTML = `<div class=\"alert alert-error\">${escapeHtml(t('validation.knowledge_file_required'))}</div>`;", "file_required"),
            ("resultDiv.innerHTML = '<div class=\"alert alert-error\">请先选择可写入的知识库</div>';", "resultDiv.innerHTML = `<div class=\"alert alert-error\">${escapeHtml(t('validation.knowledge_write_target_required'))}</div>`;", "target_required"),
            ("resultDiv.innerHTML = '<div class=\"alert alert-info\">正在上传资料...</div>';", "resultDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.knowledge_uploading'))}</div>`;", "uploading"),
            ("resultDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${data.detail}</div>`;", "if (data.detail) console.error('File upload failed:', data.detail);\n                    const message = currentLang === 'zh' && data.detail ? data.detail : t('error.knowledge_upload_failed');\n                    resultDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "response_error"),
            ("resultDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${error.message}</div>`;", "console.error('File upload failed:', error);\n                const message = currentLang === 'zh' && error.message ? error.message : t('error.knowledge_upload_failed');\n                resultDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "catch"),
        ],
        "getKnowledgeInfo": [
            ("infoDiv.innerHTML = '<div class=\"alert alert-error\">请先选择一个资料库</div>';", "infoDiv.innerHTML = `<div class=\"alert alert-error\">${escapeHtml(t('validation.knowledge_read_target_required'))}</div>`;", "target_required"),
            ("infoDiv.innerHTML = '<div class=\"alert alert-info\">加载中...</div>';", "infoDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.loading'))}</div>`;", "loading"),
            ("<span class=\"info-label\">知识库 ID：</span>", "<span class=\"info-label\">${escapeHtml(t('knowledge.info.id'))}:</span>", "id"),
            ("<span class=\"info-label\">知识库名称：</span>", "<span class=\"info-label\">${escapeHtml(t('knowledge.info.name'))}:</span>", "name"),
            ("<span class=\"info-label\">范围：</span>", "<span class=\"info-label\">${escapeHtml(t('knowledge.info.scope'))}:</span>", "scope"),
            ("<span class=\"info-label\">内部集合：</span>", "<span class=\"info-label\">${escapeHtml(t('knowledge.info.internal_collection'))}:</span>", "collection"),
            ("<span class=\"info-label\">说明：</span>", "<span class=\"info-label\">${escapeHtml(t('knowledge.info.description'))}:</span>", "description"),
            ("infoDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${data.detail}</div>`;", "if (data.detail) console.error('Knowledge base info failed:', data.detail);\n                    const message = currentLang === 'zh' && data.detail ? data.detail : t('error.knowledge_info_failed');\n                    infoDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "response_error"),
            ("infoDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${error.message}</div>`;", "console.error('Knowledge base info failed:', error);\n                const message = currentLang === 'zh' && error.message ? error.message : t('error.knowledge_info_failed');\n                infoDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "catch"),
        ],
        "getKnowledgeBaseScopeLabel": [
            ("if (scope === 'public') return '公共';\n            if (scope === 'user') return '我的';\n            if (scope === 'legacy_admin_only') return '迁移待确认';\n            return scope || '未知';", "if (scope === 'public') return t('knowledge.scope.public');\n            if (scope === 'user') return t('knowledge.scope.user');\n            if (scope === 'legacy_admin_only') return t('knowledge.scope.legacy_admin_only');\n            return scope || t('knowledge.scope.unknown');", "scope_labels"),
        ],
        "formatKnowledgeBaseLabel": [
            ("const countText = count === null ? '资料数未加载' : `${count}条资料`;", "const countText = count === null\n                ? t('knowledge.document_count.not_loaded')\n                : t('knowledge.document_count.loaded', { count });", "document_count"),
        ],
        "loadMappings": [
            ("mappingsDiv.innerHTML = '<div class=\"alert alert-info\">加载中...</div>';", "mappingsDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.loading'))}</div>`;", "loading"),
            ("mappingsDiv.innerHTML = '<div class=\"alert alert-info\">暂无名称对照记录</div>';", "mappingsDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('knowledge.mapping.empty'))}</div>`;", "empty"),
            ("共 ${data.total_count} 条名称对照", "${escapeHtml(t('knowledge.mapping.count', { count: data.total_count }))}", "count"),
            ("const docCountText = mapping.document_count !== null ? `${mapping.document_count} 条资料` : '未加载';", "const docCountText = mapping.document_count !== null\n                            ? t('knowledge.document_count.loaded', { count: mapping.document_count })\n                            : t('knowledge.document_count.not_loaded');", "documents"),
            ("📝 ${escapeHtml(mapping.original_name)}", "📝 ${mapping.display_name ? escapeHtml(mapping.display_name) : escapeHtml(mapping.original_name)}", "display_name"),
            ("范围: ${escapeHtml(mapping.scope || '')}", "${escapeHtml(t('knowledge.info.scope'))}: ${mapping.original_collection_name ? escapeHtml(mapping.original_collection_name) : escapeHtml(mapping.original_name)}", "original_collection"),
            ("➜ ${mapping.normalized_name}", "➜ ${mapping.internal_collection_name ? escapeHtml(mapping.internal_collection_name) : escapeHtml(mapping.normalized_name)}", "internal_collection"),
            ("mappingsDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${data.detail}</div>`;", "if (data.detail) console.error('Knowledge mapping load failed:', data.detail);\n                    const message = currentLang === 'zh' && data.detail ? data.detail : t('error.knowledge_mapping_failed');\n                    mappingsDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "response_error"),
            ("mappingsDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${error.message}</div>`;", "console.error('Knowledge mapping load failed:', error);\n                const message = currentLang === 'zh' && error.message ? error.message : t('error.knowledge_mapping_failed');\n                mappingsDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "catch"),
        ],
        "loadUploadAudit": [
            ("auditDiv.innerHTML = '<div class=\"alert alert-info\">加载中...</div>';", "auditDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.loading'))}</div>`;", "loading"),
            ("auditDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${data.detail}</div>`;", "if (data.detail) console.error('Upload audit load failed:', data.detail);\n                    const message = currentLang === 'zh' && data.detail ? data.detail : t('error.knowledge_audit_failed');\n                    auditDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "response_error"),
            ("auditDiv.innerHTML = '<div class=\"alert alert-info\">暂无上传审计记录</div>';", "auditDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('knowledge.audit.empty'))}</div>`;", "empty"),
            ("最近 ${data.records.length} 条上传记录", "${escapeHtml(t('knowledge.audit.recent_count', { count: data.records.length }))}", "count"),
            ("const fileName = record.original_filename || record.source_file_path || record.source_directory_path || '文本资料';", "const fileName = record.original_filename || record.source_file_path || record.source_directory_path || t('knowledge.audit.text_material');", "text_material"),
            ("const collectionName = record.display_name || record.original_collection_name || record.collection_name || '未关联资料库';", "const collectionName = record.display_name || record.original_collection_name || record.collection_name || t('knowledge.value.no_knowledge_base');", "no_kb"),
            ("状态: ${escapeHtml(record.status || 'unknown')}<br>\n                                类型: ${escapeHtml(record.usage_type || 'upload')}<br>\n                                资料库: ${escapeHtml(collectionName)}<br>\n                                范围: ${escapeHtml(record.scope || '')}<br>\n                                时间: ${escapeHtml(record.uploaded_at || '')}", "${escapeHtml(t('knowledge.audit.status'))}: ${escapeHtml(record.status || 'unknown')}<br>\n                                ${escapeHtml(t('knowledge.audit.type'))}: ${escapeHtml(record.usage_type || 'upload')}<br>\n                                ${escapeHtml(t('knowledge.audit.knowledge_base'))}: ${escapeHtml(collectionName)}<br>\n                                ${escapeHtml(t('knowledge.audit.scope'))}: ${escapeHtml(record.scope || '')}<br>\n                                ${escapeHtml(t('knowledge.audit.time'))}: ${escapeHtml(record.uploaded_at || '')}", "fields"),
            ("错误: ${escapeHtml(record.error_message)}", "${escapeHtml(t('knowledge.audit.error'))}: ${escapeHtml(record.error_message)}", "error_label"),
            ("auditDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${error.message}</div>`;", "console.error('Upload audit load failed:', error);\n                const message = currentLang === 'zh' && error.message ? error.message : t('error.knowledge_audit_failed');\n                auditDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "catch"),
        ],
        "clearKnowledgeBase": [
            ("alert('请先选择要清空的知识库');", "alert(t('validation.knowledge_manage_target_required'));", "target_required"),
            ("confirm(`确定要清空资料库“${kb.display_name}”吗？此操作不可恢复！`)", "confirm(t('confirm.knowledge_clear', { name: kb.display_name }))", "confirm"),
            ("alert('✓ 资料库已清空');", "alert(t('toast.knowledge_cleared'));", "success"),
            ("alert(`✗ 清空失败: ${data.detail}`);", "if (data.detail) console.error('Knowledge base clear failed:', data.detail);\n                    alert(currentLang === 'zh' && data.detail ? data.detail : t('error.knowledge_clear_failed'));", "response_error"),
            ("alert(`✗ 清空失败: ${error.message}`);", "console.error('Knowledge base clear failed:', error);\n                alert(currentLang === 'zh' && error.message ? error.message : t('error.knowledge_clear_failed'));", "catch"),
        ],
        "deleteKnowledgeBaseCollection": [
            ("alert('请先选择要删除的知识库');", "alert(t('validation.knowledge_manage_target_required'));", "target_required"),
            ("confirm(\n                `确定要删除资料库“${kb.display_name}”吗？\\n\\n此操作会移除资料库本身，并从资料库列表中消失；已关联该资料库的多智能体审查需要重新选择资料库。`\n            )", "confirm(t('confirm.knowledge_delete', { name: kb.display_name }))", "confirm"),
            ("prompt(`请再次输入资料库名称以确认删除：${kb.display_name}`)", "prompt(t('confirm.knowledge_delete_name', { name: kb.display_name }))", "name_prompt"),
            ("alert('资料库名称不一致，已取消删除');", "alert(t('validation.knowledge_delete_name_mismatch'));", "name_mismatch"),
            ("alert(`✓ 资料库已删除：${kb.display_name}`);", "alert(t('toast.knowledge_deleted', { name: kb.display_name }));", "success"),
            ("document.getElementById('knowledgeInfo').innerHTML = '<div class=\"alert alert-info\">资料库已删除，请重新选择资料库查看状态</div>';", "document.getElementById('knowledgeInfo').innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.knowledge_deleted'))}</div>`;", "info_status"),
            ("document.getElementById('docBrowser').innerHTML = '<div class=\"alert alert-info\">资料库已删除，请重新加载资料库列表</div>';", "document.getElementById('docBrowser').innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.knowledge_deleted'))}</div>`;", "browser_status"),
            ("alert(`✗ 删除失败: ${data.detail}`);", "if (data.detail) console.error('Knowledge base deletion failed:', data.detail);\n                    alert(currentLang === 'zh' && data.detail ? data.detail : t('error.knowledge_delete_failed'));", "response_error"),
            ("alert(`✗ 删除失败: ${error.message}`);", "console.error('Knowledge base deletion failed:', error);\n                alert(currentLang === 'zh' && error.message ? error.message : t('error.knowledge_delete_failed'));", "catch"),
        ],
        "loadDocuments": [
            ("browserDiv.innerHTML = '<div class=\"alert alert-error\">请先选择一个资料库</div>';", "browserDiv.innerHTML = `<div class=\"alert alert-error\">${escapeHtml(t('validation.knowledge_read_target_required'))}</div>`;", "target_required"),
            ("browserDiv.innerHTML = '<div class=\"alert alert-info\">加载中...</div>';", "browserDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.loading'))}</div>`;", "loading"),
            ("browserDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${data.detail}</div>`;", "if (data.detail) console.error('Document list load failed:', data.detail);\n                    const message = currentLang === 'zh' && data.detail ? data.detail : t('error.knowledge_documents_failed');\n                    browserDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "response_error"),
            ("<span class=\"doc-stat-label\">资料库：</span>", "<span class=\"doc-stat-label\">${escapeHtml(t('knowledge.documents.knowledge_base'))}:</span>", "kb_label"),
            ("<span class=\"doc-stat-label\">资料总数：</span>", "<span class=\"doc-stat-label\">${escapeHtml(t('knowledge.documents.total'))}:</span>", "total"),
            ("<span class=\"doc-stat-label\">显示：</span>", "<span class=\"doc-stat-label\">${escapeHtml(t('knowledge.documents.showing'))}:</span>", "showing"),
            ("browserDiv.innerHTML = '<div class=\"alert alert-info\">该资料库暂无资料</div>';", "browserDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('knowledge.documents.empty'))}</div>`;", "empty"),
            ("<div class=\"doc-id\">资料编号: ${doc.id}</div>", "<div class=\"doc-id\">${escapeHtml(t('knowledge.documents.document_id'))}: ${escapeHtml(doc.id)}</div>", "doc_id"),
            (">查看</button>", ">${escapeHtml(t('knowledge.action.view'))}</button>", "view"),
            (">删除</button>", ">${escapeHtml(t('knowledge.action.delete'))}</button>", "delete"),
            ("browserDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${error.message}</div>`;", "console.error('Document list load failed:', error);\n                const message = currentLang === 'zh' && error.message ? error.message : t('error.knowledge_documents_failed');\n                browserDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "catch"),
        ],
        "viewDocument": [
            ("modalBody.innerHTML = '<div class=\"alert alert-info\">加载中...</div>';", "modalBody.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.loading'))}</div>`;", "loading"),
            ("modalBody.innerHTML = `<div class=\"alert alert-error\">✗ ${data.detail}</div>`;", "if (data.detail) console.error('Document load failed:', data.detail);\n                    const message = currentLang === 'zh' && data.detail ? data.detail : t('error.knowledge_document_failed');\n                    modalBody.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "response_error"),
            ("<div class=\"doc-id\">资料编号: ${doc.id}</div>", "<div class=\"doc-id\">${escapeHtml(t('knowledge.documents.document_id'))}: ${escapeHtml(doc.id)}</div>", "doc_id"),
            ("<strong style=\"font-size: 13px; color: #6c757d;\">资料属性：</strong>", "<strong style=\"font-size: 13px; color: #6c757d;\">${escapeHtml(t('knowledge.documents.metadata'))}:</strong>", "metadata"),
            ("modalBody.innerHTML = `<div class=\"alert alert-error\">✗ ${error.message}</div>`;", "console.error('Document load failed:', error);\n                const message = currentLang === 'zh' && error.message ? error.message : t('error.knowledge_document_failed');\n                modalBody.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(message)}</div>`;", "catch"),
        ],
        "deleteCurrentDoc": [
            ("confirm('确定要删除这条资料吗？此操作不可恢复！')", "confirm(t('confirm.document_delete'))", "confirm"),
            ("alert('✓ 资料已删除');", "alert(t('toast.document_deleted'));", "success"),
            ("alert(`✗ 删除失败: ${data.detail}`);", "if (data.detail) console.error('Document deletion failed:', data.detail);\n                    alert(currentLang === 'zh' && data.detail ? data.detail : t('error.document_delete_failed'));", "response_error"),
            ("alert(`✗ 删除失败: ${error.message}`);", "console.error('Document deletion failed:', error);\n                alert(currentLang === 'zh' && error.message ? error.message : t('error.document_delete_failed'));", "catch"),
        ],
        "deleteDocumentById": [
            ("confirm('确定要删除这条资料吗？此操作不可恢复！')", "confirm(t('confirm.document_delete'))", "confirm"),
            ("alert('✓ 资料已删除');", "alert(t('toast.document_deleted'));", "success"),
            ("alert(`✗ 删除失败: ${data.detail}`);", "if (data.detail) console.error('Document deletion failed:', data.detail);\n                    alert(currentLang === 'zh' && data.detail ? data.detail : t('error.document_delete_failed'));", "response_error"),
            ("alert(`✗ 删除失败: ${error.message}`);", "console.error('Document deletion failed:', error);\n                alert(currentLang === 'zh' && error.message ? error.message : t('error.document_delete_failed'));", "catch"),
        ],
        "updateBatchDeleteButton": [
            ("btn.textContent = `删除选中资料 (${selectedDocIds.size})`;", "btn.textContent = t('knowledge.action.delete_selected', { count: selectedDocIds.size });", "label"),
        ],
        "batchDeleteDocuments": [
            ("alert('请先选择要删除的资料');", "alert(t('validation.documents_required'));", "documents_required"),
            ("alert('请先选择要管理的知识库');", "alert(t('validation.knowledge_manage_target_required'));", "target_required"),
            ("confirm(`确定要删除选中的 ${selectedDocIds.size} 条资料吗？此操作不可恢复！`)", "confirm(t('confirm.documents_batch_delete', { count: selectedDocIds.size }))", "confirm"),
            ("alert(`✓ 批量删除完成\\n成功: ${data.success_count}\\n失败: ${data.failed_count}\\n剩余资料: ${data.remaining_count}`);", "alert(t('toast.documents_batch_deleted', { success: data.success_count, failed: data.failed_count, remaining: data.remaining_count }));", "success"),
            ("alert(`✗ 批量删除失败: ${data.detail}`);", "if (data.detail) console.error('Batch document deletion failed:', data.detail);\n                    alert(currentLang === 'zh' && data.detail ? data.detail : t('error.documents_batch_delete_failed'));", "response_error"),
            ("alert(`✗ 批量删除失败: ${error.message}`);", "console.error('Batch document deletion failed:', error);\n                alert(currentLang === 'zh' && error.message ? error.message : t('error.documents_batch_delete_failed'));", "catch"),
        ],
        "renderKnowledgeBaseGroups": [
            ("${getKnowledgeBaseScopeLabel(kb.scope)} · ${escapeHtml(kb.document_count ?? '资料数未加载')}", "${getKnowledgeBaseScopeLabel(kb.scope)} · ${escapeHtml(kb.document_count == null ? t('knowledge.document_count.not_loaded') : t('knowledge.document_count.loaded', { count: kb.document_count }))}", "document_count"),
            (">管理</button>", ">${escapeHtml(t('knowledge.action.manage'))}</button>", "manage"),
            ("共 ${collections.length} 个可见知识库", "${escapeHtml(t('knowledge.group.visible_count', { count: collections.length }))}", "visible_count"),
            ("${renderGroup('公共知识库', publicCollections, '暂无公共知识库', true)}", "${renderGroup(t('knowledge.group.public_title'), publicCollections, t('knowledge.group.public_empty'), true)}", "public_group"),
            ("${renderGroup('我的知识库', myCollections, '暂无我的知识库，请先创建或联系管理员')}", "${renderGroup(t('knowledge.group.mine_title'), myCollections, t('knowledge.group.mine_empty'))}", "mine_group"),
            ("${isAdminUser() ? '<div class=\"alert alert-info\">公共知识库管理：管理员可创建、上传、清空或删除公共知识库。</div>' : ''}", "${isAdminUser() ? `<div class=\"alert alert-info\">${escapeHtml(t('knowledge.group.public_admin_notice'))}</div>` : ''}", "admin_notice"),
        ],
        "loadAllCollections": [
            ("listDiv.innerHTML = '<div class=\"alert alert-info\">加载中...</div>';", "listDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('status.loading'))}</div>`;", "loading"),
            ("throw new Error(`JSON解析失败: ${parseError.message}`);", "console.error('Collection JSON parse failed:', parseError);\n                    throw new Error(t('error.knowledge_list_failed'));", "parse_error"),
            ("listDiv.innerHTML = '<div class=\"alert alert-info\">暂无资料库，请先上传法律资料</div>';", "listDiv.innerHTML = `<div class=\"alert alert-info\">${escapeHtml(t('knowledge.group.empty'))}</div>`;", "empty"),
            ("const errorMsg = data.detail || data.message || '未知错误';\n                    listDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${errorMsg}<br><small>状态码: ${response.status}</small></div>`;", "const detail = data.detail || data.message;\n                    if (detail) console.error('Collection list load failed:', detail);\n                    const errorMsg = currentLang === 'zh' && detail ? detail : t('error.knowledge_list_failed');\n                    listDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(errorMsg)}</div>`;", "response_error"),
            ("listDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${error.message}<br><small>请检查服务器是否正常运行</small></div>`;", "const errorMsg = currentLang === 'zh' && error.message ? error.message : t('error.knowledge_list_failed');\n                listDiv.innerHTML = `<div class=\"alert alert-error\">✗ ${escapeHtml(errorMsg)}</div>`;", "catch"),
        ],
        "updateKnowledgeBaseSelects": [
            ("? '<option value=\"\">不指定单个知识库</option>'\n                        : '<option value=\"\">-- 请选择资料库 --</option>'", "? `<option value=\"\">${escapeHtml(t('knowledge.selector.none'))}</option>`\n                        : `<option value=\"\">${escapeHtml(t('knowledge.selector.readable_placeholder'))}</option>`", "readable"),
            ("fillSelect(selectId, collections.filter(canWriteKnowledgeBase), '<option value=\"\">-- 请选择可写入知识库 --</option>');", "fillSelect(selectId, collections.filter(canWriteKnowledgeBase), `<option value=\"\">${escapeHtml(t('knowledge.selector.writable_placeholder'))}</option>`);", "writable"),
            ("fillSelect(selectId, collections.filter(canManageKnowledgeBase), '<option value=\"\">-- 请选择可管理知识库 --</option>');", "fillSelect(selectId, collections.filter(canManageKnowledgeBase), `<option value=\"\">${escapeHtml(t('knowledge.selector.manageable_placeholder'))}</option>`);", "manageable"),
            ("console.log(`已更新知识库下拉选择框，数量: ${collections.length}`);", "console.log(t('knowledge.status.selects_updated', { count: collections.length }));", "updated"),
        ],
        "selectKnowledgeBase": [
            ("alert(`已选择知识库: ${kb.display_name}`);", "alert(t('knowledge.status.selected', { name: kb.display_name }));", "selected"),
        ],
        "syncKnowledgeBaseSelection": [
            ("console.log(`已同步知识库选择: ${kbId}`);", "console.log('Knowledge base selection synced:', kbId);", "synced"),
        ],
    }
    for function_name, function_rules in rules.items():
        for old, new, suffix in function_rules:
            content = _replace_js_function_text(
                content,
                function_name,
                old,
                new,
                f"p1b.knowledge.{function_name}.{suffix}",
            )
    return content


def _apply_p1b_dynamic_rerender(content: str) -> str:
    """注入唯一语言切换重绘入口，并保留用户与业务状态。"""
    content = replace_once(
        content,
        "        function displayCollaborationResult(data) {",
        "        function displayCollaborationResult(data, scroll = true) {",
        "p1b.rerender.result.optional_scroll",
    )
    content = replace_once(
        content,
        "            document.getElementById('collaborationResultCard').scrollIntoView({ behavior: 'smooth', block: 'start' });",
        "            if (scroll) {\n                document.getElementById('collaborationResultCard').scrollIntoView({ behavior: 'smooth', block: 'start' });\n            }",
        "p1b.rerender.result.scroll_guard",
    )

    rerender_runtime = """        function captureKnowledgeSelectValues() {
            const selectIds = [
                'browserCollection',
                'multiAgentKnowledgeBase',
                'uploadKbSelect',
                'fileUploadKbSelect',
                'infoCollection',
                'manageKbSelect'
            ];
            return Object.fromEntries(selectIds.map(selectId => {
                const select = document.getElementById(selectId);
                return [selectId, select ? select.value : ''];
            }));
        }

        function restoreKnowledgeSelectValues(values) {
            Object.entries(values || {}).forEach(([selectId, value]) => {
                const select = document.getElementById(selectId);
                if (select && Array.from(select.options).some(option => option.value === value)) {
                    select.value = value;
                }
            });
        }

        async function rerenderVisibleLocalizedState() {
            updateLegalTaskSection();
            renderLegalAgentSelection();
            renderLegalAgentGapWarning();

            if (currentCollaborationResult) {
                displayCollaborationResult(currentCollaborationResult, false);
            }

            const selectedValues = captureKnowledgeSelectValues();
            renderKnowledgeBaseGroups(knowledgeBases || []);
            updateKnowledgeBaseSelects(knowledgeBases || []);
            restoreKnowledgeSelectValues(selectedValues);

            const preservedSelectedAgentNames = [...selectedLegalAgentNames];
            await loadCollaborationData();
            selectedLegalAgentNames = sortLegalAgentNames(preservedSelectedAgentNames);
            enforceRequiredLegalAgents();
            renderLegalAgentSelection();
            renderLegalAgentGapWarning();
        }

        document.addEventListener('languagechange', () => {
            void rerenderVisibleLocalizedState();
        });

"""
    content = replace_once(
        content,
        "        // 加载团队和模式信息\n",
        rerender_runtime + "        // 加载团队和模式信息\n",
        "p1b.rerender.runtime",
    )
    return content


def render_global_html(index_content: str) -> str:
    """在内存中将国内版 HTML 渲染为国际版 HTML。"""
    content = index_content

    # ============================================================
    # 1. 修改 head 部分
    # ============================================================
    content = content.replace('<html lang="zh-CN">', '<html lang="en">')
    content = content.replace(
        "<title>紫微星 ChineseDragon-法律生产力操作系统</title>",
        "<title>Gaia International World Model Legal Intelligence System</title>"
    )

    # ============================================================
    # 2. 修改登录页
    # ============================================================
    content = content.replace(
        '<h2>登录紫微星 ChineseDragon-法律生产力操作系统</h2>',
        '<h2 data-i18n="login_title">Login to Gaia International World Model Legal Intelligence System</h2>'
    )
    content = content.replace(
        '<p>请使用已开通的账号进入合同审查、知识库和多智能体工作台。</p>',
        '<p data-i18n="login_subtitle">Please use your registered account to access the contract review, knowledge base, and multi-agent workstation.</p>'
    )
    content = content.replace(
        '<label for="loginUsername">用户名</label>',
        '<label for="loginUsername" data-i18n="login_username">Username</label>'
    )
    content = content.replace(
        '<label for="loginPassword">密码</label>',
        '<label for="loginPassword" data-i18n="login_password">Password</label>'
    )
    content = content.replace(
        '<button id="loginSubmitBtn" class="btn btn-primary" type="submit" style="width: 100%;">登录</button>',
        '<button id="loginSubmitBtn" class="btn btn-primary" type="submit" style="width: 100%;" data-i18n="login_button">Login</button>'
    )

    # ============================================================
    # 3. 修改 Header
    # ============================================================
    content = content.replace(
        '<h1>紫微星 ChineseDragon-法律生产力操作系统</h1>',
        '<h1 data-i18n="header_title">Gaia International World Model Legal Intelligence System</h1>'
    )
    content = content.replace(
        '<span id="authUserLabel">已登录</span>',
        '<span id="authUserLabel" data-i18n="user_label">Logged In</span>'
    )
    content = content.replace(
        '<button class="btn" type="button" onclick="logoutCurrentUser()">退出</button>',
        '<button class="btn" type="button" onclick="logoutCurrentUser()" data-i18n="logout_button">Logout</button>\n' + LANG_SWITCHER_HTML
    )

    # ============================================================
    # 4. 修改 Tabs
    # ============================================================
    content = content.replace(
        '<button class="tab active" data-tab="multiagent" onclick="switchTab(\'multiagent\')">法律多智能体问答</button>',
        '<button class="tab active" data-tab="multiagent" onclick="switchTab(\'multiagent\')" data-i18n="tab_multiagent">Multi-Agent System</button>'
    )
    content = content.replace(
        '<button class="tab" data-tab="knowledge" onclick="switchTab(\'knowledge\')">知识库管理</button>',
        '<button class="tab" data-tab="knowledge" onclick="switchTab(\'knowledge\')" data-i18n="tab_knowledge">Knowledge Base</button>'
    )

    # P1b 共享和动态文本必须先于下方旧宽松中文替换处理。
    content = _apply_p1b_shared_i18n(content)
    content = _apply_p1b_contract_parse_i18n(content)
    content = _apply_p1b_collaboration_stream_i18n(content)
    content = _apply_p1b_collaboration_result_i18n(content)
    content = _apply_p1b_collaboration_report_i18n(content)
    content = _apply_p1b_knowledge_i18n(content)
    content = _apply_p1b_dynamic_rerender(content)

    # ============================================================
    # 5. 修改 Multi-Agent Tab 中的中文文本
    # ============================================================
    replacements = [
        ('<label>协作团队：</label>', '<label data-i18n="team_label">Team:</label>'),
        ('<label>协作模式：</label>', '<label data-i18n="mode_label">Mode:</label>'),
        ('<label>法律任务：</label>', '<label data-i18n="legal_task_label">Legal Task:</label>'),
        ('<label>知识库：</label>', '<label data-i18n="kb_label">Knowledge Base:</label>'),
        ('包含公共知识库', '<span data-i18n="include_public_kb">Include Public KB</span>'),
        ('<label>合同文件：</label>', '<label data-i18n="contract_file_label">Contract File:</label>'),
        ('<label>服务器路径：</label>', '<label data-i18n="server_path_label">Server Path:</label>'),
        ('解析合同', '<span data-i18n="parse_contract_btn">Parse Contract</span>'),
        ('<span style="font-weight: 600; color: #495057;">快速任务：</span>', '<span style="font-weight: 600; color: #495057;" data-i18n="quick_tasks_label">Quick Tasks:</span>'),
        ('placeholder="请输入任务描述..."', 'placeholder="" data-i18n-placeholder="task_input_placeholder"'),
        ('开始多智能体审查', '<span data-i18n="start_collaboration_btn">Start Multi-Agent Review</span>'),
        ('恢复默认', '<span data-i18n="restore_defaults_btn">Restore Defaults</span>'),
        ('<div style="font-weight: 600; margin-bottom: 8px;">法律智能体选择</div>', '<div style="font-weight: 600; margin-bottom: 8px;" data-i18n="legal_agent_selection_label">Legal Agent Selection</div>'),
        ('<span style="margin: 0 8px; color: #6c757d;">或</span>', '<span style="margin: 0 8px; color: #6c757d;" data-i18n="or_label">or</span>'),
    ]
    for old, new in replacements:
        content = content.replace(old, new)

    # ============================================================
    # 6. 修改 Knowledge Base Tab 中的中文文本
    # ============================================================
    kb_replacements = [
        ('<h3>创建用户知识库</h3>', '<h3 data-i18n="kb_create_user_title">Create User Knowledge Base</h3>'),
        ('<h3>管理员：创建公共知识库</h3>', '<h3 data-i18n="kb_create_public_title">Admin: Create Public Knowledge Base</h3>'),
        ('<h3>上传文本</h3>', '<h3 data-i18n="kb_upload_text_title">Upload Text</h3>'),
        ('<h3>文件上传</h3>', '<h3 data-i18n="kb_upload_file_title">File Upload</h3>'),
        ('<h3>知识库信息</h3>', '<h3 data-i18n="kb_info_title">Knowledge Base Info</h3>'),
        ('<h3>所有知识库列表</h3>', '<h3 data-i18n="kb_list_title">All Knowledge Bases</h3>'),
        ('<h3>上传审计</h3>', '<h3 data-i18n="kb_audit_title">Upload Audit</h3>'),
        ('<h3>知识库管理</h3>', '<h3 data-i18n="kb_manage_title">Knowledge Base Management</h3>'),
        ('<h3>文档浏览器</h3>', '<h3 data-i18n="kb_doc_browser_title">Document Browser</h3>'),
        ('placeholder="知识库名称"', 'placeholder="" data-i18n-placeholder="kb_name_placeholder"'),
        ('placeholder="描述（可选）"', 'placeholder="" data-i18n-placeholder="kb_desc_placeholder"'),
        ('>创建</button>', ' data-i18n="kb_create_btn">Create</button>'),
        ('>上传</button>', ' data-i18n="kb_upload_btn">Upload</button>'),
        ('<option value="">选择知识库</option>', '<option value="" data-i18n="kb_select_placeholder">Select Knowledge Base</option>'),
        ('刷新列表', '<span data-i18n="kb_refresh_btn">Refresh</span>'),
        ('删除选中', '<span data-i18n="kb_delete_btn">Delete Selected</span>'),
        ('<span>资料详情</span>', '<span data-i18n="doc_modal_title">Document Details</span>'),
    ]
    for old, new in kb_replacements:
        if old in content:
            content = content.replace(old, new)

    # ============================================================
    # 7. 修改 JS 中的中文文本（alert、状态消息等）
    # ============================================================
    js_replacements = [
        ("alert('请输入任务描述')", "alert(t('alert_enter_task'))"),
        ("alert('请选择协作团队')", "alert(t('alert_select_team'))"),
        ("alert('法律智能体策略尚未加载完成，请稍后重试')", "alert(t('alert_policy_not_ready'))"),
        ("'协作失败: ' + error.message", "t('alert_collaboration_failed') + error.message"),
        ("'审查中...'", "t('reviewing_text')"),
        ("'正在初始化法律多智能体审查...'", "t('initializing_text')"),
        ("'法律专家团队已组建，开始审查...'", "t('status_team_ready')"),
        ("'正在准备法律多智能体审查...'", "t('status_preparing')"),
        ("'已登录'", "t('user_label')"),
    ]
    for old, new in js_replacements:
        if old in content:
            content = content.replace(old, new)

    content = content.replace(
        "const roleLabel = currentUser.role === 'admin' ? '管理员' : '用户';",
        "const roleLabel = currentUser.role === 'admin' ? 'Admin' : 'User';"
    )

    # ============================================================
    # 8. 注入 i18n JavaScript
    # ============================================================
    i18n_js = generate_i18n_js()
    content = content.replace(
        "    <script>\n        const API_BASE",
        "    <script>\n" + i18n_js + "\n        const API_BASE"
    )

    # ============================================================
    # 9. P1b Multi-Agent 加载与选择状态受控替换
    # ============================================================
    content = _apply_p1b_multiagent_selection_i18n(content)

    # ============================================================
    # 10. 修改 LEGAL_TASK_TEMPLATES
    # ============================================================
    task_name_replacements = [
        ("name: '合同审查'", "name: 'Contract Review'"),
        ("name: '合同风险识别'", "name: 'Risk Identification'"),
        ("name: '修改建议与替代条款'", "name: 'Revision Suggestions'"),
        ("name: '法律依据检索'", "name: 'Legal Research'"),
        ("name: '合规风险分析'", "name: 'Compliance Analysis'"),
        ("name: '审查结论摘要'", "name: 'Review Summary'"),
        ("name: '法律文书生成'", "name: 'Legal Document Generation'"),
        ("name: '红线比对'", "name: 'Redline Comparison'"),
        ("name: '法务审批流建议'", "name: 'Approval Flow Suggestion'"),
    ]
    for old, new in task_name_replacements:
        content = content.replace(old, new)

    # ============================================================
    # 11. 添加语言切换器样式
    # ============================================================
    lang_style = """
        .lang-switcher {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .lang-switcher select {
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid rgba(255,255,255,0.3);
            background: rgba(255,255,255,0.15);
            color: white;
            font-size: 13px;
            cursor: pointer;
            outline: none;
        }
        .lang-switcher select option {
            color: #333;
            background: white;
        }
        .lang-switcher select:focus {
            border-color: rgba(255,255,255,0.6);
        }"""
    
    content = content.replace(
        "        .btn:disabled {",
        lang_style + "\n        .btn:disabled {"
    )

    # ============================================================
    # 12. 全面清理残留中文文本
    # ============================================================
    content = _clean_remaining_chinese(content)

    return content


def build_global_html():
    """构建国际版 HTML，并在渲染成功后一次写入输出文件。"""
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index_content = f.read()

    content = render_global_html(index_content)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 国际版 HTML 已生成: {OUTPUT_PATH}")
    print(f"   文件大小: {len(content)} 字符")
    print(f"   语言支持: 中文 / English / Русский (默认 English)")


if __name__ == "__main__":
    build_global_html()
