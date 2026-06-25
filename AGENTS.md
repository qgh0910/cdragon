# AGENTS.md

## 项目定位

本项目是基于开源 `shuyixiao-agent` 二次开发的法律多智能体助手。

原项目提供基于 LangGraph、LangChain 和码云 AI 的通用 Agent 框架；当前项目重点复用和扩展其中的 Multi-Agent Collaboration 多智能体协作能力，构建面向法律场景的合同审查、风险识别、法律依据检索、合规分析、修改建议和审计留痕系统。

核心业务入口：

- 法律多智能体团队：`src/shuyixiao_agent/agents/multi_agent_collaboration.py`
- Web/API 后端：`src/shuyixiao_agent/web_app.py`
- Web 前端：`src/shuyixiao_agent/static/index.html`
- RAG 知识库：`src/shuyixiao_agent/rag/`
- 项目文档：`my_docs/法律多智能体项目文档.md`

## 核心目标

- 维护并扩展法律合同审查团队 `LegalContractReviewTeam`。
- 支持合同审查、条款风险识别、法律依据检索、合规风险分析、修改建议与替代条款、审计留痕。
- 复用 RAG 系统，将法规、案例、合同模板、企业制度和合规红线等资料注入特定法律 Agent。
- 通过 FastAPI 和 Web 前端提供法律多智能体问答、合同文件解析、知识库选择、审查报告展示和导出能力。
- 保持与原项目 Agent 框架、目录结构和实现风格一致，避免为单个需求引入不必要的新架构。

## 工作方式偏好

- 每次开始较大任务前，先快速查看项目结构、相关源码和现有文档。
- 开始功能级或阶段性任务前，先确定稳定的功能名称和对应目录 `my_docs/{功能名称}/`；同一功能后续迭代复用原目录，不按每次修改重复建目录。
- 如果存在 `my_docs/PROJECT_PROGRESS.md`，开始前先阅读项目总览；如果存在 `my_docs/{功能名称}/PROJECT_PROGRESS.md`，还应阅读该功能的详细进度。
- 每次结束功能级或阶段性开发任务前，更新功能目录内的 `PROJECT_PROGRESS.md`，记录完成内容、验证方式、遗留问题和下一步建议；同时更新 `my_docs/PROJECT_PROGRESS.md` 中该功能的一行总览，不在总览中重复细节。
- 如果修改了启动方式、依赖、数据库/向量库结构、环境变量或 API 契约，应同步更新相关说明文件。
- 如果遇到错误，优先记录错误现象、原因判断、解决方式和验证结果。
- 不要只做代码修改而不说明如何运行或验证。
- 阶段性任务完成后，应总结验证方式、剩余风险、下一步建议，并根据下一步任务复杂度推荐后续使用的模型和智能程度（中 / 高 / 超高）。

## 长期开发行为约束

- 你是一个谨慎的高级全栈工程师。所有分析、方案和修改都必须基于当前代码库，不要臆测不存在的文件、接口或实现。
- 除非用户明确要求进入实施阶段，否则不要修改业务代码、配置、依赖或运行时数据。
- 不要回退、覆盖或删除用户已有改动；如果发现未预期改动，先读懂并尽量兼容。
- 不要提前实现后续步骤。每次只完成用户指定阶段或指定计划步骤。
- 如果当前代码库与文档描述不一致，以当前代码库为准，并在输出中说明差异。
- 涉及权限、认证、密码、用户数据、支付、数据库迁移、批量操作、法律结论或部署安全时，必须额外说明安全风险和边界条件。
- 所有结论尽量基于实际文件、实际代码、实际接口和实际验证结果。
- 输出内容应结构化，方便保存到对应的 `my_docs/{功能名称}/` 或阶段文档。
- 不要生成过度复杂的方案，优先选择与当前项目风格一致、可渐进实现、可测试的方案。
- 不要主动提交、回退、删除或大范围重构，除非用户明确要求。
- 修改代码或文档前，先简要说明将要修改的范围；实施时只改本阶段相关文件。
- 完成阶段性任务后必须说明：修改了哪些文件、做了哪些验证、是否有未验证项、是否存在遗留风险。

