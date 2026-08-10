"""Stable domain models that do not depend on parser/exporter libraries."""

from local_document_converter.domain.models import (
    Block,
    DocumentIR,
    DocumentMetadata,
    DocumentWarning,
    HeadingBlock,
    ImageBlock,
    ListBlock,
    PageBreakBlock,
    ParagraphBlock,
    SourceInfo,
    TableBlock,
)

__all__ = [
    "Block",
    "DocumentIR",
    "DocumentMetadata",
    "DocumentWarning",
    "HeadingBlock",
    "ImageBlock",
    "ListBlock",
    "PageBreakBlock",
    "ParagraphBlock",
    "SourceInfo",
    "TableBlock",
]
