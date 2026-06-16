# LPOS 功能需求未实现项检查报告

## 检查范围

参考文件：`法律生产力操作系统LPOS功能需求.md`

当前重点已实现能力：法律合同审查团队协作场景的多智能体配置，以及多智能体 RAG 上下文注入能力。

已检查代码范围：

- `src/shuyixiao_agent/agents/multi_agent_collaboration.py`
- `src/shuyixiao_agent/rag/`
- `src/shuyixiao_agent/agents/memory_agent.py`
- `src/shuyixiao_agent/agents/planning_agent.py`
- `src/shuyixiao_agent/agents/prompt_chaining_agent.py`
- `src/shuyixiao_agent/agents/parallelization_agent.py`
- `src/shuyixiao_agent/agents/reflection_agent.py`
- `src/shuyixiao_agent/web_app.py`
- `examples/17_multi_agent_collaboration_demo.py`

## 总体结论

当前项目已经具备 LPOS 的若干底座能力，但还没有形成完整法律生产力操作系统业务闭环。

已具备或部分具备的能力：

- 多智能体协作框架。
- 法律合同审查团队的 6 个 Agent 角色配置。
- RAG 检索底座，包括文档加载、向量检索、关键词检索、混合检索、重排序、上下文管理。
- 多智能体中 `legal_researcher` 和 `compliance_checker` 的 RAG 上下文注入能力。
- Memory、Planning、Prompt Chaining、Parallelization、Reflection 等可复用 Agentic 模块。
- 通用 FastAPI Web 服务与部分 RAG API。

主要未实现能力：

- LPOS 专属合同文件上传、拍照扫描、合同结构化解析和条款识别。
- 合同风险识别的结构化结果模型和可落库数据结构。
- 标准化合同审查交付物生成器。
- 200 类以上法律文书模板体系和文书类型选择流程。
- 高阶类案检索中的意图识别、查询规划、法律元数据过滤、引用结构化输出。
- 合规规则库、红线规则库、审批规则匹配和实时风险预警。
- 法律多智能体在 Web API 中的完整暴露。
- 审计日志落库、管理员审计查询、私有化日志留存。
- 人类在环确认、补充、接受、忽略、修改建议的交互流程。
- 用户、组织、角色、权限、数据隔离。
- 报告导出、历史任务管理、项目/客户/业务线归档。

## 7.1 合同审核

### 7.1.1 文件上传与解析

状态：部分实现。

当前已有：

- `src/shuyixiao_agent/rag/document_loader.py` 的 `DocumentLoader.load_file()` 支持按扩展名加载文件。
- `src/shuyixiao_agent/rag/document_loader.py` 的 `DocumentLoader.load_pdf()` 支持 PDF。
- `src/shuyixiao_agent/rag/document_loader.py` 的 `DocumentLoader.load_text()` 支持文本。
- `src/shuyixiao_agent/rag/document_loader.py` 的 `DocumentLoader.load_markdown()` 支持 Markdown。
- `src/shuyixiao_agent/rag/document_loader.py` 的 `DocumentLoader.split_documents()` 和 `DocumentLoader.split_text()` 支持文本分片。
- `src/shuyixiao_agent/web_app.py` 已有 RAG 文件/目录/文本上传接口：`/api/rag/upload/file`、`/api/rag/upload/directory`、`/api/rag/upload/texts`。
- `src/shuyixiao_agent/web_app.py` 已有浏览器 multipart 上传接口：`/api/lpos/contracts/upload` 和 `/api/rag/upload/file-from-upload`。
- 前端法律合同审查区和知识库管理区已支持直接选择本地文件上传到服务器。

未实现：

- 常见合同文件格式的完整支持，例如 `.doc`、图片、扫描件。
- 移动端拍照或扫描入口。
- OCR 识别链路。
- 合同文本抽取后的结构化分段。
- 条款识别。
- 合同主体、金额、期限、违约责任、争议解决、保密条款等关键信息结构化抽取。

可复用代码：

