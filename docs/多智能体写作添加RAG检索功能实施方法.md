# 多智能体写作添加 RAG 检索功能实施方法

## 结论

当前 `multi_agent_collaboration` 已经在法律合同审查团队中定义了 `legal_researcher`，并在角色能力里写了 `RAG检索`，但没有真正调用知识库检索代码。

现状依据：

- `src/shuyixiao_agent/agents/multi_agent_collaboration.py` 的 `LegalContractReviewTeam.get_agents()` 中，`legal_researcher` 只是一个 `AgentProfile` 配置。
- `src/shuyixiao_agent/agents/multi_agent_collaboration.py` 的 `MultiAgentCollaboration.get_agent_response()` 只拼接 `system_prompt`、`context` 和任务，然后调用 `llm_client.simple_chat()`。
- 现有 RAG 能力集中在 `src/shuyixiao_agent/rag/`，可以直接复用，不需要重新实现向量检索、关键词检索、重排序和上下文管理。

## 可复用的 RAG 代码

优先复用 `src/shuyixiao_agent/rag/rag_agent.py` 的 `RAGAgent`。

可调用函数：

- `RAGAgent(collection_name, system_message, use_reranker, retrieval_mode, enable_query_optimization, enable_context_expansion)`：初始化指定知识库集合的 RAG Agent。
- `RAGAgent.add_documents_from_file(file_path, show_progress=True)`：把单个文件加入知识库。
- `RAGAgent.add_documents_from_directory(directory_path, glob_pattern="**/*.*", show_progress=True)`：把目录下文档批量加入知识库。
- `RAGAgent.add_texts(texts, metadatas=None)`：把文本直接加入知识库。
- `RAGAgent.retrieve(query, top_k=None, mode=None, use_rerank=True)`：只检索相关文档，返回 `Document` 列表。
- `RAGAgent.query(question, top_k=None, use_history=True, optimize_query=True, expand_context=True, stream=False)`：检索并直接生成回答。

多智能体写作建议优先调用 `retrieve()`，而不是 `query()`。原因是 `query()` 会直接生成最终回答，容易绕过 `legal_researcher`、`clause_risk_analyzer`、`drafting_specialist` 等角色分工；`retrieve()` 只返回证据片段，便于把检索结果作为上下文注入给具体 Agent。

底层组件也可以按需复用：

- `src/shuyixiao_agent/rag/vector_store.py` 的 `VectorStoreManager.add_documents()`、`VectorStoreManager.similarity_search_with_score()`：向量库写入和向量相似度检索。
- `src/shuyixiao_agent/rag/retrievers.py` 的 `VectorRetriever.retrieve()`：向量检索。
- `src/shuyixiao_agent/rag/retrievers.py` 的 `KeywordRetriever.add_documents()`、`KeywordRetriever.retrieve()`：BM25 关键词检索。
- `src/shuyixiao_agent/rag/retrievers.py` 的 `HybridRetriever.retrieve()`：混合检索。
- `src/shuyixiao_agent/rag/context_manager.py` 的 `ContextManager.build_context()`、`ContextManager.format_documents_for_prompt()`：把检索文档整理成可注入 LLM 的上下文。
- `src/shuyixiao_agent/rag/document_loader.py` 的 `DocumentLoader.load_and_split()`、`DocumentLoader.load_directory_and_split()`、`DocumentLoader.split_text()`：文档加载和切分。

## 推荐实现目标

实现“多智能体写作 RAG 上下文注入”功能：

- 支持给 `MultiAgentCollaboration` 传入一个共享的 `RAGAgent`。
- 支持指定哪些 Agent 需要 RAG，例如 `legal_researcher`、`compliance_checker`、`drafting_specialist`。
- 在这些 Agent 执行前，根据当前任务和上下文生成检索查询。
- 调用 `RAGAgent.retrieve()` 获取知识库片段。
- 把检索片段以“知识库检索结果”的形式注入该 Agent 的 prompt。
- 最终输出中保留每个 Agent 的贡献和引用来源，便于审计。

## 最小改造方案

### 1. 修改 `AgentProfile`

文件：`src/shuyixiao_agent/agents/multi_agent_collaboration.py`

给 `AgentProfile` 增加 RAG 配置字段：

```python
@dataclass
class AgentProfile:
    name: str
    role: AgentRole
    description: str
    expertise: List[str]
    system_prompt: str
    capabilities: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    priority: int = 0
    enable_rag: bool = False
    rag_top_k: int = 5
    rag_mode: str = "hybrid"
```

