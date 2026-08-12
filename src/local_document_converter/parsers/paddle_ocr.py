"""Optional PaddleOCR fallback with lazy imports and explicit trigger rules."""

from __future__ import annotations

import hashlib
import importlib.util
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Protocol, cast

from pydantic import JsonValue

from local_document_converter.capabilities import Availability
from local_document_converter.config import OcrSettings
from local_document_converter.domain.models import (
    DocumentIR,
    DocumentMetadata,
    DocumentWarning,
    HeadingBlock,
    ListBlock,
    ParagraphBlock,
    SourceInfo,
    TableBlock,
)
from local_document_converter.exceptions import (
    InputValidationError,
    ParseError,
    ParserUnavailableError,
)
from local_document_converter.parsers.base import ParseContext, ParserCapability

_SUPPORTED_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff"})
_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}
_CONFIDENCE_KEYS = ("confidence", "docling_confidence", "ocr_confidence")


class _OcrEngine(Protocol):
    def predict(self, input: str) -> Iterable[object]: ...


EngineFactory = Callable[..., _OcrEngine]


class PaddleOcrFallback:
    """Recover text only when an enabled primary image parse is insufficient."""

    def __init__(
        self,
        settings: OcrSettings | None = None,
        *,
        engine_factory: EngineFactory | None = None,
    ) -> None:
        self._settings = settings or OcrSettings()
        self._engine_factory = engine_factory
        availability = self._availability()
        self.capability = ParserCapability(
            name="paddleocr-fallback",
            supported_extensions=_SUPPORTED_EXTENSIONS,
            availability=availability,
        )

    def should_run(self, source: Path, document: DocumentIR) -> bool:
        """Require explicit enablement plus insufficient text or low confidence."""
        if not self._settings.enabled or source.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            return False
        if _text_character_count(document) < self._settings.min_text_characters:
            return True
        if any(warning.code.endswith(".low_confidence") for warning in document.warnings):
            return True
        confidences = _primary_confidences(document)
        return bool(confidences) and min(confidences) < self._settings.min_primary_confidence

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        source = source.resolve()
        self._validate_source(source)
        if context.options:
            unsupported = ", ".join(sorted(context.options))
            raise InputValidationError(f"unsupported PaddleOCR parser options: {unsupported}")

        availability = self.capability.availability
        if not availability.available:
            message = f"PaddleOCR fallback is unavailable: {availability.reason}"
            if availability.install_hint:
                message += f"; {availability.install_hint}"
            raise ParserUnavailableError(message)

        factory = self._engine_factory or _load_engine_factory()
        try:
            engine = factory(**self._engine_options())
            results = list(engine.predict(str(source)))
        except (ImportError, ModuleNotFoundError) as exc:
            raise ParserUnavailableError(
                'PaddleOCR is not installed; install it with pip install -e ".[ocr]"'
            ) from exc
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ParseError("PaddleOCR could not recover text from the input image") from exc

        return self._results_to_ir(source, results)

    def _availability(self) -> Availability:
        if not self._settings.enabled:
            return Availability.unavailable(
                "PaddleOCR fallback is disabled by configuration",
                install_hint="set ocr.enabled=true to enable the fallback",
            )
        if self._engine_factory is None and not _paddleocr_is_installed():
            return Availability.unavailable(
                "PaddleOCR or its PaddlePaddle inference engine is not installed",
                install_hint='install the optional dependencies with pip install -e ".[ocr]"',
            )
        if self._engine_factory is None and not self._settings.allow_model_download:
            directories = (
                self._settings.detection_model_directory,
                self._settings.recognition_model_directory,
            )
            if any(directory is None for directory in directories):
                return Availability.unavailable(
                    "local OCR model directories are required when model download is disabled",
                    install_hint=(
                        "configure ocr.detection_model_directory and "
                        "ocr.recognition_model_directory"
                    ),
                )
            missing = [str(path) for path in directories if path is not None and not path.is_dir()]
            if missing:
                return Availability.unavailable(
                    "configured OCR model directory does not exist",
                    install_hint="verify the local model paths against config/ocr-models.yaml",
                )
        return Availability()

    def _engine_options(self) -> dict[str, object]:
        options: dict[str, object] = {
            "text_detection_model_name": self._settings.detection_model_id,
            "text_recognition_model_name": self._settings.recognition_model_id,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            "device": self._settings.device,
            "engine": "paddle",
        }
        if self._settings.detection_model_directory is not None:
            options["text_detection_model_dir"] = str(
                self._settings.detection_model_directory.resolve()
            )
        if self._settings.recognition_model_directory is not None:
            options["text_recognition_model_dir"] = str(
                self._settings.recognition_model_directory.resolve()
            )
        return options

    @staticmethod
    def _validate_source(source: Path) -> None:
        extension = source.suffix.lower()
        if extension not in _SUPPORTED_EXTENSIONS:
            raise InputValidationError(
                f"PaddleOcrFallback does not accept extension '{extension or '<none>'}'"
            )
        if not source.exists():
            raise InputValidationError(f"input does not exist: {source}")
        if not source.is_file():
            raise InputValidationError(f"input is not a file: {source}")

    def _results_to_ir(self, source: Path, results: Sequence[object]) -> DocumentIR:
        blocks: list[ParagraphBlock] = []
        warnings: list[DocumentWarning] = []
        page_numbers: list[int] = []
        for result in results:
            payload = _result_payload(result)
            page_number = _page_number(payload)
            page_numbers.append(page_number)
            texts = _string_sequence(payload.get("rec_texts"))
            scores = _float_sequence(payload.get("rec_scores"))
            boxes = _box_sequence(payload.get("rec_boxes"))
            for index, text in enumerate(texts):
                stripped = text.strip()
                if not stripped:
                    continue
                attributes: dict[str, JsonValue] = {
                    "ocr_engine": "paddleocr",
                    "ocr_detection_model": self._settings.detection_model_id,
                    "ocr_recognition_model": self._settings.recognition_model_id,
                }
                if index < len(scores):
                    attributes["ocr_confidence"] = scores[index]
                if index < len(boxes):
                    attributes["ocr_box"] = cast(JsonValue, boxes[index])
                blocks.append(
                    ParagraphBlock(
                        id=f"ocr-block-{len(blocks) + 1}",
                        order=len(blocks),
                        page_number=page_number,
                        source_ref=f"ocr:page-{page_number}:line-{index + 1}",
                        text=stripped,
                        attributes=attributes,
                    )
                )

        if not blocks:
            raise ParseError("PaddleOCR returned no recognized text")
        if any("ocr_confidence" not in block.attributes for block in blocks):
            warnings.append(
                DocumentWarning(
                    code="ocr.confidence_unavailable",
                    message="PaddleOCR omitted confidence for one or more recognized lines",
                )
            )

        return DocumentIR(
            source=SourceInfo(
                path=str(source),
                media_type=_MEDIA_TYPES[source.suffix.lower()],
                size_bytes=source.stat().st_size,
                checksum_sha256=_sha256(source),
            ),
            metadata=DocumentMetadata(
                language=",".join(self._settings.languages),
                page_count=max(page_numbers, default=1),
                custom={
                    "ocr_detection_model": self._settings.detection_model_id,
                    "ocr_recognition_model": self._settings.recognition_model_id,
                },
            ),
            blocks=blocks,
            warnings=warnings,
        )


