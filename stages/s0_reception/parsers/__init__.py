"""File parsers"""

from .base import FileParser
from .excel import ExcelParser
from .csv import CSVParser
from .word import WordParser
from .text import TextParser, MarkdownParser
from .audio import AudioParser

__all__ = [
    "FileParser",
    "ExcelParser",
    "CSVParser",
    "WordParser",
    "TextParser",
    "MarkdownParser",
    "AudioParser",
]

