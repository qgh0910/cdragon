"""CompositeRAGRetriever 联合检索测试。"""

from langchain_core.documents import Document

from src.shuyixiao_agent.rag import CompositeRAGRetriever


class _FakeRAGAgent:
    """记录检索调用并返回预置文档。"""

    def __init__(self, documents):
        self.documents = documents
        self.calls = []

    def retrieve(self, query, top_k=None, mode=None, use_rerank=True):
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "mode": mode,
                "use_rerank": use_rerank,
            }
        )
        return self.documents[:top_k]


class _ScoreReranker:
    """按元数据中的测试分数模拟全局重排。"""

    def rerank_results(self, query, results, top_k=None):
        ranked = sorted(
            results,
            key=lambda item: item[0].metadata["test_rank"],
            reverse=True,
        )
        return ranked[:top_k]


class _FailingReranker:
    """模拟不可用的 reranker。"""

    def rerank_results(self, query, results, top_k=None):
        raise RuntimeError("reranker offline")


def _doc(text, source, chunk_index=None, test_rank=0):
    metadata = {"source": source, "test_rank": test_rank}
    if chunk_index is not None:
        metadata["chunk_index"] = chunk_index
    return Document(page_content=text, metadata=metadata)


def test_composite_retriever_searches_each_kb_and_annotates_results():
    """联合检索应分别查询每个库，并给结果补充知识库来源。"""
    public_agent = _FakeRAGAgent(
        [
            _doc("公共法规：违约责任可以约定违约金。", "law.md", 1, test_rank=10),
            _doc("公共案例：法院会审查违约金是否过高。", "case.md", 2, test_rank=5),
        ]
    )
    user_agent = _FakeRAGAgent(
        [
            _doc("用户模板：违约责任条款需要明确通知义务。", "template.docx", 3, test_rank=20),
        ]
    )
    retriever = CompositeRAGRetriever(
        [
            {
                "id": "kb_public",
                "scope": "public",
                "display_name": "法规库",
                "collection_name": "public_law",
                "rag_agent": public_agent,
            },
            {
                "id": "kb_user",
                "scope": "user",
                "display_name": "我的模板",
                "collection_name": "user_templates",
                "rag_agent": user_agent,
            },
        ],
        reranker=_ScoreReranker(),
    )

    documents = retriever.retrieve(
        "违约责任",
        top_k=2,
        per_kb_top_k=2,
        mode="hybrid",
    )

    assert public_agent.calls == [
        {
            "query": "违约责任",
            "top_k": 2,
            "mode": "hybrid",
            "use_rerank": False,
        }
    ]
    assert user_agent.calls == [
        {
            "query": "违约责任",
            "top_k": 2,
            "mode": "hybrid",
            "use_rerank": False,
        }
    ]
    assert [doc.metadata["kb_id"] for doc in documents] == ["kb_user", "kb_public"]
    assert documents[0].metadata["scope"] == "user"
    assert documents[0].metadata["display_name"] == "我的模板"
    assert documents[0].metadata["source"] == "template.docx"
    assert documents[0].metadata["collection_name"] == "user_templates"
    assert documents[0].metadata["composite_rerank_status"] == "reranked"


def test_composite_retriever_deduplicates_same_kb_source_and_chunk():
    """同一知识库内相同 source + chunk 应只保留一个候选片段。"""
    agent = _FakeRAGAgent(
        [
            (_doc("重复条款内容", "contract.docx", 7, test_rank=1), 0.2),
            (_doc("重复条款内容", "contract.docx", 7, test_rank=2), 0.9),
            (_doc("另一条款内容", "contract.docx", 8, test_rank=3), 0.7),
        ]
    )
    retriever = CompositeRAGRetriever(
        [
            {
                "id": "kb_user",
                "scope": "user",
                "display_name": "我的合同",
                "collection_name": "user_contracts",
                "rag_agent": agent,
            }
        ],
        reranker=None,
    )

    documents = retriever.retrieve("条款", top_k=5, per_kb_top_k=5)

    assert [doc.page_content for doc in documents] == ["重复条款内容", "另一条款内容"]
    assert documents[0].metadata["composite_original_score"] == 0.9
    assert documents[0].metadata["composite_rerank_status"] == "fallback_no_reranker"


def test_composite_retriever_falls_back_when_reranker_is_unavailable():
    """reranker 不可用时应按原始候选分数降级返回。"""
    public_agent = _FakeRAGAgent(
        [(_doc("公共库低分候选", "law.md", test_rank=1), 0.1)]
    )
    user_agent = _FakeRAGAgent(
        [(_doc("用户库高分候选", "template.md", test_rank=1), 0.8)]
    )
    agents = {
        "public_law": public_agent,
        "user_templates": user_agent,
    }
    retriever = CompositeRAGRetriever(
        [
            {
                "id": "kb_public",
                "scope": "public",
                "display_name": "法规库",
                "collection_name": "public_law",
            },
            {
                "id": "kb_user",
                "scope": "user",
                "display_name": "我的模板",
                "collection_name": "user_templates",
            },
        ],
        agent_factory=lambda collection_name: agents[collection_name],
        reranker=_FailingReranker(),
    )

    documents = retriever.retrieve("违约责任", top_k=1, per_kb_top_k=1)

    assert documents[0].page_content == "用户库高分候选"
    assert documents[0].metadata["kb_id"] == "kb_user"
    assert documents[0].metadata["composite_rerank_status"] == "fallback_reranker_error"
