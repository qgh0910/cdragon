"""
配置管理模块

使用 pydantic-settings 管理环境变量和配置
支持从 .env 文件或 PyCharm 环境变量中读取配置
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os
from pathlib import Path

# 项目根目录（config.py 的上上上级目录）
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


class Settings(BaseSettings):
    """应用配置类
    
    在 PyCharm 中配置环境变量的方法：
    1. 打开 Run -> Edit Configurations
    2. 选择你的运行配置
    3. 在 Environment variables 中添加以下变量：
       - DASHSCOPE_API_KEY=你的API密钥
       - DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
       - DASHSCOPE_MODEL=qwen-plus
       等等
    """
    
    # DashScope API 配置
    dashscope_api_key: str = Field(
        default="",
        description="DashScope API 密钥"
    )
    dashscope_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="DashScope API 基础 URL"
    )
    
    # 主对话模型配置
    use_cloud_chat_model: bool = Field(
        default=True,
        description="是否使用云端对话模型"
    )
    dashscope_model: str = Field(
        default="qwen-plus",
        description="云端对话模型名称"
    )
    local_chat_model: str = Field(
        default="",
        description="本地对话模型路径（仅当 use_cloud_chat_model=False 时使用）"
    )
    local_chat_device: str = Field(
        default="cpu",
        description="本地对话模型运行设备 (cpu/cuda)"
    )
    
    # Agent 配置
    agent_max_iterations: int = Field(
        default=10,
        description="Agent 最大迭代次数"
    )
    agent_verbose: bool = Field(
        default=True,
        description="是否输出详细日志"
    )
    
    # 请求配置
    request_timeout: int = Field(
        default=60,
        description="请求超时时间（秒）"
    )
    multi_agent_timeout: int = Field(
        default=180,
        description="多智能体协作超时时间（秒），因为需要多次API调用"
    )
    max_retries: int = Field(
        default=3,
        description="最大重试次数"
    )
    
    # 故障转移
    enable_failover: bool = Field(
        default=True,
        description="是否启用故障转移"
    )
    
    # SSL 配置
    ssl_verify: bool = Field(
        default=False,
        description="是否验证 SSL 证书（如遇到 SSL 错误可设为 False）"
    )
    
    # RAG 嵌入模型配置
    use_cloud_embedding: bool = Field(
        default=True,
        description="是否使用云端嵌入服务（推荐，无需下载模型）"
    )
    cloud_embedding_model: str = Field(
        default="text-embedding-v4",
        description="云端嵌入模型名称"
    )
    
    # 向量数据库配置
    vector_db_path: str = Field(
        default=str(PROJECT_ROOT / "data" / "chroma"),
        description="向量数据库存储路径（绝对路径，基于项目根目录）"
    )
    upload_root_path: str = Field(
        default=str(PROJECT_ROOT / "data" / "uploads"),
        description="Web 上传文件存储路径（绝对路径，基于项目根目录）"
    )
    max_upload_file_size_mb: int = Field(
        default=50,
        description="Web 上传文件最大大小（MB）"
    )
    allowed_upload_extensions: str = Field(
        default=".pdf,.docx,.md,.markdown,.txt,.text",
        description="允许上传的文件扩展名，多个扩展名用英文逗号分隔"
    )

    # LPOS 合同结构化解析配置
    lpos_contract_parse_max_chars: int = Field(
        default=200000,
        description="单份合同结构化解析的最大字符数"
    )
    lpos_contract_parse_max_clauses: int = Field(
        default=300,
        description="单份合同最多返回的条款数量"
    )
    lpos_contract_parse_clause_preview_chars: int = Field(
        default=1200,
        description="单条合同条款预览的最大字符数"
    )
    lpos_contract_parse_source_preview_chars: int = Field(
        default=160,
        description="合同来源定位预览的最大字符数"
    )
    lpos_contract_parse_use_llm: bool = Field(
        default=False,
        description="是否启用 LLM 辅助合同结构化抽取"
    )
    lpos_contract_parse_llm_timeout: int = Field(
        default=60,
        description="LLM 辅助合同结构化抽取超时时间（秒）"
    )

    # 认证与会话配置
    auth_secret_key: str = Field(
        default="",
        description="认证签名密钥，生产环境必须通过本地 .env 或环境变量设置"
    )
    initial_admin_username: str = Field(
        default="",
        description="首次启动时自动创建的管理员用户名"
    )
    initial_admin_password: str = Field(
        default="",
        description="首次启动时自动创建的管理员密码"
    )
    session_expire_hours: int = Field(
        default=24,
        description="Session 有效期（小时）"
    )
    auth_cookie_secure: bool = Field(
        default=False,
        description="认证 Cookie 是否仅允许 HTTPS 传输"
    )
    auth_allowed_origins: str = Field(
        default="http://127.0.0.1:8000,http://localhost:8000",
        description="允许携带认证 Cookie 的前端来源，多个来源用英文逗号分隔"
    )
    auth_enable_server_path_import: bool = Field(
        default=False,
        description="是否允许服务器路径导入能力"
    )
    auth_login_rate_limit_per_minute: int = Field(
        default=5,
        description="每分钟允许的登录尝试次数"
    )
    
    # 本地嵌入模型配置（仅当 use_cloud_embedding=False 时使用）
    embedding_model: str = Field(
        default="BAAI/bge-small-zh-v1.5",
        description="本地嵌入模型名称"
    )
    embedding_device: str = Field(
        default="cpu",
        description="本地嵌入模型运行设备 (cpu/cuda)"
    )
    
    # 文档分片配置
    chunk_size: int = Field(
        default=500,
        description="文档分片大小"
    )
    chunk_overlap: int = Field(
        default=50,
        description="文档分片重叠大小"
    )
    
    # 检索配置
    retrieval_top_k: int = Field(
        default=10,
        description="检索返回的文档数量"
    )
    rerank_top_k: int = Field(
        default=5,
        description="重排序后保留的文档数量"
    )
    hybrid_search_weight: float = Field(
        default=0.5,
        description="混合检索中向量检索的权重 (0-1)"
    )
    
    # RAG 重排序模型配置
    use_cloud_reranker: bool = Field(
        default=True,
        description="是否使用云端重排序服务（推荐，无需下载模型）"
    )
    cloud_reranker_model: str = Field(
        default="qwen3-rerank",
        description="云端重排序模型名称"
    )
    cloud_reranker_base_url: str = Field(
        default="",
        description="云端重排序 API 基础 URL；留空则复用 dashscope_base_url"
    )
    reranker_model: str = Field(
        default="BAAI/bge-reranker-base",
        description="本地重排序模型名称（仅当 use_cloud_reranker=False 时使用）"
    )
    reranker_device: str = Field(
        default="cpu",
        description="本地重排序模型运行设备 (cpu/cuda)"
    )
    
    # 查询优化模型配置
    query_optimizer_model: str = Field(
        default="",
        description="查询优化使用的模型名称（留空则使用 dashscope_model）"
    )
    
    # Agent 模型配置
    agent_model: str = Field(
        default="",
        description="Agent 使用的模型名称（留空则使用 dashscope_model）"
    )
    
    # 上下文管理
    max_context_tokens: int = Field(
        default=4000,
        description="最大上下文 token 数量"
    )
    enable_context_expansion: bool = Field(
        default=True,
        description="是否启用上下文扩展"
    )
    
    # 查询优化
    enable_query_rewrite: bool = Field(
        default=True,
        description="是否启用查询重写"
    )
    enable_subquery_expansion: bool = Field(
        default=False,
        description="是否启用子查询扩展"
    )
    max_subqueries: int = Field(
        default=3,
        description="最大子查询数量"
    )
    
    model_config = SettingsConfigDict(
        # 优先从环境变量读取，然后从 .env 文件读取
        env_file=".env" if os.path.exists(".env") else None,
        env_file_encoding="utf-8",
        # 不区分大小写，这样 DASHSCOPE_API_KEY 和 dashscope_api_key 都能识别
        case_sensitive=False,
        # 忽略额外的环境变量
        extra="ignore",
        # 支持从环境变量前缀读取（可选）
        # env_prefix="",
    )


# 全局配置实例
settings = Settings()
