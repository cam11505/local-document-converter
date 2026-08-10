"""Project-specific exceptions exposed across adapters and services."""

from typing import ClassVar


class LocalDocumentConverterError(Exception):
    """Base class for expected application failures."""

    error_code: ClassVar[str] = "ldc.error"


class InputValidationError(LocalDocumentConverterError):
    """The input cannot safely be processed."""

    error_code = "input.invalid"


class UnsupportedFormatError(LocalDocumentConverterError):
    """No registered adapter supports the requested format."""

    error_code = "format.unsupported"


class DuplicateRegistrationError(LocalDocumentConverterError):
    """A registry key or adapter name is already owned."""

    error_code = "registry.duplicate"


class InvalidAdapterError(LocalDocumentConverterError):
    """An adapter does not satisfy the registry metadata contract."""

    error_code = "adapter.invalid"


class ParserUnavailableError(LocalDocumentConverterError):
    """A parser or its optional runtime is not available."""

    error_code = "parser.unavailable"


class ExporterUnavailableError(LocalDocumentConverterError):
    """An exporter or its optional runtime is not available."""

    error_code = "exporter.unavailable"


class ParseError(LocalDocumentConverterError):
    """A supported input could not be parsed."""

    error_code = "parse.failed"


class ExportError(LocalDocumentConverterError):
    """A DocumentIR could not be exported."""

    error_code = "export.failed"


class OutputExistsError(LocalDocumentConverterError):
    """The destination exists and overwrite was not enabled."""

    error_code = "output.exists"
