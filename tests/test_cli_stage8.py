from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import local_document_converter.cli as cli_module
import local_document_converter.parsers.docling_parser as docling_adapter
from local_document_converter.cli import app
from local_document_converter.domain import DocumentIR, DocumentMetadata, SourceInfo
from local_document_converter.exceptions import ExportError, InputValidationError
from local_document_converter.exporters.base import ExportContext, ExporterCapability
from local_document_converter.exporters.json_exporter import JsonExporter
from local_document_converter.exporters.registry import ExporterRegistry
from local_document_converter.parsers.base import ParseContext, ParserCapability
from local_document_converter.parsers.markdown import MarkdownParser
from local_document_converter.parsers.registry import ParserRegistry
from local_document_converter.services.conversion_service import (
    ConversionRequest,
    ConversionService,
)

FIXTURES = Path(__file__).parent / "fixtures"


class InterruptingExporter:
    capability = ExporterCapability(format_name="interrupt", output_extension=".halt")

    def export(self, document: DocumentIR, destination: Path, context: ExportContext) -> None:
        del document, context
        destination.write_text("partial", encoding="utf-8")
        raise KeyboardInterrupt


class FailingExporter:
    capability = ExporterCapability(format_name="failure", output_extension=".fail")

    def export(self, document: DocumentIR, destination: Path, context: ExportContext) -> None:
        del document, context
        destination.write_text("partial", encoding="utf-8")
        raise ExportError("intentional partial failure")


class TwoPageParser:
    capability = ParserCapability(
        name="two-page",
        supported_extensions=frozenset({".many"}),
    )

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del context
        return DocumentIR(
            source=SourceInfo(path=str(source)),
            metadata=DocumentMetadata(page_count=2),
        )


def test_cli_config_precedence_output_directory_and_overwrite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yaml_output = tmp_path / "yaml output"
    env_output = tmp_path / "env output"
    config = tmp_path / "settings.yaml"
    config.write_text(
        f"output_directory: {yaml_output.as_posix()}\noverwrite: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LDC_OUTPUT_DIRECTORY", str(env_output))
    monkeypatch.setenv("LDC_OVERWRITE", "false")
    source = tmp_path / "中文 輸入.md"
    source.write_text("# 標題\n", encoding="utf-8")
    runner = CliRunner()

    default_result = runner.invoke(
        app,
        ["convert", str(source), "--to", "json", "--config", str(config)],
    )
    destination = env_output / "中文 輸入.json"
    destination.write_text("old", encoding="utf-8")
    overwrite_result = runner.invoke(
        app,
        [
            "convert",
            str(source),
            "--to",
            "json",
            "--config",
            str(config),
            "--overwrite",
            "--verbose",
        ],
    )

    assert default_result.exit_code == 0
    assert destination.is_file()
    assert overwrite_result.exit_code == 0
    assert DocumentIR.from_json(destination.read_text(encoding="utf-8")).blocks
    assert "parser=markdown" in overwrite_result.stderr
    assert "exporter=json" in overwrite_result.stderr
    assert "elapsed_ms=" in overwrite_result.stderr


def test_explicit_config_beats_environment_config_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    invalid_config = tmp_path / "environment.yaml"
    invalid_config.write_text("max_file_size_mb: invalid\n", encoding="utf-8")
    explicit_config = tmp_path / "explicit.yaml"
    output_directory = tmp_path / "explicit output"
    explicit_config.write_text(
        f"output_directory: {output_directory.as_posix()}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LDC_CONFIG_FILE", str(invalid_config))

    result = CliRunner().invoke(
        app,
        [
            "convert",
            str(FIXTURES / "sample.md"),
            "--to",
            "json",
            "--config",
            str(explicit_config),
        ],
    )

    assert result.exit_code == 0
    assert (output_directory / "sample.json").is_file()


def test_invalid_environment_setting_maps_to_configuration_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LDC_MAX_FILE_SIZE_MB", "invalid")

    result = CliRunner().invoke(app, ["formats"])

    assert result.exit_code == 2
    assert "Error [config.invalid]" in result.stderr
    assert "settings validation failed" in result.stderr
    assert "LDC_MAX_FILE_SIZE_MB" not in result.stderr


def test_cli_maps_configuration_usage_capability_and_internal_exit_codes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text("max_file_size_mb: invalid\n", encoding="utf-8")
    config_result = CliRunner().invoke(
        app,
        ["formats", "--config", str(invalid_config)],
    )

    monkeypatch.setattr(docling_adapter, "_docling_is_installed", lambda: False)
    unavailable_result = CliRunner().invoke(
        app,
        ["inspect", str(FIXTURES / "sample.pdf")],
    )

    def raise_internal_error(settings: object) -> ConversionService:
        del settings
        raise RuntimeError("sensitive internal details")

    monkeypatch.setattr(cli_module, "_service", raise_internal_error)
    internal_result = CliRunner().invoke(
        app,
        [
            "convert",
            str(FIXTURES / "sample.md"),
            "--to",
            "json",
            "--verbose",
        ],
    )

    assert config_result.exit_code == 2
    assert "Error [config.invalid]" in config_result.stderr
    assert unavailable_result.exit_code == 3
    assert "Error [parser.unavailable]" in unavailable_result.stderr
    assert internal_result.exit_code == 10
    assert "Error [internal.error]" in internal_result.stderr
    assert "RuntimeError" in internal_result.stderr
    assert "sensitive internal details" not in internal_result.stderr


