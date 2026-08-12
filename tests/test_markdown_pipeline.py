from pathlib import Path

import pytest
from typer.testing import CliRunner

from local_document_converter.cli import app
from local_document_converter.domain import DocumentIR, TableBlock
from local_document_converter.exceptions import (
    ExportError,
    InputValidationError,
    OutputExistsError,
    UnsupportedFormatError,
)
from local_document_converter.exporters.base import ExportContext, ExporterCapability
from local_document_converter.exporters.json_exporter import JsonExporter
from local_document_converter.exporters.markdown import MarkdownExporter
from local_document_converter.exporters.registry import ExporterRegistry
from local_document_converter.parsers.base import ParseContext
from local_document_converter.parsers.markdown import MarkdownParser
from local_document_converter.parsers.registry import ParserRegistry
from local_document_converter.services.conversion_service import (
    ConversionRequest,
    ConversionService,
)

FIXTURES = Path(__file__).parent / "fixtures"


class FailingExporter:
    capability = ExporterCapability(format_name="failing", output_extension=".fail")

    def export(
        self, document: DocumentIR, destination: Path, context: ExportContext
    ) -> None:
        del document, context
        destination.write_text("partial", encoding="utf-8")
        raise ExportError("intentional exporter failure")


@pytest.fixture
def service(tmp_path: Path) -> ConversionService:
    parsers = ParserRegistry()
    parsers.register(MarkdownParser())
    exporters = ExporterRegistry()
    exporters.register(MarkdownExporter())
    exporters.register(JsonExporter())
    return ConversionService(parsers, exporters, output_directory=tmp_path / "output")


def test_fixture_markdown_to_markdown_matches_golden(
    service: ConversionService, tmp_path: Path
) -> None:
    source = FIXTURES / "sample.md"
    original = source.read_bytes()
    destination = tmp_path / "含 空白" / "輸出.md"

    result = service.convert(
        ConversionRequest(
            source=source,
            output_format="markdown",
            destination=destination,
        )
    )

    assert result.destination == destination.resolve()
    assert result.parser_name == "markdown"
    assert result.exporter_name == "markdown"
    assert result.warning_count == 0
    assert destination.read_text(encoding="utf-8") == (
        FIXTURES / "expected" / "sample.md"
    ).read_text(encoding="utf-8")
    assert source.read_bytes() == original


def test_markdown_to_json_is_valid_document_ir(
    service: ConversionService, tmp_path: Path
) -> None:
    destination = tmp_path / "sample.json"

    service.convert(
        ConversionRequest(
            source=FIXTURES / "sample.md",
            output_format="json",
            destination=destination,
        )
    )

    document = DocumentIR.from_json(destination.read_text(encoding="utf-8"))
    assert document.schema_version == "1.0"
    assert [block.type for block in document.blocks] == [
        "heading",
        "paragraph",
        "list",
        "list",
        "table",
        "image",
    ]
    assert "範例文件" in destination.read_text(encoding="utf-8")


def test_table_parser_unescapes_pipe_and_backslash(tmp_path: Path) -> None:
    source = tmp_path / "escaped.md"
    source.write_text(
        "| 名稱 | 路徑 |\n| --- | --- |\n| A\\|B | C\\\\D |\n",
        encoding="utf-8",
    )

    document = MarkdownParser().parse(source, context=_parse_context())
    table = document.blocks[0]

    assert isinstance(table, TableBlock)
    assert table.rows == [["A|B", "C\\D"]]


def test_table_width_is_normalized_with_warning(tmp_path: Path) -> None:
    source = tmp_path / "ragged.md"
    source.write_text(
        "| A | B |\n| --- | --- |\n| one |\n| x | y | z |\n",
        encoding="utf-8",
    )

    document = MarkdownParser().parse(source, context=_parse_context())
    table = document.blocks[0]

    assert isinstance(table, TableBlock)
    assert table.column_names == ["A", "B", ""]
    assert table.rows == [["one", None, None], ["x", "y", "z"]]
    assert [warning.code for warning in document.warnings] == [
        "markdown.table_width_normalized"
    ]


def test_unsupported_markdown_is_preserved_and_warned_once_per_syntax(
    tmp_path: Path,
) -> None:
    source = tmp_path / "unsupported.md"
    source.write_text(
        "> quote\n\n```python\nprint('x')\n```\n\n  - nested\n",
        encoding="utf-8",
    )

    document = MarkdownParser().parse(source, context=_parse_context())

    syntaxes = {warning.details["syntax"] for warning in document.warnings}
    assert syntaxes == {"block_quote", "fenced_code", "nested_list"}
    assert any("quote" in getattr(block, "text", "") for block in document.blocks)


