"""LPOS pageindex 文本块与来源定位测试。"""

from langchain_core.documents import Document

from src.shuyixiao_agent.lpos import pageindex


def test_pdf_document_page_metadata_becomes_one_based_source_ref():
    """PDF loader 的 0-based page metadata 应转换为对外 1-based 页码。"""
    documents = [
        Document(page_content="第一页文本", metadata={"type": "pdf", "page": 0, "source": "/tmp/a.pdf"}),
        Document(page_content="第二页文本", metadata={"type": "pdf", "page": 1, "source": "/tmp/a.pdf"}),
    ]

    blocks = pageindex.build_page_index(
        documents,
        file_id="20260616_120000_abcdef123456",
        original_filename="合同.pdf",
        document_type="pdf",
    )

    assert blocks[0].source_ref.page_number == 1
    assert blocks[1].source_ref.page_number == 2
    assert blocks[0].source_ref.file_id == "20260616_120000_abcdef123456"
    assert blocks[0].source_ref.source_name == "合同.pdf"
    assert blocks[0].source_ref.text_preview == "第一页文本"


def test_docx_without_page_metadata_uses_paragraph_and_char_offsets():
    """无页码 metadata 的 DOCX 应按段落生成定位信息。"""
    documents = [
        Document(page_content="第一段\n\n第二段", metadata={"type": "docx", "source": "/tmp/a.docx"}),
    ]

    blocks = pageindex.build_page_index(
        documents,
        file_id="20260616_120000_abcdef123456",
        original_filename="合同.docx",
        document_type="docx",
    )

    assert [block.text for block in blocks] == ["第一段", "第二段"]
    assert blocks[0].source_ref.page_number is None
    assert blocks[0].source_ref.paragraph_index == 1
    assert blocks[1].source_ref.paragraph_index == 2
    assert blocks[0].source_ref.char_start == 0
    assert blocks[0].source_ref.char_end == len("第一段")
