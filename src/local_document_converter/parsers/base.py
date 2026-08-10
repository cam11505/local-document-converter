"""Parser contract."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from pydantic import JsonValue

from local_document_converter.domain.models import DocumentIR


@dataclass(frozen=True, slots=True)
class ParseContext:
    options: dict[str, JsonValue] = field(default_factory=dict)


class Parser(Protocol):
    name: str
    supported_extensions: frozenset[str]

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        """Parse one local file into the stable project IR."""
        ...
