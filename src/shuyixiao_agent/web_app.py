"""
Web 应用服务

提供 FastAPI 服务来支持前端界面与 Agent 交互
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Response, Request, Cookie, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, TYPE_CHECKING
import os
import json
import re
import hashlib
import uuid
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from langchain_core.messages import HumanMessage

from .agents.simple_agent import SimpleAgent
from .agents.tool_agent import ToolAgent
from .agents.prompt_chaining_agent import (
    PromptChainingAgent,
    DocumentGenerationChain,
    CodeReviewChain,
    ResearchPlanningChain,
    StoryCreationChain,
    ProductAnalysisChain
)
from .agents.routing_agent import (
    RoutingAgent,
    RoutingStrategy,
    SmartAssistantRoutes,
    DeveloperAssistantRoutes
)
from .agents.parallelization_agent import (
    ParallelizationAgent,
    ParallelStrategy,
    AggregationMethod,
    ParallelTask,
    MultiPerspectiveAnalysis,
    ParallelTranslation,
    ParallelContentGeneration,
    ParallelCodeReview,
    ParallelResearch,
    ConsensusGenerator
)
from .agents.reflection_agent import (
    ReflectionAgent,
    ReflectionStrategy,
    ReflectionCriteria,
    ContentReflection,
    CodeReflection,
    AnalysisReflection,
    TranslationReflection
)
from .agents.tool_use_agent import (
    ToolUseAgent,
    ToolType,
    ToolDefinition,
    ToolParameter,
    ToolExecutionResult
)
from .agents.planning_agent import (
    PlanningAgent,
    PlanningStrategy,
    TaskStatus,
    TaskPriority,
    ProjectPlanningScenarios,
    PlanningTaskHandlers
)
from .agents.multi_agent_collaboration import (
    MultiAgentCollaboration,
    CollaborationMode,
    AgentRole,
    AgentProfile,
    SoftwareDevelopmentTeam,
    ResearchTeam,
    ContentCreationTeam,
    BusinessConsultingTeam,
    LegalContractReviewTeam
)
from .agents.memory_agent import (
    MemoryAgent,
    MemoryType,
    MemoryImportance,
    MemoryStrategy,
    Memory
)
from .tools.predefined_tools import PredefinedToolsRegistry
from .tools.basic_tools import get_basic_tools
from .config import settings
from .gitee_ai_client import GiteeAIClient
from .database_helper import DatabaseHelper
from .auth import storage as auth_storage
from .auth.dependencies import AUTH_COOKIE_NAME, get_current_user, resolve_user_from_session_token
from .auth.models import (
    AuthResponse,
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    SuccessResponse,
    UserPublic,
)
from .auth.password import generate_password_hash, verify_password
from .auth.sessions import (
    generate_csrf_token,
    generate_session_token,
    hash_token,
)
from .kb import registry as kb_registry
from .kb.permissions import resolve_knowledge_base
from .lpos import upload_registry

# RAG Agent 延迟导入，避免阻塞启动
# 使用 TYPE_CHECKING 来支持类型注解而不影响运行时
if TYPE_CHECKING:
    from .rag.rag_agent import RAGAgent

CompositeRAGRetriever = None

# 创建 FastAPI 应用
app = FastAPI(
    title="ShuYixiao Agent Web Interface",
    description="基于 LangGraph 和 DashScope 的智能 Agent Web 界面",
    version="0.1.0"
)


def parse_auth_allowed_origins(raw_origins: str) -> List[str]:
    """解析认证场景允许的 CORS 来源，避免 credentials 搭配通配来源。"""
    origins = [
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip() and origin.strip() != "*"
    ]
    if origins:
        return origins
    return ["http://127.0.0.1:8000", "http://localhost:8000"]


# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_auth_allowed_origins(settings.auth_allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ANONYMOUS_API_PATHS = {"/api/health", "/api/auth/login"}


@app.middleware("http")
async def require_api_authentication(request: Request, call_next):
    """除匿名白名单外，所有 /api/* 请求默认要求登录。"""
    path = request.url.path
    if request.method != "OPTIONS" and path.startswith("/api/") and path not in ANONYMOUS_API_PATHS:
        try:
            request.state.current_user = resolve_user_from_session_token(
                request.cookies.get(AUTH_COOKIE_NAME)
            )
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )

    return await call_next(request)


# 启动和关闭事件
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print("=" * 60)
    print("🚀 ShuYixiao Agent Web 应用正在启动...")
    print("=" * 60)
    
    # 初始化数据库（修复权限、清理临时文件）
    db_initialized = DatabaseHelper.initialize_database(
        db_path=settings.vector_db_path,
        cleanup_temp=True
    )
    
    if not db_initialized:
        print("⚠️  警告：数据库初始化失败，可能会遇到权限问题")
    
    # 显示数据库健康状态
    health = DatabaseHelper.check_database_health(settings.vector_db_path)
    print(f"📊 数据库状态: 存在={health['exists']}, 可读={health['readable']}, 可写={health['writable']}")
    print(f"📦 数据库大小: {health['size_mb']} MB, 文件数: {health['file_count']}")
    
    # 从数据库恢复知识库名称映射关系
    print("🔄 正在恢复知识库名称映射关系...")
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        
        client = chromadb.PersistentClient(
            path=settings.vector_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        collections = client.list_collections()
        
        # 从配置文件加载已知映射（用于旧数据）
        known_mappings = {}
        mapping_file = Path(__file__).parent.parent.parent / "knowledge_base_mappings.json"
        if mapping_file.exists():
            try:
                import json
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    known_mappings = config.get('mappings', {})
                    print(f"  📄 已加载配置文件: {len(known_mappings)} 个预定义映射")
            except Exception as e:
                print(f"  ⚠️  加载配置文件失败: {e}")
        
        # 如果配置文件不存在，使用默认映射
        if not known_mappings:
            known_mappings = {
                "kb_dd65ff91_kb": "舒一笑个人信息",  # 默认映射
            }
        
        for collection in collections:
            try:
                # 从collection的metadata中读取原始名称
                metadata = collection.metadata or {}
                original_name = metadata.get('original_name')
                
                if original_name and original_name != collection.name:
                    collection_name_mapping[original_name] = collection.name
                    print(f"  ✓ 恢复映射(从metadata): '{original_name}' -> '{collection.name}'")
                elif collection.name in known_mappings:
                    # 对于旧数据，使用预定义映射
                    original_name = known_mappings[collection.name]
                    collection_name_mapping[original_name] = collection.name
                    print(f"  ✓ 恢复映射(已知旧数据): '{original_name}' -> '{collection.name}'")
            except Exception as e:
                print(f"  ⚠️  处理collection {collection.name} 时出错: {e}")
        
        print(f"✅ 已恢复 {len(collection_name_mapping)} 个名称映射关系")
    except Exception as e:
        print(f"⚠️  恢复名称映射失败: {e}")
    
    print("=" * 60)
    print("✅ ShuYixiao Agent Web 应用已启动")
    print("=" * 60)
    print(f"API Key 已配置: {bool(settings.dashscope_api_key)}")
    print(f"使用模型: {settings.dashscope_model}")
    print(f"数据库路径: {settings.vector_db_path}")
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    print("👋 ShuYixiao Agent Web 应用已关闭")

# Agent 实例缓存
agents: Dict[str, Any] = {}

# RAG Agent 实例缓存
rag_agents: Dict[str, Any] = {}

# Prompt Chaining Agent 实例缓存
prompt_chaining_agent: Optional[PromptChainingAgent] = None

# Routing Agent 实例缓存
routing_agents: Dict[str, RoutingAgent] = {}

# Parallelization Agent 实例缓存
parallelization_agent: Optional[ParallelizationAgent] = None

# Reflection Agent 实例缓存
reflection_agent: Optional[ReflectionAgent] = None

# Memory Agent 实例缓存
memory_agents: Dict[str, MemoryAgent] = {}

# 会话消息历史（简单实现，生产环境应使用数据库）
session_histories: Dict[str, List[Dict[str, str]]] = {}

# 知识库名称映射（原始名称 -> 合法名称）
collection_name_mapping: Dict[str, str] = {}


def get_allowed_upload_extensions() -> set[str]:
    """获取允许上传的文件扩展名集合"""
    return {
        ext.strip().lower()
        for ext in settings.allowed_upload_extensions.split(",")
        if ext.strip()
    }


def authorize_server_path_access(raw_path: str, current_user: Dict[str, Any]) -> str:
    """校验服务器路径导入/解析权限，并限制在上传根目录内。"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="普通用户不能使用服务器路径导入或解析")

    if not settings.auth_enable_server_path_import:
        raise HTTPException(status_code=403, detail="服务器路径导入能力未启用")

    try:
        allowed_root = Path(settings.upload_root_path).expanduser().resolve()
        target_path = Path(raw_path).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail="服务器路径非法") from exc

    if target_path != allowed_root and allowed_root not in target_path.parents:
        raise HTTPException(status_code=403, detail="服务器路径不在允许目录内")

    return str(target_path)


def normalize_tenant_id(tenant_id: Optional[str] = None) -> str:
    """将租户 ID 规范化为安全的目录和集合名前缀"""
    raw_tenant_id = (tenant_id or "default").strip()
    safe_tenant_id = re.sub(r"[^a-zA-Z0-9_-]", "_", raw_tenant_id).strip("_-").lower()

    if not safe_tenant_id:
        safe_tenant_id = f"tenant_{hashlib.md5(raw_tenant_id.encode('utf-8')).hexdigest()[:8]}"
    if len(safe_tenant_id) > 64:
        tenant_hash = hashlib.md5(raw_tenant_id.encode("utf-8")).hexdigest()[:8]
        safe_tenant_id = f"{safe_tenant_id[:55]}_{tenant_hash}"
    if safe_tenant_id in {".", ".."}:
        safe_tenant_id = "default"

    return safe_tenant_id


def scope_collection_name(collection_name: Optional[str], tenant_id: Optional[str] = None) -> str:
    """按租户隔离知识库集合名，默认租户保持兼容"""
    normalized_tenant_id = normalize_tenant_id(tenant_id)
    base_collection_name = collection_name or "default"

    if normalized_tenant_id == "default":
        return base_collection_name
    if base_collection_name.startswith(f"{normalized_tenant_id}__"):
        return base_collection_name

    return f"{normalized_tenant_id}__{base_collection_name}"


def split_scoped_collection_name(collection_name: str) -> tuple[str, str]:
    """从租户作用域集合名中拆出租户 ID 和展示名称"""
    if "__" not in collection_name:
        return "default", collection_name

    possible_tenant_id, display_name = collection_name.split("__", 1)
    if possible_tenant_id == normalize_tenant_id(possible_tenant_id) and display_name:
        return possible_tenant_id, display_name

    return "default", collection_name


def ensure_upload_dir(*parts: str) -> Path:
    """确保上传目录存在，并限制在配置的上传根目录内"""
    upload_root = Path(settings.upload_root_path).resolve()
    target_dir = upload_root.joinpath(*parts).resolve()

    if upload_root != target_dir and upload_root not in target_dir.parents:
        raise HTTPException(status_code=400, detail="上传目录非法")

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def append_upload_audit_record(record: Dict[str, Any]) -> None:
    """追加上传审计记录到 JSONL 文件"""
    audit_file = ensure_upload_dir() / "upload_manifest.jsonl"
    audit_record = {
        "audit_id": uuid.uuid4().hex,
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        **record,
    }

    with open(audit_file, "a", encoding="utf-8") as output:
        output.write(json.dumps(audit_record, ensure_ascii=False) + "\n")


def read_upload_audit_records(
    tenant_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """读取最近的上传审计记录"""
    normalized_tenant_id = normalize_tenant_id(tenant_id) if tenant_id else None
    limit = max(1, min(limit, 200))
    audit_file = Path(settings.upload_root_path).resolve() / "upload_manifest.jsonl"

    if not audit_file.exists():
        return []

    records: List[Dict[str, Any]] = []
    with open(audit_file, "r", encoding="utf-8") as source:
        for line in source:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if normalized_tenant_id and record.get("tenant_id") != normalized_tenant_id:
                continue
            records.append(record)

    return list(reversed(records[-limit:]))


def validate_upload_file(upload_file: UploadFile) -> str:
    """校验上传文件名和扩展名，返回小写扩展名"""
    original_filename = Path(upload_file.filename or "").name
    if not original_filename:
        raise HTTPException(status_code=400, detail="上传文件名不能为空")

    suffix = Path(original_filename).suffix.lower()
    allowed_extensions = get_allowed_upload_extensions()
    if suffix not in allowed_extensions:
        allowed_display = ", ".join(sorted(allowed_extensions))
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {suffix or '无扩展名'}，允许类型: {allowed_display}"
        )

    return suffix


async def save_upload_file(upload_file: UploadFile, target_dir: Path) -> Dict[str, Any]:
    """保存浏览器上传文件到受控目录"""
    suffix = validate_upload_file(upload_file)
    original_filename = Path(upload_file.filename or "").name
    file_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:12]}"
    stored_file_path = (target_dir / f"{file_id}{suffix}").resolve()
    max_bytes = settings.max_upload_file_size_mb * 1024 * 1024
    total_size = 0

    try:
        with open(stored_file_path, "wb") as output:
            while True:
                chunk = await upload_file.read(1024 * 1024)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_bytes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"上传文件超过大小限制: {settings.max_upload_file_size_mb}MB"
                    )
                output.write(chunk)
    except Exception:
        if stored_file_path.exists():
            stored_file_path.unlink()
        raise
    finally:
        await upload_file.close()

    if total_size == 0:
        stored_file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="上传文件不能为空")

    return {
        "file_id": file_id,
        "original_filename": original_filename,
        "stored_file_path": str(stored_file_path),
        "file_size": total_size,
        "content_type": upload_file.content_type,
    }


def resolve_uploaded_file(file_id: str, *category_parts: str) -> Path:
    """根据 file_id 在指定上传分类下查找文件"""
    if not re.match(r"^[0-9]{8}_[0-9]{6}_[a-f0-9]{12}$", file_id):
        raise HTTPException(status_code=400, detail="上传文件 ID 格式非法")

    upload_root = Path(settings.upload_root_path).resolve()
    category_dir = upload_root.joinpath(*category_parts).resolve()
    if not category_dir.exists():
        raise HTTPException(status_code=404, detail="上传文件不存在")

    matches = list(category_dir.rglob(f"{file_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="上传文件不存在")
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="上传文件 ID 不唯一")

    resolved_path = matches[0].resolve()
    if upload_root != resolved_path and upload_root not in resolved_path.parents:
        raise HTTPException(status_code=400, detail="上传文件路径非法")

    return resolved_path


def parse_contract_file(file_path: str) -> Dict[str, Any]:
    """复用 DocumentLoader 解析合同文件文本"""
    from .rag.document_loader import DocumentLoader

    loader = DocumentLoader()
    documents = loader.load_file(file_path)
    text = "\n\n".join(doc.page_content for doc in documents)

    return {
        "text": text,
        "document_count": len(documents),
    }


def build_normalized_collection_name(name: str) -> str:
    """
    将用户输入的名称转换为符合 ChromaDB 要求的合法名称（不修改映射）
    
    ChromaDB 要求：
    - 3-512 个字符
    - 只包含 [a-zA-Z0-9._-]
    - 必须以 [a-zA-Z0-9] 开头和结尾
    
    Args:
        name: 用户输入的名称
        
    Returns:
        合法的集合名称
    """
    # 如果已经是合法名称，直接返回
    if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{1,510}[a-zA-Z0-9]$', name):
        return name

    # 生成一个基于原始名称的哈希值（作为唯一标识）
    name_hash = hashlib.md5(name.encode('utf-8')).hexdigest()[:8]
    
    # 尝试从名称中提取合法字符作为前缀（提高可读性）
    safe_prefix = re.sub(r'[^a-zA-Z0-9._-]', '', name)
    
    # 移除前后的非法字符
    safe_prefix = safe_prefix.strip('._-')
    
    # 如果没有合法字符或太短，使用有意义的默认前缀
    if not safe_prefix or len(safe_prefix) < 2:
        safe_prefix = "kb"  # knowledge base
    else:
        # 限制前缀长度，为哈希值留出空间
        safe_prefix = safe_prefix[:20]
    
    # 组合前缀和哈希值（哈希值确保唯一性，前缀提高可读性）
    normalized_name = f"{safe_prefix}_{name_hash}"
    
    # 最终验证：确保以字母或数字开头和结尾
    if not re.match(r'^[a-zA-Z0-9]', normalized_name):
        normalized_name = "kb_" + normalized_name
    if not re.match(r'[a-zA-Z0-9]$', normalized_name):
        normalized_name = normalized_name + "_kb"
    
    # 确保长度在范围内
    if len(normalized_name) < 3:
        normalized_name = "kb_" + name_hash + "_default"
    elif len(normalized_name) > 512:
        normalized_name = normalized_name[:512]
        # 确保截断后仍以字母或数字结尾
        if not re.match(r'[a-zA-Z0-9]$', normalized_name):
            normalized_name = normalized_name.rstrip('._-')

    return normalized_name


def normalize_collection_name(name: str) -> str:
    """
    将用户输入的名称转换为符合 ChromaDB 要求的合法名称
    
    ChromaDB 要求：
    - 3-512 个字符
    - 只包含 [a-zA-Z0-9._-]
    - 必须以 [a-zA-Z0-9] 开头和结尾
    
    Args:
        name: 用户输入的名称
        
    Returns:
        合法的集合名称
    """
    # 如果已经是合法名称，直接返回
    if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{1,510}[a-zA-Z0-9]$', name):
        return name
    
    # 如果名称已经被映射过，返回之前的映射
    if name in collection_name_mapping:
        return collection_name_mapping[name]
    
    normalized_name = build_normalized_collection_name(name)
    
    # 保存映射关系
    collection_name_mapping[name] = normalized_name
    
    print(f"[知识库名称] '{name}' -> '{normalized_name}'")
    
    return normalized_name


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    agent_type: str = "simple"  # simple, tool, rag, 或 prompt_chaining
    session_id: Optional[str] = "default"
    system_message: Optional[str] = None
    collection_name: Optional[str] = "default"  # RAG 专用：知识库集合名
    tenant_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    agent_type: str
    session_id: str


class SessionHistoryResponse(BaseModel):
    """会话历史响应模型"""
    session_id: str
    messages: List[Dict[str, str]]


class DocumentUploadRequest(BaseModel):
    """文档上传请求模型"""
    file_path: str
    collection_name: Optional[str] = "default"
    tenant_id: Optional[str] = "default"


class ContractParseRequest(BaseModel):
    """合同解析请求模型"""
    file_path: Optional[str] = None
    file_id: Optional[str] = None
    tenant_id: Optional[str] = "default"


class KnowledgeBaseCreateRequest(BaseModel):
    """知识库创建请求模型"""
    scope: str = "user"
    display_name: str
    description: Optional[str] = None


class KnowledgeBaseTextUploadRequest(BaseModel):
    """kb_id 驱动的知识库文本上传请求模型"""
    texts: List[str]
    metadatas: Optional[List[Dict[str, Any]]] = None


class KnowledgeBaseBatchDeleteRequest(BaseModel):
    """kb_id 驱动的知识库文档批量删除请求模型"""
    doc_ids: List[str]


class DirectoryUploadRequest(BaseModel):
    """目录上传请求模型"""
    directory_path: str
    glob_pattern: Optional[str] = "**/*.*"
    collection_name: Optional[str] = "default"
    tenant_id: Optional[str] = "default"


