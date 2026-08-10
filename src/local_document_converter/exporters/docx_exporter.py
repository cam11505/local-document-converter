"""python-docx adapter boundary. Complete in Stage 7."""

from pathlib import Path

from local_document_converter.domain.models import DocumentIR
from local_document_converter.exporters.base import ExportContext


class DocxExporter:
    format_name = "docx"
    output_extension = ".docx"

    def export(self, document: DocumentIR, destination: Path, context: ExportContext) -> None:
        del document, destination, context
        raise NotImplementedError(
            "DOCX exporter is a Stage 7 placeholder; follow CODEX_STAGE_PROMPTS.md"
        )
