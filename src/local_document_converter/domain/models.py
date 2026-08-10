"""Versioned, serializable intermediate representation for all conversions."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class FrozenModel(BaseModel):
    """Common strict model configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceInfo(FrozenModel):
    path: str
    media_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    checksum_sha256: str | None = None


class DocumentMetadata(FrozenModel):
    title: str | None = None
    author: str | None = None
    language: str | None = None
    page_count: int | None = Field(default=None, ge=0)
    custom: dict[str, JsonValue] = Field(default_factory=dict)


class DocumentWarning(FrozenModel):
    code: str
    message: str
    page_number: int | None = Field(default=None, ge=1)
    details: dict[str, JsonValue] = Field(default_factory=dict)


class BaseBlock(FrozenModel):
    id: str
    order: int = Field(ge=0)
    page_number: int | None = Field(default=None, ge=1)
    source_ref: str | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class HeadingBlock(BaseBlock):
    type: Literal["heading"] = "heading"
    level: int = Field(ge=1, le=6)
    text: str


class ParagraphBlock(BaseBlock):
    type: Literal["paragraph"] = "paragraph"
    text: str


class ListBlock(BaseBlock):
    type: Literal["list"] = "list"
    ordered: bool = False
    items: list[str]


class TableBlock(BaseBlock):
    type: Literal["table"] = "table"
    rows: list[list[str | None]]
    column_names: list[str] | None = None
    caption: str | None = None


class ImageBlock(BaseBlock):
    type: Literal["image"] = "image"
    uri: str
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
    def block_order_must_be_unique(self) -> DocumentIR:
        orders = [block.order for block in self.blocks]
        if len(orders) != len(set(orders)):
            raise ValueError("block order values must be unique")
        return self
