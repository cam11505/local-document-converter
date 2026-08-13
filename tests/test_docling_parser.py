from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

import local_document_converter.parsers.docling_parser as docling_adapter
from local_document_converter.domain import (
    HeadingBlock,
    ImageBlock,
    ListBlock,
    ParagraphBlock,
    TableBlock,
)
from local_document_converter.exceptions import ParseError, ParserUnavailableError
from local_document_converter.exporters.base import ExportContext
from local_document_converter.exporters.markdown import MarkdownExporter
from local_document_converter.exporters.registry import ExporterRegistry
from local_document_converter.parsers.base import ParseContext
from local_document_converter.parsers.docling_parser import DoclingParser
from local_document_converter.parsers.registry import ParserRegistry
from local_document_converter.services.conversion_service import (
    ConversionRequest,
    ConversionService,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "sample.pdf"


@dataclass(frozen=True)
class FakeEnum:
    value: str


@dataclass(frozen=True)
class FakeProvenance:
    page_no: int


@dataclass(frozen=True)
class FakeCell:
    text: str
    column_header: bool = False


@dataclass(frozen=True)
class FakeTableData:
    grid: list[list[FakeCell]]


@dataclass
class FakeItem:
    label: FakeEnum
    self_ref: str
    text: str = ""
    prov: list[FakeProvenance] = field(default_factory=lambda: [FakeProvenance(page_no=1)])
    level: int = 1
    enumerated: bool = False
    data: FakeTableData | None = None
    caption: str = ""

    def caption_text(self, document: object) -> str:
        del document
        return self.caption


@dataclass
class FakeDocument:
    items: list[FakeItem]
    pages: dict[int, object] = field(default_factory=lambda: {1: object()})

    def iterate_items(self) -> list[tuple[FakeItem, int]]:
        return [(item, 0) for item in self.items]


@dataclass(frozen=True)
class FakeError:
    error_message: str


@dataclass
class FakeResult:
    status: FakeEnum
    document: FakeDocument
    errors: list[FakeError] = field(default_factory=list)


class FakeConverter:
    def __init__(self, result: FakeResult) -> None:
        self.result = result
        self.calls: list[tuple[Path, bool]] = []

    def convert(self, source: Path, *, raises_on_error: bool) -> object:
        self.calls.append((source, raises_on_error))
        return self.result


def test_mocked_docling_pdf_maps_to_document_ir_and_golden_markdown(
    tmp_path: Path,
) -> None:
    converter = FakeConverter(_successful_result())
    parser = DoclingParser(converter_factory=lambda: converter)
    parsers = ParserRegistry()
    parsers.register(parser)
    exporters = ExporterRegistry()
    exporters.register(MarkdownExporter())
    destination = tmp_path / "sample.md"

    result = ConversionService(parsers, exporters).convert(
        ConversionRequest(
            source=SAMPLE,
            output_format="markdown",
            destination=destination,
        )
    )
    document = parser.parse(SAMPLE, ParseContext())

    assert result.parser_name == "docling"
    assert converter.calls == [
        (SAMPLE.resolve(), False),
        (SAMPLE.resolve(), False),
    ]
    assert document.metadata.title == "Stage 6 PDF Sample"
    assert document.metadata.page_count == 1
    assert document.source.media_type == "application/pdf"
    assert document.source.checksum_sha256 is not None
    assert [block.type for block in document.blocks] == [
        "heading",
        "paragraph",
        "heading",
        "list",
        "table",
        "image",
    ]
    assert [block.order for block in document.blocks] == list(range(6))
    assert all(block.page_number == 1 for block in document.blocks)

    heading = document.blocks[2]
    items = document.blocks[3]
    table = document.blocks[4]
    image = document.blocks[5]
    assert isinstance(heading, HeadingBlock)
    assert heading.level == 2
    assert isinstance(items, ListBlock)
    assert items.items == ["Preserve reading order", "Map tables to DocumentIR"]
    assert isinstance(table, TableBlock)
    assert table.column_names == ["Component", "Status"]
    assert table.rows == [
        ["DoclingParser", "Ready"],
        ["MarkdownExporter", "Ready"],
    ]
    assert isinstance(image, ImageBlock)
    assert image.uri == "sample.pdf#/pictures/0"
    assert destination.read_text(encoding="utf-8") == (
        FIXTURES / "expected" / "sample.pdf.md"
    ).read_text(encoding="utf-8")


def test_partial_result_preserves_text_and_reports_mapping_warnings() -> None:
    items = [
        FakeItem(
            FakeEnum("section_header"),
            "#/texts/0",
            text="Deep heading",
            level=9,
        ),
        FakeItem(FakeEnum("formula"), "#/texts/1", text="x + y"),
    ]
    result = FakeResult(
        status=FakeEnum("partial_success"),
        document=FakeDocument(items),
        errors=[FakeError("one page was only partially parsed")],
    )

    document = DoclingParser(converter_factory=lambda: FakeConverter(result)).parse(
        SAMPLE, ParseContext()
    )

    assert isinstance(document.blocks[0], HeadingBlock)
    assert document.blocks[0].level == 6
    assert isinstance(document.blocks[1], ParagraphBlock)
    assert document.blocks[1].text == "x + y"
    assert [warning.code for warning in document.warnings] == [
        "docling.partial_success",
        "docling.heading_level_clamped",
        "docling.unmapped_item",
    ]


def test_failed_conversion_reports_docling_error_without_returning_empty_ir() -> None:
    result = FakeResult(
        status=FakeEnum("failure"),
        document=FakeDocument([]),
        errors=[FakeError("invalid or truncated PDF")],
    )

    with pytest.raises(ParseError, match="invalid or truncated PDF"):
        DoclingParser(converter_factory=lambda: FakeConverter(result)).parse(SAMPLE, ParseContext())


def test_missing_optional_docling_runtime_is_reported_at_capability_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docling_adapter, "_docling_is_installed", lambda: False)
    parser = DoclingParser()
    registry = ParserRegistry()
    registry.register(parser)

    assert not parser.capability.availability.available
    with pytest.raises(ParserUnavailableError, match="optional dependency"):
        registry.for_path(SAMPLE)


