"""Command-line boundary for Local Document Converter."""

from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from time import perf_counter
from typing import Annotated, NoReturn

import typer

from local_document_converter.config import Settings
from local_document_converter.exceptions import (
    ConfigurationError,
    ExporterUnavailableError,
    InputValidationError,
    LocalDocumentConverterError,
    ParserUnavailableError,
    UnsupportedFormatError,
)
from local_document_converter.exporters.docx_exporter import DocxExporter
from local_document_converter.exporters.json_exporter import JsonExporter
from local_document_converter.exporters.markdown import MarkdownExporter
from local_document_converter.exporters.registry import ExporterRegistry
from local_document_converter.parsers.docling_parser import DoclingParser
from local_document_converter.parsers.excel_parser import ExcelParser
from local_document_converter.parsers.markdown import MarkdownParser
from local_document_converter.parsers.registry import ParserRegistry
from local_document_converter.services.conversion_service import (
    ConversionRequest,
    ConversionResult,
    ConversionService,
)

app = typer.Typer(no_args_is_help=True, help="Convert local documents through DocumentIR.")


class ExitCode(IntEnum):
    """Stable process exit codes documented by the CLI contract."""

    ERROR = 1
    USAGE = 2
    CAPABILITY_UNAVAILABLE = 3
    INTERNAL = 10
    INTERRUPTED = 130


def build_registries(settings: Settings | None = None) -> tuple[ParserRegistry, ExporterRegistry]:
    parsers = ParserRegistry()
    parsers.register(MarkdownParser())
    parsers.register(ExcelParser(settings.excel if settings is not None else None))
    parsers.register(
        DoclingParser(enabled=settings.docling.enabled if settings is not None else True)
    )

    exporters = ExporterRegistry()
    exporters.register(MarkdownExporter())
    exporters.register(JsonExporter())
    exporters.register(DocxExporter())
    return parsers, exporters


def _load_settings(
    config: Path | None,
    *,
    overwrite: bool = False,
    verbose: bool = False,
) -> Settings:
    overrides: dict[str, bool] = {}
    if overwrite:
        overrides["overwrite"] = True
    if verbose:
        overrides["verbose"] = True
    return Settings.load(config, cli_overrides=overrides or None)


def _service(settings: Settings) -> ConversionService:
    parsers, exporters = build_registries(settings)
    return ConversionService(
        parsers,
        exporters,
        output_directory=settings.output_directory,
        max_file_size_mb=settings.max_file_size_mb,
        max_pages=settings.max_pages,
    )


def _exit_code(exc: LocalDocumentConverterError) -> ExitCode:
    if isinstance(exc, (ConfigurationError, InputValidationError, UnsupportedFormatError)):
        return ExitCode.USAGE
    if isinstance(exc, (ParserUnavailableError, ExporterUnavailableError)):
        return ExitCode.CAPABILITY_UNAVAILABLE
    return ExitCode.ERROR


def _fail(exc: LocalDocumentConverterError) -> NoReturn:
    typer.echo(f"Error [{exc.error_code}]: {exc}", err=True)
    raise typer.Exit(code=int(_exit_code(exc))) from exc


def _interrupted() -> NoReturn:
    typer.echo("Cancelled: conversion interrupted; temporary output was removed.", err=True)
    raise typer.Exit(code=int(ExitCode.INTERRUPTED))


def _internal_error(exc: Exception, *, verbose: bool) -> NoReturn:
    message = "unexpected internal error"
    if verbose:
        message += f" ({type(exc).__name__})"
    typer.echo(f"Error [internal.error]: {message}", err=True)
    raise typer.Exit(code=int(ExitCode.INTERNAL)) from exc


def _emit_verbose_result(
    result: ConversionResult,
    elapsed_seconds: float,
    *,
    include_source_path: bool,
) -> None:
    warning_codes = ", ".join(warning.code for warning in result.warnings) or "none"
    fields = []
    if include_source_path:
        fields.append(f"source={result.source.name}")
    fields.extend(
        (
            f"size_bytes={result.source.stat().st_size}",
            f"parser={result.parser_name}",
            f"exporter={result.exporter_name}",
            f"elapsed_ms={elapsed_seconds * 1000:.1f}",
            f"warnings={warning_codes}",
        )
    )
    typer.echo(
        " | ".join(fields),
        err=True,
    )