class TextUploadRequest(BaseModel):
    """文本上传请求模型"""
    texts: List[str]
    metadatas: Optional[List[Dict[str, Any]]] = None
    collection_name: Optional[str] = "default"
    tenant_id: Optional[str] = "default"


class RAGQueryRequest(BaseModel):
    """RAG 查询请求模型"""
    question: str
    kb_id: Optional[str] = None
    collection_name: Optional[str] = "default"
    tenant_id: Optional[str] = "default"
    session_id: Optional[str] = "default"
    top_k: Optional[int] = None
    use_history: bool = True
    optimize_query: bool = True


class PromptChainingRequest(BaseModel):
    """Prompt Chaining 请求模型"""
    input_text: str
    chain_type: str  # document_gen, code_review, research, story, product
    save_result: bool = True


class RoutingRequest(BaseModel):
    """Routing 请求模型"""
    input_text: str
    scenario: str = "smart_assistant"  # smart_assistant, developer_assistant, custom
    strategy: str = "hybrid"  # rule_based, keyword, llm_based, hybrid
    verbose: bool = False


class ParallelizationRequest(BaseModel):
    """Parallelization 请求模型"""
    scenario: str  # multi_perspective, translation, content_gen, code_review, research, consensus, custom
    input_text: str
    strategy: str = "full_parallel"  # full_parallel, batch_parallel, pipeline, vote, ensemble
    aggregation: str = "summarize"  # merge, concat, first, best, summarize, vote, consensus
    perspectives: Optional[List[str]] = None  # 用于 multi_perspective
    languages: Optional[List[str]] = None  # 用于 translation
    sections: Optional[List[str]] = None  # 用于 content_gen
    aspects: Optional[List[str]] = None  # 用于 research
    num_generations: Optional[int] = 5  # 用于 consensus
    batch_size: int = 3
    max_workers: int = 5


class ReflectionRequest(BaseModel):
    """Reflection 请求模型"""
    task: str
    initial_content: Optional[str] = None
    strategy: str = "simple"  # simple, multi_aspect, debate, expert
    scenario: Optional[str] = None  # content, code, analysis, translation
    max_iterations: int = 3
    score_threshold: float = 0.85
    expert_role: Optional[str] = None  # 用于 expert 策略
    expert_expertise: Optional[str] = None  # 用于 expert 策略


class ToolUseRequest(BaseModel):
    """Tool Use 请求模型"""
    user_input: str
    max_iterations: int = 5
    tool_type: Optional[str] = None  # 可选的工具类型过滤


class ToolExecuteRequest(BaseModel):
    """工具执行请求模型"""
    tool_name: str
    parameters: Dict[str, Any]


class PlanningRequest(BaseModel):
    """规划请求模型"""
    goal: str
    context: Optional[Dict[str, Any]] = None
    scenario: Optional[str] = None  # 预定义场景
    strategy: Optional[str] = "adaptive"  # 规划策略
    auto_execute: bool = False  # 是否自动执行


class PlanExecutionRequest(BaseModel):
    """计划执行请求模型"""
    plan_id: str


def get_agent(agent_type: str, system_message: Optional[str] = None):
    """获取或创建 Agent 实例"""
    cache_key = f"{agent_type}_{system_message or 'default'}"
    
    if cache_key not in agents:
        if agent_type == "simple":
            agents[cache_key] = SimpleAgent(
                system_message=system_message or "你是一个有帮助的AI助手，请友好、专业地回答用户的问题。"
            )
        elif agent_type == "tool":
            agent = ToolAgent(
                system_message=system_message or "你是一个有帮助的AI助手。你可以使用提供的工具来完成任务。"
            )
            # 注册基础工具
            for tool_info in get_basic_tools():
                agent.register_tool(
                    name=tool_info["name"],
                    func=tool_info["func"],
                    description=tool_info["description"],
                    parameters=tool_info["parameters"]
                )
            agents[cache_key] = agent
        elif agent_type == "tool_use":
            agent = ToolUseAgent(
                llm_client=GiteeAIClient(),
                verbose=True
            )
            # 注册所有预定义工具
            PredefinedToolsRegistry.register_all_tools(agent)
            agents[cache_key] = agent
        elif agent_type == "planning":
            agent = PlanningAgent(
                llm_client=GiteeAIClient(),
                strategy=PlanningStrategy.ADAPTIVE,
                verbose=True
            )
            # 注册所有预定义的任务处理器
            PlanningTaskHandlers.register_all_handlers(agent)
            agents[cache_key] = agent
        else:
            raise ValueError(f"未知的 agent 类型: {agent_type}")
    
    return agents[cache_key]


def get_rag_agent(collection_name: str = "default"):
    """获取或创建 RAG Agent 实例（延迟加载）"""
    # 转换为合法的集合名称
    normalized_name = normalize_collection_name(collection_name)
    
    # 使用转换后的名称作为缓存键
    if normalized_name not in rag_agents:
        # 延迟导入 RAG Agent
        from .rag.rag_agent import RAGAgent
        
        print(f"[信息] 首次创建 RAG Agent: {collection_name} (实际集合: {normalized_name})")
        rag_agents[normalized_name] = RAGAgent(
            collection_name=normalized_name,
            system_message="你是一个有帮助的AI助手。请基于提供的文档内容回答用户的问题。",
            use_reranker=True,
            retrieval_mode="hybrid",
            enable_query_optimization=True,
            enable_context_expansion=True,
            original_name=collection_name  # 传递原始名称用于持久化
        )
        print(f"[成功] RAG Agent 创建完成: {normalized_name}")
    
    return rag_agents[normalized_name]


def get_prompt_chaining_agent():
    """获取或创建 Prompt Chaining Agent 实例"""
    global prompt_chaining_agent
    
    if prompt_chaining_agent is None:
        llm_client = GiteeAIClient()
        prompt_chaining_agent = PromptChainingAgent(llm_client, verbose=False)
        print("[信息] Prompt Chaining Agent 已创建")
    
    return prompt_chaining_agent


def get_routing_agent(scenario: str = "smart_assistant", strategy: str = "hybrid"):
    """获取或创建 Routing Agent 实例"""
    cache_key = f"{scenario}_{strategy}"
    
    if cache_key not in routing_agents:
        llm_client = GiteeAIClient()
        agent = RoutingAgent(
            llm_client=llm_client,
            strategy=RoutingStrategy(strategy),
            verbose=False
        )
        
        # 根据场景注册路由
        if scenario == "smart_assistant":
            routes = SmartAssistantRoutes.get_routes(llm_client)
            agent.register_routes(routes)
        elif scenario == "developer_assistant":
            routes = DeveloperAssistantRoutes.get_routes(llm_client)
            agent.register_routes(routes)
        
        routing_agents[cache_key] = agent
        print(f"[信息] Routing Agent 已创建: {scenario} ({strategy})")
    
    return routing_agents[cache_key]


def get_parallelization_agent(max_workers: int = 5):
    """获取或创建 Parallelization Agent 实例"""
    global parallelization_agent
    
    if parallelization_agent is None or parallelization_agent.max_workers != max_workers:
        llm_client = GiteeAIClient()
        parallelization_agent = ParallelizationAgent(
            llm_client=llm_client,
            max_workers=max_workers,
            verbose=False
        )
        print(f"[信息] Parallelization Agent 已创建 (max_workers={max_workers})")
    
    return parallelization_agent


def get_reflection_agent(max_iterations: int = 3, score_threshold: float = 0.85):
    """获取或创建 Reflection Agent 实例"""
    global reflection_agent
    
    if (reflection_agent is None or 
        reflection_agent.max_iterations != max_iterations or
        reflection_agent.score_threshold != score_threshold):
        llm_client = GiteeAIClient()
        reflection_agent = ReflectionAgent(
            llm_client=llm_client,
            max_iterations=max_iterations,
            score_threshold=score_threshold,
            verbose=False
        )
        print(f"[信息] Reflection Agent 已创建 (max_iterations={max_iterations}, threshold={score_threshold})")
    
    return reflection_agent


def get_memory_agent(session_id: str = "default", max_memories: int = 1000):
    """获取或创建 Memory Agent 实例"""
    cache_key = f"{session_id}_{max_memories}"
    
    if cache_key not in memory_agents:
        llm_client = GiteeAIClient()
        
        # 为每个会话创建独立的存储路径
        storage_path = f"data/memories/memory_{session_id}.json"
        
        memory_agents[cache_key] = MemoryAgent(
            llm_client=llm_client,
            max_memories=max_memories,
            strategy=MemoryStrategy.HYBRID,
            verbose=False,
            storage_path=storage_path
        )
        print(f"[信息] Memory Agent 已创建 (session={session_id}, max_memories={max_memories})")
    
    return memory_agents[cache_key]


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """返回前端 HTML 页面"""
    print(f"[请求] GET / - 返回主页")
    
    static_dir = Path(__file__).parent / "static"
    html_file = static_dir / "index.html"
    
    print(f"[信息] 静态文件目录: {static_dir}")
    print(f"[信息] HTML 文件路径: {html_file}")
    print(f"[信息] 文件存在: {html_file.exists()}")
    
    if html_file.exists():
        content = html_file.read_text(encoding="utf-8")
        print(f"[成功] 返回 HTML 文件, 大小: {len(content)} 字符")
        return HTMLResponse(content=content)
    else:
        print(f"[警告] HTML 文件不存在: {html_file}")
        return HTMLResponse(content="""
        <html>
            <body>
                <h1>前端页面未找到</h1>
                <p>请确保 static/index.html 文件存在</p>
            </body>
        </html>
        """)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求（非流式）"""
    try:
        # 获取 Agent
        agent = get_agent(request.agent_type, request.system_message)
        
        # 初始化会话历史
        if request.session_id not in session_histories:
            session_histories[request.session_id] = []
        
        # 添加用户消息到历史
        session_histories[request.session_id].append({
            "role": "user",
            "content": request.message
        })
        
        # 调用 Agent
        if request.agent_type == "simple":
            response = agent.chat(request.message)
        else:  # tool agent
            response = agent.run(request.message)
        
        # 添加 AI 回复到历史
        session_histories[request.session_id].append({
            "role": "assistant",
            "content": response
        })
        
        return ChatResponse(
            response=response,
            agent_type=request.agent_type,
            session_id=request.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """处理聊天请求（流式）"""
    
    async def generate():
        try:
            # 初始化会话历史
            if request.session_id not in session_histories:
                session_histories[request.session_id] = []
            
            # 添加用户消息到历史
            session_histories[request.session_id].append({
                "role": "user",
                "content": request.message
            })
            
            # 构建消息历史
            messages = []
            
            # 添加系统消息
            system_message = request.system_message or "你是一个有帮助的AI助手，请友好、专业地回答用户的问题。"
            messages.append({
                "role": "system",
                "content": system_message
            })
            
            # 添加历史消息（最近10条）
            recent_history = session_histories[request.session_id][-10:]
            messages.extend(recent_history)
            
            # 创建客户端并调用流式API
            client = GiteeAIClient()
            full_response = ""
            
            # 对于工具调用模式，暂时使用非流式（因为需要处理工具调用）
            if request.agent_type == "tool":
                agent = get_agent(request.agent_type, request.system_message)
                response = agent.run(request.message)
                full_response = response
                
                # 一次性发送
                yield f"data: {json.dumps({'content': response, 'done': True}, ensure_ascii=False)}\n\n"
            else:
                # 简单对话模式使用流式
                stream = client.chat_completion(messages=messages, stream=True)
                
                for chunk in stream:
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        
                        if content:
                            full_response += content
                            # 发送数据块
                            yield f"data: {json.dumps({'content': content, 'done': False}, ensure_ascii=False)}\n\n"
                
                # 发送完成信号
                yield f"data: {json.dumps({'content': '', 'done': True}, ensure_ascii=False)}\n\n"
            
            # 添加完整回复到历史
            session_histories[request.session_id].append({
                "role": "assistant",
                "content": full_response
            })
            
        except Exception as e:
            error_msg = f"处理请求时出错: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg, 'done': True}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/history/{session_id}", response_model=SessionHistoryResponse)
async def get_history(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取会话历史"""
    scoped_session_id = _scope_user_session_id(current_user, session_id)
    if scoped_session_id not in session_histories:
        session_histories[scoped_session_id] = []
    
    return SessionHistoryResponse(
        session_id=session_id,
        messages=session_histories[scoped_session_id]
    )


