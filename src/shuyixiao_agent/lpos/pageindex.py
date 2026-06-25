"""将 DocumentLoader 输出规范化为 pageindex 风格文本块。"""

from __future__ import annotations

import re
from typing import Sequence

from langchain_core.documents import Document

from .contract_models import PageTextBlock, SourceRef


def build_page_index(
    documents: Sequence[Document],
    *,
    file_id: str,
    original_filename: str,
    document_type: str,
    source_preview_chars: int = 160,
) -> list[PageTextBlock]:
    """构建带来源定位的文本块列表。"""
    normalized_type = document_type.lower()
    blocks: list[PageTextBlock] = []

    for document in documents:
        text = document.page_content or ""
        if normalized_type == "pdf":
            block_text = text.strip()
            if not block_text:
                continue
            blocks.append(
                PageTextBlock(
                    text=block_text,
                    source_ref=SourceRef(
                        file_id=file_id,
                        source_name=original_filename,
                        document_type=document_type,
                        page_number=_one_based_page_number(document.metadata.get("page")),
                        char_start=0,
                        char_end=len(text),
                        text_preview=_preview(block_text, source_preview_chars),
                    ),
                )
            )
            continue

        for paragraph_index, char_start, char_end, paragraph in _iter_paragraphs(text):
            blocks.append(
                PageTextBlock(
                    text=paragraph,
                    source_ref=SourceRef(
                        file_id=file_id,
                        source_name=original_filename,
                        document_type=document_type,
                        page_number=None,
                        paragraph_index=paragraph_index,
                        char_start=char_start,
                        char_end=char_end,
                        text_preview=_preview(paragraph, source_preview_chars),
                    ),
                )
            )

    return blocks


def _one_based_page_number(raw_page: object) -> int | None:
    """将 loader 的 0-based 页码转换为对外 1-based 页码。"""
    if raw_page is None:
        return None
    try:
        return int(raw_page) + 1
    except (TypeError, ValueError):
        return None


def _iter_paragraphs(text: str):
    """按空行拆分段落，并保留原文字符范围。"""
    paragraph_index = 0
    for match in re.finditer(r"\S(?:.*?\S)?(?=(?:\n\s*\n)|\Z)", text, flags=re.DOTALL):
        paragraph = match.group(0).strip()
        if not paragraph:
            continue
        paragraph_index += 1
        leading_whitespace = len(match.group(0)) - len(match.group(0).lstrip())
        trailing_whitespace = len(match.group(0)) - len(match.group(0).rstrip())
        char_start = match.start() + leading_whitespace
        char_end = match.end() - trailing_whitespace
        yield paragraph_index, char_start, char_end, paragraph


def _preview(text: str, limit: int) -> str:
    """生成来源预览文本。"""
    if limit <= 0:
        return ""
    return text[:limit]
