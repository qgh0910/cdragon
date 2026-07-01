#!/usr/bin/env python3
"""
生成国际版前端 HTML：盖亚国际世界模型法律智能体系统
基于 index.html，添加三语支持（中文/英文/俄语，默认英文）
全面清理所有中文文本，替换为英文。
"""
import re

INDEX_PATH = "src/shuyixiao_agent/static/index.html"
OUTPUT_PATH = "src/shuyixiao_agent/static/global.html"

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
        "zh": "多智能体系统",
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


# ============================================================
# 生成 i18n JavaScript 代码
# ============================================================
def generate_i18n_js():
    """生成 i18n 字典的 JavaScript 代码"""
    import json
    return f"""        // ==================== i18n Internationalization ====================
        const I18N = {json.dumps(I18N, ensure_ascii=False, indent=12)};
        
        let currentLang = localStorage.getItem('gaia_lang') || 'en';
        
        function t(key) {{
            const entry = I18N[key];
            if (!entry) return key;
            return entry[currentLang] || entry['en'] || key;
        }}
        
        function setLanguage(lang) {{
            currentLang = lang;
            localStorage.setItem('gaia_lang', lang);
            applyTranslations();
        }}
        
        function applyTranslations() {{
            // Update all elements with data-i18n attribute
            document.querySelectorAll('[data-i18n]').forEach(el => {{
                const key = el.getAttribute('data-i18n');
                const translated = t(key);
                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {{
                    el.placeholder = translated;
                }} else if (el.tagName === 'OPTION') {{
                    el.textContent = translated;
                }} else {{
                    el.textContent = translated;
                }}
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
                        <option value="en">English</option>
                        <option value="zh">中文</option>
                        <option value="ru">Русский</option>
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


def build_global_html():
    """构建国际版 HTML"""
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()

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
    # 9. 修改 AGENT_DISPLAY_NAMES
    # ============================================================
    old_agent_names = """        const AGENT_DISPLAY_NAMES = {
            contract_reviewer: '合同审查协调员',
            clause_risk_analyzer: '条款风险分析师',
            legal_researcher: '法律依据检索员',
            drafting_specialist: '法律文书起草专家',
            compliance_checker: '合规审查专员',
            audit_recorder: '审计留痕记录员'
        };"""
    
    new_agent_names = """        const AGENT_DISPLAY_NAMES = {
            contract_reviewer: 'Contract Review Coordinator',
            clause_risk_analyzer: 'Clause Risk Analyst',
            legal_researcher: 'Legal Researcher',
            drafting_specialist: 'Legal Drafting Specialist',
            compliance_checker: 'Compliance Reviewer',
            audit_recorder: 'Audit Recorder'
        };
        
        function getAgentDisplayName(name) {
            const i18nKey = 'agent_' + name;
            return t(i18nKey) || AGENT_DISPLAY_NAMES[name] || name;
        }"""
    
    content = content.replace(old_agent_names, new_agent_names)
    content = content.replace("AGENT_DISPLAY_NAMES[agent.name] || agent.name", "getAgentDisplayName(agent.name)")
    content = content.replace("AGENT_DISPLAY_NAMES[name] || name", "getAgentDisplayName(name)")

    # ============================================================
    # 10. 修改 LEGAL_TASK_TEMPLATES
    # ============================================================
    task_name_replacements = [
        ("name: '合同审查'", "name: 'Contract Review'"),
        ("description: '完整审查合同风险并输出标准审查报告'", "description: 'Complete contract risk review with standard report'"),
        ("name: '合同风险识别'", "name: 'Risk Identification'"),
        ("description: '只识别合同条款风险和风险等级'", "description: 'Identify clause-level risks and risk levels'"),
        ("name: '修改建议与替代条款'", "name: 'Revision Suggestions'"),
        ("description: '根据合同风险生成修改建议和替代条款'", "description: 'Generate revision suggestions and alternative clauses based on risks'"),
        ("name: '法律依据检索'", "name: 'Legal Research'"),
        ("description: '检索相关法律法规、案例、监管规则和企业知识库'", "description: 'Search relevant laws, cases, regulations and enterprise knowledge bases'"),
        ("name: '合规风险分析'", "name: 'Compliance Analysis'"),
        ("description: '分析合同和业务安排中的监管合规风险'", "description: 'Analyze regulatory compliance risks in contracts and business arrangements'"),
        ("name: '审查结论摘要'", "name: 'Review Summary'"),
        ("description: '输出面向决策的合同审查结论'", "description: 'Output decision-oriented contract review conclusions'"),
        ("name: '法律文书生成'", "name: 'Legal Document Generation'"),
        ("description: '根据事实、诉求和证据生成法律文书初稿'", "description: 'Generate legal document drafts based on facts, claims and evidence'"),
        ("name: '红线比对'", "name: 'Redline Comparison'"),
        ("description: '将合同与企业红线规则或标准模板进行比对'", "description: 'Compare contracts against enterprise redline rules or standard templates'"),
        ("name: '法务审批流建议'", "name: 'Approval Flow Suggestion'"),
        ("description: '根据风险等级和业务场景给出审批流建议'", "description: 'Provide approval flow suggestions based on risk levels and business scenarios'"),
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

    # ============================================================
    # 13. 写入输出文件
    # ============================================================
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 国际版 HTML 已生成: {OUTPUT_PATH}")
    print(f"   文件大小: {len(content)} 字符")
    print(f"   语言支持: 中文 / English / Русский (默认 English)")


if __name__ == "__main__":
    build_global_html()