@app.delete("/api/history/{session_id}")
async def clear_history(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """清除会话历史"""
    scoped_session_id = _scope_user_session_id(current_user, session_id)
    if scoped_session_id in session_histories:
        session_histories[scoped_session_id] = []
    return {"message": "历史已清除", "session_id": session_id}


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    print(f"[请求] GET /api/health - 健康检查")
    result = {
        "status": "healthy",
        "api_key_configured": bool(settings.dashscope_api_key),
        "model": settings.dashscope_model
    }
    print(f"[响应] 健康检查: {result}")
    return result


def _public_user(user: Dict[str, Any]) -> UserPublic:
    """转换为可返回给前端的用户信息。"""
    return UserPublic(
        id=user["id"],
        username=user["username"],
        display_name=user["display_name"],
        role=user["role"],
        is_active=bool(user["is_active"]),
        must_change_password=bool(user["must_change_password"]),
    )


def _ensure_initial_admin() -> None:
    """如果用户表为空且配置完整，则创建初始管理员。"""
    auth_storage.initialize_auth_storage()
    if auth_storage.count_users() > 0:
        return

    if not settings.initial_admin_username or not settings.initial_admin_password:
        return

    password_hash = generate_password_hash(settings.initial_admin_password)
    auth_storage.create_user(
        username=settings.initial_admin_username,
        display_name=settings.initial_admin_username,
        password_hash=password_hash,
        role="admin",
        is_active=True,
        must_change_password=False,
    )


@app.post("/api/auth/login", response_model=AuthResponse)
async def auth_login(
    request: LoginRequest,
    response: Response,
    raw_request: Request,
):
    """登录并创建服务端 Session。"""
    _ensure_initial_admin()
    user = auth_storage.get_user_by_username(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    password_valid = verify_password(
        request.password,
        user["password_hash"],
        salt=user["password_salt"],
        iterations=user["password_iterations"],
    )
    if not password_valid or not user["is_active"]:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    session_token = generate_session_token()
    csrf_token = generate_csrf_token()
    expires_at = datetime.now() + timedelta(hours=settings.session_expire_hours)
    auth_storage.create_session(
        id_hash=hash_token(session_token),
        user_id=user["id"],
        csrf_token_hash=hash_token(csrf_token),
        expires_at=expires_at.isoformat(timespec="seconds"),
        user_agent=raw_request.headers.get("user-agent"),
        ip_address=raw_request.client.host if raw_request.client else None,
    )
    auth_storage.mark_user_login(user["id"])

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=session_token,
        max_age=settings.session_expire_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )
    return AuthResponse(
        success=True,
        user=_public_user(user),
        csrf_token=csrf_token,
    )


@app.post("/api/auth/logout", response_model=SuccessResponse)
async def auth_logout(
    response: Response,
    session_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME),
):
    """注销当前 Session。"""
    if not session_token:
        raise HTTPException(status_code=401, detail="未登录或会话已失效")

    auth_storage.revoke_session(hash_token(session_token))
    response.delete_cookie(AUTH_COOKIE_NAME)
    return SuccessResponse(success=True, message="已注销")


@app.get("/api/auth/me", response_model=CurrentUserResponse)
async def auth_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """返回当前登录用户。"""
    return CurrentUserResponse(
        success=True,
        user=_public_user(current_user),
    )


@app.post("/api/auth/change-password", response_model=SuccessResponse)
async def auth_change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """修改当前用户密码。"""
    old_password_valid = verify_password(
        request.old_password,
        current_user["password_hash"],
        salt=current_user["password_salt"],
        iterations=current_user["password_iterations"],
    )
    if not old_password_valid:
        raise HTTPException(status_code=400, detail="旧密码错误")

    auth_storage.update_user_password(
        current_user["id"],
        generate_password_hash(request.new_password),
        must_change_password=False,
    )
    return SuccessResponse(success=True, message="密码已修改")


def _is_kb_visible_to_user(knowledge_base: Dict[str, Any], current_user: Dict[str, Any]) -> bool:
    """判断知识库是否应出现在当前用户列表中。"""
    scope = knowledge_base.get("scope")
    if scope == "public":
        return True
    if scope == "user":
        return knowledge_base.get("owner_user_id") == current_user.get("id")
    if scope == "legacy_admin_only":
        return current_user.get("role") == "admin"
    return False


def _list_visible_knowledge_bases(
    current_user: Dict[str, Any],
    scope: str = "all",
) -> List[Dict[str, Any]]:
    """列出当前用户可见知识库。"""
    normalized_scope = (scope or "all").strip().lower()
    if normalized_scope not in {"all", "public", "mine"}:
        raise HTTPException(status_code=400, detail="不支持的知识库列表范围")

    if normalized_scope == "public":
        candidates = kb_registry.list_knowledge_bases(scope="public")
    elif normalized_scope == "mine":
        candidates = kb_registry.list_knowledge_bases(
            scope="user",
            owner_user_id=current_user["id"],
        )
    else:
        candidates = kb_registry.list_knowledge_bases()

    visible_collections = [
        knowledge_base
        for knowledge_base in candidates
        if _is_kb_visible_to_user(knowledge_base, current_user)
    ]
    return [_with_document_count(collection) for collection in visible_collections]


def _with_document_count(collection: Dict[str, Any]) -> Dict[str, Any]:
    """给知识库元数据补充 Chroma 资料数，供前端列表展示。"""
    enriched = dict(collection)
    enriched["document_count"] = _get_collection_document_count(collection["collection_name"])
    return enriched


def _get_collection_document_count(collection_name: str) -> Optional[int]:
    """轻量读取 Chroma collection 数量，避免列表刷新时初始化 RAG Agent。"""
    try:
        agent = rag_agents.get(collection_name)
        if agent:
            return agent.get_document_count()

        client = _create_chroma_client()
        collection = client.get_collection(name=collection_name)
        return collection.count()
    except Exception:
        return None


def _get_kb_upload_dir(collection: Dict[str, Any], current_user: Dict[str, Any]) -> Path:
    """按知识库 scope 生成浏览器上传文件保存目录。"""
    if collection.get("scope") == "public":
        return ensure_upload_dir("public", collection["id"], "rag")

    owner_user_id = collection.get("owner_user_id") or current_user["id"]
    return ensure_upload_dir("users", owner_user_id, "rag", collection["id"])


def _scope_user_session_id(current_user: Dict[str, Any], session_id: Optional[str]) -> str:
    """将 legacy session_id 绑定到当前用户，避免跨用户复用同名会话。"""
    user_id = normalize_tenant_id(current_user["id"])
    normalized_session_id = normalize_tenant_id(session_id or "default")
    return f"{user_id}__{normalized_session_id}"


def _legacy_unmapped_collection_error() -> HTTPException:
    """legacy collection 无法安全映射到 kb_id 时的统一响应。"""
    return HTTPException(
        status_code=410,
        detail="legacy 资料库接口无法安全映射到已登记知识库，请使用 kb_id 接口或先完成迁移",
    )


def _legacy_collection_candidates(collection_name: str, tenant_id: str = "default") -> set[str]:
    """生成只读候选名，不写入全局 collection_name_mapping。"""
    requested_name = (collection_name or "").strip()
    if not requested_name:
        raise HTTPException(status_code=400, detail="资料库名称不能为空")

    scoped_name = scope_collection_name(requested_name, tenant_id)
    candidates = {requested_name, scoped_name}
    for name in list(candidates):
        mapped_name = collection_name_mapping.get(name)
        if mapped_name:
            candidates.add(mapped_name)
        candidates.add(build_normalized_collection_name(name))
    return candidates


def _resolve_legacy_knowledge_base(
    current_user: Dict[str, Any],
    collection_name: str,
    action: str,
    tenant_id: str = "default",
) -> Dict[str, Any]:
    """将 legacy collection_name 安全解析为已登记且授权的知识库。"""
    candidates = _legacy_collection_candidates(collection_name, tenant_id)
    matches = [
        knowledge_base
        for knowledge_base in kb_registry.list_knowledge_bases()
        if knowledge_base["collection_name"] in candidates
        or knowledge_base["collection_original_name"] in candidates
    ]
    if not matches:
        raise _legacy_unmapped_collection_error()

    resolved_matches: List[Dict[str, Any]] = []
    last_error: Optional[HTTPException] = None
    for knowledge_base in matches:
        try:
            resolved_matches.append(
                resolve_knowledge_base(current_user, knowledge_base["id"], action)
            )
        except HTTPException as exc:
            last_error = exc

    if not resolved_matches:
        raise last_error or HTTPException(status_code=404, detail="知识库不存在")
    if len(resolved_matches) > 1:
        raise HTTPException(status_code=400, detail="legacy 资料库名称映射不唯一")
    return resolved_matches[0]


def _legacy_mapping_item(collection: Dict[str, Any]) -> Dict[str, Any]:
    """将 registry 知识库转换为 legacy mappings/collections 响应项。"""
    doc_count = None
    try:
        agent = rag_agents.get(collection["collection_name"])
        doc_count = agent.get_document_count() if agent else None
    except Exception:
        doc_count = None

    return {
        "kb_id": collection["id"],
        "original_name": collection["display_name"],
        "normalized_name": collection["collection_name"],
        "collection_name": collection["collection_name"],
        "scope": collection["scope"],
        "tenant_id": collection.get("owner_user_id") or collection["scope"],
        "document_count": doc_count,
    }


