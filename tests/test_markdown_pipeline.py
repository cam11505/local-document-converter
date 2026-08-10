from pathlib import Path

import pytest

from local_document_converter.exporters.json_exporter import JsonExporter
from local_document_converter.exporters.markdown import MarkdownExporter
from local_document_converter.exporters.registry import ExporterRegistry
from local_document_converter.parsers.markdown import MarkdownParser
from local_document_converter.parsers.registry import ParserRegistry
from local_document_converter.services.conversion_service import (
    ConversionRequest,
    ConversionService,
)


@pytest.fixture
def service(tmp_path: Path) -> ConversionService:
    parsers = ParserRegistry()
    parsers.register(MarkdownParser())
    exporters = ExporterRegistry()
    exporters.register(MarkdownExporter())
    exporters.register(JsonExporter())
    return ConversionService(parsers, exporters, output_directory=tmp_path)


def test_markdown_to_markdown(service: ConversionService, tmp_path: Path) -> None:
    source = tmp_path / "含 空白.md"
    source.write_text("# 標題\n\n段落內容\n\n- A\n- B\n", encoding="utf-8")
    destination = tmp_path / "輸出.md"

    result = service.convert(
        ConversionRequest(
            source=source,
            output_format="markdown",
            destination=destination,
        )
    )

    assert result.destination == destination.resolve()
    assert destination.read_text(encoding="utf-8") == "# 標題\n\n段落內容\n\n- A\n- B\n"


def test_markdown_to_json(service: ConversionService, tmp_path: Path) -> None:
    source = tmp_path / "sample.md"
    source.write_text("# Sample\n", encoding="utf-8")
    destination = tmp_path / "sample.json"

    service.convert(
        ConversionRequest(source=source, output_format="json", destination=destination)
    )

    content = destination.read_text(encoding="utf-8")
    assert '"schema_version": "1.0"' in content
    assert '"type": "heading"' in content
