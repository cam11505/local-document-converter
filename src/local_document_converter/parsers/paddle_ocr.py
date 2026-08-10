"""Optional PaddleOCR fallback boundary. Complete only after the Stage 9 license gate."""

from pathlib import Path

from local_document_converter.domain.models import DocumentIR
from local_document_converter.parsers.base import ParseContext


class PaddleOcrFallback:
    name = "paddleocr-fallback"
    supported_extensions = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff"})

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del source, context
        raise NotImplementedError(
            "PaddleOCR fallback is P1 optional and gated by Stage 9 license review"
        )
