"""DocumentIR JSON exporter."""

from pathlib import Path

from local_document_converter.domain.models import DocumentIR
from local_document_converter.exporters.base import ExportContext


class JsonExporter:
    format_name = "json"
    output_extension = ".json"

    def export(self, document: DocumentIR, destination: Path, context: ExportContext) -> None:
        del context
        destination.write_text(
            document.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
        )
