"""Pipeline routing: detect input type at ingestion and route to numeric vs narrative pipeline."""

from core.enums import FileType


NARRATIVE_FILE_TYPES = frozenset({
    FileType.AUDIO,
    FileType.WORD_DOCX,
    FileType.MARKDOWN,
    FileType.PLAIN_TEXT,
    FileType.PDF,
})


def is_narrative_file_type(file_type: FileType) -> bool:
    """Route to narrative pipeline: audio, documents, notes. Else numeric (tabular)."""
    return file_type in NARRATIVE_FILE_TYPES
