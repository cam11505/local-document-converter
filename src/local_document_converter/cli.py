"""Command-line boundary for Local Document Converter."""

from pathlib import Path
from typing import Annotated

import typer

from local_document_converter.config import Settings
from local_document_converter.exceptions import LocalDocumentConverterError
from local_document_converter.exporters.docx_exporter import DocxExporter
from local_document_converter.exporters.json_exporter import JsonExporter
from local_document_converter.exporters.markdown import MarkdownExporter
from local_document_converter.exporters.registry import ExporterRegistry
from local_document_converter.parsers.base import ParseContext
from local_document_converter.parsers.docling_parser import DoclingParser
from local_document_converter.parsers.excel_parser import ExcelParser
from local_document_converter.parsers.markdown import MarkdownParser
from local_document_converter.parsers.registry import ParserRegistry
from local_document_converter.services.conversion_service import (
    ConversionRequest,
    ConversionService,
)

app = typer.Typer(no_args_is_help=True, help="Convert local documents through DocumentIR.")


def build_registries() -> tuple[ParserRegistry, ExporterRegistry]:
    parsers = ParserRegistry()
    parsers.register(MarkdownParser())
    parsers.register(ExcelParser())
    parsers.register(DoclingParser())

    exporters = ExporterRegistry()
    exporters.register(MarkdownExporter())
    exporters.register(JsonExporter())
    exporters.register(DocxExporter())
    return parsers, exporters


@app.command("formats")
def formats_command() -> None:
    """List registered input extensions and output formats."""
    parsers, exporters = build_registries()
    typer.echo("Inputs: " + ", ".join(parsers.supported_extensions()))
    typer.echo("Outputs: " + ", ".join(exporters.supported_formats()))


@app.command("convert")
def convert_command(
    source: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    output_format: Annotated[str, typer.Option("--to", help="markdown, json, or docx")],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Convert one local document."""
    parsers, exporters = build_registries()
    cli_overrides = {"overwrite": True} if overwrite else None
    settings = Settings.load(cli_overrides=cli_overrides)
    service = ConversionService(
        parsers,
        exporters,
        output_directory=settings.output_directory,
        max_file_size_mb=settings.max_file_size_mb,
    )
    try:
        result = service.convert(
            ConversionRequest(
                source=source,
                output_format=output_format,
                destination=output,
                overwrite=settings.overwrite,
            )
        )
    except (LocalDocumentConverterError, NotImplementedError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(str(result.destination))


@app.command("inspect")
def inspect_command(
    source: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
) -> None:
    """Parse a document and print its IR JSON without writing an output file."""
    parsers, _ = build_registries()
    try:
        document = parsers.for_path(source).parse(source.resolve(), ParseContext())
    except (LocalDocumentConverterError, NotImplementedError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(document.to_json(indent=2))


if __name__ == "__main__":
    app()
