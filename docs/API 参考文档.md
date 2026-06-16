# API 参考文档

本文档详细介绍了 shuyixiao-agent 项目的所有 API。

## 目录

- [Web/API 登录与知识库权限接口](#webapi-登录与知识库权限接口)
- [GiteeAIClient](#giteeaiclient)
- [SimpleAgent](#simpleagent)
- [ToolAgent](#toolagent)
- [配置](#配置)
- [工具](#工具)

---

## Web/API 登录与知识库权限接口

当前 Web 后端以 FastAPI 提供法律多智能体、RAG、知识库管理和合同解析接口。除 `/`、`/api/health`、`/api/auth/login` 等匿名白名单外，业务 `/api/*` 默认需要服务端 Session 登录。

### 认证接口

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
POST /api/auth/change-password
```

登录成功后服务端写入 HttpOnly Cookie `lpos_session`，响应体返回当前用户和 CSRF token。前端非 GET 请求需要携带 `X-CSRF-Token`。`POST /api/auth/logout` 会撤销服务端 session，`GET /api/auth/me` 用于页面初始化确认登录态。

### 知识库接口

新知识库接口统一使用 `kb_id`，后端通过 `resolve_knowledge_base(current_user, kb_id, action)` 校验权限后才会加载 RAG。

```text
GET /api/kb/collections
POST /api/kb/collections
GET /api/kb/collections/{kb_id}
DELETE /api/kb/collections/{kb_id}
POST /api/kb/collections/{kb_id}/texts
POST /api/kb/collections/{kb_id}/upload
GET /api/kb/collections/{kb_id}/documents
GET /api/kb/collections/{kb_id}/documents/{doc_id}
DELETE /api/kb/collections/{kb_id}/documents/{doc_id}
DELETE /api/kb/collections/{kb_id}/documents/batch
DELETE /api/kb/collections/{kb_id}/clear
```

权限规则：

- 公共知识库：所有已登录用户可读，只有管理员可写入、删除、清空。
- 用户知识库：仅 owner 用户本人可读写删；管理员默认不能通过普通接口访问他人用户知识库。
- `legacy_admin_only`：旧 Chroma collection 的迁移期状态，仅管理员可见。

创建用户知识库：

```json
{
  "scope": "user",
  "display_name": "我的合同模板",
  "description": "个人合同模板"
}
```

管理员创建公共知识库：

```json
{
  "scope": "public",
  "display_name": "法规案例库",
  "description": "公共法规、案例和企业制度"
}
```

### RAG 查询接口

```text
POST /api/rag/query
POST /api/rag/query/stream
```

推荐请求体使用授权 `kb_id`：

```json
{
  "question": "请检索违约责任条款的法律依据",
  "kb_id": "kb_xxxxxxxxxxxx",
  "top_k": 5,
  "use_history": true,
  "optimize_query": true
}
```

无权限或不存在的 `kb_id` 会在启动 RAG/LLM 前返回 403/404，避免自动创建空 Chroma collection。

### 多智能体协作接口

```text
POST /api/multi-agent/collaborate
POST /api/multi-agent/collaborate/stream
```

启用 RAG 时使用 `knowledge_base_ids` 和 `include_public_knowledge`：

```json
{
  "input_text": "请审查这份合同的违约责任条款",
  "team_type": "legal_contract_review",
  "mode": "hierarchical",
  "enable_rag": true,
  "knowledge_base_ids": ["kb_user_contract"],
  "include_public_knowledge": true,
  "context": {}
}
```

后端会先校验所有知识库权限；任一无权限 `kb_id` 会返回 403/404 且不启动 LLM。响应 metadata 会展示知识库来源，包括 `kb_id`、`scope`、`display_name`、`collection_name` 和 `source`。

### legacy 兼容接口

旧 RAG、上传审计、memory/history 接口短期保留，但 tenant_id 不再作为权限依据。无法安全映射到已登记 `kb_id` 的 legacy 请求返回 400/404/410，不会回退到直接操作 `collection_name`。

普通用户不能使用服务器 `file_path` 或 `directory_path`；服务器路径导入仅允许管理员在 `AUTH_ENABLE_SERVER_PATH_IMPORT=true` 且路径位于允许目录内时使用。`/api/uploads/audit` 对普通用户只返回自己的审计记录。

---

## GiteeAIClient

DashScope API 客户端，提供与 DashScope OpenAI 兼容 API 交互的能力。

### 初始化

```python
from src.shuyixiao_agent import GiteeAIClient

client = GiteeAIClient(
    api_key="your_api_key",           # 可选，默认从配置读取
    base_url="...",                    # 可选，API 基础 URL
    model="qwen-plus",                 # 可选，模型名称
    enable_failover=True               # 可选，是否启用故障转移
)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | `str` | 从配置读取 | DashScope API Key |
| `base_url` | `str` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API 基础 URL |
| `model` | `str` | `qwen-plus` | 使用的模型 |
| `enable_failover` | `bool` | `True` | 是否启用故障转移 |

### 方法

#### simple_chat()

最简单的单轮对话方法。

```python
response = client.simple_chat(
    user_message="你好",
    system_message="你是助手"  # 可选
)
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_message` | `str` | 是 | 用户消息 |
| `system_message` | `str` | 否 | 系统提示词 |

**返回：** `str` - 模型回复

---

#### chat_completion()

完整的聊天补全 API。

```python
response = client.chat_completion(
    messages=[
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "你好"}
    ],
    temperature=0.7,
    max_tokens=1000,
    stream=False,
    **kwargs
)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `messages` | `List[Dict]` | - | 消息列表 |
| `temperature` | `float` | `0.7` | 温度参数 (0-2) |
| `max_tokens` | `int` | `None` | 最大生成 token 数 |
| `stream` | `bool` | `False` | 是否流式输出 |
| `**kwargs` | - | - | 其他模型参数 |

**消息格式：**

```python
{
    "role": "user" | "assistant" | "system",
    "content": "消息内容"
}
```

**返回：** `Dict` - API 响应字典

**响应格式：**

```python
{
    "id": "...",
    "model": "...",
    "created": 1234567890,
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "回复内容"
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
    }
}
```

---

#### get_embedding()

获取文本的向量表示（如果模型支持）。

```python
embedding = client.get_embedding("你好世界")
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | `str` | 是 | 输入文本 |

**返回：** `List[float]` - 向量列表

---

## SimpleAgent

简单的对话 Agent，适合基础的问答场景。

### 初始化

```python
from src.shuyixiao_agent import SimpleAgent

agent = SimpleAgent(
    api_key="your_api_key",  # 可选
    model="Qwen/Qwen2.5-7B-Instruct",  # 可选
    system_message="你是助手"  # 可选
)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | `str` | 从配置读取 | API Key |
| `model` | `str` | 从配置读取 | 模型名称 |
| `system_message` | `str` | 默认提示词 | 系统提示词 |

### 方法

#### chat()

进行单轮对话。

```python
response = agent.chat("你好，请介绍一下你自己")
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_input` | `str` | 是 | 用户输入 |

**返回：** `str` - Agent 回复

---

#### chat_stream()

流式对话（未来扩展）。

```python
for chunk in agent.chat_stream("你好"):
    print(chunk, end="")
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_input` | `str` | 是 | 用户输入 |

**返回：** `Iterator[str]` - 回复片段迭代器

---

## ToolAgent

支持工具调用的 Agent，可以让 AI 使用工具完成复杂任务。

### 初始化

```python
from src.shuyixiao_agent.agents.tool_agent import ToolAgent

agent = ToolAgent(
    api_key="your_api_key",  # 可选
    model="Qwen/Qwen2.5-7B-Instruct",  # 可选
    tools=[],  # 可选，初始工具列表
    system_message="你是助手",  # 可选
    max_iterations=10  # 可选
)
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | `str` | 从配置读取 | API Key |
| `model` | `str` | 从配置读取 | 模型名称 |
| `tools` | `List[Dict]` | `[]` | 初始工具列表 |
| `system_message` | `str` | 默认提示词 | 系统提示词 |
| `max_iterations` | `int` | `10` | 最大迭代次数 |

### 方法

#### register_tool()

注册一个工具。

```python
def my_tool(arg1: str, arg2: int) -> str:
    return f"结果: {arg1} {arg2}"

agent.register_tool(
    name="my_tool",
    func=my_tool,
    description="工具描述",
    parameters={
        "type": "object",
        "properties": {
            "arg1": {
                "type": "string",
                "description": "参数1描述"
            },
            "arg2": {
                "type": "integer",
                "description": "参数2描述"
            }
        },
        "required": ["arg1", "arg2"]
    }
)
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | `str` | 是 | 工具名称 |
| `func` | `Callable` | 是 | 工具函数 |
| `description` | `str` | 是 | 工具描述 |
| `parameters` | `Dict` | 是 | 参数定义（JSON Schema） |

**参数定义格式：**

遵循 [JSON Schema](https://json-schema.org/) 规范：

```python
{
    "type": "object",
    "properties": {
        "param_name": {
            "type": "string" | "integer" | "number" | "boolean" | "array" | "object",
            "description": "参数描述",
            "default": "默认值",  # 可选
            "enum": ["选项1", "选项2"]  # 可选
        }
    },
    "required": ["必填参数名"]
}
```

---

#### run()

运行 Agent 处理用户输入。

```python
response = agent.run("现在几点了？")
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_input` | `str` | 是 | 用户输入 |

**返回：** `str` - Agent 回复

---

## 配置

### Settings 类

全局配置类，使用 `pydantic-settings` 管理。

```python
from src.shuyixiao_agent.config import settings

# 访问配置
print(settings.dashscope_api_key)
print(settings.dashscope_model)
```

### 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `dashscope_api_key` | `str` | `""` | API Key |
| `dashscope_base_url` | `str` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API 基础 URL |
| `dashscope_model` | `str` | `qwen-plus` | 默认模型 |
| `agent_max_iterations` | `int` | `10` | Agent 最大迭代次数 |
| `agent_verbose` | `bool` | `True` | 是否输出详细日志 |
| `request_timeout` | `int` | `60` | 请求超时时间（秒） |
| `max_retries` | `int` | `3` | 最大重试次数 |
| `enable_failover` | `bool` | `True` | 是否启用故障转移 |

### 配置方式

1. **环境变量：** 在 `.env` 文件中设置
2. **代码设置：** 直接修改 `settings` 对象

```python
settings.agent_max_iterations = 20
```

---

## 工具

### 内置工具

项目提供了一些内置的基础工具。

#### get_current_time()

获取当前时间。

```python
from src.shuyixiao_agent.tools import get_current_time

time_str = get_current_time()
# 返回: "2024-01-01 12:00:00"
```

---

#### calculate()

计算数学表达式。

```python
from src.shuyixiao_agent.tools import calculate

result = calculate("2 + 3 * 4")
# 返回: 14.0
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `expression` | `str` | 是 | 数学表达式 |

**支持的运算：**
- 加法 `+`
- 减法 `-`
- 乘法 `*`
- 除法 `/`
- 括号 `()`

---

#### search_wikipedia()

搜索维基百科（模拟实现）。

```python
from src.shuyixiao_agent.tools import search_wikipedia

result = search_wikipedia("人工智能")
```

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | `str` | 是 | 搜索关键词 |

**返回：** `str` - 搜索结果摘要

---

### 工具定义

使用 `TOOL_DEFINITIONS` 获取工具的标准定义：

```python
from src.shuyixiao_agent.tools.basic_tools import TOOL_DEFINITIONS

# 获取计算工具的定义
calc_def = TOOL_DEFINITIONS["calculate"]
print(calc_def)
# {
#     "name": "calculate",
#     "description": "计算数学表达式...",
#     "parameters": { ... }
# }
```

---

## 类型定义

### AgentState

SimpleAgent 的状态类型。

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_action: str
```

### ToolAgentState

ToolAgent 的状态类型。

```python
class ToolAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_action: str
    iterations: int
```

---

## 异常处理

### 常见异常

```python
try:
    agent = SimpleAgent()
    response = agent.chat("你好")
except ValueError as e:
    # 配置错误（如缺少 API Key）
    print(f"配置错误: {e}")
except Exception as e:
    # API 请求错误
    print(f"请求失败: {e}")
```

### 建议的错误处理

```python
from src.shuyixiao_agent import SimpleAgent
import time

def chat_with_retry(agent, message, max_retries=3):
    """带重试的对话"""
    for i in range(max_retries):
        try:
            return agent.chat(message)
        except Exception as e:
            if i == max_retries - 1:
                raise
            print(f"重试 {i+1}/{max_retries}...")
            time.sleep(2 ** i)  # 指数退避
```

---

## 更多信息

- [快速开始](快速开始.md)
- [示例代码](../examples/)
- [自定义工具](./custom_tools.md)
- [最佳实践](最佳实践.md)
