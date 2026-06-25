"""LPOS 合同文本、pageindex 与结构化抽取编排。"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import contract_extractor, pageindex
from .contract_models import ContractStructure, PageTextBlock


class ContractTextExtractionError(ValueError):
    """合同文件未能抽取出有效文本。"""


def parse_contract_file(
    file_path: str,
    file_id: str | None = None,
    original_filename: str | None = None,
    parse_structure: bool = True,
    include_clause_content: bool = False,
    include_page_index: bool = False,
) -> dict[str, Any]:
    """统一编排合同文本抽取、来源定位和结构化抽取。"""
    from ..rag.document_loader import DocumentLoader

    path = Path(file_path)
    documents = DocumentLoader().load_file(str(path))
    text = "\n\n".join(document.page_content for document in documents)
    if not text.strip():
        raise ContractTextExtractionError("合同文件未抽取到有效文本")

    resolved_file_id = file_id or ""
    resolved_filename = original_filename or path.name
    document_type = _document_type(path)
    blocks: list[PageTextBlock] = []
    structure_dict: dict[str, Any] | None = None
    summary_dict: dict[str, Any] | None = None
    parse_warnings: list[str] = []
    structure_status = "text_only"

    if parse_structure or include_page_index:
        blocks = pageindex.build_page_index(
            documents,
            file_id=resolved_file_id,
            original_filename=resolved_filename,
            document_type=document_type,
        )

    if parse_structure:
        try:
            structure = contract_extractor.extract_contract_structure(
                blocks,
                file_id=resolved_file_id,
                original_filename=resolved_filename,
                document_type=document_type,
                include_clause_content=include_clause_content,
            )
            structure_dict = _structure_to_api_dict(
                structure,
                include_clause_content=include_clause_content,
            )
            summary_dict = asdict(structure.to_summary())
            parse_warnings.extend(structure.warnings)
            structure_status = structure.structure_status
        except Exception as exc:
            parse_warnings.append(f"结构化抽取失败，已降级为纯文本结果：{exc}")

    result: dict[str, Any] = {
        "text": text,
        "document_count": len(documents),
        "contract_structure": structure_dict,
        "contract_structure_summary": summary_dict,
        "parse_warnings": parse_warnings,
        "metadata": {
            "structure_status": structure_status,
            "document_count": len(documents),
            "text_char_count": len(text),
        },
    }
    if include_page_index:
        result["page_index"] = [asdict(block) for block in blocks]
    return result


def _structure_to_api_dict(
    structure: ContractStructure,
    *,
    include_clause_content: bool,
) -> dict[str, Any]:
    """序列化合同结构，并按请求控制完整条款正文。"""
    return {
        "schema_version": structure.schema_version,
        "parser_version": structure.parser_version,
        "structure_status": structure.structure_status,
        "file": structure.file,
        "contract_type": structure.contract_type,
        "key_fields": structure.key_fields,
        "clauses": [
            clause.to_api_dict(include_content=include_clause_content)
            for clause in structure.clauses
        ],
        "key_clause_summary": structure.key_clause_summary,
        "stats": structure.stats,
        "warnings": structure.warnings,
    }


def _document_type(path: Path) -> str:
    """将文件扩展名转换为 pageindex 使用的文档类型。"""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".text"}:
        return "text"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    return suffix.removeprefix(".") or "text"
