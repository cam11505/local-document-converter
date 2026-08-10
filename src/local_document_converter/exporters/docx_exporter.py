"""python-docx adapter boundary. Complete in Stage 7."""

from pathlib import Path

from local_document_converter.capabilities import Availability
from local_document_converter.domain.models import DocumentIR
from local_document_converter.exporters.base import ExportContext, ExporterCapability


class DocxExporter:
    capability = ExporterCapability(
        format_name="docx",
        output_extension=".docx",
        availability=Availability.unavailable(
            "DOCX exporter is a Stage 7 placeholder",
            install_hint="complete Stage 7 before selecting this exporter",
        ),
    )

    def export(self, document: DocumentIR, destination: Path, context: ExportContext) -> None:
        del document, destination, context
        raise NotImplementedError(
            "DOCX exporter is a Stage 7 placeholder; follow CODEX_STAGE_PROMPTS.md"
        )