- 复用 `DocumentLoader.load_file()` 作为初版合同文本抽取入口。
- 复用 `DocumentLoader.load_pdf()` 支持 PDF 合同。
- 复用 `DocumentLoader.split_documents()` 做初步分段。
- 复用 `RAGAgent.add_documents_from_file()` 将合同或法律知识库写入知识库。
- 复用 `web_app.py` 的 RAG 上传接口模式设计 LPOS 合同上传接口。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/contract_parser.py`。
- 定义 `ContractParser`：
  - `parse_file(file_path) -> ContractParseResult`
  - `extract_text(file_path) -> str`
  - `split_clauses(text) -> List[ContractClause]`
  - `extract_key_fields(text) -> ContractKeyFields`
- 新增结构模型：
  - `ContractClause`：`clause_id`、`title`、`content`、`start_offset`、`end_offset`、`clause_type`
  - `ContractKeyFields`：`parties`、`amount`、`term`、`payment_terms`、`delivery_obligations`、`liability`、`dispute_resolution`、`confidentiality`
  - `ContractParseResult`：`raw_text`、`clauses`、`key_fields`、`file_metadata`
- 对 `.docx` 增加 `python-docx` 加载器。
- 对图片/扫描件预留 `OCRProvider` 接口：`extract_text_from_image(file_path)`。
- Web 层已有 `/api/lpos/contracts/upload` 和 `/api/lpos/contracts/parse`，后续可抽象为独立 `lpos/contract_parser.py` 模块。

## 7.1.2 合同风险识别

状态：部分实现。

当前已有：

- `LegalContractReviewTeam` 中已有 `clause_risk_analyzer` Agent。
- `clause_risk_analyzer` 的 prompt 已包含条款拆分、风险识别、风险分级、风险位置、风险原因和后果说明要求。
- 多智能体协作可通过 `MultiAgentCollaboration.collaborate()` 调用该 Agent。

未实现：

- 风险识别不是结构化结果，而是自然语言输出。
- 没有 `RiskItem` 数据模型。
- 没有风险所在条款 ID、原文位置、字符偏移、页码等字段。
- 没有稳定的高/中/低风险枚举。
- 没有法律风险、商业风险、合规风险等分类枚举。
- 没有风险项与法律依据、案例依据、企业规则之间的结构化关联。
- 没有风险识别结果落库和可查询接口。

可复用代码：

- 复用 `LegalContractReviewTeam.get_agents()` 中的 `clause_risk_analyzer` prompt。
- 复用 `MultiAgentCollaboration.get_agent_response()` 执行风险分析。
- 复用 `RAGAgent.retrieve()` 为风险判断提供依据片段。
- 复用 `ReflectionAgent.reflect_and_improve()` 对风险识别结果做质量复核。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/risk_analyzer.py`。
- 定义 `ContractRiskAnalyzer`：
  - `analyze(contract: ContractParseResult, context: dict) -> ContractRiskAnalysis`
  - `normalize_agent_output(output: str) -> List[RiskItem]`
- 定义 `RiskItem`：
  - `risk_id`
  - `clause_id`
  - `clause_title`
  - `original_text`
  - `position`
  - `risk_level`
  - `risk_type`
  - `risk_reason`
  - `possible_consequence`
  - `legal_basis`
  - `suggested_action`
  - `requires_human_review`
- 在 prompt 中强制 Agent 输出 JSON，并增加 JSON 解析失败时的修复链路。

## 7.1.3 修改建议与替代条款

状态：部分实现。

当前已有：

- `LegalContractReviewTeam` 中已有 `drafting_specialist` Agent。
- `drafting_specialist` prompt 已要求生成修改建议、替代条款和法律文书初稿。

未实现：

- 没有按每个风险项生成修改建议的结构化映射。
- 没有替代条款的数据模型。
- 没有修改理由和法律依据的结构化字段。
- 没有复制、导出或应用修改建议的后端能力。
- 没有修改前后对比能力。

可复用代码：

