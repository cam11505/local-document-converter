"""openpyxl adapter boundary. Complete in Stage 5."""

from pathlib import Path

from local_document_converter.capabilities import Availability
from local_document_converter.domain.models import DocumentIR
from local_document_converter.parsers.base import ParseContext, ParserCapability


class ExcelParser:
    capability = ParserCapability(
        name="openpyxl",
        supported_extensions=frozenset({".xlsx"}),
        availability=Availability.unavailable(
            "Excel adapter is a Stage 5 placeholder",
            install_hint="complete Stage 5 before selecting this parser",
        ),
    )

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del source, context
        raise NotImplementedError(
            "Excel adapter is a Stage 5 placeholder; follow CODEX_STAGE_PROMPTS.md"
        )
