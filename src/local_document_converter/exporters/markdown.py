"""Deterministic Markdown exporter."""

from collections.abc import Sequence
from pathlib import Path

from local_document_converter.domain.models import (
    DocumentIR,
    HeadingBlock,
    ImageBlock,
    ListBlock,
    PageBreakBlock,
    ParagraphBlock,
    TableBlock,
)
from local_document_converter.exceptions import ExportError
from local_document_converter.exporters.base import ExportContext, ExporterCapability


class MarkdownExporter:
    capability = ExporterCapability(format_name="markdown", output_extension=".md")

    def export(self, document: DocumentIR, destination: Path, context: ExportContext) -> None:
        del context
        sections: list[str] = []
        for block in document.blocks:
            if isinstance(block, HeadingBlock):
                sections.append(f"{'#' * block.level} {block.text}")
            elif isinstance(block, ParagraphBlock):
                sections.append(block.text)
            elif isinstance(block, ListBlock):
                lines = [
                    f"{index}. {item}" if block.ordered else f"- {item}"
                    for index, item in enumerate(block.items, start=1)
                ]
                sections.append("\n".join(lines))
            elif isinstance(block, TableBlock):
                sections.append(self._render_table(block))
            elif isinstance(block, ImageBlock):
                rendered = f"![{block.alt_text}]({block.uri})"
                if block.caption:
                    rendered = f"{rendered}\n\n_{block.caption}_"
                sections.append(rendered)
            elif isinstance(block, PageBreakBlock):
                sections.append("<!-- page-break -->")

        content = "\n\n".join(sections)
        if content:
            content += "\n"
        try:
            destination.write_text(content, encoding="utf-8", newline="\n")
        except OSError as exc:
            raise ExportError(f"could not write Markdown output: {destination}") from exc

    @classmethod
    def _render_table(cls, block: TableBlock) -> str:
        width = len(block.column_names or [])
        if width == 0 and block.rows:
            width = max(len(row) for row in block.rows)
        if width == 0:
            return "<!-- empty-table -->"

        headers = block.column_names or [""] * width
        headers = [cls._escape(cell) for cell in cls._pad(headers, width)]
        lines = [f"| {' | '.join(headers)} |", f"| {' | '.join(['---'] * width)} |"]
        for row in block.rows:
            cells = [cls._escape(cell) for cell in cls._pad(row, width)]
            lines.append(f"| {' | '.join(cells)} |")
        return "\n".join(lines)

    @staticmethod
    def _pad(values: Sequence[str | None], width: int) -> list[str | None]:
        return (list(values) + [None] * width)[:width]

    @staticmethod
    def _escape(value: str | None) -> str:
        if value is None:
            return ""
        return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")
