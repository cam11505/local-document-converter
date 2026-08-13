"""Safe orchestration from one local input file to one output file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from local_document_converter.domain.models import DocumentIR, DocumentWarning
from local_document_converter.exceptions import (
    ExportError,
    InputValidationError,
    OutputExistsError,
    ParseError,
    ParserUnavailableError,
)
from local_document_converter.exporters.base import ExportContext
from local_document_converter.exporters.registry import ExporterRegistry
from local_document_converter.parsers.base import ParseContext, ParserFallback
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
    warnings: tuple[DocumentWarning, ...]


class ConversionService:
    def __init__(
        self,
        parsers: ParserRegistry,
        exporters: ExporterRegistry,
        *,
        output_directory: Path = Path("output"),
        max_file_size_mb: int = 100,
        max_pages: int = 500,
        parser_fallback: ParserFallback | None = None,
    ) -> None:
        self._parsers = parsers
        self._exporters = exporters
        self._output_directory = output_directory
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self._max_pages = max_pages
        self._parser_fallback = parser_fallback

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

        document = parser.parse(source, ParseContext())
        document = self._apply_parser_fallback(source, document)
        self._validate_document(document)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ExportError(f"could not create output directory: {destination.parent}") from exc
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        export_context = ExportContext()
        try:
            exporter.export(document, temporary, export_context)
            try:
                temporary.replace(destination)
            except OSError as exc:
                raise ExportError(f"could not atomically replace output: {destination}") from exc
        finally:
            temporary.unlink(missing_ok=True)

        warnings = tuple(document.warnings) + tuple(export_context.warnings)

        return ConversionResult(
            source=source,
            destination=destination,
            parser_name=parser.capability.name,
            exporter_name=exporter.capability.format_name,
            warning_count=len(warnings),
            warnings=warnings,
        )

    def inspect(self, source: Path) -> DocumentIR:
        """Parse one input through the same validation limits without writing output."""
        resolved_source = source.expanduser().resolve()
        self._validate_source(resolved_source)
        document = self._parsers.for_path(resolved_source).parse(resolved_source, ParseContext())
        document = self._apply_parser_fallback(resolved_source, document)
        self._validate_document(document)
        return document

    def _validate_source(self, source: Path) -> None:
        try:
            exists = source.exists()
            is_file = source.is_file()
            size = source.stat().st_size if exists and is_file else 0
        except OSError as exc:
            raise InputValidationError(f"input metadata could not be read: {source}") from exc
        if not exists:
            raise InputValidationError(f"input does not exist: {source}")
        if not is_file:
            raise InputValidationError(f"input is not a file: {source}")
        if size > self._max_file_size_bytes:
            raise InputValidationError("input exceeds the configured file-size limit")

    def _validate_document(self, document: DocumentIR) -> None:
        page_count = document.metadata.page_count
        if page_count is not None and page_count > self._max_pages:
            raise InputValidationError("input exceeds the configured page-count limit")

    def _apply_parser_fallback(self, source: Path, primary: DocumentIR) -> DocumentIR:
        fallback = self._parser_fallback
        if fallback is None or not fallback.should_run(source, primary):
            return primary

        availability = fallback.capability.availability
        if not availability.available:
            message = f"{fallback.capability.name} is unavailable: {availability.reason}"
            if availability.install_hint:
                message += f"; {availability.install_hint}"
            warning = DocumentWarning(
                code="ocr.fallback_unavailable",
                message=message,
                details={"fallback": fallback.capability.name},
            )
            return primary.model_copy(update={"warnings": [*primary.warnings, warning]})

        try:
            replacement = fallback.parse(source, ParseContext())
        except ParserUnavailableError as exc:
            warning = DocumentWarning(
                code="ocr.fallback_unavailable",
                message=str(exc),
                details={"fallback": fallback.capability.name},
            )
            return primary.model_copy(update={"warnings": [*primary.warnings, warning]})
        except ParseError:
            warning = DocumentWarning(
                code="ocr.fallback_failed",
                message="OCR fallback failed; the primary parser result was preserved",
                details={"fallback": fallback.capability.name},
            )
            return primary.model_copy(update={"warnings": [*primary.warnings, warning]})

        used_warning = DocumentWarning(
            code="ocr.fallback_used",
            message="OCR replaced an insufficient or low-confidence primary parse",
            details={"fallback": fallback.capability.name},
        )
        return replacement.model_copy(
            update={
                "warnings": [
                    *primary.warnings,
                    *replacement.warnings,
                    used_warning,
                ]
            }
        )

    def _destination(self, request: ConversionRequest, source: Path, output_extension: str) -> Path:
        if request.destination is not None:
            return request.destination.expanduser().resolve()
        return (self._output_directory / f"{source.stem}{output_extension}").resolve()