- 复用 `drafting_specialist` Agent 生成条款文本。
- 复用 `PromptChainingAgent.run_chain()` 拆成“风险项理解 -> 修改方向 -> 替代条款 -> 修改理由 -> 格式化输出”的链式生成。
- 复用 `RAGAgent.retrieve()` 检索合同模板或法律依据。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/drafting.py`。
- 定义 `LegalDraftingService`：
  - `generate_suggestions(risks, evidence) -> List[RevisionSuggestion]`
  - `generate_alternative_clause(risk_item, evidence) -> AlternativeClause`
  - `generate_diff(original_clause, alternative_clause) -> ClauseDiff`
- 定义数据模型：
  - `RevisionSuggestion`：`risk_id`、`suggestion`、`reason`、`legal_basis`、`priority`
  - `AlternativeClause`：`risk_id`、`original_text`、`replacement_text`、`drafting_notes`
  - `ClauseDiff`：`before`、`after`、`change_summary`
- Web 层新增：
  - `/api/lpos/contracts/{task_id}/suggestions`
  - `/api/lpos/contracts/{task_id}/clauses/{risk_id}/alternative`

## 7.1.4 审查结论摘要

状态：部分实现。

当前已有：

- `contract_reviewer` Agent prompt 已要求输出总体风险等级、签署建议和后续处理建议。
- `MultiAgentCollaboration._synthesize_results()` 能整合多个 Agent 的贡献。

未实现：

- 没有标准化 `ReviewConclusion` 模型。
- 没有稳定生成“建议签署、需修改后签署、不建议签署”的枚举字段。
- 没有关键风险点排序算法。
- 没有谈判建议结构化字段。
- 没有把审查结论与风险清单、替代条款、合规结论关联起来。

可复用代码：

- 复用 `contract_reviewer` Agent。
- 复用 `MultiAgentCollaboration._synthesize_results()` 作为初步汇总。
- 复用 `ReflectionAgent.reflect_and_improve()` 对最终审查结论做一致性和完整性检查。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/review_report.py`。
- 定义 `ReviewConclusionBuilder`：
  - `build(risks, suggestions, compliance_result, evidence) -> ReviewConclusion`
- 定义 `ReviewConclusion`：
  - `overall_risk_level`
  - `signing_recommendation`
  - `key_risks`
  - `priority_actions`
  - `negotiation_suggestions`
  - `follow_up_actions`
  - `requires_human_review`

## 7.2 标准化合同审查交付物

状态：未实现业务闭环。

当前已有：

- 多智能体自然语言输出可以覆盖部分内容。
- `CollaborationResult` 包含 `final_output`、`agent_contributions`、`messages`、`tasks`、`metadata`。

未实现：

- 合同风险清单的结构化交付物。
- 风险等级字段标准化。
- 修改建议和替代条款标准化。
- 对方法律风险画像。
- 红线比对结果。
- 法务审批流建议。
- 标准合同审查报告对象。
- 报告保存和导出。

可复用代码：

- 复用 `CollaborationResult` 作为原始协作结果容器。
- 复用 `PromptChainingAgent` 生成标准化报告章节。
- 复用 `MemoryAgent.store_memory()` 保存历史审查摘要和复用内容。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/schemas.py` 统一定义 LPOS 数据模型。
- 新增 `src/shuyixiao_agent/lpos/report_builder.py`。
- 定义 `ContractReviewReport`：
  - `task_id`
  - `contract_summary`
  - `risk_items`
  - `revision_suggestions`
  - `alternative_clauses`
  - `counterparty_risk_profile`
  - `redline_comparison`
  - `approval_flow_suggestion`
  - `review_conclusion`
  - `audit_summary`
- 定义 `ReportBuilder.build_contract_review_report()` 将多 Agent 输出转换为标准交付物。

## 7.3 法律文书生成

状态：部分实现基础能力，LPOS 业务未实现。

当前已有：

- `drafting_specialist` Agent 可以生成法律文本。
- `PromptChainingAgent` 可用于多步骤文书生成。
- `DocumentGenerationChain.get_steps()` 是通用文档生成链，可参考。
- `web_app.py` 的 `/api/prompt-chaining/run` 支持生成通用 Markdown 文件。

未实现：

- 200 类以上法律文书类型库。
- 文书类型选择接口。
- 每类文书的字段模板、事实要素、证据要素和格式规范。
- 根据用户事实、主体、诉求、证据生成文书初稿的结构化流程。
- 多轮补充信息和版本管理。
- 可编辑文档导出，例如 `.docx`。

可复用代码：

- 复用 `PromptChainingAgent.create_chain()` 和 `PromptChainingAgent.run_chain()`。
- 复用 `drafting_specialist` Agent。
- 复用 `RAGAgent.retrieve()` 检索法律依据和文书模板。
- 复用 `ReflectionAgent.reflect_and_improve()` 做文书质量复核。
- 复用 `MemoryAgent` 保存用户事实、版本修改记录和历史文书。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/document_generation.py`。
- 新增 `src/shuyixiao_agent/lpos/legal_document_templates.py`。
- 定义 `LegalDocumentType` 和模板注册表：
  - `document_type_id`
  - `name`
  - `category`
  - `required_fields`
  - `optional_fields`
  - `evidence_fields`
  - `output_sections`
  - `risk_warnings`
