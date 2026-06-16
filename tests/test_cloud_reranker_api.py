"""云端 reranker API 兼容测试。"""

from src.shuyixiao_agent.rag.reranker import CloudReranker


class _FakeResponse:
    status_code = 200

    def json(self):
        return {
            "results": [
                {"index": 0, "relevance_score": 0.9},
            ]
        }


def test_qwen3_reranker_uses_dedicated_base_url_and_reranks_endpoint(monkeypatch):
    """qwen3-rerank 应使用独立 base url，避免拼到 chat/embedding 的接口下。"""
    captured = {}

    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.reranker.settings.dashscope_base_url",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.reranker.settings.cloud_reranker_base_url",
        "https://dashscope.aliyuncs.com/compatible-api/v1",
    )

    def fake_post(url, headers=None, json=None, timeout=None, verify=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse()

    monkeypatch.setattr(
        "src.shuyixiao_agent.rag.reranker.requests.post",
        fake_post,
    )

    reranker = CloudReranker(
        api_key="test-key",
        model="qwen3-rerank",
        max_retries=1,
    )

    result = reranker._call_rerank_api("什么是文本排序模型", ["候选文本"], 1)

    assert captured["url"] == "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"
    assert captured["json"] == {
        "model": "qwen3-rerank",
        "query": "什么是文本排序模型",
        "documents": ["候选文本"],
        "top_n": 1,
    }
    assert result == [(0, 0.9)]