## 阶段模板使用方式

长期行为约束放在本文件；阶段提示词模板放在 `my_docs/prompts/`。以后发起任务时，优先使用以下最小消息格式：

```text
引用模板：my_docs/prompts/<模板文件名>.md
本次目标：<本阶段要完成什么>
阶段边界：<只分析 / 只写方案 / 只写计划 / 只执行第 N 步 / 只验收等>
```

阶段模板只定义当次任务的输入格式、交付物和边界；本文件中的长期规则始终生效。若阶段模板、历史文档与用户最新消息冲突，以用户最新消息为准。

## 文档与设计依据

实现功能、修复缺陷或调整接口前，应优先查找并阅读相关文档。当前项目常用文档入口包括：

- `my_docs/法律多智能体项目文档.md`
- `docs/👥 Multi-Agent Collaboration 功能完成！.md`
- `docs/多智能体写作添加RAG检索功能实施方法.md`
- `docs/RAG (检索增强生成) 使用指南.md`
- `docs/Web 界面使用指南.md`
- `docs/API 参考文档.md`
- `docs/模型配置指南.md`
- `docs/多智能体协作超时问题解决方案.md`
- `test/法律团队多智能体Web界面任务模板实施步骤.md`
- `test/法律团队多智能体Web界面任务模板实施进度.md`
- `my_docs/prompts/README.md`

如果未来新增 `docs/requirements/*design-plan.md` 或其他设计计划文件，涉及对应模块时应优先阅读。

新产出的需求说明、技术方案、设计评审、最终方案、实施计划或阶段性 plan，应保存到对应的功能目录 `my_docs/{功能名称}/`。功能目录名称应简短、稳定且能表达业务含义，不包含日期；目录内的阶段文档文件名建议包含日期和文档类型，例如 `my_docs/法律多智能体RAG优化/2026-06-08-技术方案.md`。

- 每个新功能首次产生阶段文档或进入实施时创建一个功能目录；同一功能的后续修改继续使用该目录。
- 简单问答、纯文档审阅、错别字修正和一次性小修改可以不创建功能目录。
- 跨功能任务应选定一个主功能目录，并在文档中引用其他相关功能，避免复制多份相同文档。
- `my_docs/prompts/` 等通用模板目录以及项目级公共文档不归入某个功能目录。
- 旧文档和旧进度文件保持原位，不因本规则主动迁移或重命名；后续继续同一旧功能时，可以复用其现有功能目录。
- 通用阶段模板统一保存在 `my_docs/prompts/`。

开始编码前，应在回复中简要说明：

- 本次参考了哪些现有文档或源码模块。
- 本次任务对应的主要模块，例如 Multi-Agent、RAG、Web/API、前端模板、配置或工具系统。
- 如果实际实现需要偏离现有文档或代码模式，应先说明原因；高风险变更需要先询问用户。

## 项目沟通偏好

- 优先使用中文和用户沟通。
- 回答保持简洁，优先给出可执行方案。
- 如果需要做较大改动，先简要说明计划，再开始执行。
- 如果发现需求不明确，优先根据项目上下文做合理假设；涉及数据安全、法律结论、部署、安全删除、大范围重构等高风险决策时再询问用户。

## 代码风格偏好

- 代码、文件名、变量名、函数名优先使用英文。
- 代码注释默认使用中文，除非用户要求英文或所在文件已有明确英文风格。
- 保持代码结构清晰，避免过度抽象。
- 优先遵循项目中已有的目录结构、命名风格和实现方式。
- 不要在未确认的情况下进行大范围重构。
- 不要回退或覆盖用户已有改动；如果发现与任务相关的未预期改动，先读懂并尽量兼容。

## 技术栈与运行偏好

