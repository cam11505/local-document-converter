"""Parser contract."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import JsonValue

from local_document_converter.capabilities import Availability, normalize_extension
from local_document_converter.domain.models import DocumentIR


@dataclass(frozen=True, slots=True)
class ParserCapability:
    name: str
    supported_extensions: frozenset[str]
    availability: Availability = field(default_factory=Availability)

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("parser name cannot be empty")
        if not self.supported_extensions:
            raise ValueError("parser must support at least one file extension")
        extensions = frozenset(normalize_extension(item) for item in self.supported_extensions)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "supported_extensions", extensions)


@dataclass(frozen=True, slots=True)
class ParseContext:
    options: dict[str, JsonValue] = field(default_factory=dict)


@runtime_checkable
class Parser(Protocol):
    capability: ParserCapability

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        """Parse one local file into the stable project IR."""
        ...
