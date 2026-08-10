"""Safe orchestration from one local input file to one output file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from local_document_converter.exceptions import InputValidationError, OutputExistsError
from local_document_converter.exporters.base import ExportContext
from local_document_converter.exporters.registry import ExporterRegistry
from local_document_converter.parsers.base import ParseContext
from local_document_converter.parsers.registry import ParserRegistry


@dataclass(frozen=True, slots=True)
class ConversionRequest:
    source: Path
    output_format: str
    destination: Path | None = None
    overwrite: bool = False


@dataclass(frozen=True, slots=True)
class ConversionResult:
    source: Path
    destination: Path
    parser_name: str
    exporter_name: str
    warning_count: int


class ConversionService:
    def __init__(
        self,
        parsers: ParserRegistry,
        exporters: ExporterRegistry,
        *,
        output_directory: Path = Path("output"),
        max_file_size_mb: int = 100,
    ) -> None:
        self._parsers = parsers
        self._exporters = exporters
        self._output_directory = output_directory
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def convert(self, request: ConversionRequest) -> ConversionResult:
        source = request.source.expanduser().resolve()
        self._validate_source(source)
        parser = self._parsers.for_path(source)
        exporter = self._exporters.for_format(request.output_format)
        destination = self._destination(request, source, exporter.capability.output_extension)

        if source == destination:
            raise InputValidationError("input and output paths must be different")
        if destination.exists() and not request.overwrite:
            raise OutputExistsError(f"output already exists: {destination}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        document = parser.parse(source, ParseContext())
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            exporter.export(document, temporary, ExportContext())
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)

        return ConversionResult(
            source=source,
            destination=destination,
            parser_name=parser.capability.name,
            exporter_name=exporter.capability.format_name,
            warning_count=len(document.warnings),
        )

    def _validate_source(self, source: Path) -> None:
        if not source.exists():
            raise InputValidationError(f"input does not exist: {source}")
        if not source.is_file():
            raise InputValidationError(f"input is not a file: {source}")
        if source.stat().st_size > self._max_file_size_bytes:
            raise InputValidationError("input exceeds the configured file-size limit")

    def _destination(
        self, request: ConversionRequest, source: Path, output_extension: str
    ) -> Path:
        if request.destination is not None:
            return request.destination.expanduser().resolve()
        return (self._output_directory / f"{source.stem}{output_extension}").resolve()
