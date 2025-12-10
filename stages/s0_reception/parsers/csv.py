"""CSV file parser"""

import pandas as pd
import csv
from pathlib import Path
from typing import List

from core.models import (
    ReceptionResult, FileMetadata, SheetPreview
)
from core.enums import FileType
from core.exceptions import FileParseError
from .base import FileParser
from utils.encoding import detect_encoding


class CSVParser(FileParser):
    """Parser for CSV files"""
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]
    
    def detect_encoding(self, file_path: str) -> str:
        """Detect CSV file encoding"""
        return detect_encoding(Path(file_path))
    
    def parse(self, file_path: str) -> ReceptionResult:
        """Parse CSV file"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileParseError(f"File not found: {file_path}", file_path)
        
        try:
            encoding = self.detect_encoding(path)
            file_size = path.stat().st_size
            
            # Detect delimiter
            delimiter = self._detect_delimiter(path, encoding)
            
            # Read CSV
            df = pd.read_csv(
                path,
                encoding=encoding,
                delimiter=delimiter,
                header=None,
                dtype=str,
                keep_default_na=False,
                on_bad_lines='skip'
            )
            
            # Generate column letters
            col_letters = self._generate_column_letters(len(df.columns))
            
            # Get preview rows
            preview_rows = df.head(50).values.tolist()
            
            metadata = FileMetadata(
                file_path=str(path.absolute()),
                file_name=path.name,
                file_type=FileType.CSV,
                file_size_bytes=file_size,
                encoding=encoding,
                sheets=[]  # CSV is single sheet
            )
            
            preview = SheetPreview(
                sheet_name="Sheet1",  # Default name for CSV
                row_count=len(df),
                col_count=len(df.columns),
                preview_rows=preview_rows,
                column_letters=col_letters
            )
            
            return ReceptionResult(
                metadata=metadata,
                previews=[preview],
                raw_data={"Sheet1": df}
            )
            
        except Exception as e:
            raise FileParseError(
                f"Failed to parse CSV file: {e}",
                file_path
            ) from e
    
    def _detect_delimiter(self, path: Path, encoding: str) -> str:
        """Detect CSV delimiter"""
        delimiters = [',', '\t', '|', ';', ':']
        
        with open(path, 'r', encoding=encoding) as f:
            sample = f.read(4096)
        
        scores = {}
        for delim in delimiters:
            counts = [line.count(delim) for line in sample.split('\n')[:10] if line.strip()]
            if counts and min(counts) > 0:
                avg = sum(counts) / len(counts)
                variance = sum((c - avg) ** 2 for c in counts) / len(counts)
                scores[delim] = min(counts) if variance < 2 else 0
        
        return max(scores, key=scores.get) if scores else ','
    
    def _generate_column_letters(self, count: int) -> List[str]:
        """Generate Excel-style column letters"""
        letters = []
        for i in range(count):
            result = ""
            n = i
            while n >= 0:
                result = chr(n % 26 + ord('A')) + result
                n = n // 26 - 1
            letters.append(result)
        return letters