作用：让每个 Agent 自己声明是否需要知识库检索。

### 2. 修改 `MultiAgentCollaboration.__init__()`

文件：`src/shuyixiao_agent/agents/multi_agent_collaboration.py`

新增可选参数 `rag_agent`：

```python
def __init__(
    self,
    llm_client,
    mode: Union[CollaborationMode, str] = CollaborationMode.HIERARCHICAL,
    verbose: bool = True,
    max_rounds: int = 5,
    rag_agent: Optional[Any] = None
):
    self.llm_client = llm_client
    self.mode = CollaborationMode(mode) if isinstance(mode, str) else mode
    self.verbose = verbose
    self.max_rounds = max_rounds
    self.rag_agent = rag_agent
```

作用：不强制多智能体依赖 RAG，只有传入 `rag_agent` 时才启用检索。

### 3. 新增 RAG 上下文构建方法

文件：`src/shuyixiao_agent/agents/multi_agent_collaboration.py`

在 `MultiAgentCollaboration` 中新增方法：

```python
def _build_rag_context(self, agent: AgentProfile, input_text: str) -> str:
    if not self.rag_agent or not agent.enable_rag:
        return ""

    documents = self.rag_agent.retrieve(
        query=input_text,
        top_k=agent.rag_top_k,
        mode=agent.rag_mode,
        use_rerank=True
    )

    if not documents:
        return ""

    lines = ["## 知识库检索结果"]
    for index, doc in enumerate(documents, 1):
        source = doc.metadata.get("source", "unknown")
        content = doc.page_content.strip()
        lines.append(f"[{index}] 来源: {source}\n{content}")

    return "\n\n".join(lines)
```

作用：把 RAG 检索结果转换成可注入 prompt 的文本。

如果希望更好地控制 token，可以改用：

- `self.rag_agent.context_manager.build_context(documents, query=input_text)`
- 或 `self.rag_agent.context_manager.format_documents_for_prompt(documents, input_text, instruction="...")`

### 4. 修改 `get_agent_response()` 注入检索结果

文件：`src/shuyixiao_agent/agents/multi_agent_collaboration.py`

在构建 prompt 时，加入 RAG 上下文：

```python
rag_context = self._build_rag_context(agent, input_text)
if rag_context:
    prompt += f"{rag_context}\n\n"
```

建议插入位置：在已有 `context` 拼接之后、`## 任务` 之前。

完整逻辑应变成：

```python
prompt = f"{agent.system_prompt}\n\n"

if context:
    prompt += "## 上下文信息\n"
    for key, value in context.items():
        prompt += f"- {key}: {value}\n"
    prompt += "\n"

rag_context = self._build_rag_context(agent, input_text)
if rag_context:
    prompt += f"{rag_context}\n\n"

prompt += f"## 任务\n{input_text}\n\n请提供你的专业见解："
```

作用：Agent 在回答任务前可以看到知识库检索结果。

### 5. 为法律合同审查团队开启 RAG

文件：`src/shuyixiao_agent/agents/multi_agent_collaboration.py`

建议至少给 `legal_researcher` 开启 RAG：

```python
AgentProfile(
    name="legal_researcher",
    role=AgentRole.ADVISOR,
    description="法律依据检索智能体",
    expertise=["法律检索", "法规分析", "案例检索", "RAG检索"],
    system_prompt="""...""",
    capabilities=["法条检索", "案例检索", "依据摘要", "来源标注"],
    constraints=["不直接给出最终签署建议", "不将依据改写为正式条款"],
    priority=8,
    enable_rag=True,
    rag_top_k=5,
    rag_mode="hybrid"
)
```

可选给 `compliance_checker` 开启 RAG，用于检索监管规则、企业制度、合规红线：

```python
enable_rag=True,
rag_top_k=5,
rag_mode="hybrid"
```

`drafting_specialist` 是否开启 RAG 取决于产品定位。如果它需要引用合同模板或条款范本，可以开启；如果只应基于上游 Agent 输出起草，建议先不开启，避免直接引用未经审查的模板。

## 使用方式示例

在法律合同审查入口或 demo 中初始化 RAG Agent：