def test_default_factory_uses_unicode_safe_pdf_backend_and_disables_torch_compile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: dict[str, object] = {}

    class FakePipelineOptions:
        def __init__(self) -> None:
            self.layout_options = SimpleNamespace(engine_options=None)

    class FakeEngineOptions:
        def __init__(self, *, compile_model: bool) -> None:
            self.compile_model = compile_model

    class FakePdfFormatOption:
        def __init__(self, *, pipeline_options: FakePipelineOptions, backend: object) -> None:
            self.pipeline_options = pipeline_options
            self.backend = backend

    class FakeDocumentConverter:
        def __init__(self, *, format_options: dict[object, object]) -> None:
            created["format_options"] = format_options

    fake_backend = object()
    modules = {
        "docling.backend.pypdfium2_backend": SimpleNamespace(PyPdfiumDocumentBackend=fake_backend),
        "docling.datamodel.base_models": SimpleNamespace(InputFormat=SimpleNamespace(PDF="pdf")),
        "docling.datamodel.object_detection_engine_options": SimpleNamespace(
            TransformersObjectDetectionEngineOptions=FakeEngineOptions
        ),
        "docling.datamodel.pipeline_options": SimpleNamespace(
            PdfPipelineOptions=FakePipelineOptions
        ),
        "docling.document_converter": SimpleNamespace(
            DocumentConverter=FakeDocumentConverter,
            PdfFormatOption=FakePdfFormatOption,
        ),
    }
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: modules[name],
    )

    converter = docling_adapter._load_converter_factory()()

    assert isinstance(converter, FakeDocumentConverter)
    format_options = created["format_options"]
    assert isinstance(format_options, dict)
    pdf_option = format_options["pdf"]
    assert isinstance(pdf_option, FakePdfFormatOption)
    assert pdf_option.backend is fake_backend
    engine_options = pdf_option.pipeline_options.layout_options.engine_options
    assert engine_options.compile_model is False


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("LDC_RUN_DOCLING_INTEGRATION") != "1",
    reason="set LDC_RUN_DOCLING_INTEGRATION=1 to exercise the real Docling runtime",
)
def test_real_docling_sample_pdf_to_markdown(tmp_path: Path) -> None:
    parser = DoclingParser()
    if not parser.capability.availability.available:
        pytest.skip("Docling optional dependency is not installed")
    document = parser.parse(SAMPLE, ParseContext())
    destination = tmp_path / "sample.md"

    MarkdownExporter().export(document, destination, context=ExportContext())

    markdown = destination.read_text(encoding="utf-8")
    golden = (FIXTURES / "expected" / "sample.pdf.md").read_text(encoding="utf-8")
    assert document.blocks
    assert markdown.strip()
    for key_text in (
        "Stage 6 PDF Sample",
        "This PDF verifies the Docling parser path.",
    ):
        assert key_text in golden
        assert key_text in markdown


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("LDC_RUN_DOCLING_INTEGRATION") != "1",
    reason="set LDC_RUN_DOCLING_INTEGRATION=1 to exercise the real Docling runtime",
)
def test_real_docling_rejects_corrupt_pdf(tmp_path: Path) -> None:
    source = tmp_path / "corrupt.pdf"
    source.write_bytes(b"%PDF-1.7\ntruncated")

    with pytest.raises(ParseError, match="Docling"):
        DoclingParser().parse(source, ParseContext())


def _successful_result() -> FakeResult:
    cells = [
        [FakeCell("Component", column_header=True), FakeCell("Status", True)],
        [FakeCell("DoclingParser"), FakeCell("Ready")],
        [FakeCell("MarkdownExporter"), FakeCell("Ready")],
    ]
    return FakeResult(
        status=FakeEnum("success"),
        document=FakeDocument(
            [
                FakeItem(FakeEnum("title"), "#/texts/0", text="Stage 6 PDF Sample"),
                FakeItem(
                    FakeEnum("paragraph"),
                    "#/texts/1",
                    text="This PDF verifies the Docling parser path.",
                ),
                FakeItem(
                    FakeEnum("section_header"),
                    "#/texts/2",
                    text="Expected behavior",
                    level=2,
                ),
                FakeItem(
                    FakeEnum("list_item"),
                    "#/texts/3",
                    text="Preserve reading order",
                ),
                FakeItem(
                    FakeEnum("list_item"),
                    "#/texts/4",
                    text="Map tables to DocumentIR",
                ),
                FakeItem(
                    FakeEnum("table"),
                    "#/tables/0",
                    data=FakeTableData(cells),
                ),
                FakeItem(
                    FakeEnum("picture"),
                    "#/pictures/0",
                    caption="DocumentIR flow",
                ),
            ]
        ),
    )
