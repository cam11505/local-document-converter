"""DocumentIR JSON exporter."""

from pathlib import Path

from local_document_converter.domain.models import DocumentIR
from local_document_converter.exceptions import ExportError
from local_document_converter.exporters.base import ExportContext, ExporterCapability


class JsonExporter:
    capability = ExporterCapability(format_name="json", output_extension=".json")

    def export(self, document: DocumentIR, destination: Path, context: ExportContext) -> None:
        del context
        try:
            destination.write_text(
                document.to_json(indent=2) + "\n", encoding="utf-8", newline="\n"
            )
        except OSError as exc:
            raise ExportError(f"could not write JSON output: {destination}") from exc