```python
from src.shuyixiao_agent.gitee_ai_client import GiteeAIClient
from src.shuyixiao_agent.rag import RAGAgent
from src.shuyixiao_agent.agents.multi_agent_collaboration import (
    MultiAgentCollaboration,
    CollaborationMode,
    LegalContractReviewTeam,
)

llm_client = GiteeAIClient()

rag_agent = RAGAgent(
    collection_name="legal_contract_kb",
    use_reranker=True,
    retrieval_mode="hybrid"
)

rag_agent.add_documents_from_directory(
    "./docs/legal_kb",
    glob_pattern="**/*.*",
    show_progress=True
)

collaboration = MultiAgentCollaboration(
    llm_client=llm_client,
    mode=CollaborationMode.HIERARCHICAL,
    verbose=True,
    rag_agent=rag_agent
)

collaboration.register_agents(LegalContractReviewTeam.get_agents())

result = collaboration.collaborate("审查这份采购合同，重点关注付款、违约责任和争议解决条款")
print(result.final_output)
```

## 更推荐的增强方案

如果要让多智能体写作更稳定，可以在最小方案基础上继续做三点增强。

### 1. 按 Agent 定制检索查询

新增方法：

```python
def _build_rag_query(self, agent: AgentProfile, input_text: str, context: Optional[Dict[str, Any]]) -> str:
    if agent.name == "legal_researcher":
        return f"法律法规 司法解释 判例 合同审查 风险点：{input_text}"
    if agent.name == "compliance_checker":
        return f"监管规则 合规要求 企业红线：{input_text}"
    return input_text
```

然后 `_build_rag_context()` 使用 `_build_rag_query()` 的结果检索。

### 2. 把引用来源写入消息 metadata

修改 `send_message()`，允许传入 `metadata`：

```python
def send_message(
    self,
    sender: str,
    receiver: str,
    content: str,
    message_type: str = "task",
    metadata: Optional[Dict[str, Any]] = None
) -> Message:
    message = Message(
        sender=sender,
        receiver=receiver,
        content=content,
        message_type=message_type,
        timestamp=time.time(),
        metadata=metadata or {}
    )
```

在 RAG 检索后保存：

```python
metadata={"rag_sources": sources}
```

作用：`audit_recorder` 可以检查每个关键结论是否有来源。

### 3. 在最终结果 metadata 中保留 RAG 命中信息

在 `CollaborationResult.metadata` 中增加：

```python
{
    "rag_enabled_agents": ["legal_researcher", "compliance_checker"],
    "rag_collection_name": self.rag_agent.collection_name,
    "rag_sources": rag_sources
}
```

作用：前端或审计模块可以展示知识库命中来源。

## 不建议的实现方式

不建议在多智能体流程里直接把 `RAGAgent.query()` 当成一个普通 Agent 回答，因为它会完成“检索 + 生成”，可能导致：

- `legal_researcher` 的角色提示词被弱化。
- `contract_reviewer` 难以区分哪些内容来自知识库、哪些内容来自模型推理。
- `audit_recorder` 不容易追踪引用来源。
- `drafting_specialist` 可能直接使用未经风险审查的检索内容。

更稳妥的方式是：`RAGAgent.retrieve()` 只提供证据，具体判断和写作仍由对应 Agent 完成。

## 验证步骤

1. 准备法律知识库目录，例如 `docs/legal_kb/`，放入法规、合同模板、企业制度等文件。
2. 使用 `RAGAgent.add_documents_from_directory()` 导入知识库。
3. 注册 `LegalContractReviewTeam.get_agents()`。
4. 执行一条合同审查任务。
5. 检查 `legal_researcher` 输出是否包含知识库依据和来源。
6. 检查 `contract_reviewer` 汇总时是否能引用 `legal_researcher` 的依据。
7. 检查没有开启 RAG 的 Agent 是否仍按原流程工作。

## 文件级实施清单

需要修改：

- `src/shuyixiao_agent/agents/multi_agent_collaboration.py`

建议新增或更新示例：

- `examples/17_multi_agent_collaboration_demo.py`：增加法律合同审查 + RAG 知识库检索 demo。

可直接复用，不需要修改：

- `src/shuyixiao_agent/rag/rag_agent.py`
- `src/shuyixiao_agent/rag/vector_store.py`
- `src/shuyixiao_agent/rag/retrievers.py`
- `src/shuyixiao_agent/rag/context_manager.py`
- `src/shuyixiao_agent/rag/document_loader.py`

参考示例：

- `examples/07_rag_basic_usage.py`
- `examples/08_rag_file_upload.py`
- `docs/RAG (检索增强生成) 使用指南.md`
