"""Parser selection by normalized file extension."""

from pathlib import Path

from local_document_converter.capabilities import normalize_extension
from local_document_converter.exceptions import (
    DuplicateRegistrationError,
    InvalidAdapterError,
    ParserUnavailableError,
    UnsupportedFormatError,
)
from local_document_converter.parsers.base import Parser, ParserCapability


class ParserRegistry:
    def __init__(self) -> None:
        self._by_extension: dict[str, Parser] = {}
        self._by_name: dict[str, Parser] = {}

    def register(self, parser: Parser) -> None:
        if not isinstance(parser, Parser) or not isinstance(
            parser.capability, ParserCapability
        ):
            raise InvalidAdapterError("parser does not satisfy the Parser protocol")
        capability = parser.capability
        if capability.name in self._by_name:
            raise DuplicateRegistrationError(
                f"parser name '{capability.name}' is already registered"
            )

        conflicts = {
            extension: self._by_extension[extension].capability.name
            for extension in capability.supported_extensions
            if extension in self._by_extension
        }
        if conflicts:
            details = ", ".join(
                f"{extension} by {owner}" for extension, owner in sorted(conflicts.items())
            )
            raise DuplicateRegistrationError(f"parser extension already registered: {details}")

        self._by_name[capability.name] = parser
        for extension in capability.supported_extensions:
            self._by_extension[extension] = parser

    def for_path(self, source: Path) -> Parser:
        try:
            extension = normalize_extension(source.suffix)
        except ValueError:
            extension = ""
        try:
            parser = self._by_extension[extension]
        except KeyError as exc:
            supported = ", ".join(self.supported_extensions()) or "<none>"
            raise UnsupportedFormatError(
                f"unsupported input extension '{extension or '<none>'}'; supported: {supported}"
            ) from exc

        availability = parser.capability.availability
        if not availability.available:
            message = f"parser '{parser.capability.name}' is unavailable: {availability.reason}"
            if availability.install_hint:
                message += f"; {availability.install_hint}"
            raise ParserUnavailableError(message)
        return parser

    def supported_extensions(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_extension))

    def capabilities(self) -> tuple[ParserCapability, ...]:
        return tuple(self._by_name[name].capability for name in sorted(self._by_name))
