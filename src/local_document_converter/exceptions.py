"""Project-specific exceptions exposed across adapters and services."""


class LocalDocumentConverterError(Exception):
    """Base class for expected application failures."""


class InputValidationError(LocalDocumentConverterError):
    """The input cannot safely be processed."""


class UnsupportedFormatError(LocalDocumentConverterError):
    """No registered adapter supports the requested format."""


class ParserUnavailableError(LocalDocumentConverterError):
    """A parser or its optional runtime is not available."""


class ParseError(LocalDocumentConverterError):
    """A supported input could not be parsed."""


class ExportError(LocalDocumentConverterError):
    """A DocumentIR could not be exported."""


class OutputExistsError(LocalDocumentConverterError):
    """The destination exists and overwrite was not enabled."""
