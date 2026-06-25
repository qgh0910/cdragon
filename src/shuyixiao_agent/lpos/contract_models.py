"""LPOS 合同解析基础数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceRef:
    """合同文本来源定位，不包含服务端绝对路径。"""

    file_id: str
    source_name: str
    document_type: str
    page_number: int | None = None
    paragraph_index: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    text_preview: str = ""
    confidence: float | None = None


@dataclass(frozen=True)
class PageTextBlock:
    """pageindex 风格文本块。"""

    text: str
    source_ref: SourceRef


@dataclass(frozen=True)
class ContractClause:
    """合同条款结构。"""

    clause_id: str
    title: str
    clause_type: str
    content_preview: str
    content_truncated: bool
    source_refs: list[SourceRef] = field(default_factory=list)
    confidence: float = 0.8
    content: str | None = None

    def to_api_dict(self, *, include_content: bool = False) -> dict[str, Any]:
        """转换为 API 友好的字典，默认不返回完整条款正文。"""
        data: dict[str, Any] = {
            "clause_id": self.clause_id,
            "title": self.title,
            "clause_type": self.clause_type,
            "content_preview": self.content_preview,
            "content_truncated": self.content_truncated,
            "source_refs": [asdict(source_ref) for source_ref in self.source_refs],
            "confidence": self.confidence,
        }
        if include_content and self.content is not None:
            data["content"] = self.content
        return data


@dataclass(frozen=True)
class ContractStructureSummary:
    """供前端和多智能体使用的合同结构摘要。"""

    contract_type: str
    parties: list[str]
    amount: list[str]
    term: list[str]
    effective_date: list[str]
    clause_count: int
    key_clause_summary: list[dict[str, Any]]
    warning_count: int
    warnings: list[str]


@dataclass(frozen=True)
class ContractStructure:
    """合同结构化抽取结果。"""

    file: dict[str, Any]
    contract_type: dict[str, Any]
    key_fields: dict[str, list[dict[str, Any]]]
    clauses: list[ContractClause]
    key_clause_summary: list[dict[str, Any]]
    stats: dict[str, Any]
    warnings: list[str]
    schema_version: str = "1.0"
    parser_version: str = "pageindex-contract-v1"
    structure_status: str = "success"

    def to_summary(self) -> ContractStructureSummary:
        """生成合同结构摘要。"""
        return ContractStructureSummary(
            contract_type=str(self.contract_type.get("value", "未知合同")),
            parties=[item["value"] for item in self.key_fields.get("parties", [])],
            amount=[item["value"] for item in self.key_fields.get("amount", [])],
            term=[item["value"] for item in self.key_fields.get("term", [])],
            effective_date=[item["value"] for item in self.key_fields.get("effective_date", [])],
            clause_count=len(self.clauses),
            key_clause_summary=self.key_clause_summary,
            warning_count=len(self.warnings),
            warnings=self.warnings,
        )
