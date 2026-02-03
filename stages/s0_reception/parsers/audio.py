"""Audio file parser with transcription."""

from pathlib import Path
from typing import List

from core.models import ReceptionResult, FileMetadata, SheetPreview
from core.enums import FileType
from core.exceptions import FileParseError
from config import settings
from .base import FileParser


class AudioParser(FileParser):
    """Parser for audio files (transcribes to text)."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm"]

    def detect_encoding(self, file_path: str) -> str:
        return "binary"

    def parse(self, file_path: str) -> ReceptionResult:
        path = Path(file_path)
        if not path.exists():
            raise FileParseError(f"File not found: {file_path}", file_path)

        if not settings.OPENAI_API_KEY:
            raise FileParseError(
                "OPENAI_API_KEY is required to transcribe audio files.",
                file_path,
            )

        try:
            from openai import OpenAI
        except ImportError:
            raise FileParseError(
                "openai not installed. Install with: pip install openai",
                file_path,
            )

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            with open(path, "rb") as audio_file:
                request = {
                    "model": settings.AUDIO_TRANSCRIPTION_MODEL,
                    "file": audio_file,
                }
                if settings.AUDIO_TRANSCRIPTION_LANGUAGE:
                    request["language"] = settings.AUDIO_TRANSCRIPTION_LANGUAGE
                response = client.audio.transcriptions.create(**request)
            transcript = (response.text or "").strip()
            language = getattr(response, "language", None)

            lines = [line for line in transcript.splitlines() if line.strip()]
            preview_rows = [[line] for line in lines[:50]]

            metadata = FileMetadata(
                file_path=str(path.absolute()),
                file_name=path.name,
                file_type=FileType.AUDIO,
                file_size_bytes=path.stat().st_size,
                encoding=None,
                transcript_language=language,
                transcript_language_confirmed=False,
            )

            preview = SheetPreview(
                sheet_name="Transcript",
                row_count=len(lines),
                col_count=1,
                preview_rows=preview_rows,
                column_letters=["A"],
            )

            return ReceptionResult(
                metadata=metadata,
                previews=[preview],
                raw_data={"Transcript": transcript},
            )
        except FileParseError:
            raise
        except Exception as e:
            raise FileParseError(f"Failed to transcribe audio: {e}", file_path) from e