@app.get("/api/kb/collections")
async def list_kb_collections(
    scope: str = "all",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """列出当前用户可见知识库。"""
    collections = _list_visible_knowledge_bases(current_user, scope)
    return {
        "success": True,
        "collections": collections,
        "total_count": len(collections),
        "scope": scope,
    }


@app.post("/api/kb/collections")
async def create_kb_collection(
    request: KnowledgeBaseCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建公共或用户知识库元数据。"""
    scope = request.scope.strip().lower()
    if scope not in {"public", "user"}:
        raise HTTPException(status_code=400, detail="仅支持创建 public 或 user 知识库")

    if scope == "public" and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="普通用户不能创建公共知识库")

    owner_user_id = current_user["id"] if scope == "user" else None
    try:
        collection = kb_registry.create_knowledge_base(
            scope=scope,
            owner_user_id=owner_user_id,
            display_name=request.display_name,
            description=request.description,
            created_by=current_user["id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="知识库名称已存在") from exc

    return {
        "success": True,
        "collection": collection,
    }


@app.get("/api/kb/collections/{kb_id}")
async def get_kb_collection(
    kb_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取授权知识库详情。"""
    collection = resolve_knowledge_base(current_user, kb_id, "read")
    return {
        "success": True,
        "collection": collection,
    }


@app.delete("/api/kb/collections/{kb_id}")
async def delete_kb_collection(
    kb_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除授权知识库 collection 并软删除元数据。"""
    collection = resolve_knowledge_base(current_user, kb_id, "delete")
    agent = get_rag_agent(collection["collection_name"])
    agent.delete_knowledge_base()
    _remove_collection_runtime_state(
        collection["collection_name"],
        collection["collection_original_name"],
    )
    deleted = kb_registry.soft_delete_knowledge_base(collection["id"])
    return {
        "success": deleted,
        "message": "知识库已删除" if deleted else "知识库未删除",
        "kb_id": kb_id,
        "collection_name": collection["collection_name"],
        "deleted": deleted,
    }


@app.post("/api/kb/collections/{kb_id}/texts")
async def upload_kb_texts(
    kb_id: str,
    request: KnowledgeBaseTextUploadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """通过 kb_id 向授权知识库写入文本。"""
    if not request.texts:
        raise HTTPException(status_code=400, detail="文本列表不能为空")

    collection = resolve_knowledge_base(current_user, kb_id, "write")
    try:
        agent = get_rag_agent(collection["collection_name"])
        count = agent.add_texts(request.texts, request.metadatas)
        total_documents = agent.get_document_count()
        append_upload_audit_record({
            "actor_user_id": current_user["id"],
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "usage_type": "kb_texts",
            "status": "success",
            "collection_name": collection["collection_name"],
            "display_name": collection["display_name"],
            "text_count": len(request.texts),
            "chunks_added": count,
            "total_documents": total_documents,
        })

        return {
            "success": True,
            "message": "文本上传成功",
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "display_name": collection["display_name"],
            "collection_name": collection["collection_name"],
            "chunks_added": count,
            "total_documents": total_documents,
        }
    except HTTPException:
        raise
    except Exception as e:
        append_upload_audit_record({
            "actor_user_id": current_user["id"],
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "usage_type": "kb_texts",
            "status": "failed",
            "collection_name": collection["collection_name"],
            "display_name": collection["display_name"],
            "text_count": len(request.texts),
            "error_message": str(e),
        })
        raise HTTPException(status_code=500, detail=f"上传文本失败: {str(e)}")


@app.post("/api/kb/collections/{kb_id}/upload")
async def upload_kb_file(
    kb_id: str,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """通过 kb_id 向授权知识库上传浏览器文件。"""
    collection = resolve_knowledge_base(current_user, kb_id, "write")
    saved_file: Optional[Dict[str, Any]] = None
    try:
        target_dir = _get_kb_upload_dir(collection, current_user)
        saved_file = await save_upload_file(file, target_dir)
        agent = get_rag_agent(collection["collection_name"])
        count = agent.add_documents_from_file(
            saved_file["stored_file_path"],
            show_progress=True,
        )
        total_documents = agent.get_document_count()
        append_upload_audit_record({
            "actor_user_id": current_user["id"],
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "usage_type": "kb_file_upload",
            "status": "success",
            "file_id": saved_file["file_id"],
            "original_filename": saved_file["original_filename"],
            "stored_file_path": saved_file["stored_file_path"],
            "file_size": saved_file["file_size"],
            "content_type": saved_file["content_type"],
            "collection_name": collection["collection_name"],
            "display_name": collection["display_name"],
            "chunks_added": count,
            "total_documents": total_documents,
        })

        return {
            "success": True,
            "message": "文件上传成功",
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "display_name": collection["display_name"],
            "collection_name": collection["collection_name"],
            "file_id": saved_file["file_id"],
            "original_filename": saved_file["original_filename"],
            "stored_file_path": saved_file["stored_file_path"],
            "file_size": saved_file["file_size"],
            "chunks_added": count,
            "total_documents": total_documents,
        }
    except HTTPException:
        raise
    except Exception as e:
        if saved_file:
            append_upload_audit_record({
                "actor_user_id": current_user["id"],
                "kb_id": collection["id"],
                "scope": collection["scope"],
                "usage_type": "kb_file_upload",
                "status": "failed",
                "file_id": saved_file["file_id"],
                "original_filename": saved_file["original_filename"],
                "stored_file_path": saved_file["stored_file_path"],
                "file_size": saved_file["file_size"],
                "content_type": saved_file["content_type"],
                "collection_name": collection["collection_name"],
                "display_name": collection["display_name"],
                "error_message": str(e),
            })
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")


@app.get("/api/kb/collections/{kb_id}/documents")
async def list_kb_documents(
    kb_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """通过 kb_id 列出授权知识库中的文档。"""
    collection = resolve_knowledge_base(current_user, kb_id, "read")
    try:
        agent = get_rag_agent(collection["collection_name"])
        documents = agent.list_documents(limit=limit, offset=offset)
        return {
            "success": True,
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "display_name": collection["display_name"],
            "collection_name": collection["collection_name"],
            "total_count": agent.get_document_count(),
            "documents": documents,
            "count": len(documents),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@app.delete("/api/kb/collections/{kb_id}/documents/batch")
async def batch_delete_kb_documents(
    kb_id: str,
    request: KnowledgeBaseBatchDeleteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """通过 kb_id 批量删除授权知识库中的文档。"""
    if not request.doc_ids:
        raise HTTPException(status_code=400, detail="文档 ID 列表不能为空")

    collection = resolve_knowledge_base(current_user, kb_id, "delete")
    try:
        agent = get_rag_agent(collection["collection_name"])
        success_count, failed_ids = agent.batch_delete_documents(request.doc_ids)
        return {
            "success": True,
            "message": "批量删除完成",
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "display_name": collection["display_name"],
            "collection_name": collection["collection_name"],
            "success_count": success_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids,
            "remaining_count": agent.get_document_count(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


@app.get("/api/kb/collections/{kb_id}/documents/{doc_id}")
async def get_kb_document(
    kb_id: str,
    doc_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """通过 kb_id 获取授权知识库中的单个文档。"""
    collection = resolve_knowledge_base(current_user, kb_id, "read")
    try:
        agent = get_rag_agent(collection["collection_name"])
        document = agent.get_document_by_id(doc_id)
        if document is None:
            raise HTTPException(status_code=404, detail="文档不存在")

        return {
            "success": True,
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "display_name": collection["display_name"],
            "collection_name": collection["collection_name"],
            "document": document,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档失败: {str(e)}")


@app.delete("/api/kb/collections/{kb_id}/documents/{doc_id}")
async def delete_kb_document(
    kb_id: str,
    doc_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """通过 kb_id 删除授权知识库中的单个文档。"""
    collection = resolve_knowledge_base(current_user, kb_id, "delete")
    try:
        agent = get_rag_agent(collection["collection_name"])
        success = agent.delete_document(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="文档不存在或删除失败")

        return {
            "success": True,
            "message": "文档已删除",
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "display_name": collection["display_name"],
            "collection_name": collection["collection_name"],
            "document_id": doc_id,
            "remaining_count": agent.get_document_count(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@app.delete("/api/kb/collections/{kb_id}/clear")
async def clear_kb_collection_documents(
    kb_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """通过 kb_id 清空授权知识库中的全部文档。"""
    collection = resolve_knowledge_base(current_user, kb_id, "delete")
    try:
        agent = get_rag_agent(collection["collection_name"])
        agent.clear_knowledge_base()
        return {
            "success": True,
            "message": "知识库已清空",
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "display_name": collection["display_name"],
            "collection_name": collection["collection_name"],
            "remaining_count": agent.get_document_count(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空知识库失败: {str(e)}")


@app.get("/api/uploads/audit")
async def get_upload_audit(
    tenant_id: Optional[str] = None,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取上传审计记录"""
    try:
        records = read_upload_audit_records(tenant_id=tenant_id, limit=limit)
        if current_user.get("role") != "admin":
            records = [
                record
                for record in records
                if record.get("actor_user_id") == current_user["id"]
            ]
        return {
            "records": records,
            "total_count": len(records),
            "tenant_id": normalize_tenant_id(tenant_id) if tenant_id else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取上传审计记录失败: {str(e)}")


# ========== RAG 相关接口 ==========

@app.post("/api/rag/upload/file")
async def upload_file(
    request: DocumentUploadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传单个文件到知识库"""
    try:
        file_path = authorize_server_path_access(request.file_path, current_user)
        collection = _resolve_legacy_knowledge_base(
            current_user,
            request.collection_name or "default",
            "write",
            request.tenant_id or "default",
        )
        tenant_id = normalize_tenant_id(request.tenant_id)
        normalized_name = collection["collection_name"]
        agent = get_rag_agent(normalized_name)
        count = agent.add_documents_from_file(
            file_path,
            show_progress=True
        )
        append_upload_audit_record({
            "actor_user_id": current_user["id"],
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "tenant_id": tenant_id,
            "usage_type": "rag_path_import",
            "status": "success",
            "collection_name": normalized_name,
            "original_collection_name": request.collection_name,
            "source_file_path": file_path,
            "chunks_added": count,
            "total_documents": agent.get_document_count(),
        })
        
        return {
            "message": "文件上传成功",
            "collection_name": normalized_name,  # 返回规范化后的名称
            "original_name": request.collection_name,  # 保留原始名称
            "tenant_id": tenant_id,
            "chunks_added": count,
            "total_documents": agent.get_document_count()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")


@app.post("/api/rag/upload/file-from-upload")
async def upload_file_from_upload(
    file: UploadFile = File(...),
    collection_name: str = Form("default"),
    tenant_id: str = Form("default"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """通过浏览器上传文件并写入知识库"""
    saved_file: Optional[Dict[str, Any]] = None
    normalized_tenant_id = normalize_tenant_id(tenant_id)
    collection = _resolve_legacy_knowledge_base(
        current_user,
        collection_name,
        "write",
        normalized_tenant_id,
    )
    normalized_name = collection["collection_name"]
    try:
        target_dir = ensure_upload_dir(normalized_tenant_id, "rag", normalized_name)
        saved_file = await save_upload_file(file, target_dir)

        agent = get_rag_agent(normalized_name)
        count = agent.add_documents_from_file(
            saved_file["stored_file_path"],
            show_progress=True
        )
        append_upload_audit_record({
            "actor_user_id": current_user["id"],
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "tenant_id": normalized_tenant_id,
            "usage_type": "rag_knowledge",
            "status": "success",
            "file_id": saved_file["file_id"],
            "original_filename": saved_file["original_filename"],
            "stored_file_path": saved_file["stored_file_path"],
            "file_size": saved_file["file_size"],
            "content_type": saved_file["content_type"],
            "collection_name": normalized_name,
            "original_collection_name": collection_name,
            "chunks_added": count,
            "total_documents": agent.get_document_count(),
        })

        return {
            "message": "文件上传成功",
            "file_id": saved_file["file_id"],
            "original_filename": saved_file["original_filename"],
            "stored_file_path": saved_file["stored_file_path"],
            "file_size": saved_file["file_size"],
            "collection_name": normalized_name,
            "original_name": collection_name,
            "tenant_id": normalized_tenant_id,
            "chunks_added": count,
            "total_documents": agent.get_document_count()
        }
    except HTTPException:
        raise
    except Exception as e:
        if saved_file:
            append_upload_audit_record({
                "tenant_id": normalized_tenant_id,
                "usage_type": "rag_knowledge",
                "status": "failed",
                "file_id": saved_file["file_id"],
                "original_filename": saved_file["original_filename"],
                "stored_file_path": saved_file["stored_file_path"],
                "file_size": saved_file["file_size"],
                "content_type": saved_file["content_type"],
                "collection_name": normalized_name,
                "original_collection_name": collection_name,
                "error_message": str(e),
            })
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")


@app.post("/api/rag/upload/directory")
async def upload_directory(
    request: DirectoryUploadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传整个目录到知识库"""
    try:
        directory_path = authorize_server_path_access(request.directory_path, current_user)
        collection = _resolve_legacy_knowledge_base(
            current_user,
            request.collection_name or "default",
            "write",
            request.tenant_id or "default",
        )
        tenant_id = normalize_tenant_id(request.tenant_id)
        normalized_name = collection["collection_name"]
        agent = get_rag_agent(normalized_name)
        count = agent.add_documents_from_directory(
            directory_path,
            request.glob_pattern,
            show_progress=True
        )
        append_upload_audit_record({
            "actor_user_id": current_user["id"],
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "tenant_id": tenant_id,
            "usage_type": "rag_directory_import",
            "status": "success",
            "collection_name": normalized_name,
            "original_collection_name": request.collection_name,
            "source_directory_path": directory_path,
            "glob_pattern": request.glob_pattern,
            "chunks_added": count,
            "total_documents": agent.get_document_count(),
        })
        
        return {
            "message": "目录上传成功",
            "collection_name": normalized_name,  # 返回规范化后的名称
            "original_name": request.collection_name,  # 保留原始名称
            "tenant_id": tenant_id,
            "chunks_added": count,
            "total_documents": agent.get_document_count()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传目录失败: {str(e)}")


@app.post("/api/rag/upload/texts")
async def upload_texts(
    request: TextUploadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传文本列表到知识库"""
    try:
        collection = _resolve_legacy_knowledge_base(
            current_user,
            request.collection_name or "default",
            "write",
            request.tenant_id or "default",
        )
        tenant_id = normalize_tenant_id(request.tenant_id)
        normalized_name = collection["collection_name"]
        agent = get_rag_agent(normalized_name)
        count = agent.add_texts(
            request.texts,
            request.metadatas
        )
        append_upload_audit_record({
            "actor_user_id": current_user["id"],
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "tenant_id": tenant_id,
            "usage_type": "rag_texts",
            "status": "success",
            "collection_name": normalized_name,
            "original_collection_name": request.collection_name,
            "text_count": len(request.texts),
            "chunks_added": count,
            "total_documents": agent.get_document_count(),
        })
        
        return {
            "message": "文本上传成功",
            "collection_name": normalized_name,  # 返回规范化后的名称
            "original_name": request.collection_name,  # 保留原始名称
            "tenant_id": tenant_id,
            "chunks_added": count,
            "total_documents": agent.get_document_count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传文本失败: {str(e)}")


@app.post("/api/rag/query")
async def rag_query(
    request: RAGQueryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """RAG 查询（非流式），优先使用 kb_id 授权解析。"""
    try:
        if request.kb_id:
            collection = resolve_knowledge_base(current_user, request.kb_id, "read")
        else:
            collection = _resolve_legacy_knowledge_base(
                current_user,
                request.collection_name or "default",
                "read",
                request.tenant_id or "default",
            )
        agent = get_rag_agent(collection["collection_name"])
        
        answer = agent.query(
            question=request.question,
            top_k=request.top_k,
            use_history=request.use_history,
            optimize_query=request.optimize_query,
            stream=False
        )
        
        return {
            "answer": answer,
            "kb_id": collection["id"],
            "scope": collection["scope"],
            "display_name": collection["display_name"],
            "collection_name": collection["collection_name"],
            "original_name": collection["display_name"],
            "tenant_id": collection.get("owner_user_id") or collection["scope"],
            "session_id": request.session_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@app.post("/api/rag/query/stream")
async def rag_query_stream(
    request: RAGQueryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """RAG 查询（流式），授权失败时不启动 RAG。"""
    if request.kb_id:
        collection = resolve_knowledge_base(current_user, request.kb_id, "read")
    else:
        collection = _resolve_legacy_knowledge_base(
            current_user,
            request.collection_name or "default",
            "read",
            request.tenant_id or "default",
        )
    
    async def generate():
        try:
            agent = get_rag_agent(collection["collection_name"])
            
            # 获取流式响应
            stream = agent.query(
                question=request.question,
                top_k=request.top_k,
                use_history=request.use_history,
                optimize_query=request.optimize_query,
                stream=True
            )
            
            # 发送流式数据
            for chunk in stream:
                yield f"data: {json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
            
            # 发送完成信号
            yield f"data: {json.dumps({'content': '', 'done': True}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            error_msg = f"查询失败: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg, 'done': True}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/rag/info/{collection_name}")
async def get_rag_info(
    collection_name: str,
    tenant_id: str = "default",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取 RAG 知识库信息"""
    try:
        collection = _resolve_legacy_knowledge_base(
            current_user,
            collection_name,
            "read",
            tenant_id,
        )
        agent = get_rag_agent(collection["collection_name"])
        
        return {
            "kb_id": collection["id"],
            "collection_name": collection["collection_name"],
            "original_name": collection["display_name"],
            "tenant_id": collection.get("owner_user_id") or collection["scope"],
            "scope": collection["scope"],
            "is_normalized": collection["collection_original_name"] != collection["collection_name"],
            "document_count": agent.get_document_count(),
            "retrieval_mode": agent.retrieval_mode
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取信息失败: {str(e)}")


@app.get("/api/rag/mappings")
async def get_collection_mappings(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取当前用户可见的知识库名称映射关系。"""
    try:
        visible_collections = _list_visible_knowledge_bases(current_user)
        mappings = [_legacy_mapping_item(collection) for collection in visible_collections]
        
        return {
            "mappings": mappings,
            "total_count": len(mappings)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取映射失败: {str(e)}")


def _create_chroma_client():
    """创建 ChromaDB 持久化客户端"""
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    return chromadb.PersistentClient(
        path=settings.vector_db_path,
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )


def _resolve_collection_for_delete(collection_name: str, tenant_id: str = "default") -> Dict[str, str]:
    """解析删除目标，兼容系统集合名和用户原始集合名"""
    requested_name = collection_name.strip()
    if not requested_name:
        raise HTTPException(status_code=400, detail="资料库名称不能为空")

    normalized_tenant_id = normalize_tenant_id(tenant_id)
    client = _create_chroma_client()
    collections = client.list_collections()
    existing_names = {collection.name for collection in collections}
    collection_by_name = {
        collection.name: collection
        for collection in collections
    }

    scoped_original_name = scope_collection_name(requested_name, tenant_id)
    scoped_normalized_name = collection_name_mapping.get(
        scoped_original_name,
        build_normalized_collection_name(scoped_original_name)
    )

    # 非默认租户下，用户输入展示名时优先删除租户作用域集合，避免误删默认租户同名资料库。
    if normalized_tenant_id != "default" and scoped_normalized_name in existing_names:
        resolved_tenant_id, display_name = split_scoped_collection_name(scoped_original_name)
        return {
            "tenant_id": resolved_tenant_id,
            "display_name": display_name,
            "original_name": scoped_original_name,
            "normalized_name": scoped_normalized_name
        }

    if requested_name in existing_names:
        normalized_name = requested_name
        original_name = requested_name
        collection = collection_by_name[normalized_name]
        metadata = collection.metadata or {}
        original_name = metadata.get("original_name") or requested_name
        resolved_tenant_id, display_name = split_scoped_collection_name(original_name)

        if normalized_tenant_id != "default" and resolved_tenant_id != normalized_tenant_id:
            raise HTTPException(status_code=404, detail="资料库不存在")
    else:
        normalized_name = scoped_normalized_name
        original_name = scoped_original_name
        resolved_tenant_id, display_name = split_scoped_collection_name(original_name)

    if normalized_name not in existing_names:
        raise HTTPException(status_code=404, detail="资料库不存在")

    return {
        "tenant_id": resolved_tenant_id,
        "display_name": display_name,
        "original_name": original_name,
        "normalized_name": normalized_name
    }


def _remove_collection_runtime_state(normalized_name: str, original_name: str) -> None:
    """删除资料库后清理运行态缓存和名称映射"""
    rag_agents.pop(normalized_name, None)

    stale_mapping_keys = [
        mapping_key
        for mapping_key, mapping_value in collection_name_mapping.items()
        if mapping_key == original_name or mapping_value == normalized_name
    ]
    for mapping_key in stale_mapping_keys:
        collection_name_mapping.pop(mapping_key, None)


@app.delete("/api/rag/collection/{collection_name}")
async def delete_rag_collection(
    collection_name: str,
    tenant_id: str = "default",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除 RAG 资料库集合本身"""
    try:
        collection = _resolve_legacy_knowledge_base(
            current_user,
            collection_name,
            "delete",
            tenant_id,
        )
        client = _create_chroma_client()
        client.delete_collection(name=collection["collection_name"])
        _remove_collection_runtime_state(
            collection["collection_name"],
            collection["collection_original_name"]
        )
        kb_registry.soft_delete_knowledge_base(collection["id"])

        return {
            "message": "资料库已删除",
            "kb_id": collection["id"],
            "collection_name": collection["collection_name"],
            "original_name": collection["display_name"],
            "tenant_id": collection.get("owner_user_id") or collection["scope"],
            "deleted": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除资料库失败: {str(e)}")


@app.delete("/api/rag/clear/{collection_name}")
async def clear_rag_knowledge_base(
    collection_name: str,
    tenant_id: str = "default",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """清空 RAG 知识库"""
    try:
        collection = _resolve_legacy_knowledge_base(
            current_user,
            collection_name,
            "delete",
            tenant_id,
        )
        agent = get_rag_agent(collection["collection_name"])
        agent.clear_knowledge_base()
        
        return {
            "message": "知识库已清空",
            "kb_id": collection["id"],
            "collection_name": collection["collection_name"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空知识库失败: {str(e)}")


@app.delete("/api/rag/history/{collection_name}/{session_id}")
async def clear_rag_history(
    collection_name: str,
    session_id: str,
    tenant_id: str = "default",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """清空 RAG 对话历史"""
    try:
        collection = _resolve_legacy_knowledge_base(
            current_user,
            collection_name,
            "read",
            tenant_id,
        )
        agent = get_rag_agent(collection["collection_name"])
        agent.clear_history()
        
        return {
            "message": "对话历史已清空",
            "kb_id": collection["id"],
            "collection_name": collection["collection_name"],
            "session_id": session_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空历史失败: {str(e)}")


@app.get("/api/rag/documents/{collection_name}")
async def list_documents(
    collection_name: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    tenant_id: str = "default",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """列出知识库中的文档"""
    try:
        collection = _resolve_legacy_knowledge_base(
            current_user,
            collection_name,
            "read",
            tenant_id,
        )
        agent = get_rag_agent(collection["collection_name"])
        documents = agent.list_documents(limit=limit, offset=offset)
        
        return {
            "kb_id": collection["id"],
            "collection_name": collection["collection_name"],
            "total_count": agent.get_document_count(),
            "documents": documents,
            "count": len(documents)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@app.get("/api/rag/document/{collection_name}/{doc_id}")
async def get_document(
    collection_name: str,
    doc_id: str,
    tenant_id: str = "default",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取单个文档内容"""
    try:
        collection = _resolve_legacy_knowledge_base(
            current_user,
            collection_name,
            "read",
            tenant_id,
        )
        agent = get_rag_agent(collection["collection_name"])
        document = agent.get_document_by_id(doc_id)
        
        if document is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return {
            "kb_id": collection["id"],
            "collection_name": collection["collection_name"],
            "document": document
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档失败: {str(e)}")


@app.delete("/api/rag/document/{collection_name}/{doc_id}")
async def delete_document(
    collection_name: str,
    doc_id: str,
    tenant_id: str = "default",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除指定文档"""
    try:
        collection = _resolve_legacy_knowledge_base(
            current_user,
            collection_name,
            "delete",
            tenant_id,
        )
        agent = get_rag_agent(collection["collection_name"])
        success = agent.delete_document(doc_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="文档不存在或删除失败")
        
        return {
            "message": "文档已删除",
            "kb_id": collection["id"],
            "collection_name": collection["collection_name"],
            "document_id": doc_id,
            "remaining_count": agent.get_document_count()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@app.get("/api/rag/collections")
async def list_collections(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """列出当前用户可见的 legacy 知识库集合。"""
    try:
        visible_collections = _list_visible_knowledge_bases(current_user)
        result = [_legacy_mapping_item(collection) for collection in visible_collections]
        return {
            "collections": result,
            "total_count": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取集合列表失败: {str(e)}")


class BatchDeleteRequest(BaseModel):
    """批量删除请求模型"""
    doc_ids: List[str]
    collection_name: str


@app.delete("/api/rag/documents/batch")
async def batch_delete_documents(
    request: BatchDeleteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量删除文档（物理删除）"""
    try:
        collection = _resolve_legacy_knowledge_base(
            current_user,
            request.collection_name,
            "delete",
        )
        agent = get_rag_agent(collection["collection_name"])
        
        # 使用优化的批量删除方法
        success_count, failed_ids = agent.batch_delete_documents(request.doc_ids)
        
        return {
            "message": f"批量删除完成（已物理删除）",
            "kb_id": collection["id"],
            "collection_name": collection["collection_name"],
            "success_count": success_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids,
            "remaining_count": agent.get_document_count()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


# ========== Prompt Chaining 相关接口 ==========

@app.post("/api/prompt-chaining/run")
async def run_prompt_chain(request: PromptChainingRequest):
    """运行提示链（非流式）"""
    try:
        agent = get_prompt_chaining_agent()
        
        # 根据类型选择对应的链
        chain_types = {
            "document_gen": ("文档生成", DocumentGenerationChain.get_steps()),
            "code_review": ("代码审查", CodeReviewChain.get_steps()),
            "research": ("研究规划", ResearchPlanningChain.get_steps()),
            "story": ("故事创作", StoryCreationChain.get_steps()),
            "product": ("产品分析", ProductAnalysisChain.get_steps())
        }
        
        if request.chain_type not in chain_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的链类型: {request.chain_type}"
            )
        
        chain_name, steps = chain_types[request.chain_type]
        
        # 创建并运行链
        agent.create_chain(request.chain_type, steps)
        result = agent.run_chain(request.chain_type, request.input_text)
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"链执行失败: {result.error_message}"
            )
        
        # 可选：保存结果到文件
        output_file = None
        if request.save_result:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"prompt_chain_{request.chain_type}_{timestamp}.md"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {chain_name}结果\n\n")
                f.write(f"**输入:** {request.input_text}\n\n")
                f.write(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                f.write(result.final_output)
        
        return {
            "success": True,
            "chain_type": request.chain_type,
            "chain_name": chain_name,
            "final_output": result.final_output,
            "total_steps": result.total_steps,
            "execution_time": result.execution_time,
            "output_file": output_file,
            "intermediate_results": [
                {
                    "step": r["step"],
                    "name": r["name"],
                    "output": r["output"]
                }
                for r in result.intermediate_results
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"执行提示链失败: {str(e)}")


@app.post("/api/prompt-chaining/run/stream")
async def run_prompt_chain_stream(request: PromptChainingRequest):
    """运行提示链（流式，逐步返回结果）"""
    
    async def generate():
        try:
            agent = get_prompt_chaining_agent()
            
            # 根据类型选择对应的链
            chain_types = {
                "document_gen": ("文档生成", DocumentGenerationChain.get_steps()),
                "code_review": ("代码审查", CodeReviewChain.get_steps()),
                "research": ("研究规划", ResearchPlanningChain.get_steps()),
                "story": ("故事创作", StoryCreationChain.get_steps()),
                "product": ("产品分析", ProductAnalysisChain.get_steps())
            }
            
            if request.chain_type not in chain_types:
                yield f"data: {json.dumps({'error': f'不支持的链类型: {request.chain_type}', 'done': True}, ensure_ascii=False)}\n\n"
                return
            
            chain_name, steps = chain_types[request.chain_type]
            
            # 发送链信息
            yield f"data: {json.dumps({'type': 'info', 'chain_name': chain_name, 'total_steps': len(steps)}, ensure_ascii=False)}\n\n"
            
            # 逐步执行链
            current_input = request.input_text
            llm_client = GiteeAIClient()
            
            for i, step in enumerate(steps, 1):
                # 发送步骤开始信号
                yield f"data: {json.dumps({'type': 'step_start', 'step': i, 'name': step.name, 'description': step.description}, ensure_ascii=False)}\n\n"
                
                # 格式化提示词
                prompt = step.prompt_template.format(input=current_input)
                
                # 调用 LLM（流式）
                full_output = ""
                stream = llm_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    stream=True
                )
                
                for chunk in stream:
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        
                        if content:
                            full_output += content
                            # 发送内容块
                            yield f"data: {json.dumps({'type': 'content', 'step': i, 'content': content}, ensure_ascii=False)}\n\n"
                
                # 应用转换函数（如果有）
                if step.transform_fn:
                    full_output = step.transform_fn(full_output)
                
                # 发送步骤完成信号
                yield f"data: {json.dumps({'type': 'step_complete', 'step': i, 'output': full_output}, ensure_ascii=False)}\n\n"
                
                # 下一步的输入是当前步的输出
                current_input = full_output
            
            # 可选：保存结果
            output_file = None
            if request.save_result:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"prompt_chain_{request.chain_type}_{timestamp}.md"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {chain_name}结果\n\n")
                    f.write(f"**输入:** {request.input_text}\n\n")
                    f.write(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")
                    f.write(current_input)
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'final_output': current_input, 'output_file': output_file}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"执行提示链失败: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg, 'done': True}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/prompt-chaining/types")
async def get_chain_types():
    """获取所有可用的提示链类型"""
    return {
        "chain_types": [
            {
                "id": "document_gen",
                "name": "文档生成",
                "description": "根据主题自动生成结构化技术文档",
                "steps": ["生成大纲", "撰写内容", "添加示例", "优化润色"],
                "input_hint": "请输入文档主题，例如：Python 异步编程入门"
            },
            {
                "id": "code_review",
                "name": "代码审查",
                "description": "系统化的代码审查和改进建议",
                "steps": ["理解代码", "检查问题", "提出建议", "生成报告"],
                "input_hint": "请粘贴要审查的代码"
            },
            {
                "id": "research",
                "name": "研究规划",
                "description": "将研究问题转化为系统化的研究计划",
                "steps": ["问题分析", "文献综述", "研究方法", "时间规划"],
                "input_hint": "请输入研究问题，例如：如何提高深度学习模型的训练效率？"
            },
            {
                "id": "story",
                "name": "故事创作",
                "description": "创意写作工作流，生成完整故事",
                "steps": ["构思情节", "角色塑造", "撰写初稿", "润色完善"],
                "input_hint": "请输入故事主题，例如：时间旅行者的困境"
            },
            {
                "id": "product",
                "name": "产品分析",
                "description": "系统化的产品需求分析和规划",
                "steps": ["需求理解", "功能设计", "技术方案", "实施计划"],
                "input_hint": "请描述产品需求，例如：一个帮助开发者快速搭建API的工具"
            }
        ]
    }


# ========== Routing Agent 相关接口 ==========

@app.post("/api/routing/route")
async def route_request(request: RoutingRequest):
    """执行路由决策和处理"""
    try:
        agent = get_routing_agent(request.scenario, request.strategy)
        result = agent.route(request.input_text)
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"路由失败: {result.error_message}"
            )
        
        return {
            "success": True,
            "route_name": result.route_name,
            "route_description": result.route_description,
            "output": result.handler_output,
            "confidence": result.confidence,
            "routing_reason": result.routing_reason,
            "execution_time": result.execution_time
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"路由执行失败: {str(e)}")


@app.get("/api/routing/routes")
async def get_routes(scenario: str = "smart_assistant"):
    """获取指定场景的所有路由信息"""
    try:
        # 创建一个临时 agent 来获取路由信息
        llm_client = GiteeAIClient()
        agent = RoutingAgent(llm_client=llm_client, strategy="hybrid", verbose=False)
        
        # 注册路由
        if scenario == "smart_assistant":
            routes = SmartAssistantRoutes.get_routes(llm_client)
        elif scenario == "developer_assistant":
            routes = DeveloperAssistantRoutes.get_routes(llm_client)
        else:
            raise HTTPException(status_code=400, detail=f"未知场景: {scenario}")
        
        agent.register_routes(routes)
        
        # 获取路由信息
        routes_info = agent.get_routes_info()
        
        return {
            "scenario": scenario,
            "routes": routes_info,
            "total_count": len(routes_info)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取路由信息失败: {str(e)}")


@app.get("/api/routing/scenarios")
async def get_scenarios():
    """获取所有可用的路由场景"""
    return {
        "scenarios": [
            {
                "id": "smart_assistant",
                "name": "智能助手",
                "description": "通用智能助手，支持代码生成、写作、分析、翻译等任务",
                "routes": [
                    "代码生成",
                    "内容创作",
                    "数据分析",
                    "翻译",
                    "问答",
                    "摘要总结"
                ]
            },
            {
                "id": "developer_assistant",
                "name": "开发者助手",
                "description": "专为开发者设计，支持代码审查、调试、优化、架构设计",
                "routes": [
                    "代码审查",
                    "调试",
                    "性能优化",
                    "架构设计"
                ]
            }
        ],
        "strategies": [
            {
                "id": "rule_based",
                "name": "规则路由",
                "description": "基于正则表达式的精确匹配"
            },
            {
                "id": "keyword",
                "name": "关键词路由",
                "description": "基于关键词的快速匹配"
            },
            {
                "id": "llm_based",
                "name": "LLM路由",
                "description": "使用大语言模型进行智能路由决策"
            },
            {
                "id": "hybrid",
                "name": "混合路由（推荐）",
                "description": "结合规则、关键词和LLM的优势"
            }
        ]
    }


# ========== Parallelization Agent 相关接口 ==========

@app.post("/api/parallelization/execute")
async def execute_parallelization(request: ParallelizationRequest):
    """执行并行化任务"""
    try:
        agent = get_parallelization_agent(request.max_workers)
        
        # 根据场景创建任务
        tasks = []
        
        if request.scenario == "multi_perspective":
            tasks = MultiPerspectiveAnalysis.create_tasks(
                request.input_text,
                perspectives=request.perspectives
            )
        
        elif request.scenario == "translation":
            tasks = ParallelTranslation.create_tasks(
                request.input_text,
                target_languages=request.languages
            )
        
        elif request.scenario == "content_gen":
            tasks = ParallelContentGeneration.create_tasks(
                request.input_text,
                sections=request.sections
            )
        
        elif request.scenario == "code_review":
            tasks = ParallelCodeReview.create_tasks(request.input_text)
        
        elif request.scenario == "research":
            tasks = ParallelResearch.create_tasks(
                request.input_text,
                aspects=request.aspects
            )
        
        elif request.scenario == "consensus":
            tasks = ConsensusGenerator.create_tasks(
                request.input_text,
                num_generations=request.num_generations or 5
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的场景类型: {request.scenario}"
            )
        
        # 执行并行任务
        result = agent.execute_parallel(
            tasks,
            strategy=ParallelStrategy(request.strategy),
            aggregation=AggregationMethod(request.aggregation),
            batch_size=request.batch_size
        )
        
        return {
            "success": result.success_count > 0,
            "aggregated_result": result.aggregated_result,
            "total_time": result.total_time,
            "parallel_time": result.parallel_time,
            "success_count": result.success_count,
            "failed_count": result.failed_count,
            "strategy": result.strategy,
            "aggregation_method": result.aggregation_method,
            "task_results": [
                {
                    "task_name": r.task_name,
                    "output": r.output,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "error_message": r.error_message
                }
                for r in result.task_results
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"执行并行任务失败: {str(e)}")


@app.post("/api/parallelization/execute/stream")
async def execute_parallelization_stream(request: ParallelizationRequest):
    """执行并行化任务（流式，实时返回进度）"""
    
    async def generate():
        try:
            agent = get_parallelization_agent(request.max_workers)
            
            # 根据场景创建任务
            tasks = []
            
            if request.scenario == "multi_perspective":
                tasks = MultiPerspectiveAnalysis.create_tasks(
                    request.input_text,
                    perspectives=request.perspectives
                )
            elif request.scenario == "translation":
                tasks = ParallelTranslation.create_tasks(
                    request.input_text,
                    target_languages=request.languages
                )
            elif request.scenario == "content_gen":
                tasks = ParallelContentGeneration.create_tasks(
                    request.input_text,
                    sections=request.sections
                )
            elif request.scenario == "code_review":
                tasks = ParallelCodeReview.create_tasks(request.input_text)
            elif request.scenario == "research":
                tasks = ParallelResearch.create_tasks(
                    request.input_text,
                    aspects=request.aspects
                )
            elif request.scenario == "consensus":
                tasks = ConsensusGenerator.create_tasks(
                    request.input_text,
                    num_generations=request.num_generations or 5
                )
            else:
                yield f"data: {json.dumps({'error': f'不支持的场景类型: {request.scenario}', 'done': True}, ensure_ascii=False)}\n\n"
                return
            
            # 发送任务信息
            yield f"data: {json.dumps({'type': 'info', 'total_tasks': len(tasks), 'scenario': request.scenario}, ensure_ascii=False)}\n\n"
            
            # 执行并行任务（这里我们使用一个简单的包装来发送进度）
            import time
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def execute_task_with_progress(task):
                start_time = time.time()
                try:
                    output = task.handler(task.input_data, agent.llm_client)
                    execution_time = time.time() - start_time
                    return {
                        "task_name": task.name,
                        "output": output,
                        "success": True,
                        "execution_time": execution_time,
                        "error_message": ""
                    }
                except Exception as e:
                    execution_time = time.time() - start_time
                    return {
                        "task_name": task.name,
                        "output": None,
                        "success": False,
                        "execution_time": execution_time,
                        "error_message": str(e)
                    }
            
            task_results = []
            parallel_start = time.time()
            
            with ThreadPoolExecutor(max_workers=request.max_workers) as executor:
                future_to_task = {
                    executor.submit(execute_task_with_progress, task): task
                    for task in tasks
                }
                
                for future in as_completed(future_to_task):
                    result = future.result()
                    task_results.append(result)
                    
                    # 发送任务完成事件
                    yield f"data: {json.dumps({'type': 'task_complete', 'task_name': result['task_name'], 'success': result['success'], 'completed': len(task_results), 'total': len(tasks)}, ensure_ascii=False)}\n\n"
            
            parallel_time = time.time() - parallel_start
            
            # 聚合结果
            from src.shuyixiao_agent.agents.parallelization_agent import TaskResult
            
            task_result_objects = [
                TaskResult(
                    task_name=r["task_name"],
                    output=r["output"],
                    success=r["success"],
                    execution_time=r["execution_time"],
                    error_message=r["error_message"]
                )
                for r in task_results
            ]
            
            aggregated = agent._aggregate_results(
                task_result_objects,
                AggregationMethod(request.aggregation)
            )
            
            total_time = time.time() - parallel_start
            success_count = sum(1 for r in task_results if r["success"])
            
            # 发送最终结果
            yield f"data: {json.dumps({'type': 'done', 'aggregated_result': aggregated, 'total_time': total_time, 'parallel_time': parallel_time, 'success_count': success_count, 'task_results': task_results}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"执行并行任务失败: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg, 'done': True}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/parallelization/scenarios")
async def get_parallelization_scenarios():
    """获取所有可用的并行化场景"""
    return {
        "scenarios": [
            {
                "id": "multi_perspective",
                "name": "多角度分析",
                "description": "从多个角度同时分析同一问题",
                "default_perspectives": [
                    "技术角度",
                    "商业角度",
                    "用户体验角度",
                    "风险和挑战角度",
                    "创新和机会角度"
                ],
                "input_hint": "请输入要分析的主题或问题"
            },
            {
                "id": "translation",
                "name": "并行翻译",
                "description": "同时将文本翻译成多种语言",
                "default_languages": ["英语", "日语", "法语", "德语", "西班牙语"],
                "input_hint": "请输入要翻译的文本"
            },
            {
                "id": "content_gen",
                "name": "并行内容生成",
                "description": "同时生成文档的不同章节",
                "default_sections": [
                    "简介和背景",
                    "核心概念",
                    "实践示例",
                    "最佳实践",
                    "常见问题"
                ],
                "input_hint": "请输入文档主题"
            },
            {
                "id": "code_review",
                "name": "并行代码审查",
                "description": "从多个维度同时审查代码",
                "aspects": [
                    "代码质量",
                    "性能分析",
                    "安全检查",
                    "最佳实践",
                    "测试建议"
                ],
                "input_hint": "请粘贴要审查的代码"
            },
            {
                "id": "research",
                "name": "并行研究",
                "description": "同时研究问题的不同方面",
                "default_aspects": [
                    "历史背景和发展",
                    "当前状态和趋势",
                    "主要方法和技术",
                    "实际应用案例",
                    "未来展望和挑战"
                ],
                "input_hint": "请输入研究问题"
            },
            {
                "id": "consensus",
                "name": "共识生成",
                "description": "通过多次生成寻找最佳答案",
                "num_generations": 5,
                "input_hint": "请输入问题或提示词"
            }
        ],
        "strategies": [
            {
                "id": "full_parallel",
                "name": "全并行（推荐）",
                "description": "所有任务同时执行，最大化并行效率"
            },
            {
                "id": "batch_parallel",
                "name": "批量并行",
                "description": "将任务分批执行，控制资源使用"
            },
            {
                "id": "pipeline",
                "name": "流水线",
                "description": "考虑任务依赖关系，分阶段并行"
            },
            {
                "id": "vote",
                "name": "投票",
                "description": "多个相同任务并行，结果投票决定"
            },
            {
                "id": "ensemble",
                "name": "集成",
                "description": "多个不同方法并行，结果融合"
            }
        ],
        "aggregation_methods": [
            {
                "id": "merge",
                "name": "合并",
                "description": "将所有结果合并到字典"
            },
            {
                "id": "concat",
                "name": "连接",
                "description": "将所有结果连接成文本"
            },
            {
                "id": "first",
                "name": "第一个",
                "description": "使用第一个完成的结果"
            },
            {
                "id": "best",
                "name": "最佳",
                "description": "选择质量最高的结果"
            },
            {
                "id": "summarize",
                "name": "总结（推荐）",
                "description": "使用LLM总结所有结果"
            },
            {
                "id": "vote",
                "name": "投票",
                "description": "选择最常见的结果"
            },
            {
                "id": "consensus",
                "name": "共识",
                "description": "使用LLM寻找共识"
            }
        ]
    }


# ========== Reflection Agent 相关接口 ==========

@app.post("/api/reflection/reflect")
async def reflect_and_improve(request: ReflectionRequest):
    """执行反思和改进（非流式）"""
    try:
        agent = get_reflection_agent(
            max_iterations=request.max_iterations,
            score_threshold=request.score_threshold
        )
        
        # 根据场景选择标准
        criteria = None
        context = {}
        
        if request.scenario == "content":
            criteria = ContentReflection.get_criteria()
        elif request.scenario == "code":
            criteria = CodeReflection.get_criteria()
        elif request.scenario == "analysis":
            criteria = AnalysisReflection.get_criteria()
        elif request.scenario == "translation":
            criteria = TranslationReflection.get_criteria()
        
        # 设置专家上下文
        if request.strategy == "expert":
            if request.expert_role:
                context['expert_role'] = request.expert_role
            if request.expert_expertise:
                context['expert_expertise'] = request.expert_expertise
        
        # 执行反思
        result = agent.reflect_and_improve(
            task=request.task,
            initial_content=request.initial_content,
            strategy=ReflectionStrategy(request.strategy),
            criteria=criteria,
            context=context
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"反思过程失败: {result.error_message}"
            )
        
        return {
            "success": True,
            "final_content": result.final_content,
            "total_iterations": result.total_iterations,
            "final_score": result.final_score,
            "improvement_summary": result.improvement_summary,
            "total_time": result.total_time,
            "reflection_history": [
                {
                    "iteration": r.iteration,
                    "score": r.score,
                    "critique": r.critique,
                    "improvements": r.improvements,
                    "timestamp": r.timestamp
                }
                for r in result.reflection_history
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"执行反思失败: {str(e)}")


@app.post("/api/reflection/reflect/stream")
async def reflect_and_improve_stream(request: ReflectionRequest):
    """执行反思和改进（流式，实时返回每轮迭代）"""
    
    async def generate():
        from datetime import datetime as dt_now
        
        try:
            agent = get_reflection_agent(
                max_iterations=request.max_iterations,
                score_threshold=request.score_threshold
            )
            
            # 根据场景选择标准
            criteria = None
            context = {}
            
            if request.scenario == "content":
                criteria = ContentReflection.get_criteria()
            elif request.scenario == "code":
                criteria = CodeReflection.get_criteria()
            elif request.scenario == "analysis":
                criteria = AnalysisReflection.get_criteria()
            elif request.scenario == "translation":
                criteria = TranslationReflection.get_criteria()
            
            # 设置专家上下文
            if request.strategy == "expert":
                if request.expert_role:
                    context['expert_role'] = request.expert_role
                if request.expert_expertise:
                    context['expert_expertise'] = request.expert_expertise
            
            # 发送初始信息
            yield f"data: {json.dumps({'type': 'info', 'max_iterations': request.max_iterations, 'strategy': request.strategy}, ensure_ascii=False)}\n\n"
            
            # 1. 生成初始内容（如果没有提供）
            if request.initial_content is None:
                yield f"data: {json.dumps({'type': 'generating', 'message': '正在生成初始内容...'}, ensure_ascii=False)}\n\n"
                
                initial_content = agent._generate_initial_content(request.task, context)
                
                yield f"data: {json.dumps({'type': 'initial_content', 'content': initial_content}, ensure_ascii=False)}\n\n"
            else:
                initial_content = request.initial_content
                yield f"data: {json.dumps({'type': 'initial_content', 'content': initial_content}, ensure_ascii=False)}\n\n"
            
            current_content = initial_content
            reflection_history = []
            
            # 2. 迭代反思和改进
            for iteration in range(1, request.max_iterations + 1):
                # 发送迭代开始信号
                yield f"data: {json.dumps({'type': 'iteration_start', 'iteration': iteration}, ensure_ascii=False)}\n\n"
                
                # 执行反思
                critique, score, improvements = agent._reflect(
                    content=current_content,
                    task=request.task,
                    strategy=ReflectionStrategy(request.strategy),
                    criteria=criteria,
                    context=context
                )
                
                # 发送反思结果
                yield f"data: {json.dumps({'type': 'reflection', 'iteration': iteration, 'critique': critique, 'score': score, 'improvements': improvements}, ensure_ascii=False)}\n\n"
                
                # 记录历史
                reflection_result = {
                    "iteration": iteration,
                    "content": current_content,
                    "critique": critique,
                    "score": score,
                    "improvements": improvements,
                    "timestamp": dt_now.now().isoformat()
                }
                reflection_history.append(reflection_result)
                
                # 检查是否达到质量阈值
                if score >= request.score_threshold:
                    yield f"data: {json.dumps({'type': 'threshold_reached', 'score': score, 'threshold': request.score_threshold}, ensure_ascii=False)}\n\n"
                    break
                
                # 如果不是最后一轮，进行改进
                if iteration < request.max_iterations:
                    yield f"data: {json.dumps({'type': 'improving', 'message': '正在改进内容...'}, ensure_ascii=False)}\n\n"
                    
                    current_content = agent._improve(
                        content=current_content,
                        critique=critique,
                        improvements=improvements,
                        task=request.task,
                        context=context
                    )
                    
                    yield f"data: {json.dumps({'type': 'improved_content', 'iteration': iteration, 'content': current_content}, ensure_ascii=False)}\n\n"
            
            # 3. 生成改进总结
            from src.shuyixiao_agent.agents.reflection_agent import ReflectionResult
            
            history_objects = [
                ReflectionResult(
                    iteration=r['iteration'],
                    content=r['content'],
                    critique=r['critique'],
                    score=r['score'],
                    improvements=r['improvements'],
                    timestamp=r['timestamp']
                )
                for r in reflection_history
            ]
            
            improvement_summary = agent._generate_improvement_summary(history_objects, request.task)
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'final_content': current_content, 'final_score': reflection_history[-1]['score'], 'improvement_summary': improvement_summary, 'total_iterations': len(reflection_history)}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"执行反思失败: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg, 'done': True}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/reflection/scenarios")
async def get_reflection_scenarios():
    """获取所有可用的反思场景"""
    return {
        "scenarios": [
            {
                "id": "content",
                "name": "内容创作",
                "description": "对文章、博客、报告等内容进行反思和改进",
                "criteria": [c.name for c in ContentReflection.get_criteria()],
                "input_hint": "请输入要改进的任务描述或内容"
            },
            {
                "id": "code",
                "name": "代码优化",
                "description": "对代码进行反思和优化",
                "criteria": [c.name for c in CodeReflection.get_criteria()],
                "input_hint": "请输入代码编写任务或粘贴要优化的代码"
            },
            {
                "id": "analysis",
                "name": "分析报告",
                "description": "对分析报告进行反思和完善",
                "criteria": [c.name for c in AnalysisReflection.get_criteria()],
                "input_hint": "请输入分析任务或要改进的分析报告"
            },
            {
                "id": "translation",
                "name": "翻译优化",
                "description": "对翻译结果进行反思和改进",
                "criteria": [c.name for c in TranslationReflection.get_criteria()],
                "input_hint": "请输入翻译任务或要改进的译文"
            }
        ],
        "strategies": [
            {
                "id": "simple",
                "name": "简单反思",
                "description": "由单一批评者进行反思，适合一般性改进"
            },
            {
                "id": "multi_aspect",
                "name": "多维度反思（推荐）",
                "description": "从多个维度进行深入反思，全面提升质量"
            },
            {
                "id": "debate",
                "name": "辩论式反思",
                "description": "正反两方辩论，从对立角度发现问题"
            },
            {
                "id": "expert",
                "name": "专家反思",
                "description": "由特定领域专家进行专业评估"
            }
        ],
        "default_settings": {
            "max_iterations": 3,
            "score_threshold": 0.85
        }
    }


# ==================== Tool Use Agent API ====================

@app.post("/api/tool-use/execute")
async def execute_tool_use_request(request: ToolUseRequest):
    """执行Tool Use请求"""
    try:
        agent = get_agent("tool_use")
        
        # 如果指定了工具类型，可以进行过滤（这里简化处理）
        result = await agent.process_request(
            user_input=request.user_input,
            max_iterations=request.max_iterations
        )
        
        return {
            "success": result["success"],
            "message": result["message"],
            "results": result["results"],
            "total_iterations": result.get("total_iterations", 0),
            "execution_history": agent.get_execution_history()[-10:]  # 最近10条记录
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool Use执行失败: {str(e)}")


@app.post("/api/tool-use/execute/stream")
async def execute_tool_use_request_stream(request: ToolUseRequest):
    """流式执行Tool Use请求"""
    async def generate():
        try:
            agent = get_agent("tool_use")
            
            yield f"data: {json.dumps({'type': 'start', 'message': '开始处理请求'}, ensure_ascii=False)}\n\n"
            
            # 简化的流式处理，实际应该在agent中实现真正的流式
            result = await agent.process_request(
                user_input=request.user_input,
                max_iterations=request.max_iterations
            )
            
            # 逐步发送结果
            for i, step_result in enumerate(result.get("results", []), 1):
                yield f"data: {json.dumps({'type': 'step', 'step': i, 'result': step_result}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'type': 'complete', 'final_result': result}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/api/tool-use/execute-tool")
async def execute_single_tool(request: ToolExecuteRequest):
    """执行单个工具"""
    try:
        agent = get_agent("tool_use")
        
        result = await agent.execute_tool(
            tool_name=request.tool_name,
            parameters=request.parameters
        )
        
        return {
            "success": result.success,
            "result": result.result,
            "error_message": result.error_message,
            "execution_time": result.execution_time,
            "tool_name": result.tool_name,
            "parameters": result.parameters
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工具执行失败: {str(e)}")


@app.get("/api/tool-use/tools")
async def get_available_tools(tool_type: Optional[str] = None):
    """获取可用工具列表"""
    try:
        agent = get_agent("tool_use")
        
        # 转换工具类型
        filter_type = None
        if tool_type:
            try:
                filter_type = ToolType(tool_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的工具类型: {tool_type}")
        
        tools = agent.get_available_tools(tool_type=filter_type)
        
        return {
            "tools": tools,
            "total_count": len(tools),
            "tool_types": [t.value for t in ToolType]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工具列表失败: {str(e)}")


@app.get("/api/tool-use/history")
async def get_tool_execution_history():
    """获取工具执行历史"""
    try:
        agent = get_agent("tool_use")
        
        history = agent.get_execution_history()
        statistics = agent.get_tool_statistics()
        
        return {
            "history": history,
            "statistics": statistics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取执行历史失败: {str(e)}")


@app.delete("/api/tool-use/history")
async def clear_tool_execution_history():
    """清除工具执行历史"""
    try:
        agent = get_agent("tool_use")
        agent.clear_history()
        
        return {"message": "执行历史已清除"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除历史失败: {str(e)}")


@app.get("/api/tool-use/scenarios")
async def get_tool_use_scenarios():
    """获取Tool Use场景信息"""
    return {
        "scenarios": [
            {
                "id": "file_operations",
                "name": "文件操作",
                "description": "读取、写入、管理文件和目录",
                "example_tasks": [
                    "读取配置文件内容",
                    "保存数据到文件",
                    "列出目录中的文件",
                    "获取文件信息"
                ]
            },
            {
                "id": "network_requests",
                "name": "网络请求",
                "description": "发送HTTP请求，获取网络数据",
                "example_tasks": [
                    "获取API数据",
                    "检查网站状态",
                    "提交表单数据",
                    "测试网络连通性"
                ]
            },
            {
                "id": "data_processing",
                "name": "数据处理",
                "description": "解析、过滤、聚合各种格式的数据",
                "example_tasks": [
                    "解析JSON数据",
                    "过滤符合条件的记录",
                    "按字段聚合统计",
                    "排序数据"
                ]
            },
            {
                "id": "system_monitoring",
                "name": "系统监控",
                "description": "获取系统信息和性能数据",
                "example_tasks": [
                    "查看CPU使用率",
                    "检查内存状态",
                    "获取磁盘信息",
                    "列出运行进程"
                ]
            },
            {
                "id": "calculations",
                "name": "计算工具",
                "description": "数学计算、统计分析、单位转换",
                "example_tasks": [
                    "计算数学表达式",
                    "统计数据分析",
                    "单位换算",
                    "科学计算"
                ]
            },
            {
                "id": "text_processing",
                "name": "文本处理",
                "description": "文本分析、搜索替换、格式化",
                "example_tasks": [
                    "分析文本统计",
                    "搜索替换内容",
                    "提取文本模式",
                    "计算文本哈希"
                ]
            }
        ],
        "tool_types": [
            {
                "id": "file_operation",
                "name": "文件操作",
                "description": "文件和目录的读写操作"
            },
            {
                "id": "network_request",
                "name": "网络请求",
                "description": "HTTP请求和网络通信"
            },
            {
                "id": "data_processing",
                "name": "数据处理",
                "description": "数据解析、转换和分析"
            },
            {
                "id": "system_info",
                "name": "系统信息",
                "description": "系统状态和性能监控"
            },
            {
                "id": "calculation",
                "name": "计算工具",
                "description": "数学计算和统计分析"
            },
            {
                "id": "text_processing",
                "name": "文本处理",
                "description": "文本分析和处理工具"
            }
        ],
        "features": [
            "🔧 智能工具选择：自动分析需求并选择最合适的工具",
            "⚡ 高效执行：支持同步和异步工具执行",
            "📊 执行追踪：详细记录每个工具的执行过程和结果",
            "🔄 链式调用：支持多个工具协作完成复杂任务",
            "🛠️ 丰富工具库：内置20+常用工具，覆盖多个领域",
            "📈 统计分析：提供工具使用统计和性能分析"
        ]
    }


# Planning Agent API 端点

@app.post("/api/planning/create")
async def create_planning(request: PlanningRequest):
    """创建规划计划"""
    try:
        agent = get_agent("planning")
        
        # 如果指定了预定义场景，使用场景模板
        if request.scenario:
            scenarios = ProjectPlanningScenarios.get_all_scenarios(agent.llm_client)
            if request.scenario in scenarios:
                scenario_data = scenarios[request.scenario]
                
                # 创建基于模板的计划
                from .agents.planning_agent import ExecutionPlan, Task
                import time
                
                plan_id = f"plan_{int(time.time())}"
                plan = ExecutionPlan(
                    id=plan_id,
                    name=f"{scenario_data['name']} - {request.goal}",
                    description=f"基于 {scenario_data['description']} 为目标 '{request.goal}' 创建的计划",
                    strategy=PlanningStrategy(scenario_data['strategy'])
                )
                
                # 创建任务
                for task_data in scenario_data['template_tasks']:
                    task = Task(
                        id=task_data['id'],
                        name=task_data['name'],
                        description=task_data['description'],
                        priority=TaskPriority(task_data['priority']),
                        estimated_duration=task_data['estimated_duration'],
                        dependencies=task_data.get('dependencies', []),
                        metadata=task_data.get('metadata', {})
                    )
                    
                    # 设置任务处理器
                    task_type = task_data.get('task_type', 'default')
                    if task_type in agent.task_handlers:
                        task.handler = agent.task_handlers[task_type]
                    else:
                        task.handler = agent._default_task_handler
                    
                    plan.add_task(task)
                
                # 保存计划
                agent.plans[plan.id] = plan
                
                result_data = {
                    "success": True,
                    "plan": plan.to_dict(),
                    "message": f"成功创建基于 {scenario_data['name']} 的规划计划"
                }
                
                # 如果需要自动执行
                if request.auto_execute:
                    execution_result = agent.execute_plan(plan.id)
                    result_data["execution_result"] = execution_result.to_dict()
                
                return result_data
            else:
                raise HTTPException(status_code=400, detail=f"未知的场景类型: {request.scenario}")
        else:
            # 使用LLM创建自定义计划
            result = agent.create_plan_from_goal(request.goal, request.context)
            
            result_data = {
                "success": result.success,
                "plan": result.plan.to_dict() if result.plan else None,
                "error_message": result.error_message,
                "execution_log": result.execution_log
            }
            
            # 如果需要自动执行
            if request.auto_execute and result.success:
                execution_result = agent.execute_plan(result.plan.id)
                result_data["execution_result"] = execution_result.to_dict()
            
            return result_data
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建规划失败: {str(e)}")


@app.post("/api/planning/execute")
async def execute_planning(request: PlanExecutionRequest):
    """执行规划计划"""
    try:
        agent = get_agent("planning")
        result = agent.execute_plan(request.plan_id)
        
        return {
            "success": result.success,
            "plan": result.plan.to_dict() if result.plan else None,
            "execution_log": result.execution_log,
            "error_message": result.error_message,
            "total_duration": result.total_duration,
            "completed_tasks": result.completed_tasks,
            "failed_tasks": result.failed_tasks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行规划失败: {str(e)}")


@app.post("/api/planning/execute/stream")
async def execute_planning_stream(request: PlanExecutionRequest):
    """流式执行规划计划"""
    try:
        agent = get_agent("planning")
        
        def generate_progress():
            def progress_callback(progress: float, current_task):
                progress_data = {
                    "type": "progress",
                    "progress": progress,
                    "current_task": current_task.to_dict() if current_task else None,
                    "timestamp": datetime.now().isoformat()
                }
                return f"data: {json.dumps(progress_data, ensure_ascii=False)}\n\n"
            
            # 开始执行
            yield f"data: {json.dumps({'type': 'start', 'message': '开始执行规划'}, ensure_ascii=False)}\n\n"
            
            result = agent.execute_plan(request.plan_id, progress_callback)
            
            # 发送最终结果
            final_data = {
                "type": "complete",
                "success": result.success,
                "plan": result.plan.to_dict() if result.plan else None,
                "execution_log": result.execution_log,
                "error_message": result.error_message,
                "total_duration": result.total_duration,
                "completed_tasks": result.completed_tasks,
                "failed_tasks": result.failed_tasks
            }
            yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_progress(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式执行规划失败: {str(e)}")


@app.get("/api/planning/plans")
async def get_all_plans():
    """获取所有规划计划"""
    try:
        agent = get_agent("planning")
        plans = agent.list_plans()
        
        return {
            "success": True,
            "plans": [plan.to_dict() for plan in plans],
            "count": len(plans)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取规划列表失败: {str(e)}")


@app.get("/api/planning/plan/{plan_id}")
async def get_plan_detail(plan_id: str):
    """获取规划计划详情"""
    try:
        agent = get_agent("planning")
        plan = agent.get_plan(plan_id)
        
        if not plan:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")
        
        return {
            "success": True,
            "plan": plan.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取规划详情失败: {str(e)}")


@app.delete("/api/planning/plan/{plan_id}")
async def delete_plan(plan_id: str):
    """删除规划计划"""
    try:
        agent = get_agent("planning")
        success = agent.delete_plan(plan_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")
        
        return {
            "success": True,
            "message": f"成功删除计划: {plan_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除规划失败: {str(e)}")


@app.get("/api/planning/scenarios")
async def get_planning_scenarios():
    """获取所有预定义的规划场景"""
    try:
        agent = get_agent("planning")
        scenarios = ProjectPlanningScenarios.get_all_scenarios(agent.llm_client)
        
        # 转换为前端友好的格式
        scenario_list = []
        for scenario_id, scenario_data in scenarios.items():
            scenario_info = {
                "id": scenario_id,
                "name": scenario_data["name"],
                "description": scenario_data["description"],
                "strategy": scenario_data["strategy"],
                "task_count": len(scenario_data["template_tasks"]),
                "estimated_duration": sum(task["estimated_duration"] for task in scenario_data["template_tasks"]),
                "features": [
                    f"📋 {len(scenario_data['template_tasks'])} 个预定义任务",
                    f"⏱️ 预计耗时 {sum(task['estimated_duration'] for task in scenario_data['template_tasks']) // 3600} 小时",
                    f"🎯 策略: {scenario_data['strategy']}",
                    f"🔄 自动依赖管理"
                ]
            }
            scenario_list.append(scenario_info)
        
        return {
            "success": True,
            "scenarios": scenario_list,
            "count": len(scenario_list)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取规划场景失败: {str(e)}")


# ==================== LPOS APIs ====================

@app.post("/api/lpos/contracts/upload")
async def upload_contract(
    file: UploadFile = File(...),
    parse_after_upload: bool = Form(True),
    tenant_id: str = Form("default"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """上传合同或法律材料文件，并可立即解析文本"""
    saved_file: Optional[Dict[str, Any]] = None
    normalized_tenant_id = normalize_tenant_id(tenant_id)
    try:
        target_dir = ensure_upload_dir("users", current_user["id"], "lpos", "contracts")
        saved_file = await save_upload_file(file, target_dir)
        upload_registry.register_uploaded_file(
            file_id=saved_file["file_id"],
            owner_user_id=current_user["id"],
            tenant_id=normalized_tenant_id,
            original_filename=saved_file["original_filename"],
            stored_file_path=saved_file["stored_file_path"],
            file_size=saved_file["file_size"],
            content_type=saved_file["content_type"],
        )

        metadata = {
            "file_id": saved_file["file_id"],
            "tenant_id": normalized_tenant_id,
            "original_filename": saved_file["original_filename"],
            "stored_file_path": saved_file["stored_file_path"],
            "file_size": saved_file["file_size"],
            "content_type": saved_file["content_type"],
            "document_count": 0,
        }
        text = ""

        if parse_after_upload:
            parsed = parse_contract_file(saved_file["stored_file_path"])
            text = parsed["text"]
            metadata["document_count"] = parsed["document_count"]

        append_upload_audit_record({
            "tenant_id": normalized_tenant_id,
            "usage_type": "lpos_contract",
            "status": "success",
            "file_id": saved_file["file_id"],
            "original_filename": saved_file["original_filename"],
            "stored_file_path": saved_file["stored_file_path"],
            "file_size": saved_file["file_size"],
            "content_type": saved_file["content_type"],
            "parse_after_upload": parse_after_upload,
            "document_count": metadata["document_count"],
            "text_length": len(text),
        })

        return {
            "success": True,
            "file_id": saved_file["file_id"],
            "tenant_id": normalized_tenant_id,
            "original_filename": saved_file["original_filename"],
            "stored_file_path": saved_file["stored_file_path"],
            "file_size": saved_file["file_size"],
            "text": text,
            "metadata": metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        if saved_file:
            append_upload_audit_record({
                "tenant_id": normalized_tenant_id,
                "usage_type": "lpos_contract",
                "status": "failed",
                "file_id": saved_file["file_id"],
                "original_filename": saved_file["original_filename"],
                "stored_file_path": saved_file["stored_file_path"],
                "file_size": saved_file["file_size"],
                "content_type": saved_file["content_type"],
                "parse_after_upload": parse_after_upload,
                "error_message": str(e),
            })
        raise HTTPException(status_code=500, detail=f"合同上传失败: {str(e)}")


@app.post("/api/lpos/contracts/parse")
async def parse_contract(
    request: ContractParseRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """解析合同文件文本"""
    try:
        tenant_id = normalize_tenant_id(request.tenant_id)
        if request.file_id:
            record = upload_registry.resolve_uploaded_file_for_user(
                request.file_id,
                current_user=current_user,
                tenant_id=tenant_id,
            )
            upload_root = Path(settings.upload_root_path).expanduser().resolve()
            stored_path = Path(record["stored_file_path"]).expanduser().resolve()
            if upload_root != stored_path and upload_root not in stored_path.parents:
                raise HTTPException(status_code=400, detail="上传文件路径非法")
            if not stored_path.is_file():
                raise HTTPException(status_code=404, detail="上传文件不存在")
            file_path = str(stored_path)
        elif request.file_path:
            file_path = authorize_server_path_access(request.file_path, current_user)
        else:
            raise HTTPException(status_code=400, detail="请提供 file_path 或 file_id")

        parsed = parse_contract_file(file_path)

        return {
            "success": True,
            "text": parsed["text"],
            "metadata": {
                "file_path": file_path,
                "file_id": request.file_id,
                "tenant_id": tenant_id,
                "document_count": parsed["document_count"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合同解析失败: {str(e)}")


# ==================== Multi-Agent Collaboration APIs ====================

class MultiAgentCollaborationRequest(BaseModel):
    """多智能体协作请求"""
    input_text: str
    team_type: str
    mode: Optional[str] = "hierarchical"
    context: Optional[Dict[str, Any]] = None
    enable_rag: bool = False
    knowledge_base_ids: Optional[List[str]] = None
    include_public_knowledge: bool = False
    collection_name: Optional[str] = None
    tenant_id: Optional[str] = "default"
    uploaded_file_path: Optional[str] = None
    legal_task_type: Optional[str] = None


def _get_multi_agent_team(team_type: str) -> tuple[List[AgentProfile], str]:
    """按团队类型返回 Agent 列表和展示名。"""
    if team_type == "software_dev":
        return SoftwareDevelopmentTeam.get_agents(), "软件开发团队"
    if team_type == "research":
        return ResearchTeam.get_agents(), "研究团队"
    if team_type == "content":
        return ContentCreationTeam.get_agents(), "内容创作团队"
    if team_type == "business":
        return BusinessConsultingTeam.get_agents(), "商业咨询团队"
    if team_type == "legal_contract_review":
        return LegalContractReviewTeam.get_agents(), "法律合同审查团队"
    raise HTTPException(status_code=400, detail=f"未知的团队类型: {team_type}")


def _knowledge_base_metadata_item(collection: Dict[str, Any]) -> Dict[str, Any]:
    """返回可暴露给前端和报告的知识库来源元数据。"""
    return {
        "kb_id": collection["id"],
        "scope": collection["scope"],
        "display_name": collection["display_name"],
        "collection_name": collection["collection_name"],
        "source": collection.get("collection_original_name") or collection["collection_name"],
    }


def _dedupe_knowledge_bases(collections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按 kb_id 去重，保持首次出现顺序。"""
    deduped = []
    seen = set()
    for collection in collections:
        kb_id = collection["id"]
        if kb_id in seen:
            continue
        seen.add(kb_id)
        deduped.append(collection)
    return deduped


def _resolve_multi_agent_knowledge_bases(
    current_user: Dict[str, Any],
    request: MultiAgentCollaborationRequest,
) -> List[Dict[str, Any]]:
    """解析多智能体请求中的知识库，确保授权早于 RAG/LLM 运行时。"""
    if not request.enable_rag:
        return []

    collections: List[Dict[str, Any]] = []
    for kb_id in request.knowledge_base_ids or []:
        normalized_kb_id = (kb_id or "").strip()
        if not normalized_kb_id:
            raise HTTPException(status_code=400, detail="knowledge_base_ids 不能包含空值")
        collections.append(resolve_knowledge_base(current_user, normalized_kb_id, "read"))

    if request.include_public_knowledge:
        for public_collection in kb_registry.list_knowledge_bases(scope="public"):
            collections.append(
                resolve_knowledge_base(current_user, public_collection["id"], "read")
            )

    if not collections and request.collection_name:
        collections.append(
            _resolve_legacy_knowledge_base(
                current_user,
                request.collection_name,
                "read",
                request.tenant_id or "default",
            )
        )

    return _dedupe_knowledge_bases(collections)


def _build_multi_agent_rag_agent(collections: List[Dict[str, Any]]):
    """根据授权知识库数量构建单库 RAGAgent 或多库 CompositeRAGRetriever。"""
    if not collections:
        return None
    if len(collections) == 1:
        return get_rag_agent(collections[0]["collection_name"])

    global CompositeRAGRetriever
    composite_retriever_cls = CompositeRAGRetriever
    if composite_retriever_cls is None:
        from .rag.composite_retriever import CompositeRAGRetriever as composite_retriever_cls
        CompositeRAGRetriever = composite_retriever_cls
    return composite_retriever_cls(collections, agent_factory=get_rag_agent)


def _multi_agent_kb_metadata(collections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """生成多智能体响应中的知识库 metadata。"""
    return {
        "knowledge_bases": [
            _knowledge_base_metadata_item(collection)
            for collection in collections
        ]
    }


class MemoryStoreRequest(BaseModel):
    """存储记忆请求"""
    content: str
    memory_type: str = "semantic"
    importance: int = 3
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    session_id: str = "default"


class MemoryRetrieveRequest(BaseModel):
    """检索记忆请求"""
    query: str
    memory_types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    top_k: int = 5
    min_importance: Optional[int] = None
    session_id: str = "default"


class MemoryChatRequest(BaseModel):
    """基于记忆的对话请求"""
    user_input: str
    use_memory_types: Optional[List[str]] = None
    session_id: str = "default"


class WorkingMemoryUpdateRequest(BaseModel):
    """工作记忆更新请求"""
    key: str
    value: Any
    session_id: str = "default"


@app.get("/api/multi-agent/teams")
async def get_collaboration_teams():
    """获取可用的协作团队类型"""
    teams = {
        "software_dev": {
            "name": "软件开发团队",
            "description": "产品经理、系统架构师、开发工程师、QA 工程师协同工作",
            "agents": [
                {"name": "产品经理", "role": "coordinator", "expertise": ["需求分析", "产品规划"]},
                {"name": "系统架构师", "role": "specialist", "expertise": ["系统架构", "技术选型"]},
                {"name": "后端开发工程师", "role": "executor", "expertise": ["后端开发", "API设计"]},
                {"name": "前端开发工程师", "role": "executor", "expertise": ["前端开发", "UI实现"]},
                {"name": "QA工程师", "role": "reviewer", "expertise": ["测试", "质量保证"]}
            ],
            "use_cases": ["需求分析与设计", "系统架构设计", "功能开发规划", "代码质量审查"]
        },
        "research": {
            "name": "研究团队",
            "description": "研究负责人、理论专家、数据科学家、实验研究者、同行评审专家协同研究",
            "agents": [
                {"name": "研究负责人", "role": "coordinator", "expertise": ["研究规划", "团队协调"]},
                {"name": "理论研究者", "role": "specialist", "expertise": ["理论分析", "模型构建"]},
                {"name": "数据科学家", "role": "specialist", "expertise": ["数据分析", "统计建模"]},
                {"name": "实验研究者", "role": "executor", "expertise": ["实验设计", "数据收集"]},
                {"name": "同行评审专家", "role": "reviewer", "expertise": ["学术评审", "质量控制"]}
            ],
            "use_cases": ["研究课题设计", "数据分析方案", "实验方案设计", "论文质量评审"]
        },
        "content": {
            "name": "内容创作团队",
            "description": "内容策略师、撰写者、编辑、SEO专家协同创作",
            "agents": [
                {"name": "内容策略师", "role": "coordinator", "expertise": ["内容策划", "受众分析"]},
                {"name": "内容撰写者", "role": "executor", "expertise": ["写作", "文案"]},
                {"name": "内容编辑", "role": "reviewer", "expertise": ["编辑", "校对"]},
                {"name": "SEO专家", "role": "advisor", "expertise": ["SEO", "关键词优化"]}
            ],
            "use_cases": ["文章策划与创作", "营销文案撰写", "技术文档编写", "内容SEO优化"]
        },
        "business": {
            "name": "商业咨询团队",
            "description": "首席顾问、商业分析师、财务顾问、实施专家、质量保证专家协同咨询",
            "agents": [
                {"name": "首席顾问", "role": "coordinator", "expertise": ["战略规划", "项目管理"]},
                {"name": "商业分析师", "role": "specialist", "expertise": ["业务分析", "市场研究"]},
                {"name": "财务顾问", "role": "specialist", "expertise": ["财务分析", "成本效益"]},
                {"name": "实施专家", "role": "executor", "expertise": ["方案实施", "变革管理"]},
                {"name": "质量保证专家", "role": "reviewer", "expertise": ["质量审核", "风险评估"]}
            ],
            "use_cases": ["业务战略规划", "市场分析报告", "财务可行性分析", "项目实施方案"]
        },
        "legal_contract_review": {
            "name": "法律合同审查团队",
            "description": "合同审查、风险识别、法律检索、合规检查、修改建议和审计留痕",
            "agents": [
                {"name": "contract_reviewer", "role": "coordinator", "expertise": ["合同审查", "任务拆解", "风险汇总", "审查结论"]},
                {"name": "clause_risk_analyzer", "role": "specialist", "expertise": ["条款拆分", "风险识别", "风险分级"]},
                {"name": "legal_researcher", "role": "advisor", "expertise": ["法律检索", "法规分析", "案例检索", "RAG检索"]},
                {"name": "drafting_specialist", "role": "executor", "expertise": ["条款起草", "修改建议", "法律文书生成"]},
                {"name": "compliance_checker", "role": "reviewer", "expertise": ["合规审查", "监管规则映射", "企业红线"]},
                {"name": "audit_recorder", "role": "reviewer", "expertise": ["审计留痕", "引用追溯", "输出完整性校验"]}
            ],
            "use_cases": ["合同审查", "合同风险识别", "修改建议与替代条款", "合规风险分析", "法律依据检索"]
        }
    }
    
    return {
        "success": True,
        "teams": teams,
        "count": len(teams)
    }


@app.get("/api/multi-agent/modes")
async def get_collaboration_modes():
    """获取可用的协作模式"""
    modes = {
        "sequential": {
            "name": "顺序协作",
            "description": "Agents 按顺序工作，后面的 Agent 基于前面的结果继续工作",
            "icon": "🔄",
            "use_case": "适合有明确流程的任务"
        },
        "parallel": {
            "name": "并行协作",
            "description": "所有 Agents 同时工作，然后整合各自的结果",
            "icon": "⚡",
            "use_case": "适合需要多角度分析的任务"
        },
        "hierarchical": {
            "name": "层级协作",
            "description": "有明确的管理层级，协调者分配任务，专家执行，审核者检查",
            "icon": "🏢",
            "use_case": "适合复杂的、需要专业分工的任务（推荐）"
        },
        "peer_to_peer": {
            "name": "对等协作",
            "description": "Agents 平等协作，相互讨论和改进",
            "icon": "🤝",
            "use_case": "适合需要反复讨论和优化的任务"
        },
        "hybrid": {
            "name": "混合模式",
            "description": "结合多种协作方式的优势",
            "icon": "🔀",
            "use_case": "灵活适应不同场景"
        }
    }
    
    return {
        "success": True,
        "modes": modes
    }


@app.post("/api/multi-agent/collaborate")
async def multi_agent_collaborate(
    request: MultiAgentCollaborationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """执行多智能体协作"""
    try:
        knowledge_bases = _resolve_multi_agent_knowledge_bases(current_user, request)
        rag_agent = _build_multi_agent_rag_agent(knowledge_bases)

        # 获取 LLM 客户端
        llm_client = GiteeAIClient()

        # 创建协作系统
        collaboration = MultiAgentCollaboration(
            llm_client=llm_client,
            mode=request.mode,
            verbose=True,
            rag_agent=rag_agent
        )
        
        # 根据团队类型注册 Agents
        agents, _ = _get_multi_agent_team(request.team_type)
        collaboration.register_agents(agents)
        
        # 执行协作
        result = collaboration.collaborate(request.input_text, request.context)
        
        return {
            "success": result.success,
            "final_output": result.final_output,
            "agent_contributions": result.agent_contributions,
            "messages": [
                {
                    "sender": msg.sender,
                    "receiver": msg.receiver,
                    "content": msg.content,
                    "type": msg.message_type,
                    "timestamp": msg.timestamp
                }
                for msg in result.messages
            ],
            "execution_time": result.execution_time,
            "error_message": result.error_message,
            "metadata": _multi_agent_kb_metadata(knowledge_bases)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"多智能体协作失败: {str(e)}")


@app.post("/api/multi-agent/collaborate/stream")
async def multi_agent_collaborate_stream(
    request: MultiAgentCollaborationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """流式执行多智能体协作"""
    try:
        knowledge_bases = _resolve_multi_agent_knowledge_bases(current_user, request)
        rag_agent = _build_multi_agent_rag_agent(knowledge_bases)
        metadata = _multi_agent_kb_metadata(knowledge_bases)

        # 获取 LLM 客户端
        llm_client = GiteeAIClient()
        
        def generate_collaboration():
            try:
                # 发送开始事件
                yield f"data: {json.dumps({'type': 'start', 'message': '开始多智能体协作'}, ensure_ascii=False)}\n\n"

                # 创建协作系统
                collaboration = MultiAgentCollaboration(
                    llm_client=llm_client,
                    mode=request.mode,
                    verbose=False,  # 流式模式下关闭控制台输出
                    rag_agent=rag_agent
                )
                
                # 根据团队类型注册 Agents
                agents, team_name = _get_multi_agent_team(request.team_type)
                collaboration.register_agents(agents)
                
                # 发送团队信息
                team_info = {
                    "type": "team_info",
                    "team_name": team_name,
                    "agent_count": len(agents),
                    "agents": [{"name": a.name, "role": a.role.value, "description": a.description} for a in agents],
                    "mode": request.mode,
                    "metadata": metadata,
                }
                yield f"data: {json.dumps(team_info, ensure_ascii=False)}\n\n"
                
                # 执行协作
                result = collaboration.collaborate(request.input_text, request.context)
                
                # 发送完成事件
                complete_data = {
                    "type": "complete",
                    "success": result.success,
                    "final_output": result.final_output,
                    "agent_contributions": result.agent_contributions,
                    "messages": [
                        {
                            "sender": msg.sender,
                            "receiver": msg.receiver,
                            "content": msg.content,
                            "type": msg.message_type,
                            "timestamp": msg.timestamp
                        }
                        for msg in result.messages
                    ],
                    "execution_time": result.execution_time,
                    "error_message": result.error_message,
                    "metadata": metadata,
                }
                yield f"data: {json.dumps(complete_data, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                error_data = {
                    "type": "error",
                    "message": f"协作执行失败: {str(e)}"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_collaboration(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式协作失败: {str(e)}")


# ==================== Memory Management APIs ====================

@app.post("/api/memory/store")
async def store_memory(
    request: MemoryStoreRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """存储新记忆"""
    try:
        scoped_session_id = _scope_user_session_id(current_user, request.session_id)
        agent = get_memory_agent(scoped_session_id)
        
        memory = agent.store_memory(
            content=request.content,
            memory_type=MemoryType(request.memory_type),
            importance=MemoryImportance(request.importance),
            tags=request.tags,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "memory": memory.to_dict(),
            "message": "记忆已存储"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"存储记忆失败: {str(e)}")


@app.post("/api/memory/retrieve")
async def retrieve_memories(
    request: MemoryRetrieveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """检索相关记忆"""
    try:
        scoped_session_id = _scope_user_session_id(current_user, request.session_id)
        agent = get_memory_agent(scoped_session_id)
        
        # 转换记忆类型
        memory_types = None
        if request.memory_types:
            memory_types = [MemoryType(mt) for mt in request.memory_types]
        
        # 转换重要性
        min_importance = None
        if request.min_importance is not None:
            min_importance = MemoryImportance(request.min_importance)
        
        results = agent.retrieve_memories(
            query=request.query,
            memory_types=memory_types,
            tags=request.tags,
            top_k=request.top_k,
            min_importance=min_importance
        )
        
        return {
            "success": True,
            "results": [
                {
                    "memory": result.memory.to_dict(),
                    "relevance_score": result.relevance_score,
                    "reason": result.reason
                }
                for result in results
            ],
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索记忆失败: {str(e)}")


@app.post("/api/memory/chat")
async def chat_with_memory(
    request: MemoryChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """基于记忆的对话（非流式）"""
    try:
        scoped_session_id = _scope_user_session_id(current_user, request.session_id)
        agent = get_memory_agent(scoped_session_id)
        
        # 转换记忆类型
        use_memory_types = None
        if request.use_memory_types:
            use_memory_types = [MemoryType(mt) for mt in request.use_memory_types]
        
        response = agent.chat_with_memory(
            user_input=request.user_input,
            use_memory_types=use_memory_types
        )
        
        return {
            "success": True,
            "response": response,
            "session_id": request.session_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")


@app.post("/api/memory/chat/stream")
async def chat_with_memory_stream(
    request: MemoryChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """基于记忆的对话（流式）"""
    scoped_session_id = _scope_user_session_id(current_user, request.session_id)
    
    async def generate():
        try:
            agent = get_memory_agent(scoped_session_id)
            
            # 转换记忆类型
            use_memory_types = None
            if request.use_memory_types:
                use_memory_types = [MemoryType(mt) for mt in request.use_memory_types]
            
            # 检索相关记忆
            relevant_memories = agent.retrieve_memories(
                query=request.user_input,
                memory_types=use_memory_types,
                top_k=5
            )
            
            # 发送记忆信息
            if relevant_memories:
                memory_info = {
                    "type": "memories",
                    "memories": [
                        {
                            "content": result.memory.content,
                            "type": result.memory.memory_type.value,
                            "relevance": result.relevance_score
                        }
                        for result in relevant_memories
                    ]
                }
                yield f"data: {json.dumps(memory_info, ensure_ascii=False)}\n\n"
            
            # 调用LLM并流式返回
            response = agent.chat_with_memory(
                user_input=request.user_input,
                use_memory_types=use_memory_types
            )
            
            # 逐字发送响应
            for char in response:
                yield f"data: {json.dumps({'type': 'content', 'content': char}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)  # 模拟流式效果
            
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            error_msg = f"对话失败: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.put("/api/memory/working")
async def update_working_memory(
    request: WorkingMemoryUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新工作记忆"""
    try:
        scoped_session_id = _scope_user_session_id(current_user, request.session_id)
        agent = get_memory_agent(scoped_session_id)
        agent.update_working_memory(request.key, request.value)
        
        return {
            "success": True,
            "message": f"工作记忆已更新: {request.key}",
            "working_memory": agent.working_memory
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新工作记忆失败: {str(e)}")


@app.delete("/api/memory/working/{session_id}")
async def clear_working_memory(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """清空工作记忆"""
    try:
        scoped_session_id = _scope_user_session_id(current_user, session_id)
        agent = get_memory_agent(scoped_session_id)
        agent.clear_working_memory()
        
        return {
            "success": True,
            "message": "工作记忆已清空"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空工作记忆失败: {str(e)}")


@app.delete("/api/memory/session/{session_id}")
async def clear_session_context(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """清空会话上下文"""
    try:
        scoped_session_id = _scope_user_session_id(current_user, session_id)
        agent = get_memory_agent(scoped_session_id)
        agent.clear_session_context()
        
        return {
            "success": True,
            "message": "会话上下文已清空"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空会话上下文失败: {str(e)}")


@app.get("/api/memory/statistics/{session_id}")
async def get_memory_statistics(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取记忆统计信息"""
    try:
        scoped_session_id = _scope_user_session_id(current_user, session_id)
        agent = get_memory_agent(scoped_session_id)
        stats = agent.get_statistics()
        
        return {
            "success": True,
            "statistics": {
                "total_memories": stats.total_memories,
                "by_type": stats.by_type,
                "by_importance": stats.by_importance,
                "oldest_memory": stats.oldest_memory,
                "newest_memory": stats.newest_memory,
                "most_accessed": stats.most_accessed.to_dict() if stats.most_accessed else None,
                "storage_size_bytes": stats.storage_size_bytes,
                "storage_size_kb": round(stats.storage_size_bytes / 1024, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@app.get("/api/memory/types/{session_id}/{memory_type}")
async def get_memories_by_type(
    session_id: str,
    memory_type: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取指定类型的所有记忆"""
    try:
        scoped_session_id = _scope_user_session_id(current_user, session_id)
        agent = get_memory_agent(scoped_session_id)
        memories = agent.get_memories_by_type(MemoryType(memory_type))
        
        return {
            "success": True,
            "memories": [m.to_dict() for m in memories],
            "count": len(memories),
            "memory_type": memory_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记忆失败: {str(e)}")


@app.get("/api/memory/tags/{session_id}/{tag}")
async def get_memories_by_tag(
    session_id: str,
    tag: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取指定标签的所有记忆"""
    try:
        scoped_session_id = _scope_user_session_id(current_user, session_id)
        agent = get_memory_agent(scoped_session_id)
        memories = agent.get_memories_by_tag(tag)
        
        return {
            "success": True,
            "memories": [m.to_dict() for m in memories],
            "count": len(memories),
            "tag": tag
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记忆失败: {str(e)}")


@app.get("/api/memory/info")
async def get_memory_info():
    """获取记忆管理系统信息"""
    return {
        "memory_types": [
            {
                "id": "short_term",
                "name": "短期记忆",
                "description": "最近的对话和交互",
                "icon": "⚡"
            },
            {
                "id": "long_term",
                "name": "长期记忆",
                "description": "重要的知识和经验",
                "icon": "💾"
            },
            {
                "id": "working",
                "name": "工作记忆",
                "description": "当前任务相关的临时信息",
                "icon": "🔧"
            },
            {
                "id": "semantic",
                "name": "语义记忆",
                "description": "事实和概念性知识",
                "icon": "📚"
            },
            {
                "id": "episodic",
                "name": "情景记忆",
                "description": "具体的事件和经历",
                "icon": "📖"
            },
            {
                "id": "procedural",
                "name": "程序性记忆",
                "description": "技能和操作步骤",
                "icon": "⚙️"
            }
        ],
        "importance_levels": [
            {"value": 5, "name": "关键", "description": "必须保留"},
            {"value": 4, "name": "高", "description": "应该保留"},
            {"value": 3, "name": "中", "description": "可以保留"},
            {"value": 2, "name": "低", "description": "可以遗忘"},
            {"value": 1, "name": "最低", "description": "优先遗忘"}
        ],
        "strategies": [
            {
                "id": "fifo",
                "name": "先进先出",
                "description": "删除最早的记忆"
            },
            {
                "id": "lru",
                "name": "最近最少使用",
                "description": "删除最少访问的记忆"
            },
            {
                "id": "importance",
                "name": "基于重要性",
                "description": "优先删除不重要的记忆"
            },
            {
                "id": "hybrid",
                "name": "混合策略（推荐）",
                "description": "综合考虑时间、重要性和访问频率"
            }
        ],
        "features": [
            "🧠 多层次记忆：支持短期、长期、工作记忆等多种类型",
            "🔍 智能检索：根据相关性和重要性检索记忆",
            "🔄 自动管理：自动整理、压缩、遗忘不重要的记忆",
            "💾 持久化：记忆可以持久化存储，跨会话使用",
            "🎯 上下文感知：根据当前任务动态调整记忆使用策略",
            "📊 统计分析：提供详细的记忆使用统计和分析"
        ]
    }


@app.post("/api/memory/export/{session_id}")
async def export_memories(
    session_id: str,
    memory_types: Optional[List[str]] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """导出记忆"""
    try:
        scoped_session_id = _scope_user_session_id(current_user, session_id)
        agent = get_memory_agent(scoped_session_id)
        
        # 转换记忆类型
        types = None
        if memory_types:
            types = [MemoryType(mt) for mt in memory_types]
        
        # 导出到临时文件
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"data/memories/export_{scoped_session_id}_{timestamp}.json"
        
        agent.export_memories(export_path, types)
        
        return {
            "success": True,
            "message": "记忆已导出",
            "export_path": export_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出记忆失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import asyncio
    uvicorn.run(
        "shuyixiao_agent.web_app:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
