"""规则优先的 LPOS 合同结构化抽取。"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Iterable

from .contract_models import ContractClause, ContractStructure, PageTextBlock, SourceRef


CONTRACT_TYPE_KEYWORDS = ("采购合同", "租赁合同", "服务合同", "劳动合同", "保密协议")
CLAUSE_PATTERN = re.compile(
    r"(?m)^\s*(?:第[一二三四五六七八九十百千万0-9]+条\s*([^\n]*)|[一二三四五六七八九十百千万]+[、.．]\s*([^\n]+))"
)
PARTY_PATTERN = re.compile(
    r"((?:甲方|乙方|出租方|承租方|委托方|受托方|买方|卖方)(?:[（(][^）)\n]{1,30}[）)])?)[:：]\s*([^\n。；;]+)"
)
AMOUNT_PATTERN = re.compile(
    r"(?:合同总价|合同金额|总价|价款)[^\n。；;]*?(?:人民币)?[0-9][0-9,.]*(?:万|亿)?元"
    r"|(?:人民币)?[0-9][0-9,.]*(?:万|亿)?元"
)
TERM_PATTERN = re.compile(r"(?:履行期限|租赁期限|有效期)[:：为，自\s]*[^\n。；;]+")


def extract_contract_structure(
    blocks: list[PageTextBlock],
    *,
    file_id: str,
    original_filename: str,
    document_type: str,
    include_clause_content: bool = False,
    max_clauses: int = 300,
    clause_preview_chars: int = 160,
) -> ContractStructure:
    """从 pageindex 文本块中抽取合同结构。"""
    full_text = "\n\n".join(block.text for block in blocks)
    source_refs = [block.source_ref for block in blocks]
    warnings: list[str] = []

    contract_type = _extract_contract_type(full_text, source_refs, original_filename)
    key_fields = {
        "parties": _extract_parties(full_text, source_refs),
        "amount": _extract_pattern_fields(full_text, AMOUNT_PATTERN, source_refs),
        "term": _extract_pattern_fields(full_text, TERM_PATTERN, source_refs),
        "effective_date": [],
        "governing_law": [],
    }
    all_clauses = _extract_clauses(
        full_text,
        source_refs,
        include_clause_content=include_clause_content,
        clause_preview_chars=clause_preview_chars,
    )
    if len(all_clauses) > max_clauses:
        warnings.append(f"超过条款数量上限 {max_clauses}，已截断。")
    clauses = all_clauses[:max_clauses]

    return ContractStructure(
        file={
            "file_id": file_id,
            "original_filename": original_filename,
            "document_type": document_type,
            "page_count": _count_pages(source_refs),
        },
        contract_type=contract_type,
        key_fields=key_fields,
        clauses=clauses,
        key_clause_summary=_build_key_clause_summary(clauses),
        stats={
            "clause_count": len(clauses),
            "page_count": _count_pages(source_refs),
            "text_char_count": len(full_text),
        },
        warnings=warnings,
    )


def _extract_contract_type(
    full_text: str,
    source_refs: list[SourceRef],
    original_filename: str,
) -> dict[str, Any]:
    """从标题区域识别合同类型。"""
    title_area = "\n".join(full_text.splitlines()[:10])
    normalized_title_area = _remove_whitespace(title_area)
    for keyword in CONTRACT_TYPE_KEYWORDS:
        if keyword in title_area or keyword in normalized_title_area:
            return _field(keyword, 0.78, source_refs[:1])

    normalized_filename = _remove_whitespace(original_filename)
    for keyword in CONTRACT_TYPE_KEYWORDS:
        if keyword in normalized_filename:
            return _field(keyword, 0.66, source_refs[:1])

    return _field("未知合同", 0.3, source_refs[:1])


def _extract_parties(full_text: str, source_refs: list[SourceRef]) -> list[dict[str, Any]]:
    """抽取合同主体。"""
    fields = []
    for match in PARTY_PATTERN.finditer(full_text):
        fields.append(_field(f"{match.group(1)}：{match.group(2).strip()}", 0.82, source_refs[:1]))
    return fields


def _extract_pattern_fields(
    full_text: str,
    pattern: re.Pattern[str],
    source_refs: list[SourceRef],
) -> list[dict[str, Any]]:
    """按正则抽取字段，保持顺序并去重。"""
    values: list[str] = []
    for match in pattern.finditer(full_text):
        value = match.group(0).strip()
        if value and value not in values:
            values.append(value)
    return [_field(value, 0.76, source_refs[:1]) for value in values]


def _extract_clauses(
    full_text: str,
    source_refs: list[SourceRef],
    *,
    include_clause_content: bool,
    clause_preview_chars: int,
) -> list[ContractClause]:
    """按“第X条”标题切分条款。"""
    matches = list(CLAUSE_PATTERN.finditer(full_text))
    clauses: list[ContractClause] = []
    for index, match in enumerate(matches, start=1):
        end = matches[index].start() if index < len(matches) else len(full_text)
        content = full_text[match.start():end].strip()
        raw_title = next((group for group in match.groups() if group), "")
        title = raw_title.strip() or f"条款{index}"
        content_preview = content[:clause_preview_chars] if clause_preview_chars > 0 else ""
        clauses.append(
            ContractClause(
                clause_id=f"clause_{index:04d}",
                title=title,
                clause_type=_classify_clause(title),
                content_preview=content_preview,
                content_truncated=len(content) > len(content_preview),
                source_refs=source_refs[:1],
                confidence=0.81,
                content=content if include_clause_content else None,
            )
        )
    return clauses


def _classify_clause(title: str) -> str:
    """按标题关键词粗分条款类型。"""
    if any(keyword in title for keyword in ("付款", "支付", "价款")):
        return "payment"
    if any(keyword in title for keyword in ("违约", "责任", "赔偿")):
        return "liability"
    if any(keyword in title for keyword in ("期限", "有效期")):
        return "term"
    if any(keyword in title for keyword in ("保密", "秘密")):
        return "confidentiality"
    return "general"


def _build_key_clause_summary(clauses: Iterable[ContractClause]) -> list[dict[str, Any]]:
    """生成关键条款摘要入口，不生成法律结论。"""
    summaries = []
    for clause in clauses:
        if clause.clause_type in {"payment", "liability", "term", "confidentiality"}:
            summaries.append(
                {
                    "clause_id": clause.clause_id,
                    "title": clause.title,
                    "clause_type": clause.clause_type,
                    "summary": clause.content_preview,
                    "source_refs": [asdict(source_ref) for source_ref in clause.source_refs],
                }
            )
    return summaries


def _remove_whitespace(value: str) -> str:
    """用于标题和文件名兜底识别，消除 DOCX 标题字间空格影响。"""
    return re.sub(r"\s+", "", value or "")


def _field(value: str, confidence: float, source_refs: list[SourceRef]) -> dict[str, Any]:
    """构建带来源的字段。"""
    return {
        "value": value,
        "confidence": confidence,
        "source_refs": [asdict(source_ref) for source_ref in source_refs],
    }


def _count_pages(source_refs: list[SourceRef]) -> int | None:
    """统计 pageindex 中的页数；无页码时返回 None。"""
    page_numbers = {source_ref.page_number for source_ref in source_refs if source_ref.page_number is not None}
    return len(page_numbers) or None