def test_existing_destination_is_not_overwritten(
    service: ConversionService, tmp_path: Path
) -> None:
    destination = tmp_path / "existing.md"
    destination.write_text("keep me", encoding="utf-8")

    with pytest.raises(OutputExistsError):
        service.convert(
            ConversionRequest(
                source=FIXTURES / "sample.md",
                output_format="markdown",
                destination=destination,
            )
        )

    assert destination.read_text(encoding="utf-8") == "keep me"
    assert not list(tmp_path.glob(".existing.md.*.tmp"))


def test_overwrite_must_be_explicit(service: ConversionService, tmp_path: Path) -> None:
    destination = tmp_path / "overwrite.md"
    destination.write_text("old", encoding="utf-8")

    service.convert(
        ConversionRequest(
            source=FIXTURES / "sample.md",
            output_format="markdown",
            destination=destination,
            overwrite=True,
        )
    )

    assert destination.read_text(encoding="utf-8").startswith("# 範例文件")


def test_unknown_input_and_output_formats_are_rejected(
    service: ConversionService, tmp_path: Path
) -> None:
    unknown_source = tmp_path / "sample.txt"
    unknown_source.write_text("text", encoding="utf-8")

    with pytest.raises(UnsupportedFormatError):
        service.convert(ConversionRequest(source=unknown_source, output_format="json"))

    with pytest.raises(UnsupportedFormatError):
        service.convert(
            ConversionRequest(source=FIXTURES / "sample.md", output_format="xml")
        )


def test_input_and_output_paths_cannot_be_the_same(service: ConversionService) -> None:
    source = FIXTURES / "sample.md"

    with pytest.raises(InputValidationError, match="must be different"):
        service.convert(
            ConversionRequest(
                source=source,
                output_format="markdown",
                destination=source,
                overwrite=True,
            )
        )


def test_temporary_output_is_removed_when_export_fails(tmp_path: Path) -> None:
    parsers = ParserRegistry()
    parsers.register(MarkdownParser())
    exporters = ExporterRegistry()
    exporters.register(FailingExporter())
    service = ConversionService(parsers, exporters)
    destination = tmp_path / "failed.fail"

    with pytest.raises(ExportError, match="intentional exporter failure"):
        service.convert(
            ConversionRequest(
                source=FIXTURES / "sample.md",
                output_format="failing",
                destination=destination,
            )
        )

    assert not destination.exists()
    assert not list(tmp_path.glob(".failed.fail.*.tmp"))


def test_default_output_path_uses_configured_directory(
    service: ConversionService, tmp_path: Path
) -> None:
    result = service.convert(
        ConversionRequest(source=FIXTURES / "sample.md", output_format="json")
    )

    assert result.destination == (tmp_path / "output" / "sample.json").resolve()
    assert result.destination.is_file()


def test_cli_convert_and_inspect_support_unicode_paths(tmp_path: Path) -> None:
    source = tmp_path / "中文 輸入.md"
    source.write_text("# 標題\n\n內容\n", encoding="utf-8")
    destination = tmp_path / "中文 輸出.json"
    runner = CliRunner()

    convert_result = runner.invoke(
        app,
        ["convert", str(source), "--to", "json", "--output", str(destination)],
    )
    inspect_result = runner.invoke(app, ["inspect", str(source)])

    assert convert_result.exit_code == 0
    assert destination.is_file()
    assert inspect_result.exit_code == 0
    assert '"schema_version": "1.0"' in inspect_result.stdout
    assert "標題" in inspect_result.stdout


def test_cli_reports_existing_and_unknown_output_errors(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Source\n", encoding="utf-8")
    destination = tmp_path / "existing.json"
    destination.write_text("existing", encoding="utf-8")
    runner = CliRunner()

    existing_result = runner.invoke(
        app,
        ["convert", str(source), "--to", "json", "--output", str(destination)],
    )
    unknown_result = runner.invoke(app, ["convert", str(source), "--to", "xml"])

    assert existing_result.exit_code == 1
    assert "output already exists" in existing_result.stderr
    assert unknown_result.exit_code == 2
    assert "unsupported output format" in unknown_result.stderr


def _parse_context() -> ParseContext:
    return ParseContext()
