"""Exporter contract."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import JsonValue

from local_document_converter.capabilities import Availability, normalize_extension
from local_document_converter.domain.models import DocumentIR


def normalize_format_name(format_name: str) -> str:
    """Return a lowercase output format without a leading dot."""
    cleaned = format_name.strip().lower().lstrip(".")
    if not cleaned:
        raise ValueError("output format name cannot be empty")
    return cleaned


@dataclass(frozen=True, slots=True)
class ExporterCapability:
    format_name: str
    output_extension: str
    availability: Availability = field(default_factory=Availability)

    def __post_init__(self) -> None:
        object.__setattr__(self, "format_name", normalize_format_name(self.format_name))
        object.__setattr__(self, "output_extension", normalize_extension(self.output_extension))


@dataclass(frozen=True, slots=True)
class ExportContext:
    options: dict[str, JsonValue] = field(default_factory=dict)


@runtime_checkable
class Exporter(Protocol):
    capability: ExporterCapability

    def export(self, document: DocumentIR, destination: Path, context: ExportContext) -> None:
        """Write one DocumentIR to a temporary destination."""
        ...