def _paddleocr_is_installed() -> bool:
    return (
        importlib.util.find_spec("paddleocr") is not None
        and importlib.util.find_spec("paddle") is not None
    )


def _load_engine_factory() -> EngineFactory:
    try:
        from paddleocr import PaddleOCR  # type: ignore[import-not-found]
    except (ImportError, ModuleNotFoundError) as exc:
        raise ParserUnavailableError(
            'PaddleOCR is not installed; install it with pip install -e ".[ocr]"'
        ) from exc
    return cast(EngineFactory, PaddleOCR)


def _text_character_count(document: DocumentIR) -> int:
    values: list[str] = []
    for block in document.blocks:
        if isinstance(block, (HeadingBlock, ParagraphBlock)):
            values.append(block.text)
        elif isinstance(block, ListBlock):
            values.extend(block.items)
        elif isinstance(block, TableBlock):
            values.extend(block.column_names or [])
            values.extend(cell or "" for row in block.rows for cell in row)
            if block.caption:
                values.append(block.caption)
    return sum(len(value.strip()) for value in values)


def _primary_confidences(document: DocumentIR) -> list[float]:
    confidences: list[float] = []
    for block in document.blocks:
        for key in _CONFIDENCE_KEYS:
            value = block.attributes.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                confidences.append(float(value))
                break
    return confidences


def _result_payload(result: object) -> Mapping[str, object]:
    raw = result if isinstance(result, Mapping) else getattr(result, "json", None)
    if callable(raw):
        raw = raw()
    if not isinstance(raw, Mapping):
        raise ParseError("PaddleOCR result did not expose a JSON mapping")
    nested = raw.get("res")
    return cast(Mapping[str, object], nested) if isinstance(nested, Mapping) else raw


def _page_number(payload: Mapping[str, object]) -> int:
    page_index = payload.get("page_index")
    if isinstance(page_index, int) and not isinstance(page_index, bool) and page_index >= 0:
        return page_index + 1
    return 1


def _string_sequence(value: object) -> list[str]:
    values = _iterable_values(value)
    if values is None:
        raise ParseError("PaddleOCR result rec_texts must be a sequence")
    return [str(item) for item in values]


def _float_sequence(value: object) -> list[float]:
    values = _iterable_values(value)
    if values is None:
        return []
    return [number for item in values if (number := _float_value(item)) is not None]


def _box_sequence(value: object) -> list[list[int | float]]:
    values = _iterable_values(value)
    if values is None:
        return []
    boxes: list[list[int | float]] = []
    for raw_box in values:
        raw_values = _iterable_values(raw_box)
        if raw_values is None:
            continue
        box = [number for item in raw_values if (number := _number_value(item)) is not None]
        boxes.append(box)
    return boxes


def _iterable_values(value: object) -> list[object] | None:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return None
    return list(value)


def _float_value(value: object) -> float | None:
    number = _number_value(value)
    return float(number) if number is not None else None


def _number_value(value: object) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    scalar = getattr(value, "item", None)
    if not callable(scalar):
        return None
    converted = scalar()
    if isinstance(converted, (int, float)) and not isinstance(converted, bool):
        return converted
    return None


def _sha256(source: Path) -> str:
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
