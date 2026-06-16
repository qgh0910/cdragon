"""多知识库 RAG 组合检索器。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional

from langchain_core.documents import Document

from ..config import settings
from .reranker import SimpleReranker


_DEFAULT_RERANKER = object()


@dataclass(frozen=True)
class CompositeRAGSource:
    """一个已授权知识库对应的检索源。"""

    kb_id: str
    scope: str
    display_name: str
    collection_name: str
    rag_agent: Any = None

    @classmethod
    def from_item(cls, item: "CompositeRAGSource | Mapping[str, Any]") -> "CompositeRAGSource":
        """从 registry 字典或已构造 source 生成检索源。"""
        if isinstance(item, cls):
            return item
        return cls(
            kb_id=str(item.get("kb_id") or item.get("id") or ""),
            scope=str(item.get("scope") or ""),
            display_name=str(item.get("display_name") or ""),
            collection_name=str(item.get("collection_name") or ""),
            rag_agent=item.get("rag_agent") or item.get("agent") or item.get("retriever"),
        )


class CompositeRAGRetriever:
    """对多个已授权 RAG 知识库执行合并检索、去重和全局重排。"""

    def __init__(
        self,
        knowledge_bases: Iterable[CompositeRAGSource | Mapping[str, Any]],
        *,
        agent_factory: Optional[Callable[[str], Any]] = None,
        reranker: Any = _DEFAULT_RERANKER,
        per_kb_top_k: int = 5,
        deduplicate: bool = True,
    ):
        self.sources = [CompositeRAGSource.from_item(item) for item in knowledge_bases]
        self.agent_factory = agent_factory
        self.reranker = SimpleReranker() if reranker is _DEFAULT_RERANKER else reranker
        self.per_kb_top_k = per_kb_top_k
        self.deduplicate = deduplicate
        self._validate_sources()

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        per_kb_top_k: Optional[int] = None,
        mode: Optional[str] = None,
        use_rerank: bool = True,
    ) -> list[Document]:
        """分别检索多个知识库，合并去重后返回带来源标注的文档。"""
        final_top_k = top_k or settings.rerank_top_k
        candidate_top_k = per_kb_top_k or self.per_kb_top_k
        candidates: list[tuple[Document, float]] = []

        for source in self.sources:
            agent = self._resolve_agent(source)
            raw_results = agent.retrieve(
                query,
                top_k=candidate_top_k,
                mode=mode,
                use_rerank=False,
            )
            candidates.extend(self._annotate_results(source, raw_results))

        if self.deduplicate:
            candidates = self._deduplicate_candidates(candidates)

        ranked_results, rerank_status = self._rerank_or_fallback(
            query,
            candidates,
            final_top_k,
            use_rerank,
        )
        return [
            self._with_final_metadata(document, score, rerank_status)
            for document, score in ranked_results[:final_top_k]
        ]

    def format_documents_for_prompt(self, documents: list[Document]) -> str:
        """将联合检索结果格式化为带知识库来源的上下文文本。"""
        formatted = []
        for index, document in enumerate(documents, start=1):
            metadata = document.metadata or {}
            formatted.append(
                "\n".join(
                    [
                        (
                            f"[资料 {index}] 知识库: {metadata.get('display_name', '未知')} "
                            f"({metadata.get('scope', 'unknown')}, {metadata.get('kb_id', 'unknown')})"
                        ),
                        f"来源: {metadata.get('source', '未知')}",
                        document.page_content,
                    ]
                )
            )
        return "\n\n".join(formatted)

    def _validate_sources(self) -> None:
        """校验检索源字段，避免静默进入错误 collection。"""
        for source in self.sources:
            if not source.kb_id:
                raise ValueError("联合检索知识库缺少 kb_id")
            if not source.scope:
                raise ValueError(f"知识库 {source.kb_id} 缺少 scope")
            if not source.display_name:
                raise ValueError(f"知识库 {source.kb_id} 缺少 display_name")
            if not source.collection_name:
                raise ValueError(f"知识库 {source.kb_id} 缺少 collection_name")
            if source.rag_agent is None and self.agent_factory is None:
                raise ValueError(f"知识库 {source.kb_id} 缺少 RAGAgent 或 agent_factory")

    def _resolve_agent(self, source: CompositeRAGSource) -> Any:
        """按 source 取 RAGAgent，必要时延迟创建。"""
        if source.rag_agent is not None:
            return source.rag_agent
        if self.agent_factory is None:
            raise ValueError(f"知识库 {source.kb_id} 缺少 RAGAgent 或 agent_factory")
        return self.agent_factory(source.collection_name)

    def _annotate_results(
        self,
        source: CompositeRAGSource,
        raw_results: Iterable[Any],
    ) -> list[tuple[Document, float]]:
        """补充知识库来源元数据并统一结果形态。"""
        items = list(raw_results or [])
        annotated: list[tuple[Document, float]] = []
        for rank, item in enumerate(items):
            document, score = self._normalize_result_item(item, rank, len(items))
            metadata = dict(document.metadata or {})
            metadata.setdefault("source", source.collection_name)
            metadata.update(
                {
                    "kb_id": source.kb_id,
                    "scope": source.scope,
                    "display_name": source.display_name,
                    "collection_name": source.collection_name,
                    "composite_original_rank": rank,
                    "composite_original_score": score,
                }
            )
            annotated.append((self._clone_document(document, metadata), score))
        return annotated

    def _normalize_result_item(
        self,
        item: Any,
        rank: int,
        total: int,
    ) -> tuple[Document, float]:
        """兼容 RAGAgent.retrieve 的 Document 列表和底层 retriever 的带分数结果。"""
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], Document):
            return item[0], float(item[1])
        if isinstance(item, Document):
            return item, float(total - rank)
        raise TypeError("联合检索只支持 Document 或 (Document, score) 结果")

    def _deduplicate_candidates(
        self,
        candidates: list[tuple[Document, float]],
    ) -> list[tuple[Document, float]]:
        """按 kb_id + source + chunk 标识去重，保留原始分更高的候选。"""
        unique: dict[tuple[str, str, str], tuple[Document, float]] = {}
        order: list[tuple[str, str, str]] = []
        for document, score in candidates:
            key = self._dedupe_key(document)
            if key not in unique:
                unique[key] = (document, score)
                order.append(key)
            elif score > unique[key][1]:
                unique[key] = (document, score)
        return [unique[key] for key in order]

    def _dedupe_key(self, document: Document) -> tuple[str, str, str]:
        """生成去重 key。"""
        metadata = document.metadata or {}
        source = str(metadata.get("source") or "")
        chunk_id = self._first_present(
            metadata,
            ("chunk_id", "chunk_index", "document_id", "doc_id", "id"),
        )
        if chunk_id is None:
            chunk_id = hashlib.sha256(document.page_content.encode("utf-8")).hexdigest()
        return (str(metadata.get("kb_id") or ""), source, str(chunk_id))

    def _rerank_or_fallback(
        self,
        query: str,
        candidates: list[tuple[Document, float]],
        top_k: int,
        use_rerank: bool,
    ) -> tuple[list[tuple[Document, float]], str]:
        """全局重排；reranker 不可用时退回原始分排序。"""
        if not candidates:
            return [], "empty"
        if not use_rerank:
            return self._fallback_sort(candidates, top_k), "fallback_disabled"
        if self.reranker is None:
            return self._fallback_sort(candidates, top_k), "fallback_no_reranker"

        try:
            reranked = self.reranker.rerank_results(query, candidates, top_k=top_k)
            return self._normalize_ranked_results(reranked), "reranked"
        except Exception:
            return self._fallback_sort(candidates, top_k), "fallback_reranker_error"

    def _normalize_ranked_results(self, results: Iterable[Any]) -> list[tuple[Document, float]]:
        """兼容不同 reranker 返回形态。"""
        items = list(results or [])
        normalized: list[tuple[Document, float]] = []
        for rank, item in enumerate(items):
            if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], Document):
                normalized.append((item[0], float(item[1])))
            elif isinstance(item, Document):
                normalized.append((item, float(len(items) - rank)))
            else:
                raise TypeError("reranker 只支持 Document 或 (Document, score) 结果")
        return normalized

    def _fallback_sort(
        self,
        candidates: list[tuple[Document, float]],
        top_k: int,
    ) -> list[tuple[Document, float]]:
        """按原始候选分数排序。"""
        return sorted(candidates, key=lambda item: item[1], reverse=True)[:top_k]

    def _with_final_metadata(
        self,
        document: Document,
        score: float,
        rerank_status: str,
    ) -> Document:
        """写入最终排序信息。"""
        metadata = dict(document.metadata or {})
        metadata["composite_score"] = float(score)
        metadata["composite_rerank_status"] = rerank_status
        return self._clone_document(document, metadata)

    @staticmethod
    def _first_present(metadata: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
        """返回 metadata 中第一个存在且非空的字段。"""
        for key in keys:
            value = metadata.get(key)
            if value is not None and value != "":
                return value
        return None

    @staticmethod
    def _clone_document(document: Document, metadata: dict[str, Any]) -> Document:
        """复制 Document，避免修改原始单库检索结果。"""
        return Document(page_content=document.page_content, metadata=metadata)
