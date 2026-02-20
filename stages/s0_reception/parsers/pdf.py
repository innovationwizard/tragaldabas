"""PDF parser with layout-aware extraction. Uses unstructured.io when available."""

from pathlib import Path
from typing import List

from core.models import ReceptionResult, FileMetadata, SheetPreview
from core.enums import FileType
from core.exceptions import FileParseError
from .base import FileParser


class PDFParser(FileParser):
    """Parser for PDF files. Uses unstructured.io for layout-aware chunking when available."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    def detect_encoding(self, file_path: str) -> str:
        return "binary"

    def _extract_with_unstructured(self, path: Path) -> str:
        """Extract text using unstructured.io (layout-aware, best quality)."""
        try:
            from unstructured.partition.auto import partition

            elements = partition(filename=str(path), strategy="fast")
            parts = []
            for el in elements:
                text = getattr(el, "text", None) or str(el)
                if text and text.strip():
                    parts.append(text.strip())
            return "\n\n".join(parts) if parts else ""
        except ImportError:
            raise FileParseError(
                "unstructured not installed. Install with: pip install 'unstructured[pdf]'",
                str(path),
            )
        except Exception as e:
            raise FileParseError(f"unstructured PDF extraction failed: {e}", str(path)) from e

    def _extract_with_pypdf(self, path: Path) -> str:
        """Fallback: basic text extraction with pypdf."""
        try:
            from pypdf import PdfReader

            reader = PdfReader(path)
            parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text and text.strip():
                    parts.append(text.strip())
            return "\n\n".join(parts) if parts else ""
        except ImportError:
            raise FileParseError(
                "pypdf not installed. Install with: pip install pypdf",
                str(path),
            )
        except Exception as e:
            raise FileParseError(f"pypdf extraction failed: {e}", str(path)) from e

    def parse(self, file_path: str) -> ReceptionResult:
        path = Path(file_path)
        if not path.exists():
            raise FileParseError(f"File not found: {file_path}", file_path)

        full_text = ""
        try:
            full_text = self._extract_with_unstructured(path)
        except (FileParseError, ImportError, Exception):
            try:
                full_text = self._extract_with_pypdf(path)
            except FileParseError:
                raise
            except Exception as e:
                raise FileParseError(f"PDF extraction failed: {e}", file_path) from e

        if not full_text.strip():
            full_text = "(No text extracted from PDF)"

        lines = [l.strip() for l in full_text.splitlines() if l.strip()]
        preview_rows = [[line] for line in lines[:50]]

        metadata = FileMetadata(
            file_path=str(path.absolute()),
            file_name=path.name,
            file_type=FileType.PDF,
            file_size_bytes=path.stat().st_size,
            encoding=None,
        )

        preview = SheetPreview(
            sheet_name="Document",
            row_count=len(lines),
            col_count=1,
            preview_rows=preview_rows,
            column_letters=["A"],
        )

        return ReceptionResult(
            metadata=metadata,
            previews=[preview],
            raw_data={"Document": full_text},
        )
