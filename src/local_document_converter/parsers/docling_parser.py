"""Docling adapter boundary. Complete in Stage 6 after checking the installed API."""

from pathlib import Path

from local_document_converter.domain.models import DocumentIR
from local_document_converter.parsers.base import ParseContext


class DoclingParser:
    name = "docling"
    supported_extensions = frozenset({".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tif", ".tiff"})

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del source, context
        raise NotImplementedError(
            "Docling adapter is a Stage 6 placeholder; follow CODEX_STAGE_PROMPTS.md"
        )