def _emit_verbose_inspection(
    source: Path,
    *,
    parser_name: str,
    elapsed_seconds: float,
    warning_codes: list[str],
    include_source_path: bool,
) -> None:
    fields = []
    if include_source_path:
        fields.append(f"source={source.name}")
    fields.extend(
        (
            f"size_bytes={source.stat().st_size}",
            f"parser={parser_name}",
            f"elapsed_ms={elapsed_seconds * 1000:.1f}",
            f"warnings={', '.join(warning_codes) or 'none'}",
        )
    )
    typer.echo(
        " | ".join(fields),
        err=True,
    )


@app.command("formats")
def formats_command(
    config: Annotated[Path | None, typer.Option("--config", help="Settings YAML path.")] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Show adapter availability details.")
    ] = False,
) -> None:
    """List registered input extensions and output formats."""
    effective_verbose = verbose
    try:
        settings = _load_settings(config, verbose=verbose)
        effective_verbose = settings.verbose
        parsers, exporters = build_registries(settings)
        typer.echo("Inputs: " + ", ".join(parsers.supported_extensions()))
        typer.echo("Outputs: " + ", ".join(exporters.supported_formats()))
        if effective_verbose:
            for parser_capability in parsers.capabilities():
                status = "available" if parser_capability.availability.available else "unavailable"
                typer.echo(
                    f"Input parser {parser_capability.name}: {status} "
                    f"({', '.join(sorted(parser_capability.supported_extensions))})",
                    err=True,
                )
            for exporter_capability in exporters.capabilities():
                status = (
                    "available" if exporter_capability.availability.available else "unavailable"
                )
                typer.echo(
                    f"Output exporter {exporter_capability.format_name}: {status}",
                    err=True,
                )
    except KeyboardInterrupt:
        _interrupted()
    except LocalDocumentConverterError as exc:
        _fail(exc)
    except Exception as exc:
        _internal_error(exc, verbose=effective_verbose)


@app.command("convert")
def convert_command(
    source: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    output_format: Annotated[str, typer.Option("--to", help="markdown, json, or docx")],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
    config: Annotated[Path | None, typer.Option("--config", help="Settings YAML path.")] = None,
) -> None:
    """Convert one local document."""
    effective_verbose = verbose
    started = perf_counter()
    try:
        settings = _load_settings(config, overwrite=overwrite, verbose=verbose)
        effective_verbose = settings.verbose
        result = _service(settings).convert(
            ConversionRequest(
                source=source,
                output_format=output_format,
                destination=output,
                overwrite=settings.overwrite,
            )
        )
    except KeyboardInterrupt:
        _interrupted()
    except LocalDocumentConverterError as exc:
        _fail(exc)
    except Exception as exc:
        _internal_error(exc, verbose=effective_verbose)
    if effective_verbose:
        _emit_verbose_result(
            result,
            perf_counter() - started,
            include_source_path=settings.logging.include_source_path,
        )
    typer.echo(str(result.destination))


@app.command("inspect")
def inspect_command(
    source: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
    config: Annotated[Path | None, typer.Option("--config", help="Settings YAML path.")] = None,
) -> None:
    """Parse a document and print its IR JSON without writing an output file."""
    effective_verbose = verbose
    started = perf_counter()
    try:
        settings = _load_settings(config, verbose=verbose)
        effective_verbose = settings.verbose
        service = _service(settings)
        resolved_source = source.resolve()
        document = service.inspect(resolved_source)
        parser_name = build_registries(settings)[0].for_path(resolved_source).capability.name
    except KeyboardInterrupt:
        _interrupted()
    except LocalDocumentConverterError as exc:
        _fail(exc)
    except Exception as exc:
        _internal_error(exc, verbose=effective_verbose)
    if effective_verbose:
        _emit_verbose_inspection(
            resolved_source,
            parser_name=parser_name,
            elapsed_seconds=perf_counter() - started,
            warning_codes=[warning.code for warning in document.warnings],
            include_source_path=settings.logging.include_source_path,
        )
    typer.echo(document.to_json(indent=2))


if __name__ == "__main__":
    app()
