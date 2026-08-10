"""Exporter selection by normalized format name."""

from local_document_converter.exceptions import (
    DuplicateRegistrationError,
    ExporterUnavailableError,
    InvalidAdapterError,
    UnsupportedFormatError,
)
from local_document_converter.exporters.base import (
    Exporter,
    ExporterCapability,
    normalize_format_name,
)


class ExporterRegistry:
    def __init__(self) -> None:
        self._by_format: dict[str, Exporter] = {}

    def register(self, exporter: Exporter) -> None:
        if not isinstance(exporter, Exporter) or not isinstance(
            exporter.capability, ExporterCapability
        ):
            raise InvalidAdapterError("exporter does not satisfy the Exporter protocol")
        format_name = exporter.capability.format_name
        if format_name in self._by_format:
            raise DuplicateRegistrationError(f"export format '{format_name}' is already registered")
        self._by_format[format_name] = exporter

    def for_format(self, format_name: str) -> Exporter:
        try:
            normalized = normalize_format_name(format_name)
        except ValueError:
            normalized = ""
        try:
            exporter = self._by_format[normalized]
        except KeyError as exc:
            supported = ", ".join(self.supported_formats()) or "<none>"
            raise UnsupportedFormatError(
                f"unsupported output format '{normalized or '<none>'}'; supported: {supported}"
            ) from exc

        availability = exporter.capability.availability
        if not availability.available:
            message = (
                f"exporter '{exporter.capability.format_name}' is unavailable: "
                f"{availability.reason}"
            )
            if availability.install_hint:
                message += f"; {availability.install_hint}"
            raise ExporterUnavailableError(message)
        return exporter

    def supported_formats(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_format))

    def capabilities(self) -> tuple[ExporterCapability, ...]:
        return tuple(self._by_format[name].capability for name in sorted(self._by_format))
