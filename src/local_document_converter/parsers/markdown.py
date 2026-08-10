"""Small MVP Markdown parser; it is intentionally not a full CommonMark parser."""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from local_document_converter.domain.models import (
    Block,
    DocumentIR,
    HeadingBlock,
    ImageBlock,
    ListBlock,
    ParagraphBlock,
    SourceInfo,
    TableBlock,
)
from local_document_converter.parsers.base import ParseContext

_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_LIST_ITEM = re.compile(r"^\s*(?:(\d+)[.)]|[-+*])\s+(.+)$")
_IMAGE = re.compile(r"^!\[([^]]*)]\(([^)]+)\)$")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")


class MarkdownParser:
    name = "markdown"
    supported_extensions = frozenset({".md", ".markdown"})

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del context
        lines = source.read_text(encoding="utf-8").splitlines()
        blocks: list[Block] = []
        order = 0
        index = 0

        while index < len(lines):
            line = lines[index].strip()
            if not line:
                index += 1
                continue

            heading = _HEADING.match(line)
            if heading:
                blocks.append(
                    HeadingBlock(
                        id=f"block-{order}",
                        order=order,
                        level=len(heading.group(1)),
                        text=heading.group(2).strip(),
                    )
                )
                order += 1
                index += 1
                continue

            image = _IMAGE.match(line)
            if image:
                blocks.append(
                    ImageBlock(
                        id=f"block-{order}",
                        order=order,
                        alt_text=image.group(1),
                        uri=image.group(2),
                    )
                )
                order += 1
                index += 1
                continue

            if index + 1 < len(lines) and "|" in line and _TABLE_SEPARATOR.match(
                lines[index + 1]
            ):
                column_names = self._cells(line)
                index += 2
                rows: list[list[str | None]] = []
                while index < len(lines) and "|" in lines[index] and lines[index].strip():
                    row: list[str | None] = []
                    row.extend(self._cells(lines[index]))
                    rows.append(row)
                    index += 1
                blocks.append(
                    TableBlock(
                        id=f"block-{order}",
                        order=order,
                        column_names=column_names,
                        rows=rows,
                    )
                )
                order += 1
                continue

            list_match = _LIST_ITEM.match(line)
            if list_match:
                ordered = list_match.group(1) is not None
                items: list[str] = []
                while index < len(lines):
                    match = _LIST_ITEM.match(lines[index])
                    if match is None or (match.group(1) is not None) != ordered:
                        break
                    items.append(match.group(2).strip())
                    index += 1
                blocks.append(
                    ListBlock(
                        id=f"block-{order}",
                        order=order,
                        ordered=ordered,
                        items=items,
                    )
                )
                order += 1
                continue

            paragraph_lines = [line]
            index += 1
            while index < len(lines) and lines[index].strip():
                candidate = lines[index].strip()
                starts_new_block = (
                    _HEADING.match(candidate)
                    or _LIST_ITEM.match(candidate)
                    or _IMAGE.match(candidate)
                )
                if starts_new_block:
                    break
                paragraph_lines.append(candidate)
                index += 1
            blocks.append(
                ParagraphBlock(
                    id=f"block-{order}", order=order, text=" ".join(paragraph_lines)
                )
            )
            order += 1

        media_type, _ = mimetypes.guess_type(source.name)
        return DocumentIR(
            source=SourceInfo(
                path=str(source),
                media_type=media_type or "text/markdown",
                size_bytes=source.stat().st_size,
            ),
            blocks=blocks,
        )

    @staticmethod
    def _cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]
