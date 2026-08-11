"""Docling adapter with a lazy optional-dependency boundary."""

from __future__ import annotations

import hashlib
import importlib.util
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Protocol, cast

from local_document_converter.capabilities import Availability
from local_document_converter.domain.models import (
    Block,
    DocumentIR,
    DocumentMetadata,
    DocumentWarning,
    HeadingBlock,
    ImageBlock,
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

_SUPPORTED_EXTENSIONS = frozenset(
    {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
)
_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}
_TEXT_LABELS = {
    "caption",
    "checkbox_selected",
    "checkbox_unselected",
    "empty_value",
    "field_hint",
    "field_key",
    "footnote",
    "handwritten_text",
    "marker",
    "page_footer",
    "page_header",
    "paragraph",
    "reference",
    "text",
}


class _Converter(Protocol):
    def convert(self, source: Path, *, raises_on_error: bool) -> object: ...


ConverterFactory = Callable[[], _Converter]


class DoclingParser:
    """Convert Docling's reading-order document model into the stable project IR."""

    def __init__(self, *, converter_factory: ConverterFactory | None = None) -> None:
        self._converter_factory = converter_factory
        availability = Availability()
        if converter_factory is None and not _docling_is_installed():
            availability = Availability.unavailable(
                "Docling is not installed",
                install_hint='install the optional dependency with pip install -e ".[docling]"',
            )
        self.capability = ParserCapability(
            name="docling",
            supported_extensions=_SUPPORTED_EXTENSIONS,
            availability=availability,
        )

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        source = source.resolve()
        self._validate_source(source)
        if context.options:
            unsupported = ", ".join(sorted(context.options))
            raise InputValidationError(f"unsupported Docling parser options: {unsupported}")

        converter_factory = self._converter_factory or _load_converter_factory()
        try:
            result = converter_factory().convert(source, raises_on_error=False)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ParseError(f"Docling could not parse input: {source}") from exc

        return self._result_to_ir(source, result)

    @staticmethod
    def _validate_source(source: Path) -> None:
        extension = source.suffix.lower()
        if extension not in _SUPPORTED_EXTENSIONS:
            raise InputValidationError(
                f"DoclingParser does not accept extension '{extension or '<none>'}'"
            )
        if not source.exists():
            raise InputValidationError(f"input does not exist: {source}")
        if not source.is_file():
            raise InputValidationError(f"input is not a file: {source}")

    @classmethod
    def _result_to_ir(cls, source: Path, result: object) -> DocumentIR:
        status = _enum_value(_attribute(result, "status"))
        errors = _conversion_errors(result)
        if status not in {"success", "partial_success"}:
            details = f": {'; '.join(errors)}" if errors else ""
            raise ParseError(f"Docling conversion failed with status '{status}'{details}")

        document = _attribute(result, "document")
        iterator = _attribute(document, "iterate_items")
        if not callable(iterator):
            raise ParseError("Docling result does not expose iterate_items()")

        raw_items = cast(Callable[[], Iterable[tuple[object, int]]], iterator)()
        blocks, warnings = cls._map_items(source, document, raw_items)
        if status == "partial_success":
            warnings.insert(
                0,
                DocumentWarning(
                    code="docling.partial_success",
                    message="Docling completed with recoverable conversion errors",
                    details={"errors": errors},
                ),
            )
        if not blocks:
            warnings.append(
                DocumentWarning(
                    code="docling.no_content",
                    message="Docling returned no mappable document content",
                )
            )

        title = next(
            (
                block.text
                for block in blocks
                if isinstance(block, HeadingBlock)
                and block.attributes.get("docling_label") == "title"
            ),
            None,
        )
        return DocumentIR(
            source=SourceInfo(
                path=str(source),
                media_type=_MEDIA_TYPES[source.suffix.lower()],
                size_bytes=source.stat().st_size,
                checksum_sha256=_sha256(source),
            ),
            metadata=DocumentMetadata(
                title=title,
                page_count=_page_count(document, blocks),
            ),
            blocks=blocks,
            warnings=warnings,
        )

    @classmethod
    def _map_items(
        cls,
        source: Path,
        document: object,
        items: Iterable[tuple[object, int]],
    ) -> tuple[list[Block], list[DocumentWarning]]:
        blocks: list[Block] = []
        warnings: list[DocumentWarning] = []
        pending_list: list[object] = []

        def flush_list() -> None:
            if not pending_list:
                return
            first = pending_list[0]
            blocks.append(
                ListBlock(
                    id=_block_id(len(blocks)),
                    order=len(blocks),
                    page_number=_page_number(first),
                    source_ref=_source_ref(first),
                    ordered=bool(_attribute(first, "enumerated", False)),
                    items=[_text(item) for item in pending_list if _text(item)],
                    attributes={
                        "docling_label": "list_item",
                        "source_refs": [
                            reference
                            for item in pending_list
                            if (reference := _source_ref(item)) is not None
                        ],
                    },
                )
            )
            pending_list.clear()

        for item, _level in items:
            label = _label(item)
            if label == "list_item":
                if pending_list and (
                    bool(_attribute(pending_list[0], "enumerated", False))
                    != bool(_attribute(item, "enumerated", False))
                    or _page_number(pending_list[0]) != _page_number(item)
                ):
                    flush_list()
                if _text(item):
                    pending_list.append(item)
                else:
                    warnings.append(_unmapped_warning(item, label))
                continue

            flush_list()
            block = cls._map_item(source, document, item, label, len(blocks), warnings)
            if block is not None:
                blocks.append(block)

        flush_list()
        return blocks, warnings

    @classmethod
    def _map_item(
        cls,
        source: Path,
        document: object,
        item: object,
        label: str,
        order: int,
        warnings: list[DocumentWarning],
    ) -> Block | None:
        common = {
            "id": _block_id(order),
            "order": order,
            "page_number": _page_number(item),
            "source_ref": _source_ref(item),
            "attributes": {"docling_label": label},
        }
        text = _text(item)

        if label == "title":
            if not text:
                warnings.append(_unmapped_warning(item, label))
                return None
            return HeadingBlock(level=1, text=text, **common)
        if label == "section_header":
            if not text:
                warnings.append(_unmapped_warning(item, label))
                return None
            raw_level = _positive_int(_attribute(item, "level", 1), default=1)
            level = min(raw_level, 6)
            if raw_level > 6:
                warnings.append(
                    DocumentWarning(
                        code="docling.heading_level_clamped",
                        message=f"Docling heading level {raw_level} was clamped to 6",
                        page_number=_page_number(item),
                        details={"source_ref": _source_ref(item) or ""},
                    )
                )
            return HeadingBlock(level=level, text=text, **common)
        if label == "table":
            table = cls._map_table(document, item, common)
            if table is None:
                warnings.append(_unmapped_warning(item, label))
            return table
        if label in {"picture", "chart"}:
            caption = _caption(item, document)
            return ImageBlock(
                uri=f"{source.name}{_source_ref(item) or '#image'}",
                alt_text=caption or ("Chart" if label == "chart" else "Image"),
                caption=caption or None,
                **common,
            )
        if label in _TEXT_LABELS and text:
            attributes = cast(dict[str, object], common["attributes"])
            if label == "checkbox_selected":
                text = f"[x] {text}"
            elif label == "checkbox_unselected":
                text = f"[ ] {text}"
            attributes["docling_label"] = label
            return ParagraphBlock(text=text, **common)

        warnings.append(_unmapped_warning(item, label))
        if text:
            return ParagraphBlock(text=text, **common)
        return None

    @staticmethod
    def _map_table(
        document: object, item: object, common: dict[str, object]
    ) -> TableBlock | None:
        data = _attribute(item, "data", None)
        grid = _attribute(data, "grid", None) if data is not None else None
        if not isinstance(grid, Sequence) or isinstance(grid, (str, bytes)):
            return None

        rows: list[list[str | None]] = []
        header_flags: list[list[bool]] = []
        for raw_row in grid:
            if not isinstance(raw_row, Sequence) or isinstance(raw_row, (str, bytes)):
                return None
            row: list[str | None] = []
            flags: list[bool] = []
            for cell in raw_row:
                cell_text = _text(cell)
                row.append(cell_text or None)
                flags.append(bool(_attribute(cell, "column_header", False)))
            rows.append(row)
            header_flags.append(flags)

        width = max((len(row) for row in rows), default=0)
        if width == 0:
            return TableBlock(rows=[], caption=_caption(item, document) or None, **common)
        normalized = [(row + [None] * width)[:width] for row in rows]
        has_header = bool(header_flags and any(header_flags[0]))
        column_names = [cell or "" for cell in normalized[0]] if has_header else None
        body_rows = normalized[1:] if has_header else normalized
        return TableBlock(
            rows=body_rows,
            column_names=column_names,
            caption=_caption(item, document) or None,
            **common,
        )


def _docling_is_installed() -> bool:
    return (
        importlib.util.find_spec("docling") is not None
        and importlib.util.find_spec("docling_core") is not None
    )


def _load_converter_factory() -> ConverterFactory:
    try:
        from docling.document_converter import DocumentConverter
    except (ImportError, ModuleNotFoundError) as exc:
        raise ParserUnavailableError(
            'Docling is not installed; install it with pip install -e ".[docling]"'
        ) from exc
    return cast(ConverterFactory, DocumentConverter)


def _attribute(value: object, name: str, default: object | None = None) -> object:
    return cast(object, getattr(value, name, default))


def _enum_value(value: object) -> str:
    raw = _attribute(value, "value", value)
    return str(raw).strip().lower()


def _label(item: object) -> str:
    return _enum_value(_attribute(item, "label", "unknown"))


def _text(item: object) -> str:
    value = _attribute(item, "text", "")
    return str(value).strip() if value is not None else ""


def _source_ref(item: object) -> str | None:
    value = _attribute(item, "self_ref", None)
    return str(value) if value else None


def _page_number(item: object) -> int | None:
    provenance = _attribute(item, "prov", ())
    if not isinstance(provenance, Sequence) or not provenance:
        return None
    value = _attribute(provenance[0], "page_no", None)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 1 else None


def _positive_int(value: object, *, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
        return value
    return default


def _caption(item: object, document: object) -> str:
    method = _attribute(item, "caption_text", None)
    if not callable(method):
        return ""
    try:
        value = cast(Callable[[object], object], method)(document)
    except (AttributeError, KeyError, TypeError, ValueError):
        return ""
    return str(value).strip() if value is not None else ""


def _conversion_errors(result: object) -> list[str]:
    raw_errors = _attribute(result, "errors", ())
    if not isinstance(raw_errors, Sequence) or isinstance(raw_errors, (str, bytes)):
        return []
    return [
        str(_attribute(error, "error_message", error)).strip()
        for error in raw_errors
        if str(_attribute(error, "error_message", error)).strip()
    ]


def _page_count(document: object, blocks: Sequence[Block]) -> int | None:
    pages = _attribute(document, "pages", None)
    page_numbers = [block.page_number for block in blocks if block.page_number is not None]
    mapped_page_count = max(page_numbers, default=0)
    if isinstance(pages, dict):
        return max(len(pages), mapped_page_count)
    return mapped_page_count or None


def _unmapped_warning(item: object, label: str) -> DocumentWarning:
    return DocumentWarning(
        code="docling.unmapped_item",
        message=f"Docling item with label '{label}' could not be mapped exactly",
        page_number=_page_number(item),
        details={"label": label, "source_ref": _source_ref(item) or ""},
    )


def _block_id(order: int) -> str:
    return f"docling-block-{order + 1}"


def _sha256(source: Path) -> str:
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
