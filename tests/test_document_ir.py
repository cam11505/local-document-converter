import json

import pytest
from pydantic import ValidationError

from local_document_converter.domain.models import (
    DocumentIR,
    DocumentMetadata,
    DocumentWarning,
    HeadingBlock,
    ImageBlock,
    ListBlock,
    PageBreakBlock,
    ParagraphBlock,
    SourceInfo,
    TableBlock,
)


def test_document_ir_json_is_deterministic_utf8_and_round_trips() -> None:
    document = DocumentIR(
        source=SourceInfo(
            path="測試/sample.pdf",
            media_type="application/pdf",
            size_bytes=128,
            checksum_sha256="a" * 64,
        ),
        metadata=DocumentMetadata(
            title="測試文件",
            language="zh-Hant",
            page_count=1,
            custom={"z-last": 2, "a-first": 1},
        ),
        blocks=[
            HeadingBlock(
                id="h1",
                order=0,
                page_number=1,
                level=1,
                text="測試文件",
                attributes={"z-last": True, "a-first": "值"},
            ),
            ParagraphBlock(id="p1", order=1, page_number=1, text="Unicode 內容: 臺灣"),
        ],
        warnings=[DocumentWarning(code="layout.partial", message="部分版面未映射")],
    )

    encoded = document.to_json(indent=2)
    restored = DocumentIR.from_json(encoded)
    normalized = json.dumps(
        json.loads(encoded),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    )

    assert restored == document
    assert restored.schema_version == "1.0"
    assert restored.to_json(indent=2) == encoded
    assert normalized == encoded
    assert "測試文件" in encoded
    assert "\\u6e2c" not in encoded


def test_all_block_types_are_supported() -> None:
    document = DocumentIR(
        source=SourceInfo(path="all-blocks.md"),
        metadata=DocumentMetadata(page_count=2),
        blocks=[
            HeadingBlock(id="heading", order=0, page_number=1, level=2, text="標題"),
            ParagraphBlock(id="paragraph", order=1, page_number=1, text="段落"),
            ListBlock(id="list", order=2, page_number=1, ordered=True, items=["甲", "乙"]),
            TableBlock(
                id="table",
                order=3,
                page_number=1,
                column_names=["欄一", "欄二"],
                rows=[["值", None], ["", "第二列"]],
                caption="資料表",
            ),
            ImageBlock(
                id="image",
                order=4,
                page_number=2,
                uri="images/example.png",
                alt_text="範例圖片",
                caption="圖一",
            ),
            PageBreakBlock(id="page-break", order=5, page_number=2),
        ],
    )

    restored = DocumentIR.from_json(document.to_json())

    assert [block.type for block in restored.blocks] == [
        "heading",
        "paragraph",
        "list",
        "table",
        "image",
        "page_break",
    ]


def test_empty_document_and_empty_table_are_valid() -> None:
    empty_document = DocumentIR(source=SourceInfo(path="empty.md"))
    document_with_empty_table = DocumentIR(
        source=SourceInfo(path="empty-table.md"),
        blocks=[TableBlock(id="table", order=0, rows=[], column_names=[])],
    )

    assert DocumentIR.from_json(empty_document.to_json()) == empty_document
    assert DocumentIR.from_json(document_with_empty_table.to_json()) == document_with_empty_table


def test_block_ids_must_be_unique() -> None:
    with pytest.raises(ValidationError, match="block id values must be unique"):
        DocumentIR(
            source=SourceInfo(path="duplicate-id.md"),
            blocks=[
                ParagraphBlock(id="same", order=0, text="第一段"),
                ParagraphBlock(id="same", order=1, text="第二段"),
            ],
        )


@pytest.mark.parametrize("orders", [[0, 0], [0, 2], [1, 0]])
def test_block_orders_must_be_contiguous_and_match_list_order(orders: list[int]) -> None:
    with pytest.raises(ValidationError, match="block order values must be contiguous"):
        DocumentIR(
            source=SourceInfo(path="invalid-order.md"),
            blocks=[
                ParagraphBlock(id="first", order=orders[0], text="第一段"),
                ParagraphBlock(id="second", order=orders[1], text="第二段"),
            ],
        )


def test_page_numbers_must_be_positive_and_within_page_count() -> None:
    with pytest.raises(ValidationError):
        ParagraphBlock(id="paragraph", order=0, page_number=0, text="內容")

    with pytest.raises(ValidationError, match=r"cannot exceed metadata\.page_count"):
        DocumentIR(
            source=SourceInfo(path="page-range.md"),
            metadata=DocumentMetadata(page_count=1),
            blocks=[ParagraphBlock(id="paragraph", order=0, page_number=2, text="內容")],
        )

    with pytest.raises(ValidationError, match="warning page_number cannot exceed"):
        DocumentIR(
            source=SourceInfo(path="warning-page.md"),
            metadata=DocumentMetadata(page_count=1),
            warnings=[DocumentWarning(code="page.warning", message="警告", page_number=2)],
        )


def test_table_rows_must_be_rectangular_and_match_columns() -> None:
    with pytest.raises(ValidationError, match="same number of cells"):
        TableBlock(id="ragged", order=0, rows=[["A"], ["B", "C"]])

    with pytest.raises(ValidationError, match="column_names length must match"):
        TableBlock(id="headers", order=0, column_names=["A"], rows=[["1", "2"]])

    with pytest.raises(ValidationError):
        TableBlock(id="invalid-cell", order=0, rows=[[123]])


def test_required_content_and_json_attributes_are_validated() -> None:
    with pytest.raises(ValidationError):
        SourceInfo(path="")

    with pytest.raises(ValidationError):
        SourceInfo(path="sample.pdf", checksum_sha256="not-a-sha256")

    with pytest.raises(ValidationError):
        ImageBlock(id="image", order=0, uri="")

    with pytest.raises(ValidationError):
        ListBlock(id="list", order=0, items=[])

    with pytest.raises(ValidationError):
        ParagraphBlock(id="paragraph", order=0, text="內容", attributes={"score": float("nan")})


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        DocumentIR.model_validate(
            {
                "schema_version": "1.0",
                "source": {"path": "sample.md"},
                "blocks": [],
                "unknown": True,
            }
        )
