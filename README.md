# CDragon 法律多智能体合同审查助手

基于 LangGraph、LangChain、FastAPI、DashScope 和 ChromaDB 的法律多智能体合同审查系统。

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 项目定位

CDragon 是在开源 `shuyixiao-agent` 通用 Agent 框架基础上二次开发的法律场景项目。当前主线不再是通用聊天机器人或工具演示，而是面向企业法务、合同管理和合规审查的多智能体助手。

项目重点支持：

- 合同上传、文本解析和结构化摘要
- 条款级风险识别和风险分级
- 法律依据、案例、合同模板和企业制度检索
- 合规风险分析和监管红线提示
- 修改建议、替代条款和法律文书初稿
- 多智能体协作过程、合同解析事件和审计留痕
- Web 前端、FastAPI 接口、RAG 知识库和权限控制

> 注意：本项目输出仅作为合同审查辅助信息，不构成正式律师意见。涉及签署、诉讼、监管处罚、重大交易或个人敏感信息时，应由具备资质的法律专业人员复核。

## 当前核心模块

### 法律多智能体团队

核心入口：`src/shuyixiao_agent/agents/multi_agent_collaboration.py`

法律团队 `LegalContractReviewTeam` 包含 6 个专业 Agent：

| Agent | 角色 | 主要职责 |
| --- | --- | --- |
| `contract_reviewer` | 合同审查协调员 | 识别合同背景、拆解任务、汇总风险和签署建议 |
| `clause_risk_analyzer` | 条款风险分析师 | 识别条款风险、风险等级、风险原因和后果 |
| `legal_researcher` | 法律依据检索员 | 通过 RAG 检索法规、案例、模板和企业知识库 |
| `drafting_specialist` | 法律文本起草员 | 生成修改建议、替代条款和文书草稿 |
| `compliance_checker` | 合规审查员 | 映射监管规则、企业红线和整改建议 |
| `audit_recorder` | 审计留痕员 | 检查引用完整性、输出可追溯性和过程摘要 |

前端和后端共同支持 9 类法律任务模板：

- `contract_review`：合同审查
- `risk_identification`：合同风险识别
- `revision_suggestions`：修改建议与替代条款
- `legal_research`：法律依据检索
- `compliance_analysis`：合规风险分析
- `review_summary`：审查结论摘要
- `legal_document_generation`：法律文书生成
- `redline_comparison`：红线对比
- `approval_flow_suggestion`：审批流程建议

服务端会强制保留 `contract_reviewer` 主控 Agent，并在 `metadata.agent_selection` 中返回本次实际参与者、选择来源和能力缺口提示。

### LPOS 合同上传与结构化解析

核心入口：

- `src/shuyixiao_agent/lpos/contract_parser.py`
- `src/shuyixiao_agent/lpos/contract_extractor.py`
- `src/shuyixiao_agent/lpos/pageindex.py`
- `src/shuyixiao_agent/lpos/audit.py`
- `src/shuyixiao_agent/web_app.py`

当前合同解析链路：

1. 登录用户上传合同文件，文件保存到 user-scoped 目录。
2. `upload_registry` 登记 `file_id`、owner、租户和存储路径。
3. `DocumentLoader` 抽取 PDF、DOCX、Markdown、TXT 等文本。
4. `pageindex` 生成来源定位块，避免把服务端绝对路径注入 prompt。
5. `contract_extractor` 规则优先抽取合同类型、主体、金额、期限、条款和关键条款摘要。
6. `audit` 写入上传、解析、越权、失败等合同事件审计日志。
7. 前端展示结构化摘要，多智能体只接收安全摘要和必要文件标识。

默认响应不会返回完整条款正文和完整 pageindex。需要调试时可通过请求参数显式打开。

### RAG 知识库

核心入口：

- `src/shuyixiao_agent/rag/`
- `src/shuyixiao_agent/kb/`
- `src/shuyixiao_agent/web_app.py`

RAG 系统支持：

- ChromaDB 持久化向量库，默认目录为 `data/chroma`
- 用户知识库和公共知识库
- 知识库权限校验，普通用户只能读写自己的用户知识库
- 管理员维护公共法规、案例、模板和企业制度资料
- 向量检索、关键词检索、混合检索、查询优化和重排序
- 法律团队中的 `legal_researcher` 和 `compliance_checker` 接收 RAG 上下文

设计原则：RAG 负责提供可核验资料和上下文，不直接替代法律 Agent 生成最终结论。

### Web/API 后端

核心入口：`src/shuyixiao_agent/web_app.py`

主要接口：

| 能力 | 接口 |
| --- | --- |
| 健康检查 | `GET /api/health` |
| 登录与会话 | `POST /api/auth/login`、`POST /api/auth/logout`、`GET /api/auth/me` |
| 知识库管理 | `GET/POST /api/kb/collections`、`POST /api/kb/collections/{kb_id}/upload` |
| RAG 查询 | `POST /api/rag/query`、`POST /api/rag/query/stream` |
| 合同上传解析 | `POST /api/lpos/contracts/upload`、`POST /api/lpos/contracts/parse` |
| 多智能体团队 | `GET /api/multi-agent/teams`、`GET /api/multi-agent/modes` |
| 多智能体协作 | `POST /api/multi-agent/collaborate`、`POST /api/multi-agent/collaborate/stream` |

