"""Plain text and Markdown parsers.

High-quality parsing: UTF-8 with BOM/fallback detection, structure preservation,
and consistent output format for downstream analysis.
"""

from pathlib import Path
from typing import List

from core.models import ReceptionResult, FileMetadata, SheetPreview
from core.enums import FileType
from core.exceptions import FileParseError
from .base import FileParser


def _detect_encoding(file_path: Path) -> str:
    """Detect file encoding. Try UTF-8 first, use chardet if available for robustness."""
    try:
        # Try UTF-8 first (most common for .md and .txt)
        raw = file_path.read_bytes()
        raw[:65536].decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        import chardet
        result = chardet.detect(raw[:65536])
        enc = (result.get("encoding") or "utf-8").lower()
        if enc.startswith("utf-8") or enc in ("ascii", "iso-8859-1", "utf-8"):
            return "utf-8" if enc.startswith("utf-8") or enc == "ascii" else enc
        return enc or "utf-8"
    except Exception:
        return "utf-8"


def _read_text(file_path: Path, encoding: str) -> str:
    """Read file with encoding fallback."""
    errors = "replace"  # Replace invalid chars instead of failing
    try:
        return file_path.read_text(encoding=encoding, errors=errors)
    except UnicodeDecodeError:
        if encoding != "utf-8":
            return file_path.read_text(encoding="utf-8", errors=errors)
        return file_path.read_bytes().decode("utf-8", errors=errors)


def _parse_content(content: str, is_markdown: bool) -> tuple[str, List[List[str]]]:
    """
    Parse content into full text and preview rows.
    Preserves structure: paragraphs for .txt, sections for .md.
    """
    lines = content.splitlines()
    if not lines:
        return "", [[]]

    # Build preview rows (max 50 rows, each row as one cell)
    preview_rows: List[List[str]] = []
    for line in lines[:50]:
        line = line.strip()
        if line or not is_markdown:  # Include blank lines for .txt structure
            preview_rows.append([line[:500] if line else ""])  # Truncate long lines

    if not preview_rows:
        preview_rows = [[]]

    full_text = content
    return full_text, preview_rows


class TextParser(FileParser):
    """Parser for plain text (.txt)"""

    @property
    def supported_extensions(self) -> List[str]:
        return [".txt"]

    def detect_encoding(self, file_path: str) -> str:
        return _detect_encoding(Path(file_path))

    def parse(self, file_path: str) -> ReceptionResult:
        path = Path(file_path)
        if not path.exists():
            raise FileParseError(f"File not found: {file_path}", file_path)

        encoding = _detect_encoding(path)
        content = _read_text(path, encoding)
        full_text, preview_rows = _parse_content(content, is_markdown=False)

        metadata = FileMetadata(
            file_path=str(path.absolute()),
            file_name=path.name,
            file_type=FileType.PLAIN_TEXT,
            file_size_bytes=path.stat().st_size,
            encoding=encoding,
        )

        preview = SheetPreview(
            sheet_name="Document",
            row_count=len(preview_rows),
            col_count=1,
            preview_rows=preview_rows,
            column_letters=["A"],
        )

        return ReceptionResult(
            metadata=metadata,
            previews=[preview],
            raw_data={"Document": full_text},
        )


class MarkdownParser(FileParser):
    """Parser for Markdown (.md)"""

    @property
    def supported_extensions(self) -> List[str]:
        return [".md"]

    def detect_encoding(self, file_path: str) -> str:
        return _detect_encoding(Path(file_path))

    def parse(self, file_path: str) -> ReceptionResult:
        path = Path(file_path)
        if not path.exists():
            raise FileParseError(f"File not found: {file_path}", file_path)

        encoding = _detect_encoding(path)
        content = _read_text(path, encoding)
        full_text, preview_rows = _parse_content(content, is_markdown=True)

        metadata = FileMetadata(
            file_path=str(path.absolute()),
            file_name=path.name,
            file_type=FileType.MARKDOWN,
            file_size_bytes=path.stat().st_size,
            encoding=encoding,
        )

        preview = SheetPreview(
            sheet_name="Document",
            row_count=len(preview_rows),
            col_count=1,
            preview_rows=preview_rows,
            column_letters=["A"],
        )

        return ReceptionResult(
            metadata=metadata,
            previews=[preview],
            raw_data={"Document": full_text},
        )