- 定义 `LegalDocumentGenerationService`：
  - `list_document_types()`
  - `create_draft(document_type, facts, parties, claims, evidence)`
  - `revise_draft(draft_id, user_feedback)`
  - `export_docx(draft_id)`
- Web 层新增：
  - `/api/lpos/documents/types`
  - `/api/lpos/documents/draft`
  - `/api/lpos/documents/{draft_id}/revise`
  - `/api/lpos/documents/{draft_id}/export`

## 7.4 高阶类案检索

状态：部分实现。

当前已有：

- `RAGAgent.retrieve()` 支持检索。
- `RAGAgent.query()` 支持检索增强问答。
- `VectorRetriever.retrieve()` 支持向量检索。
- `KeywordRetriever.retrieve()` 支持 BM25 关键词检索。
- `HybridRetriever.retrieve()` 支持混合检索。
- `Reranker.rerank_results()`、`CloudReranker`、`SimpleReranker` 支持重排序。
- `QueryOptimizer.optimize_query()` 支持查询优化。
- `VectorRetriever.retrieve()` 支持 `filter` 参数。
- Web 层已有 `/api/rag/query`、`/api/rag/query/stream`、`/api/rag/documents` 等接口。
- 多智能体中 `legal_researcher` 和 `compliance_checker` 已可接入 RAG 上下文。

未实现：

- 法律检索专属意图识别。
- 类案检索查询规划。
- 法规、案例、企业知识库的类型化 collection 或元数据体系。
- 案例案由、法院层级、裁判日期、地域、审级、文书类型等法律元数据过滤。
- 检索结果输出为法条、相似案例、裁判观点、引用来源的结构化对象。
- 与合同审查、风险分析、文书生成之间的稳定证据传递协议。

可复用代码：

- 复用 `RAGAgent.retrieve()` 作为统一召回入口。
- 复用 `QueryOptimizer.optimize_query()` 做查询重写。
- 复用 `HybridRetriever.retrieve()` 做混合检索。
- 复用 `Reranker.rerank_results()` 做重排序。
- 复用 `ContextManager.format_documents_for_prompt()` 做上下文格式化。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/legal_retrieval.py`。
- 定义 `LegalRetrievalService`：
  - `classify_intent(query) -> LegalRetrievalIntent`
  - `plan_query(query, context) -> LegalQueryPlan`
  - `search_laws(plan) -> List[LegalEvidence]`
  - `search_cases(plan) -> List[CaseEvidence]`
  - `search_enterprise_kb(plan) -> List[EnterpriseEvidence]`
  - `search_all(query, filters) -> LegalRetrievalResult`
- 定义法律元数据：
  - `source_type`：`law`、`case`、`regulation`、`template`、`enterprise_policy`
  - `jurisdiction`
  - `court_level`
  - `case_type`
  - `cause_of_action`
  - `publish_date`
  - `effective_date`
  - `document_no`
- Web 层新增 `/api/lpos/legal-search`。

## 7.5 合规风险智能分析

状态：部分实现角色，缺少规则库和业务逻辑。

当前已有：

- `compliance_checker` Agent 已定义合规风险审查职责。
- 多智能体中 `compliance_checker` 已开启 RAG。
- RAG 可检索监管规则、企业制度和红线规则。

未实现：

- 监管规则映射引擎。
- 行业合规规则识别。
- 实时风险预警。
- 合规分析报告结构。
- 企业红线规则和审批规则匹配。
- 合规风险等级结构化输出。
- 合规风险落库和审计追踪。

可复用代码：

- 复用 `compliance_checker` Agent。
- 复用 `RAGAgent.retrieve()` 检索监管规则和企业制度。
- 复用 `ReflectionAgent` 对合规结论做复核。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/compliance.py`。
- 定义 `ComplianceRule`：`rule_id`、`industry`、`scenario`、`trigger_terms`、`risk_level`、`requirement`、`source`。
- 定义 `ComplianceAnalyzer`：
  - `match_rules(contract, business_context) -> List[ComplianceRuleMatch]`
  - `analyze(contract, rules, evidence) -> ComplianceAnalysisResult`
  - `check_draft(draft_text, rules) -> ComplianceReviewResult`
- 新增规则库加载器，可先复用 RAG 文档存储，后续再升级为数据库表。

## 7.6 多智能体协同处理

状态：核心角色已实现，业务协作流程仍需增强。