业务 `/api/*` 默认需要登录；登录成功后使用 HttpOnly Cookie 保存 session，非 GET 请求需要携带 CSRF token。

### Web 前端

核心入口：`src/shuyixiao_agent/static/index.html`

前端是一个单文件应用，当前重点能力包括：

- 登录态初始化和 CSRF 请求封装
- 知识库选择、公共知识库开关和权限提示
- 合同上传、解析状态、结构化摘要展示
- 法律任务模板、Agent 选择区和能力缺口提示
- SSE 流式多智能体协作
- 服务端权威参与者 metadata 展示
- 审查结果复制、下载和人工复核声明

## 技术栈

- Python `>=3.12`
- FastAPI、Uvicorn
- LangGraph、LangChain
- DashScope 兼容 OpenAI 接口模型，默认推荐 `qwen-plus`
- ChromaDB、Sentence Transformers、BM25、Cross-Encoder
- SQLite，用于认证、知识库 registry、上传登记和审计日志
- 单文件 HTML/CSS/JavaScript 前端

包名目前仍沿用上游项目的 `shuyixiao_agent`，这是为了减少迁移成本。项目业务定位以本 README 和 `AGENTS.md` 为准。

## 快速开始

### 1. 准备环境

```bash
git clone <your-repo-url>
cd cdragon

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

也可以使用 Poetry：

```bash
poetry install
poetry shell
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

至少需要配置：

```bash
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen-plus
AUTH_SECRET_KEY=replace-with-a-random-secret
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=change-me-before-sharing
AUTH_COOKIE_SECURE=false
```

RAG 推荐配置：

```bash
USE_CLOUD_EMBEDDING=true
CLOUD_EMBEDDING_MODEL=text-embedding-v4
USE_CLOUD_RERANKER=true
CLOUD_RERANKER_BASE_URL=https://dashscope.aliyuncs.com/compatible-api/v1
CLOUD_RERANKER_MODEL=qwen3-rerank
```

LPOS 合同解析可选配置：

```bash
LPOS_CONTRACT_PARSE_MAX_CHARS=200000
LPOS_CONTRACT_PARSE_MAX_CLAUSES=300
LPOS_CONTRACT_PARSE_CLAUSE_PREVIEW_CHARS=1200
LPOS_CONTRACT_PARSE_SOURCE_PREVIEW_CHARS=160
LPOS_CONTRACT_PARSE_USE_LLM=false
LPOS_CONTRACT_PARSE_LLM_TIMEOUT=60
```

不要把真实的 `.env`、API Key、管理员密码、合同原文或客户资料提交到仓库。

### 3. 启动服务

推荐本地启动：

```bash
python run_web_auto.py
```

标准启动脚本：

```bash
python run_web.py
```

也可以直接启动 FastAPI：

```bash
PYTHONPATH=src python -m uvicorn shuyixiao_agent.web_app:app --host 127.0.0.1 --port 8000
```

访问地址：

- Web 界面：`http://127.0.0.1:8000/` 或启动脚本输出的端口
- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/health`

`run_web.py` 当前默认端口为 `8001`；`run_web_auto.py` 会从 `8000` 开始自动选择可用端口。

### 4. 典型使用流程

1. 使用 `.env` 中的初始管理员账号登录。
2. 在知识库页面创建用户知识库或公共知识库。
3. 上传法规、案例、合同模板、企业制度或合规红线资料。
4. 上传合同文件，确认解析出的合同类型、主体、金额、期限和关键条款摘要。
5. 选择法律任务模板，例如合同审查、风险识别或修改建议。
6. 按需要调整参与 Agent，选择知识库，发起流式多智能体协作。
7. 查看报告、各 Agent 贡献、引用来源、能力缺口和人工复核提示。

## API 示例

### 法律多智能体协作

```json
{
  "input_text": "请审查这份租赁合同，重点关注付款、违约责任和解除条款。",
  "team_type": "legal_contract_review",
  "mode": "hierarchical",
  "legal_task_type": "contract_review",
  "selected_agent_names": [
    "contract_reviewer",
    "clause_risk_analyzer",
    "legal_researcher",
    "compliance_checker"
  ],
  "enable_rag": true,
  "knowledge_base_ids": ["kb_xxxxxxxxxxxx"],
  "include_public_knowledge": true,
  "context": {
    "uploaded_file_id": "20260616_120000_abcdef123456",
    "uploaded_file_name": "租赁合同.docx",
    "contract_structure_summary": {
      "contract_type": "租赁合同",
      "clause_count": 12
    }
  }
}
```

### 合同解析

```json
{
  "file_id": "20260616_120000_abcdef123456",
  "tenant_id": "default",
  "parse_structure": true,
  "include_clause_content": false,
  "include_page_index": false
}
```

更多接口细节见 [API 参考文档](docs/API%20参考文档.md)。

## 项目结构

```text
cdragon/
├── src/shuyixiao_agent/
│   ├── agents/
│   │   └── multi_agent_collaboration.py   # 多智能体协作和法律团队
│   ├── auth/                              # 登录、会话、密码和认证依赖
│   ├── kb/                                # 知识库 registry 与权限
│   ├── lpos/                              # 合同上传登记、解析、pageindex、审计
│   ├── rag/                               # 文档加载、向量库、检索、重排、RAG Agent
│   ├── static/index.html                  # Web 前端单文件应用
│   ├── config.py                          # 环境变量和默认配置
│   ├── gitee_ai_client.py                 # DashScope 兼容客户端
│   └── web_app.py                         # FastAPI 应用入口
├── docs/                                  # 公开使用文档和 API 文档
├── my_docs/                               # 本地阶段文档，默认不纳入 Git
├── tests/                                 # 自动化测试
├── data/                                  # 本地运行数据，默认不应提交敏感内容
├── .env.example                           # 环境变量示例
├── run_web.py                             # 标准 Web 启动脚本
├── run_web_auto.py                        # 自动端口 Web 启动脚本
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 测试与验证

