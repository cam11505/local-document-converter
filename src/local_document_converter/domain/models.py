"""Versioned, serializable intermediate representation for all conversions."""

from __future__ import annotations

import json
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    model_validator,
)

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
Sha256Checksum = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class FrozenModel(BaseModel):
    """Common strict model configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class SourceInfo(FrozenModel):
    path: NonEmptyString
    media_type: NonEmptyString | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    checksum_sha256: Sha256Checksum | None = None


class DocumentMetadata(FrozenModel):
    title: str | None = None
    author: str | None = None
    language: str | None = None
    page_count: int | None = Field(default=None, ge=0)
    custom: dict[str, JsonValue] = Field(default_factory=dict)


class DocumentWarning(FrozenModel):
    code: NonEmptyString
    message: NonEmptyString
    page_number: int | None = Field(default=None, ge=1)
    details: dict[str, JsonValue] = Field(default_factory=dict)


class BaseBlock(FrozenModel):
    id: NonEmptyString
    order: int = Field(ge=0)
    page_number: int | None = Field(default=None, ge=1)
    source_ref: NonEmptyString | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class HeadingBlock(BaseBlock):
    type: Literal["heading"] = "heading"
    level: int = Field(ge=1, le=6)
    text: NonEmptyString


class ParagraphBlock(BaseBlock):
    type: Literal["paragraph"] = "paragraph"
    text: NonEmptyString


class ListBlock(BaseBlock):
    type: Literal["list"] = "list"
    ordered: bool = False
    items: list[NonEmptyString] = Field(min_length=1)


class TableBlock(BaseBlock):
    type: Literal["table"] = "table"
    rows: list[list[str | None]]
    column_names: list[str] | None = None
    caption: str | None = None

    @model_validator(mode="after")
    def rows_and_columns_must_be_rectangular(self) -> TableBlock:
        widths = {len(row) for row in self.rows}
        if len(widths) > 1:
            raise ValueError("table rows must all have the same number of cells")

        row_width = next(iter(widths), None)
        if (
            self.column_names is not None
            and row_width is not None
            and len(self.column_names) != row_width
        ):
            raise ValueError("table column_names length must match row width")
        return self


class ImageBlock(BaseBlock):
    type: Literal["image"] = "image"
    uri: NonEmptyString
    alt_text: str = ""
    caption: str | None = None


class PageBreakBlock(BaseBlock):
    type: Literal["page_break"] = "page_break"


Block = Annotated[
    HeadingBlock | ParagraphBlock | ListBlock | TableBlock | ImageBlock | PageBreakBlock,
    Field(discriminator="type"),
]


class DocumentIR(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    source: SourceInfo
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    blocks: list[Block] = Field(default_factory=list)
    warnings: list[DocumentWarning] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_document_invariants(self) -> DocumentIR:
        block_ids = [block.id for block in self.blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("block id values must be unique")

        orders = [block.order for block in self.blocks]
        expected_orders = list(range(len(self.blocks)))
        if orders != expected_orders:
            raise ValueError(
                "block order values must be contiguous and match list order starting at 0"
            )

        if self.metadata.page_count is not None:
            page_count = self.metadata.page_count
            for block in self.blocks:
                if block.page_number is not None and block.page_number > page_count:
                    raise ValueError("block page_number cannot exceed metadata.page_count")
            for warning in self.warnings:
                if warning.page_number is not None and warning.page_number > page_count:
                    raise ValueError("warning page_number cannot exceed metadata.page_count")
        return self

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize the official IR JSON with stable key ordering and UTF-8 text."""
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=indent,
        )

    @classmethod
    def from_json(cls, data: str | bytes) -> Self:
        """Validate and restore a DocumentIR from its JSON representation."""
        return cls.model_validate_json(data)