当前已有：

- `MultiAgentCollaboration` 支持 `SEQUENTIAL`、`PARALLEL`、`HIERARCHICAL`、`PEER_TO_PEER`、`HYBRID`。
- `LegalContractReviewTeam.get_agents()` 已包含 6 个 Agent：
  - `contract_reviewer`
  - `clause_risk_analyzer`
  - `legal_researcher`
  - `drafting_specialist`
  - `compliance_checker`
  - `audit_recorder`
- `Message` 已记录 `sender`、`receiver`、`content`、`message_type`、`timestamp`、`metadata`。
- `CollaborationResult` 已记录 `final_output`、`agent_contributions`、`messages`、`tasks`、`metadata`。
- `legal_researcher`、`compliance_checker` 已支持 RAG 注入。

未实现：

- Web API 没有暴露法律合同审查团队。
- `web_app.py` 的 `/api/multi-agent/teams` 只有 `software_dev`、`research`、`content`、`business`。
- `web_app.py` 的 `/api/multi-agent/collaborate` 没有处理 `legal_contract_review`。
- `web_app.py` 的多智能体接口没有传入 `rag_agent`。
- 当前层级协作流程不是严格按 LPOS 推荐流程执行。
- `Clause Risk Agent`、`Legal Research Agent`、`Compliance Agent` 没有真正并行执行。
- `Drafting Agent` 没有强制等待风险识别和法律检索完成后再执行结构化任务。
- `Compliance Agent` 没有对 `Drafting Agent` 输出进行二次复核的明确阶段。
- `Audit Agent` 只是作为普通 reviewer 调用，没有生成结构化审计记录。
- 单个 Agent 失败后虽然 `get_agent_response()` 返回错误文本，但没有标准化标记缺失结果和人工复核。
- 每个 Agent 输出没有强制采用 7.6.10 的结构化字段。

可复用代码：

- 复用 `MultiAgentCollaboration` 的协作模式和消息结构。
- 复用 `ParallelizationAgent.execute_parallel()` 实现 `Clause Risk Agent`、`Legal Research Agent`、`Compliance Agent` 并行处理。
- 复用 `PlanningAgent` 拆分合同审查流程任务。
- 复用 `ReflectionAgent` 实现审核协作和一致性检查。
- 复用 `MemoryAgent` 保存任务上下文、历史审查记录和用户确认记录。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/legal_collaboration.py`。
- 定义 `LegalContractReviewOrchestrator`，不要把所有 LPOS 逻辑塞进通用 `MultiAgentCollaboration`。
- 核心方法：
  - `run_contract_review(contract_input, context, collection_name) -> ContractReviewReport`
  - `run_document_generation(document_request) -> LegalDocumentDraft`
- 内部流程严格执行：
  - 解析合同。
  - Contract Reviewer 制定计划。
  - Clause Risk、Legal Research、Compliance 并行。
  - Drafting 基于前三者结果生成建议和替代条款。
  - Compliance 复核 Drafting 输出。
  - Contract Reviewer 汇总。
  - Audit Agent 生成审计摘要。
- 更新 `web_app.py`：
  - 导入 `LegalContractReviewTeam`。
  - `/api/multi-agent/teams` 增加 `legal_contract_review`。
  - `/api/multi-agent/collaborate` 支持 `legal_contract_review`。
  - 请求模型增加 `collection_name`、`enable_rag`。
  - 调用 `get_rag_agent(collection_name)` 并传入 `MultiAgentCollaboration(rag_agent=rag_agent)`。

## 7.6.10 标准化智能体输出结构

状态：未实现。

当前已有：

- `agent_contributions` 是字典，保存每个 Agent 的 `role`、`response`、`phase` 等非统一字段。

未实现：

- `agent_name`
- `task_id`
- `input_summary`
- `findings`
- `evidence`
- `confidence`
- `requires_human_review`
- `output`
- `created_at`

可复用代码：

- 复用 `CollaborationResult.agent_contributions` 作为兼容输出容器。
- 复用 `Message.metadata` 保存结构化 evidence 和 task_id。

建议新增代码方案：

- 新增 `AgentStructuredOutput` 数据模型。
- 为 `get_agent_response()` 增加结构化输出模式：
  - prompt 要求 JSON。
  - 解析 JSON。
  - 解析失败时调用修复 prompt。
  - 仍保留原始文本作为 `raw_output`。
- 所有 LPOS Agent 输出统一写入 `AgentStructuredOutput`。

## 7.7 审计与可解释性

状态：部分实现概念，缺少审计系统。

当前已有：

- `Message` 可记录多智能体消息。
- `CollaborationResult.messages` 可返回协作过程。
- `audit_recorder` Agent 已定义审计留痕职责。
- `MemoryAgent.store_memory()` 可作为轻量持久化记录能力。
- `MemoryAgent.export_memories()` 可导出记忆。

未实现：

- 审计日志模型。
- 审计日志落库。
- 管理员审计日志查询。
- 上传文件元数据记录。
- 模型调用信息记录。
- 权限上下文记录。
- 用户确认、忽略、修改、导出操作记录。
- 私有化部署日志留存策略。
- 责任定位和报告追溯。

可复用代码：

- 复用 `Message` 和 `CollaborationResult` 作为审计原始事件来源。
- 复用 `MemoryAgent.store_memory()` 临时保存审计摘要。
- 复用 `PlanningResult.execution_log` 的日志结构设计。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/audit.py`。
- 定义：
  - `AuditEvent`
  - `AuditLog`
  - `AgentCallRecord`
  - `EvidenceRecord`
  - `UserActionRecord`
