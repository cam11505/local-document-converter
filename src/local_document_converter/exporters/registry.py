"""Exporter selection by normalized format name."""

from local_document_converter.exceptions import UnsupportedFormatError
from local_document_converter.exporters.base import Exporter


class ExporterRegistry:
    def __init__(self) -> None:
        self._by_format: dict[str, Exporter] = {}

    def register(self, exporter: Exporter) -> None:
        normalized = self._normalize(exporter.format_name)
        if normalized in self._by_format:
            raise ValueError(f"export format '{normalized}' is already registered")
        self._by_format[normalized] = exporter

    def for_format(self, format_name: str) -> Exporter:
        normalized = self._normalize(format_name)
        try:
            return self._by_format[normalized]
        except KeyError as exc:
            supported = ", ".join(self.supported_formats())
            raise UnsupportedFormatError(
                f"unsupported output format '{normalized}'; supported: {supported}"
            ) from exc

    def supported_formats(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_format))

    @staticmethod
    def _normalize(format_name: str) -> str:
        return format_name.strip().lower().lstrip(".")
