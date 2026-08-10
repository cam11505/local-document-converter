from pathlib import Path

import pytest

from local_document_converter.capabilities import Availability
from local_document_converter.domain import DocumentIR, SourceInfo
from local_document_converter.exceptions import (
    DuplicateRegistrationError,
    ExporterUnavailableError,
    InvalidAdapterError,
    ParserUnavailableError,
    UnsupportedFormatError,
)
from local_document_converter.exporters import (
    ExportContext,
    Exporter,
    ExporterCapability,
    ExporterRegistry,
)
from local_document_converter.parsers import (
    ParseContext,
    Parser,
    ParserCapability,
    ParserRegistry,
)


class FakeParser:
    def __init__(self, capability: ParserCapability) -> None:
        self.capability = capability

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del context
        return DocumentIR(source=SourceInfo(path=str(source)))


class FakeExporter:
    def __init__(self, capability: ExporterCapability) -> None:
        self.capability = capability

    def export(
        self, document: DocumentIR, destination: Path, context: ExportContext
    ) -> None:
        del document, context
        destination.write_text("fake output\n", encoding="utf-8")


def test_capability_metadata_is_normalized_and_satisfies_protocols() -> None:
    parser = FakeParser(
        ParserCapability(
            name=" fake-parser ", supported_extensions=frozenset({"PDF", " .Md "})
        )
    )
    exporter = FakeExporter(
        ExporterCapability(format_name=" .JSON ", output_extension="JSON")
    )

    assert isinstance(parser, Parser)
    assert isinstance(exporter, Exporter)
    assert parser.capability.name == "fake-parser"
    assert parser.capability.supported_extensions == frozenset({".pdf", ".md"})
    assert exporter.capability.format_name == "json"
    assert exporter.capability.output_extension == ".json"


def test_parser_registry_selects_case_insensitively_and_lists_capabilities() -> None:
    parser = FakeParser(
        ParserCapability(name="fake", supported_extensions=frozenset({"PDF", ".md"}))
    )
    registry = ParserRegistry()
    registry.register(parser)

    assert registry.for_path(Path("REPORT.PDF")) is parser
    assert registry.supported_extensions() == (".md", ".pdf")
    assert registry.capabilities() == (parser.capability,)


def test_parser_registration_is_atomic_when_an_extension_conflicts() -> None:
    registry = ParserRegistry()
    registry.register(
        FakeParser(ParserCapability(name="pdf", supported_extensions=frozenset({".pdf"})))
    )
    conflicting = FakeParser(
        ParserCapability(name="mixed", supported_extensions=frozenset({".pdf", ".docx"}))
    )

    with pytest.raises(DuplicateRegistrationError, match=r"\.pdf by pdf"):
        registry.register(conflicting)

    assert registry.supported_extensions() == (".pdf",)
    with pytest.raises(UnsupportedFormatError):
        registry.for_path(Path("not-partially-registered.docx"))


def test_parser_name_cannot_be_registered_twice() -> None:
    registry = ParserRegistry()
    registry.register(
        FakeParser(ParserCapability(name="same", supported_extensions=frozenset({".one"})))
    )

    with pytest.raises(DuplicateRegistrationError, match="parser name 'same'"):
        registry.register(
            FakeParser(ParserCapability(name="same", supported_extensions=frozenset({".two"})))
        )


def test_unknown_input_lists_supported_extensions() -> None:
    registry = ParserRegistry()
    registry.register(
        FakeParser(ParserCapability(name="markdown", supported_extensions=frozenset({".md"})))
    )

    with pytest.raises(UnsupportedFormatError) as exc_info:
        registry.for_path(Path("sample.unknown"))

    assert exc_info.value.error_code == "format.unsupported"
    assert ".md" in str(exc_info.value)

    with pytest.raises(UnsupportedFormatError, match="supported: <none>"):
        ParserRegistry().for_path(Path("no-extension"))


def test_unavailable_parser_returns_stable_capability_error() -> None:
    parser = FakeParser(
        ParserCapability(
            name="optional",
            supported_extensions=frozenset({".optional"}),
            availability=Availability.unavailable(
                "dependency is not installed", install_hint="install the optional extra"
            ),
        )
    )
    registry = ParserRegistry()
    registry.register(parser)

    with pytest.raises(ParserUnavailableError) as exc_info:
        registry.for_path(Path("sample.optional"))

    assert exc_info.value.error_code == "parser.unavailable"
    assert "dependency is not installed" in str(exc_info.value)
    assert "install the optional extra" in str(exc_info.value)


def test_exporter_registry_normalizes_rejects_duplicates_and_lists_formats() -> None:
    exporter = FakeExporter(
        ExporterCapability(format_name=".JSON", output_extension="JSON")
    )
    registry = ExporterRegistry()
    registry.register(exporter)

    assert registry.for_format(" .Json ") is exporter
    assert registry.supported_formats() == ("json",)
    assert registry.capabilities() == (exporter.capability,)

    with pytest.raises(DuplicateRegistrationError, match="export format 'json'"):
        registry.register(
            FakeExporter(ExporterCapability(format_name="json", output_extension=".json"))
        )


def test_unknown_and_unavailable_exporters_use_project_errors() -> None:
    registry = ExporterRegistry()
    unavailable = FakeExporter(
        ExporterCapability(
            format_name="optional",
            output_extension=".optional",
            availability=Availability.unavailable(
                "dependency is not installed", install_hint="install exporter extra"
            ),
        )
    )
    registry.register(unavailable)

    with pytest.raises(ExporterUnavailableError) as exc_info:
        registry.for_format("optional")

    assert exc_info.value.error_code == "exporter.unavailable"
    assert "install exporter extra" in str(exc_info.value)

    with pytest.raises(UnsupportedFormatError, match="supported: optional"):
        registry.for_format("unknown")


def test_context_defaults_are_isolated() -> None:
    first_parse = ParseContext()
    second_parse = ParseContext()
    first_export = ExportContext()
    second_export = ExportContext()

    first_parse.options["mode"] = "first"
    first_export.options["mode"] = "first"

    assert second_parse.options == {}
    assert second_export.options == {}


def test_invalid_capability_metadata_is_rejected() -> None:
    with pytest.raises(ValueError, match="parser name cannot be empty"):
        ParserCapability(name=" ", supported_extensions=frozenset({".md"}))

    with pytest.raises(ValueError, match="at least one"):
        ParserCapability(name="empty", supported_extensions=frozenset())

    with pytest.raises(ValueError, match="output format name cannot be empty"):
        ExporterCapability(format_name=".", output_extension=".out")

    with pytest.raises(ValueError, match="unavailable capability must include a reason"):
        Availability(available=False)

    with pytest.raises(ValueError, match="available capability cannot include"):
        Availability(available=True, reason="contradiction")


def test_objects_that_do_not_satisfy_adapter_protocols_are_rejected() -> None:
    with pytest.raises(InvalidAdapterError) as parser_error:
        ParserRegistry().register(object())  # type: ignore[arg-type]

    with pytest.raises(InvalidAdapterError) as exporter_error:
        ExporterRegistry().register(object())  # type: ignore[arg-type]

    assert parser_error.value.error_code == "adapter.invalid"
    assert exporter_error.value.error_code == "adapter.invalid"
