"""File parsers"""

from .base import FileParser
from .excel import ExcelParser
from .csv import CSVParser
from .word import WordParser
from .audio import AudioParser

__all__ = ["FileParser", "ExcelParser", "CSVParser", "WordParser", "AudioParser"]