本项目当前推荐使用 Python 3.12 环境运行测试：

```bash
python -m pytest tests
```

如果只验证法律多智能体、LPOS、RAG 授权和前端静态主链路，可运行：

```bash
python -m pytest \
  tests/test_lpos_contract_api.py \
  tests/test_multi_agent_kb_authorization.py \
  tests/test_multi_agent_rag_query.py \
  tests/test_server_path_authorization.py \
  tests/test_step20_documentation_sync.py \
  tests/test_legal_agent_routing.py \
  tests/test_lpos_config_and_audit.py \
  tests/test_lpos_contract_extractor.py \
  tests/test_lpos_contract_parser.py \
  tests/test_lpos_frontend_static.py \
  tests/test_lpos_pageindex.py \
  tests/test_multi_agent_context_format.py \
  tests/test_multi_agent_execution_policy.py \
  tests/test_multi_agent_failure_and_synthesis.py \
  tests/test_multi_agent_routing_api.py
```

提交前建议至少执行：

```bash
git diff --check
python -m pytest tests/test_lpos_frontend_static.py tests/test_multi_agent_routing_api.py
```

涉及真实 LLM 或云端 RAG 的验证需要先确认本地已配置 `DASHSCOPE_API_KEY`，并注意调用成本和数据合规。

## 安全与合规边界

- 不要提交真实 `.env`、API Key、管理员密码、合同原文、客户资料或内部制度。
- `AUTH_SECRET_KEY` 和 `INITIAL_ADMIN_PASSWORD` 必须在生产环境中替换为强随机值。
- `AUTH_ENABLE_SERVER_PATH_IMPORT` 默认应保持 `false`；服务器路径导入只适合受控管理员环境。
- 普通用户不得通过 `file_id` 解析他人上传的合同。
- 前端和多智能体 prompt 默认只使用结构化摘要、`file_id`、文件名和安全上下文字段。
- 审计日志只记录摘要级安全字段，不写入完整合同正文或服务端绝对路径。
- 规则优先合同抽取对复杂表格、扫描件、OCR 质量差的文档和非标准条款格式仍有局限。
- 法律输出必须保留人工复核语义，不能包装成正式律师意见。

## 相关文档

- [API 参考文档](docs/API%20参考文档.md)
- [Web 界面使用指南](docs/Web%20界面使用指南.md)
- [RAG 使用指南](docs/RAG%20%28检索增强生成%29%20使用指南.md)
- [模型配置指南](docs/模型配置指南.md)
- [多智能体协作说明](docs/👥%20Multi-Agent%20Collaboration%20功能完成！.md)
- [多智能体协作超时问题解决方案](docs/多智能体协作超时问题解决方案.md)

部分上游通用 Agent 能力，如 Tool Agent、Prompt Chaining、Routing、Planning、Reflection 和 Memory，仍保留在代码中，主要作为框架能力或后续扩展基础。当前 README 以法律合同审查主线为准。

## 开源说明

本项目基于 `shuyixiao-agent` 的通用 Agent 框架继续开发，保留了部分原有包名、基础 Agent、工具和示例代码。后续如果继续推进开源化，建议逐步完成：

- 项目包名和元数据从 `shuyixiao-agent` 迁移到新的项目名
- 通用 Agent 示例与法律主线文档分离
- 完整测试套件中的历史文档产物和旧断言清理
- Docker、部署示例和生产安全配置文档
- 更完整的合同样例、脱敏演示数据和截图

## 许可证

本项目采用 MIT License，详见 [LICENSE](LICENSE)。

## 致谢

- [LangGraph](https://github.com/langchain-ai/langgraph)
- [LangChain](https://github.com/langchain-ai/langchain)
- [ChromaDB](https://www.trychroma.com/)
- [阿里云百炼 DashScope](https://bailian.console.aliyun.com/)
- 原始开源项目 `shuyixiao-agent`
