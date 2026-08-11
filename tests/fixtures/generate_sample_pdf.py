"""Regenerate the self-authored Stage 6 PDF fixture."""

from pathlib import Path

from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.pdfgen.canvas import Canvas  # type: ignore[import-untyped]


def generate(destination: Path) -> None:
    canvas = Canvas(
        str(destination),
        pagesize=letter,
        invariant=1,
        pageCompression=1,
    )
    canvas.setTitle("Stage 6 PDF Sample")
    canvas.setAuthor("Local Document Converter contributors")

    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(72, 720, "Stage 6 PDF Sample")
    canvas.setFont("Helvetica", 11)
    canvas.drawString(72, 688, "This PDF verifies the Docling parser path.")

    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(72, 648, "Expected behavior")
    canvas.setFont("Helvetica", 11)
    canvas.drawString(88, 624, "- Preserve reading order")
    canvas.drawString(88, 604, "- Map tables to DocumentIR")

    left, bottom, width, row_height = 72, 488, 360, 30
    canvas.setLineWidth(1)
    for row in range(4):
        y = bottom + row * row_height
        canvas.line(left, y, left + width, y)
    for x in (left, left + 180, left + width):
        canvas.line(x, bottom, x, bottom + 3 * row_height)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(left + 8, bottom + 2 * row_height + 10, "Component")
    canvas.drawString(left + 188, bottom + 2 * row_height + 10, "Status")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(left + 8, bottom + row_height + 10, "DoclingParser")
    canvas.drawString(left + 188, bottom + row_height + 10, "Ready")
    canvas.drawString(left + 8, bottom + 10, "MarkdownExporter")
    canvas.drawString(left + 188, bottom + 10, "Ready")

    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(72, 442, "DocumentIR flow")
    canvas.roundRect(72, 366, 360, 54, 8, stroke=1, fill=0)
    canvas.setFont("Helvetica", 11)
    canvas.drawCentredString(252, 388, "PDF  ->  DoclingParser  ->  DocumentIR  ->  Markdown")
    canvas.setFont("Helvetica-Oblique", 9)
    canvas.drawString(72, 340, "Self-authored fixture; safe to redistribute with this project.")
    canvas.showPage()
    canvas.save()


if __name__ == "__main__":
    generate(Path(__file__).with_name("sample.pdf"))
