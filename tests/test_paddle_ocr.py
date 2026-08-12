from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

import local_document_converter.parsers.paddle_ocr as ocr_adapter
from local_document_converter.config import OcrSettings
from local_document_converter.domain import (
    DocumentIR,
    DocumentMetadata,
    ParagraphBlock,
    SourceInfo,
)
from local_document_converter.exporters.markdown import MarkdownExporter
from local_document_converter.exporters.registry import ExporterRegistry
from local_document_converter.parsers.base import ParseContext, ParserCapability
from local_document_converter.parsers.paddle_ocr import PaddleOcrFallback
from local_document_converter.parsers.registry import ParserRegistry
from local_document_converter.services.conversion_service import (
    ConversionRequest,
    ConversionService,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "sample.png"


class PrimaryImageParser:
    capability = ParserCapability(
        name="primary-image",
        supported_extensions=frozenset({".png"}),
    )

    def __init__(self, document: DocumentIR) -> None:
        self._document = document

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del source, context
        return self._document


class FakeResult:
    def __init__(self, payload: dict[str, object]) -> None:
        self.json = {"res": payload}


class FakeEngine:
    def __init__(self, results: list[FakeResult], *, fail: bool = False) -> None:
        self._results = results
        self._fail = fail
        self.inputs: list[str] = []

    def predict(self, input: str) -> list[FakeResult]:
        self.inputs.append(input)
        if self._fail:
            raise RuntimeError("mocked OCR failure")
        return self._results


class ArrayLike:
    """Small iterable used to model PaddleOCR numpy arrays without importing numpy."""

    def __init__(self, values: list[object]) -> None:
        self._values = values

    def __iter__(self) -> object:
        return iter(self._values)


class ScalarLike:
    def __init__(self, value: int | float) -> None:
        self._value = value

    def item(self) -> int | float:
        return self._value


class CapturingFactory:
    def __init__(self, engine: FakeEngine) -> None:
        self.engine = engine
        self.options: list[dict[str, object]] = []

    def __call__(self, **options: object) -> FakeEngine:
        self.options.append(options)
        return self.engine


def test_ocr_disabled_never_runs_even_when_primary_text_is_empty() -> None:
    factory = CapturingFactory(_successful_engine())
    service = _service(
        _primary_document(),
        PaddleOcrFallback(
            OcrSettings(enabled=False, min_text_characters=100),
            engine_factory=factory,
        ),
    )

    document = service.inspect(SAMPLE)

    assert document.blocks == []
    assert factory.options == []
    assert document.warnings == []


def test_missing_optional_runtime_preserves_primary_and_gives_install_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ocr_adapter, "_paddleocr_is_installed", lambda: False)
    fallback = PaddleOcrFallback(
        OcrSettings(
            enabled=True,
            min_text_characters=100,
            allow_model_download=True,
        )
    )

    document = _service(_primary_document(), fallback).inspect(SAMPLE)

    assert document.blocks == []
    assert [warning.code for warning in document.warnings] == ["ocr.fallback_unavailable"]
    assert 'pip install -e ".[ocr]"' in document.warnings[0].message


def test_insufficient_primary_text_triggers_mocked_ocr_and_golden_markdown(
    tmp_path: Path,
) -> None:
    engine = _successful_engine()
    factory = CapturingFactory(engine)
    fallback = PaddleOcrFallback(
        OcrSettings(enabled=True, min_text_characters=100),
        engine_factory=factory,
    )
    destination = tmp_path / "sample.md"

    result = _service(_primary_document(), fallback).convert(
        ConversionRequest(
            source=SAMPLE,
            output_format="markdown",
            destination=destination,
        )
    )
    document = _service(_primary_document(), fallback).inspect(SAMPLE)

    assert result.parser_name == "primary-image"
    assert [block.text for block in document.blocks if isinstance(block, ParagraphBlock)] == [
        "Stage 9 OCR Sample",
        "Fallback text recovered.",
    ]
    assert document.blocks[0].attributes["ocr_confidence"] == 0.99
    assert document.blocks[0].attributes["ocr_box"] == [48, 52, 390, 90]
    assert [warning.code for warning in document.warnings] == ["ocr.fallback_used"]
    assert engine.inputs == [str(SAMPLE.resolve()), str(SAMPLE.resolve())]
    assert factory.options[0] == {
        "text_detection_model_name": "PP-OCRv5_mobile_det",
        "text_recognition_model_name": "chinese_cht_PP-OCRv3_mobile_rec",
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
        "device": "cpu",
        "engine": "paddle",
    }
    assert destination.read_text(encoding="utf-8") == (
        FIXTURES / "expected" / "sample.png.md"
    ).read_text(encoding="utf-8")


def test_sufficient_primary_text_does_not_trigger_ocr() -> None:
    factory = CapturingFactory(_successful_engine())
    primary = _primary_document(text="Primary parser already recovered enough text.")
    fallback = PaddleOcrFallback(
        OcrSettings(enabled=True, min_text_characters=10),
        engine_factory=factory,
    )

    document = _service(primary, fallback).inspect(SAMPLE)

    assert document == primary
    assert factory.options == []


