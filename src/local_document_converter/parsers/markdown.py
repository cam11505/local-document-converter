"""Small MVP Markdown parser; it is intentionally not a full CommonMark parser."""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from local_document_converter.domain.models import (
    Block,
    DocumentIR,
    DocumentWarning,
    HeadingBlock,
    ImageBlock,
    ListBlock,
    ParagraphBlock,
    SourceInfo,
    TableBlock,
)
from local_document_converter.exceptions import ParseError
from local_document_converter.parsers.base import ParseContext, ParserCapability

_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_LIST_ITEM = re.compile(r"^\s*(?:(\d+)[.)]|[-+*])\s+(.+)$")
_IMAGE = re.compile(r"^!\[([^]]*)]\(([^)]+)\)$")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_NESTED_LIST = re.compile(r"^\s{2,}(?:(?:\d+)[.)]|[-+*])\s+")
_THEMATIC_BREAK = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})$")
_SETEXT_UNDERLINE = re.compile(r"^(?:=+|-+)$")


class MarkdownParser:
    capability = ParserCapability(
        name="markdown", supported_extensions=frozenset({".md", ".markdown"})
    )

    def parse(self, source: Path, context: ParseContext) -> DocumentIR:
        del context
        try:
            lines = source.read_text(encoding="utf-8").splitlines()
            source_size = source.stat().st_size
        except (OSError, UnicodeError) as exc:
            raise ParseError(f"could not read Markdown input as UTF-8: {source}") from exc

        blocks: list[Block] = []
        warnings = self._unsupported_syntax_warnings(lines)
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
                table_line = index + 1
                column_names = self._cells(line)
                index += 2
                parsed_rows: list[list[str]] = []
                while index < len(lines) and "|" in lines[index] and lines[index].strip():
                    parsed_rows.append(self._cells(lines[index]))
                    index += 1

                width = max(
                    [len(column_names), *(len(row) for row in parsed_rows)], default=0
                )
                if len(column_names) != width or any(
                    len(row) != width for row in parsed_rows
                ):
                    warnings.append(
                        DocumentWarning(
                            code="markdown.table_width_normalized",
                            message="Markdown table rows were padded to a consistent width",
                            details={"line_number": table_line, "column_count": width},
                        )
                    )
                column_names = (column_names + [""] * width)[:width]
                rows: list[list[str | None]] = []
                for parsed_row in parsed_rows:
                    row: list[str | None] = []
                    row.extend(parsed_row)
                    row.extend([None] * (width - len(row)))
                    rows.append(row)
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
                size_bytes=source_size,
            ),
            blocks=blocks,
            warnings=warnings,
        )

    @staticmethod
    def _cells(line: str) -> list[str]:
        content = line.strip()
        if content.startswith("|"):
            content = content[1:]
        if content.endswith("|") and not content.endswith("\\|"):
            content = content[:-1]

        cells: list[str] = []
        current: list[str] = []
        escaped = False
        for character in content:
            if escaped:
                if character in {"|", "\\"}:
                    current.append(character)
                else:
                    current.extend(("\\", character))
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == "|":
                cells.append("".join(current).strip())
                current = []
            else:
                current.append(character)
        if escaped:
            current.append("\\")
        cells.append("".join(current).strip())
        return cells

    @staticmethod
    def _unsupported_syntax_warnings(lines: list[str]) -> list[DocumentWarning]:
        first_occurrence: dict[str, int] = {}
        for index, raw_line in enumerate(lines):
            stripped = raw_line.strip()
            syntax: str | None = None
            if stripped.startswith(("```", "~~~")):
                syntax = "fenced_code"
            elif stripped.startswith(">"):
                syntax = "block_quote"
            elif _NESTED_LIST.match(raw_line):
                syntax = "nested_list"
            elif _THEMATIC_BREAK.fullmatch(stripped):
                syntax = "thematic_break"
            elif (
                index > 0
                and lines[index - 1].strip()
                and _SETEXT_UNDERLINE.fullmatch(stripped)
            ):
                syntax = "setext_heading"
            if syntax is not None:
                first_occurrence.setdefault(syntax, index + 1)

        return [
            DocumentWarning(
                code="markdown.unsupported_syntax",
                message="Unsupported Markdown syntax was preserved as plain paragraph text",
                details={"syntax": syntax, "line_number": line_number},
            )
            for syntax, line_number in sorted(first_occurrence.items())
        ]