def test_verbose_logging_reports_metadata_and_warning_codes_not_content(
    tmp_path: Path,
) -> None:
    source = tmp_path / "safe-name.md"
    secret = "CUSTOMER_SECRET_DO_NOT_LOG"
    source.write_text(f"> {secret}\n", encoding="utf-8")
    destination = tmp_path / "output.json"

    result = CliRunner().invoke(
        app,
        [
            "convert",
            str(source),
            "--to",
            "json",
            "--output",
            str(destination),
            "--verbose",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == str(destination.resolve())
    assert "source=safe-name.md" in result.stderr
    assert "warnings=markdown.unsupported_syntax" in result.stderr
    assert secret not in result.stderr


def test_verbose_logging_can_hide_source_filename(tmp_path: Path) -> None:
    source = tmp_path / "customer-name.md"
    source.write_text("# Safe content\n", encoding="utf-8")
    destination = tmp_path / "output.json"
    config = tmp_path / "settings.yaml"
    config.write_text(
        "logging:\n  include_source_path: false\n  include_document_content: false\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "convert",
            str(source),
            "--to",
            "json",
            "--output",
            str(destination),
            "--config",
            str(config),
            "--verbose",
        ],
    )

    assert result.exit_code == 0
    assert "customer-name.md" not in result.stderr
    assert "size_bytes=" in result.stderr


def test_inspect_verbose_keeps_json_on_stdout_and_diagnostics_on_stderr() -> None:
    result = CliRunner().invoke(
        app,
        ["inspect", str(FIXTURES / "sample.md"), "--verbose"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["schema_version"] == "1.0"
    assert "parser=markdown" in result.stderr
    assert "size_bytes=" in result.stderr
    assert "elapsed_ms=" in result.stderr


def test_cli_enforces_file_size_and_same_path_safety(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.md"
    oversized.write_bytes(b"x" * (1024 * 1024 + 1))
    config = tmp_path / "limit.yaml"
    config.write_text("max_file_size_mb: 1\n", encoding="utf-8")
    size_result = CliRunner().invoke(
        app,
        [
            "inspect",
            str(oversized),
            "--config",
            str(config),
        ],
    )

    source = tmp_path / "same.md"
    original = "# Preserve me\n"
    source.write_text(original, encoding="utf-8")
    same_path_result = CliRunner().invoke(
        app,
        [
            "convert",
            str(source),
            "--to",
            "markdown",
            "--output",
            str(source),
            "--overwrite",
        ],
    )

    assert size_result.exit_code == 2
    assert "file-size limit" in size_result.stderr
    assert same_path_result.exit_code == 2
    assert "must be different" in same_path_result.stderr
    assert source.read_text(encoding="utf-8") == original


@pytest.mark.parametrize(
    ("exporter", "format_name", "expected_exit"),
    [
        (InterruptingExporter(), "interrupt", 130),
        (FailingExporter(), "failure", 1),
    ],
)
def test_cli_partial_failure_and_ctrl_c_remove_temporary_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    exporter: InterruptingExporter | FailingExporter,
    format_name: str,
    expected_exit: int,
) -> None:
    parsers = ParserRegistry()
    parsers.register(MarkdownParser())
    exporters = ExporterRegistry()
    exporters.register(exporter)
    service = ConversionService(parsers, exporters)
    monkeypatch.setattr(cli_module, "_service", lambda settings: service)
    destination = tmp_path / f"partial.{format_name}"

    result = CliRunner().invoke(
        app,
        [
            "convert",
            str(FIXTURES / "sample.md"),
            "--to",
            format_name,
            "--output",
            str(destination),
        ],
    )

    assert result.exit_code == expected_exit
    assert not destination.exists()
    assert not list(tmp_path.glob(f".{destination.name}.*.tmp"))
    if expected_exit == 130:
        assert "temporary output was removed" in result.stderr
    else:
        assert "intentional partial failure" in result.stderr


def test_formats_verbose_reports_configured_docling_disabled(tmp_path: Path) -> None:
    config = tmp_path / "settings.yaml"
    config.write_text("docling:\n  enabled: false\n", encoding="utf-8")

    formats_result = CliRunner().invoke(
        app,
        ["formats", "--config", str(config), "--verbose"],
    )
    convert_result = CliRunner().invoke(
        app,
        [
            "inspect",
            str(FIXTURES / "sample.pdf"),
            "--config",
            str(config),
        ],
    )

    assert formats_result.exit_code == 0
    assert "Input parser docling: unavailable" in formats_result.stderr
    assert convert_result.exit_code == 3
    assert "disabled by configuration" in convert_result.stderr


def test_service_enforces_page_limit_and_wraps_output_directory_failure(
    tmp_path: Path,
) -> None:
    many_source = tmp_path / "sample.many"
    many_source.write_text("fixture", encoding="utf-8")
    parsers = ParserRegistry()
    parsers.register(TwoPageParser())
    exporters = ExporterRegistry()
    exporters.register(JsonExporter())
    limited_service = ConversionService(parsers, exporters, max_pages=1)

    with pytest.raises(InputValidationError, match="page-count limit"):
        limited_service.inspect(many_source)

    markdown_parsers = ParserRegistry()
    markdown_parsers.register(MarkdownParser())
    occupied_parent = tmp_path / "occupied"
    occupied_parent.write_text("not a directory", encoding="utf-8")
    service = ConversionService(markdown_parsers, exporters)

    with pytest.raises(ExportError, match="could not create output directory"):
        service.convert(
            ConversionRequest(
                source=FIXTURES / "sample.md",
                output_format="json",
                destination=occupied_parent / "output.json",
            )
        )

    replacement_target = tmp_path / "replacement-target.json"
    replacement_target.mkdir()
    with pytest.raises(ExportError, match="could not atomically replace output"):
        service.convert(
            ConversionRequest(
                source=FIXTURES / "sample.md",
                output_format="json",
                destination=replacement_target,
                overwrite=True,
            )
        )
    assert replacement_target.is_dir()
    assert not list(tmp_path.glob(".replacement-target.json.*.tmp"))
