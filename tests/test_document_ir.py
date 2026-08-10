from local_document_converter.domain.models import (
    DocumentIR,
    HeadingBlock,
    ParagraphBlock,
    SourceInfo,
)


def test_document_ir_json_round_trip() -> None:
    document = DocumentIR(
        source=SourceInfo(path="測試/sample.pdf", media_type="application/pdf"),
        blocks=[
            HeadingBlock(id="h1", order=0, level=1, text="測試文件"),
            ParagraphBlock(id="p1", order=1, text="內容"),
        ],
    )

    restored = DocumentIR.model_validate_json(document.model_dump_json())

    assert restored == document
    assert restored.schema_version == "1.0"
