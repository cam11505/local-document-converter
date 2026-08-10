"""Optional PaddleOCR fallback boundary. Complete only after the Stage 9 license gate."""

from pathlib import Path

from local_document_converter.capabilities import Availability
from local_document_converter.domain.models import DocumentIR
from local_document_converter.parsers.base import ParseContext, ParserCapability


class PaddleOcrFallback:
    capability = ParserCapability(
        name="paddleocr-fallback",
        supported_extensions=frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff"}),
        availability=Availability.unavailable(
            "PaddleOCR fallback is gated by the Stage 9 license review",
            install_hint='after approval, install with pip install -e ".[ocr]"',
        ),
    )

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del source, context
        raise NotImplementedError(
            "PaddleOCR fallback is P1 optional and gated by Stage 9 license review"
        )