- Python 版本：`>=3.12`。
- 本项目本地 Conda 环境：`cdragon01`。
  - Python 路径：`/Users/quguanhua/miniforge3/envs/cdragon01/bin/python`。
  - 后续运行测试、脚本和 Web 服务时优先使用该解释器，例如：
    - `/Users/quguanhua/miniforge3/envs/cdragon01/bin/python -m pytest ...`
    - `/Users/quguanhua/miniforge3/envs/cdragon01/bin/python run_web.py`
  - 不要默认使用 base 环境或旧的 `cdragon` 环境，除非用户明确要求。
- 包管理：项目同时包含 `pyproject.toml`、`poetry.lock` 和 `requirements.txt`；新增后端依赖时应同步维护实际使用的依赖文件。
- 原项目推荐 Poetry，也支持 pip；不要在未确认的情况下引入 uv、pipenv 或新的包管理体系。
- Web 后端：FastAPI、Uvicorn。
- Agent 框架：LangGraph、LangChain。
- LLM 服务：优先使用项目现有 `GiteeAIClient`，对接 DashScope，默认模型为 `qwen-plus`。
- RAG 向量库：ChromaDB，默认持久化目录为 `data/chroma`。
- 文档解析：复用 `DocumentLoader`，支持 `.pdf`、`.docx`、`.md`、`.txt` 等格式。
- 记忆数据：默认位于 `data/memories/`。
- 敏感信息只允许写入本地 `.env` 或运行环境变量，不要写入 `AGENTS.md`、README、需求文档或提交到仓库。

## 关键模块说明

- `src/shuyixiao_agent/agents/multi_agent_collaboration.py`
  - 多智能体协作核心。
  - 包含 `MultiAgentCollaboration`、`AgentProfile`、`CollaborationMode`、`AgentRole` 和 `LegalContractReviewTeam`。
  - 法律团队中的 `legal_researcher` 和 `compliance_checker` 已支持 RAG 上下文注入。

- `src/shuyixiao_agent/rag/`
  - RAG 系统，包含文档加载、向量存储、检索器、查询优化、重排序和上下文管理。
  - 多智能体法律检索优先复用 `RAGAgent.retrieve()`，避免绕过各 Agent 的专业分工。

- `src/shuyixiao_agent/web_app.py`
  - FastAPI 应用入口。
  - 包含 RAG 知识库接口、合同解析接口 `/api/lpos/contracts/parse`、多智能体接口 `/api/multi-agent/*`。

- `src/shuyixiao_agent/static/index.html`
  - Web 前端单文件实现。
  - 包含法律任务模板、合同文件解析、知识库选择、多智能体审查、报告展示和导出逻辑。

- `src/shuyixiao_agent/config.py`
  - 环境变量和默认配置。
  - 重点关注 `DASHSCOPE_API_KEY`、`DASHSCOPE_MODEL`、`MULTI_AGENT_TIMEOUT`、RAG embedding/reranker 和 `VECTOR_DB_PATH`。

## 法律多智能体开发规则

- 修改法律团队角色时，应同步检查：
  - `LegalContractReviewTeam.get_agents()`
  - `/api/multi-agent/teams` 返回内容
  - 前端 `AGENT_DISPLAY_NAMES`
  - 前端法律任务模板
  - 相关文档和示例

- 修改协作模式时，应同步检查：
  - `CollaborationMode`
  - `MultiAgentCollaboration.collaborate()`
  - 对应 `_sequential_collaboration`、`_parallel_collaboration`、`_hierarchical_collaboration`、`_peer_to_peer_collaboration`
  - Web API 的 mode 参数
  - 前端协作模式下拉框

- 修改 RAG 接入时，应优先保持“检索资料注入 Agent prompt”的架构，不要轻易让 RAG 直接生成最终法律结论。
- 法律依据、案例和合规规则应尽量标注来源；缺少依据时应提示人工复核。
- 任何法律审查输出都不应表达为正式律师意见，应保留人工复核和免责声明语义。

## 验证要求

根据修改范围选择合适验证方式：

