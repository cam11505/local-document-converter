"""Exporter contract."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from pydantic import JsonValue

from local_document_converter.domain.models import DocumentIR


@dataclass(frozen=True, slots=True)
class ExportContext:
    options: dict[str, JsonValue] = field(default_factory=dict)


class Exporter(Protocol):
    format_name: str
    output_extension: str

    def export(self, document: DocumentIR, destination: Path, context: ExportContext) -> None:
        """Write one DocumentIR to a temporary destination."""
        ...
