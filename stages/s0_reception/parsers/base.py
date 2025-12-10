"""Base file parser"""

from abc import ABC, abstractmethod
from pathlib import Path
from core.interfaces import FileParser as IFileParser
from core.models import ReceptionResult


class FileParser(IFileParser, ABC):
    """Abstract base class for file parsers"""
    
    @abstractmethod
    def parse(self, file_path: str) -> ReceptionResult:
        """Parse file and return ReceptionResult"""
        pass
    
    @abstractmethod
    def detect_encoding(self, file_path: str) -> str:
        """Detect file encoding"""
        pass

