"""Parser selection by normalized file extension."""

from pathlib import Path

from local_document_converter.exceptions import UnsupportedFormatError
from local_document_converter.parsers.base import Parser


class ParserRegistry:
    def __init__(self) -> None:
        self._by_extension: dict[str, Parser] = {}

    def register(self, parser: Parser) -> None:
        for extension in parser.supported_extensions:
            normalized = self._normalize(extension)
            if normalized in self._by_extension:
                owner = self._by_extension[normalized].name
                raise ValueError(f"parser extension {normalized} is already registered by {owner}")
            self._by_extension[normalized] = parser

    def for_path(self, source: Path) -> Parser:
        extension = self._normalize(source.suffix)
        try:
            return self._by_extension[extension]
        except KeyError as exc:
            supported = ", ".join(self.supported_extensions())
            raise UnsupportedFormatError(
                f"unsupported input extension '{extension or '<none>'}'; supported: {supported}"
            ) from exc

    def supported_extensions(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_extension))

    @staticmethod
    def _normalize(extension: str) -> str:
        cleaned = extension.strip().lower()
        if not cleaned:
            return ""
        return cleaned if cleaned.startswith(".") else f".{cleaned}"
