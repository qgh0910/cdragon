"""DashScope 云服务配置测试。"""

from src.shuyixiao_agent.config import Settings
from src.shuyixiao_agent.gitee_ai_client import GiteeAIClient
from src.shuyixiao_agent.rag.cloud_embeddings import CloudEmbeddingManager
from src.shuyixiao_agent.rag.reranker import CloudReranker


def test_settings_reads_dashscope_environment(monkeypatch):
    """云服务配置应从 DASHSCOPE_* 环境变量读取。"""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://dashscope.example/v1")
    monkeypatch.setenv("DASHSCOPE_MODEL", "qwen-plus")

    settings = Settings(_env_file=None)

    assert settings.dashscope_api_key == "dashscope-key"
    assert settings.dashscope_base_url == "https://dashscope.example/v1"
    assert settings.dashscope_model == "qwen-plus"


def test_cloud_clients_use_dashscope_settings(monkeypatch):
    """对话、embedding 和 rerank 客户端应统一读取 DashScope 配置。"""
    monkeypatch.setattr(
        "src.shuyixiao_agent.gitee_ai_client.settings.dashscope_api_key",
        "dashscope-key",
    )
    monkeypatch.setattr(
        "src.shuyixiao_agent.gitee_ai_client.settings.dashscope_base_url",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    monkeypatch.setattr(
        "src.shuyixiao_agent.gitee_ai_client.settings.dashscope_model",
        "qwen-plus",
    )
    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.cloud_embeddings.settings.dashscope_api_key",
        "dashscope-key",
    )
    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.cloud_embeddings.settings.dashscope_base_url",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.reranker.settings.dashscope_api_key",
        "dashscope-key",
    )
    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.reranker.settings.dashscope_base_url",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.reranker.settings.cloud_reranker_base_url",
        "",
    )

    chat_client = GiteeAIClient()
    embedding_client = CloudEmbeddingManager()
    reranker = CloudReranker()

    assert chat_client.api_key == "dashscope-key"
    assert chat_client.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert chat_client.model == "qwen-plus"
    assert embedding_client.api_key == "dashscope-key"
    assert embedding_client.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert reranker.api_key == "dashscope-key"
    assert reranker.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
