"""Stage 0: Reception - File parsing and validation"""

from pathlib import Path
from typing import Union

from core.interfaces import Stage
from core.models import ReceptionResult
from core.exceptions import StageError, FileParseError
from .parsers import ExcelParser, CSVParser, WordParser, AudioParser


class Receiver(Stage[str, ReceptionResult]):
    """Stage 0: Reception - Parse and validate input file"""
    
    @property
    def name(self) -> str:
        return "Reception"
    
    @property
    def stage_number(self) -> int:
        return 0
    
    def __init__(self):
        self.parsers = {
            ".xlsx": ExcelParser(),
            ".xls": ExcelParser(),
            ".csv": CSVParser(),
            ".docx": WordParser(),
            ".mp3": AudioParser(),
            ".wav": AudioParser(),
            ".m4a": AudioParser(),
            ".flac": AudioParser(),
            ".ogg": AudioParser(),
            ".webm": AudioParser(),
        }
    
    def validate_input(self, input_data: str) -> bool:
        """Validate file path"""
        if not isinstance(input_data, str):
            return False
        
        path = Path(input_data)
        return path.exists() and path.is_file()
    
    async def execute(self, input_data: str) -> ReceptionResult:
        """Execute reception stage"""
        path = Path(input_data)
        
        # Get file extension
        ext = path.suffix.lower()
        
        if ext not in self.parsers:
            raise StageError(
                self.stage_number,
                f"Unsupported file type: {ext}. Supported: {', '.join(self.parsers.keys())}"
            )
        
        # Parse file
        parser = self.parsers[ext]
        
        try:
            result = parser.parse(str(path))
            return result
        except FileParseError as e:
            raise StageError(self.stage_number, str(e)) from e
        except Exception as e:
            raise StageError(
                self.stage_number,
                f"Unexpected error parsing file: {e}"
            ) from e

