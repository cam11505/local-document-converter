from pathlib import Path

import pytest
from pydantic import JsonValue
from typer.testing import CliRunner

from local_document_converter.cli import app
from local_document_converter.config import ExcelSettings
from local_document_converter.domain import DocumentIR, HeadingBlock, TableBlock
from local_document_converter.exceptions import InputValidationError, ParseError
from local_document_converter.exporters.json_exporter import JsonExporter
from local_document_converter.exporters.markdown import MarkdownExporter
from local_document_converter.exporters.registry import ExporterRegistry
from local_document_converter.parsers.base import ParseContext
from local_document_converter.parsers.excel_parser import ExcelParser
from local_document_converter.parsers.registry import ParserRegistry
from local_document_converter.services.conversion_service import (
    ConversionRequest,
    ConversionService,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "sample.xlsx"


def test_fixture_preserves_sheet_order_cells_dates_blanks_and_merges() -> None:
    document = ExcelParser().parse(SAMPLE, ParseContext())

    assert [block.type for block in document.blocks] == [
        "heading",
        "table",
        "heading",
        "table",
    ]
    headings = [block for block in document.blocks if isinstance(block, HeadingBlock)]
    tables = [block for block in document.blocks if isinstance(block, TableBlock)]
    assert [heading.text for heading in headings] == ["摘要", "空白與合併"]
    assert [heading.attributes["sheet_index"] for heading in headings] == [0, 1]
    assert tables[0].column_names == ["A", "B", "C", "D", "E"]
    assert tables[0].rows[2] == [
        "2026-08-01T00:00:00",
        "竹科測試板",
        "2",
        "1250",
        "2500",
    ]
    assert tables[1].rows[1] == [None, None, None, None]
    assert tables[1].rows[4] == [None, None, None, None]
    assert [warning.code for warning in document.warnings] == [
        "excel.merged_cells",
        "excel.merged_cells",
    ]
    assert document.warnings[1].details["ranges"] == ["A1:D1", "A6:B6"]


def test_data_only_false_preserves_formula_text() -> None:
    document = ExcelParser().parse(SAMPLE, ParseContext(options={"data_only": False}))
    summary = document.blocks[1]

    assert isinstance(summary, TableBlock)
    assert summary.rows[2][4] == "=C3*D3"
    assert summary.rows[5][4] == "=SUM(E3:E5)"
    assert "excel.formula_cache_missing" not in {warning.code for warning in document.warnings}


def test_missing_formula_cache_is_blank_but_retains_position_and_warns() -> None:
    rows, start_row, start_column, warnings = ExcelParser._materialize_sheet(
        sheet_name="公式",
        value_rows=[("標題",), (None,)],
        formula_rows=[("標題",), ("=1+1",)],
        max_rows=10,
        max_columns=10,
    )

    assert rows == [["標題"], [None]]
    assert (start_row, start_column) == (1, 1)
    assert [warning.code for warning in warnings] == ["excel.formula_cache_missing"]
    assert warnings[0].details["cells"] == ["A2"]


def test_blank_outer_ranges_are_trimmed_but_origin_is_recorded() -> None:
    rows, start_row, start_column, warnings = ExcelParser._materialize_sheet(
        sheet_name="空白邊界",
        value_rows=[(), (None, "內容", None), ()],
        formula_rows=None,
        max_rows=10,
        max_columns=10,
    )

    assert rows == [["內容"]]
    assert (start_row, start_column) == (2, 2)
    assert [warning.code for warning in warnings] == ["excel.blank_edges_trimmed"]


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"max_rows_per_sheet": 5}, "max_rows_per_sheet=5"),
        ({"max_columns_per_sheet": 4}, "max_columns_per_sheet=4"),
    ],
)
def test_sheet_size_limits_are_enforced(options: dict[str, JsonValue], message: str) -> None:
    with pytest.raises(InputValidationError, match=message):
        ExcelParser().parse(SAMPLE, ParseContext(options=options))


def test_configured_sheet_limit_and_option_types_are_enforced() -> None:
    parser = ExcelParser(ExcelSettings(max_rows_per_sheet=5))

    with pytest.raises(InputValidationError, match="max_rows_per_sheet=5"):
        parser.parse(SAMPLE, ParseContext())
    with pytest.raises(InputValidationError, match="must be a boolean"):
        ExcelParser().parse(SAMPLE, ParseContext(options={"data_only": "yes"}))


def test_only_valid_xlsx_files_are_accepted(tmp_path: Path) -> None:
    wrong_extension = tmp_path / "sample.xls"
    wrong_extension.write_bytes(SAMPLE.read_bytes())
    corrupt = tmp_path / "corrupt.xlsx"
    corrupt.write_text("not a zip archive", encoding="utf-8")

    with pytest.raises(InputValidationError, match=r"only \.xlsx"):
        ExcelParser().parse(wrong_extension, ParseContext())
    with pytest.raises(ParseError, match="could not parse XLSX"):
        ExcelParser().parse(corrupt, ParseContext())


def test_xlsx_to_markdown_and_json_are_deterministic(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first_markdown = tmp_path / "first.md"
    second_markdown = tmp_path / "second.md"
    first_json = tmp_path / "first.json"
    second_json = tmp_path / "second.json"

    for destination, output_format in [
        (first_markdown, "markdown"),
        (second_markdown, "markdown"),
        (first_json, "json"),
        (second_json, "json"),
    ]:
        service.convert(
            ConversionRequest(
                source=SAMPLE,
                output_format=output_format,
                destination=destination,
            )
        )

    markdown = first_markdown.read_text(encoding="utf-8")
    assert markdown == second_markdown.read_text(encoding="utf-8")
    assert markdown == (FIXTURES / "expected" / "sample.xlsx.md").read_text(encoding="utf-8")
    assert first_json.read_bytes() == second_json.read_bytes()
    restored = DocumentIR.from_json(first_json.read_text(encoding="utf-8"))
    assert [warning.code for warning in restored.warnings] == [
        "excel.merged_cells",
        "excel.merged_cells",
    ]


def test_cli_convert_and_inspect_xlsx(tmp_path: Path) -> None:
    destination = tmp_path / "excel.json"
    runner = CliRunner()

    convert_result = runner.invoke(
        app,
        ["convert", str(SAMPLE), "--to", "json", "--output", str(destination)],
    )
    inspect_result = runner.invoke(app, ["inspect", str(SAMPLE)])

    assert convert_result.exit_code == 0
    assert destination.is_file()
    assert inspect_result.exit_code == 0
    assert '"sheet_name": "摘要"' in inspect_result.stdout


def _service(tmp_path: Path) -> ConversionService:
    parsers = ParserRegistry()
    parsers.register(ExcelParser())
    exporters = ExporterRegistry()
    exporters.register(MarkdownExporter())
    exporters.register(JsonExporter())
    return ConversionService(parsers, exporters, output_directory=tmp_path)
