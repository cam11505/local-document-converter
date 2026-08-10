"""Docling adapter boundary. Complete in Stage 6 after checking the installed API."""

from pathlib import Path

from local_document_converter.capabilities import Availability
from local_document_converter.domain.models import DocumentIR
from local_document_converter.parsers.base import ParseContext, ParserCapability


class DoclingParser:
    capability = ParserCapability(
        name="docling",
        supported_extensions=frozenset(
            {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
        ),
        availability=Availability.unavailable(
            "Docling adapter is a Stage 6 placeholder",
            install_hint="complete Stage 6 before selecting this parser",
        ),
    )

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del source, context
        raise NotImplementedError(
            "Docling adapter is a Stage 6 placeholder; follow CODEX_STAGE_PROMPTS.md"
        )
