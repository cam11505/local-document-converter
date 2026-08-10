"""openpyxl adapter boundary. Complete in Stage 5."""

from pathlib import Path

from local_document_converter.domain.models import DocumentIR
from local_document_converter.parsers.base import ParseContext


class ExcelParser:
    name = "openpyxl"
    supported_extensions = frozenset({".xlsx"})

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del source, context
        raise NotImplementedError(
            "Excel adapter is a Stage 5 placeholder; follow CODEX_STAGE_PROMPTS.md"
        )