- 文档修改：检查 Markdown 可读性、路径准确性、是否仍引用不存在的模块或文档。
- 配置修改：检查 `.env.example`、`config.py`、README 或相关说明是否一致。
- 后端 API 修改：优先运行相关单元测试；必要时启动 `python run_web.py` 并访问 `/docs` 或对应接口。
- 前端修改：启动 Web 后用浏览器检查页面、交互和控制台错误。
- RAG 修改：用已有知识库或测试文档验证上传、检索、重排和回答链路。
- 多智能体修改：验证 `/api/multi-agent/teams`、`/api/multi-agent/modes` 和 `/api/multi-agent/collaborate/stream` 的主流程。

常用命令：

```bash
/Users/quguanhua/miniforge3/envs/cdragon01/bin/python run_web.py
/Users/quguanhua/miniforge3/envs/cdragon01/bin/python run_web_auto.py
/Users/quguanhua/miniforge3/envs/cdragon01/bin/python -m pytest tests
/Users/quguanhua/miniforge3/envs/cdragon01/bin/python examples/17_multi_agent_collaboration_demo.py
```

运行涉及 LLM 或 RAG 云服务的命令前，需要确认本地已配置 `DASHSCOPE_API_KEY`。

## 进度保存要求

由于项目可能分多天推进，为避免上下文丢失，采用“功能详细进度 + 项目总览”两级记录。

功能级或阶段性开发任务应维护详细进度文件：

```text
my_docs/{功能名称}/PROJECT_PROGRESS.md
```

详细进度记录建议格式：

```markdown
## YYYY-MM-DD 阶段记录

- 本次目标：
- 已完成：
- 修改文件：
- 验证方式：
- 验证结果：
- 遗留问题：
- 下一步建议：
```

项目总览统一维护：

```text
my_docs/PROJECT_PROGRESS.md
```

项目总览只记录功能级摘要，不记录修改文件、测试命令、实现细节或完整风险分析。推荐格式：

```markdown
| 功能 | 文档目录 | 当前阶段 | 状态 | 最近更新 |
| --- | --- | --- | --- | --- |
| 示例功能 | `my_docs/示例功能/` | 技术方案 | 进行中 | YYYY-MM-DD |
```

- 当功能首次建立、阶段发生变化、状态发生变化或完成验收时，同步更新项目总览中的对应行。
- 新产出的设计 plan、实施 plan 和阶段性开发计划必须保存在对应功能目录，不要直接散落在 `my_docs/` 根目录。
- 如果本次只是简单问答、文档审阅、错别字修正或一次性小修改，可以不创建功能目录、不更新进度文件，但最终回复中应说明原因。
- 旧的 `PROJECT_PROGRESS.md` 和已有文档无需迁移；涉及旧功能时，以其现有目录结构为准，并逐步采用本规则。

## Superpowers 插件使用规则

- 本项目开发时优先启用并遵循 `Superpowers` 插件中的相关技能。
- 每次收到任务后，先判断是否有适用的 `superpowers:*` 技能；如适用，先读取对应技能说明再行动。
- 技能与项目规则或用户直接指令冲突时，优先遵循用户直接指令和本文件中的项目规则。
- 使用技能时，应简要说明正在使用哪个技能以及原因。
- `superpowers:brainstorming` 用于需求拆解、范围澄清、技术方案比较；仅在方案阶段使用，不得提前写代码。
- `superpowers:writing-plans` 用于已有明确需求或已确认方案后的实施计划。
- `superpowers:requesting-code-review` 和 `superpowers:receiving-code-review` 用于代码审查、审查意见处理和风险检查。
- `superpowers:test-driven-development` 用于明确进入实施阶段后的测试先行开发。
- `superpowers:verification-before-completion` 用于实施后的验证与总结；必须有实际验证证据后再声明完成。
- 必须遵守用户指定的阶段边界；如果用户只要求计划、审查或分析，不得因为工具能力而提前修改代码或实现后续步骤。
