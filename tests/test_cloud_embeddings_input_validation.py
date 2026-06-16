"""云端 embedding 输入长度校验测试。"""

import pytest

from src.shuyixiao_agent.rag.cloud_embeddings import CloudEmbeddingManager


def _manager(monkeypatch):
    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.cloud_embeddings.settings.dashscope_api_key",
        "test-key",
    )
    return CloudEmbeddingManager(api_key="test-key", model="text-embedding-v4")


def test_cloud_embedding_rejects_empty_input_before_request(monkeypatch):
    manager = _manager(monkeypatch)

    def fail_post(*args, **kwargs):
        raise AssertionError("不应发起网络请求")

    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.cloud_embeddings.requests.post",
        fail_post,
    )

    with pytest.raises(ValueError, match="不能为空"):
        manager._call_api([""])


def test_cloud_embedding_rejects_too_long_input_before_request(monkeypatch):
    manager = _manager(monkeypatch)

    def fail_post(*args, **kwargs):
        raise AssertionError("不应发起网络请求")

    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.cloud_embeddings.requests.post",
        fail_post,
    )

    with pytest.raises(ValueError, match="超过云端嵌入服务限制"):
        manager._call_api(["x" * 8193])