- 定义 `AuditService`：
  - `record_task_started()`
  - `record_agent_call()`
  - `record_evidence_used()`
  - `record_user_action()`
  - `build_audit_summary()`
  - `query_logs(filters)`
- Web 层新增：
  - `/api/lpos/audit/logs`
  - `/api/lpos/audit/tasks/{task_id}`

## 7.8 人类在环交互

状态：未实现 LPOS 专属流程。

当前已有：

- 通用聊天和多智能体接口可以由用户再次输入补充信息。
- `MemoryAgent.update_working_memory()` 可保存工作记忆。

未实现：

- 信息不足时自动识别并引导用户补充背景。
- 生成文书前确认关键事实和诉求。
- 合同审查后接受、忽略或修改建议。
- 高风险场景中强制提示律师复核。
- 用户操作记录进入审计日志。

可复用代码：

- 复用 `MemoryAgent.update_working_memory()` 保存用户补充信息。
- 复用 `PlanningAgent` 将合同审查拆成需要用户确认的阶段。
- 复用 `ReflectionAgent` 判断信息是否充分、是否需要人工复核。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/hitl.py`。
- 定义 `HITLCheckpoint`：
  - `checkpoint_id`
  - `task_id`
  - `checkpoint_type`
  - `question`
  - `required_fields`
  - `options`
  - `status`
- 定义 `HITLService`：
  - `detect_missing_information()`
  - `create_checkpoint()`
  - `submit_user_confirmation()`
  - `apply_user_decision()`
- Web 层新增：
  - `/api/lpos/tasks/{task_id}/checkpoints`
  - `/api/lpos/checkpoints/{checkpoint_id}/submit`

## 7.9 用户与权限管理

状态：未实现。

当前已有：

- `web_app.py` 是开放 FastAPI 服务。
- CORS 当前允许所有来源。
- 没有认证、用户、组织、角色或数据隔离。

未实现：

- 个人账号。
- 企业账号。
- 成员管理。
- 企业组织架构。
- 角色权限。
- 数据隔离。
- 管理员、法务、业务人员、普通成员等角色。
- 文件、报告、审批记录、审计日志权限控制。

可复用代码：

- 当前基本没有可直接复用的权限代码。
- 可复用 `MemoryAgent` 或未来数据库层保存用户上下文，但不建议把它作为正式权限系统。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/auth.py`。
- 新增数据库模型或持久化层：
  - `User`
  - `Organization`
  - `Membership`
  - `Role`
  - `Permission`
  - `ResourcePermission`
- 实现 `AuthService`：
  - `authenticate()`
  - `get_current_user()`
  - `check_permission(user, action, resource)`
  - `filter_resources_by_permission()`
- Web 层接入 FastAPI dependency，对 LPOS API 做权限校验。

## 7.10 报告导出与结果管理

状态：部分实现通用文件保存，LPOS 报告管理未实现。

当前已有：

- `PromptChainingAgent.save_chain_result()` 可保存 JSON。
- `web_app.py` 的 `/api/prompt-chaining/run` 可将输出保存为 Markdown。
- `MemoryAgent.export_memories()` 可导出记忆。
- `examples/17_multi_agent_collaboration_demo.py` 可保存协作结果 JSON。