def test_low_primary_confidence_triggers_ocr_even_with_sufficient_text() -> None:
    factory = CapturingFactory(_successful_engine())
    primary = _primary_document(
        text="Primary parser recovered enough characters but confidence is low.",
        confidence=0.2,
    )
    fallback = PaddleOcrFallback(
        OcrSettings(
            enabled=True,
            min_text_characters=10,
            min_primary_confidence=0.5,
        ),
        engine_factory=factory,
    )

    document = _service(primary, fallback).inspect(SAMPLE)

    first = document.blocks[0]
    assert isinstance(first, ParagraphBlock)
    assert first.text == "Stage 9 OCR Sample"
    assert factory.options


def test_ocr_failure_preserves_primary_result() -> None:
    primary = _primary_document(text="short")
    engine = FakeEngine([], fail=True)
    fallback = PaddleOcrFallback(
        OcrSettings(enabled=True, min_text_characters=100),
        engine_factory=CapturingFactory(engine),
    )

    document = _service(primary, fallback).inspect(SAMPLE)

    assert document.blocks == primary.blocks
    assert [warning.code for warning in document.warnings] == ["ocr.fallback_failed"]


def test_model_manifest_has_traceable_source_checksum_license_and_notice() -> None:
    manifest = yaml.safe_load(
        (Path(__file__).parents[1] / "config" / "ocr-models.yaml").read_text(encoding="utf-8")
    )

    assert manifest["license_evidence"]["notice"]
    for model in manifest["models"].values():
        assert model["id"]
        assert model["version"]
        assert model["source"].startswith("https://")
        assert len(model["archive_sha256"]) == 64
        assert model["license"] == "Apache-2.0"

    assert manifest["models"]["detection"]["archive_sha256"] == (
        "50446e5d01ac2a73d5319c89513281f6578414c888c602f9af13f93feefffc58"
    )
    assert manifest["models"]["recognition"]["archive_sha256"] == (
        "f03bd54fe9911a6a10a09956cae570294eb55c61096a12e437d5eb9501f52288"
    )


def test_paddleocr_array_like_scores_and_boxes_are_preserved() -> None:
    parser = PaddleOcrFallback(
        OcrSettings(enabled=True),
        engine_factory=CapturingFactory(
            FakeEngine(
                [
                    FakeResult(
                        {
                            "rec_texts": ["Array result"],
                            "rec_scores": ArrayLike([ScalarLike(0.88)]),
                            "rec_boxes": ArrayLike(
                                [ArrayLike([ScalarLike(1), ScalarLike(2), 3, 4])]
                            ),
                        }
                    )
                ]
            )
        ),
    )

    document = parser.parse(SAMPLE, ParseContext())

    assert document.blocks[0].attributes["ocr_confidence"] == 0.88
    assert document.blocks[0].attributes["ocr_box"] == [1, 2, 3, 4]


@pytest.mark.ocr
@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("LDC_RUN_OCR_INTEGRATION") != "1",
    reason="set LDC_RUN_OCR_INTEGRATION=1 with local model directories",
)
def test_real_paddleocr_sample_image() -> None:
    detection_directory = os.environ.get("LDC_OCR_DETECTION_MODEL_DIR")
    recognition_directory = os.environ.get("LDC_OCR_RECOGNITION_MODEL_DIR")
    if not detection_directory or not recognition_directory:
        pytest.skip("local OCR model directories were not configured")
    parser = PaddleOcrFallback(
        OcrSettings(
            enabled=True,
            detection_model_directory=Path(detection_directory),
            recognition_model_directory=Path(recognition_directory),
        )
    )
    if not parser.capability.availability.available:
        pytest.skip(parser.capability.availability.reason or "OCR runtime unavailable")

    document = parser.parse(SAMPLE, ParseContext())

    text = " ".join(block.text for block in document.blocks if isinstance(block, ParagraphBlock))
    assert "Stage 9 OCR Sample" in text
    assert "Fallback text recovered" in text


def _service(primary: DocumentIR, fallback: PaddleOcrFallback) -> ConversionService:
    parsers = ParserRegistry()
    parsers.register(PrimaryImageParser(primary))
    exporters = ExporterRegistry()
    exporters.register(MarkdownExporter())
    return ConversionService(parsers, exporters, parser_fallback=fallback)


def _primary_document(*, text: str | None = None, confidence: float | None = None) -> DocumentIR:
    blocks: list[ParagraphBlock] = []
    if text is not None:
        attributes = {} if confidence is None else {"confidence": confidence}
        blocks.append(
            ParagraphBlock(
                id="primary-block-1",
                order=0,
                page_number=1,
                text=text,
                attributes=attributes,
            )
        )
    return DocumentIR(
        source=SourceInfo(path=str(SAMPLE), media_type="image/png"),
        metadata=DocumentMetadata(page_count=1),
        blocks=blocks,
    )


def _successful_engine() -> FakeEngine:
    return FakeEngine(
        [
            FakeResult(
                {
                    "input_path": str(SAMPLE),
                    "page_index": None,
                    "rec_texts": ["Stage 9 OCR Sample", "Fallback text recovered."],
                    "rec_scores": [0.99, 0.97],
                    "rec_boxes": [[48, 52, 390, 90], [48, 120, 360, 154]],
                }
            )
        ]
    )