未实现：

- 合同审查报告导出。
- 法律文书导出为可编辑格式。
- 历史任务查询。
- 按合同、项目、客户或业务线归档。
- 风险清单和审查结论复用。
- 报告版本管理。

可复用代码：

- 复用 `PromptChainingAgent.save_chain_result()` 的保存思路。
- 复用 `MemoryAgent.store_memory()` 保存可复用审查结论和风险清单摘要。
- 复用 `web_app.py` 中文件输出方式作为初版 Markdown 导出。

建议新增代码方案：

- 新增 `src/shuyixiao_agent/lpos/report_export.py`。
- 定义 `ReportExportService`：
  - `export_contract_review_markdown(report) -> str`
  - `export_contract_review_docx(report) -> str`
  - `export_legal_document_docx(draft) -> str`
  - `export_json(data) -> str`
- 新增 `TaskRepository` 或简单文件存储：
  - `save_task_result(task_id, report)`
  - `get_task(task_id)`
  - `list_tasks(filters)`
  - `archive_task(task_id, project_id, customer_id, business_line)`
- Web 层新增：
  - `/api/lpos/tasks`
  - `/api/lpos/tasks/{task_id}`
  - `/api/lpos/reports/{task_id}/export`
  - `/api/lpos/documents/{draft_id}/export`

## 建议实施优先级

### P0：先补齐合同审查闭环

目标：让已经完成的法律合同审查多智能体真正输出可用的标准化交付物。

建议实现：

- `lpos/schemas.py`
- `lpos/contract_parser.py`
- `lpos/legal_collaboration.py`
- `lpos/report_builder.py`
- Web API 支持 `legal_contract_review` 团队和 RAG collection 参数。

复用代码：

- `MultiAgentCollaboration`
- `LegalContractReviewTeam`
- `RAGAgent.retrieve()`
- `DocumentLoader`
- `ReflectionAgent`

### P1：补齐法律检索与合规规则

目标：让法律依据、监管规则和企业红线真正成为风险判断依据。

建议实现：

- `lpos/legal_retrieval.py`
- `lpos/compliance.py`
- 法律元数据 schema。
- 企业规则/红线规则导入和匹配。

复用代码：

- `RAGAgent`
- `HybridRetriever`
- `QueryOptimizer`
- `Reranker`
- `ContextManager`

### P2：补齐审计、HITL、报告导出

目标：满足企业法务和私有化客户的可追溯、可复核、可交付要求。

建议实现：

- `lpos/audit.py`
- `lpos/hitl.py`
- `lpos/report_export.py`
- 历史任务存储和查询接口。

复用代码：

- `Message`
- `CollaborationResult`
- `MemoryAgent`
- `PlanningAgent`
- `PromptChainingAgent`

### P3：补齐文书生成和权限系统

目标：扩展 LPOS 到完整法律生产力系统。

建议实现：

- `lpos/document_generation.py`
- `lpos/legal_document_templates.py`
- `lpos/auth.py`
- 文书模板库和组织权限模型。

复用代码：

- `PromptChainingAgent`
- `drafting_specialist`
- `RAGAgent.retrieve()`
- `ReflectionAgent`

## 建议新增目录结构

```text
src/shuyixiao_agent/lpos/
  __init__.py
  schemas.py
  contract_parser.py
  risk_analyzer.py
  legal_retrieval.py
  compliance.py
  drafting.py
  legal_collaboration.py
  report_builder.py
  report_export.py
  audit.py
  hitl.py
  document_generation.py
  legal_document_templates.py
  auth.py
  repositories.py
```

## 最小下一步建议

下一步最值得做的是 P0：把法律合同审查团队从“自然语言多 Agent 演示”升级为“结构化合同审查服务”。

具体任务：

1. 新增 `lpos/schemas.py`，定义合同、条款、风险、依据、建议、报告、审计事件的数据结构。
2. 新增 `lpos/contract_parser.py`，复用 `DocumentLoader` 完成 PDF/TXT/MD 合同文本抽取和初步条款切分。
3. 新增 `lpos/legal_collaboration.py`，封装法律合同审查专用编排，不直接污染通用 `MultiAgentCollaboration`。
4. 新增 `lpos/report_builder.py`，把 Agent 输出转为 `ContractReviewReport`。
5. 更新 `web_app.py`，增加 LPOS 合同审查 API，并支持 `collection_name` 传入 RAG 知识库。
