"""Abstract base classes for Tragaldabas components"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Stage(ABC, Generic[InputT, OutputT]):
    """Abstract base class for all pipeline stages"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable stage name"""
        pass
    
    @property
    @abstractmethod
    def stage_number(self) -> int:
        """Stage number (0-7)"""
        pass
    
    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """Execute the stage"""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: InputT) -> bool:
        """Validate input before processing"""
        pass


class FileParser(ABC):
    """Abstract base class for file parsers"""
    
    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """List of supported file extensions"""
        pass
    
    @abstractmethod
    def parse(self, file_path: str) -> "ReceptionResult":
        """Parse file and return ReceptionResult"""
        pass
    
    @abstractmethod
    def detect_encoding(self, file_path: str) -> str:
        """Detect file encoding"""
        pass


class LLMTask(ABC):
    """Abstract base class for LLM-powered tasks"""
    
    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Prompt template for this task"""
        pass
    
    @abstractmethod
    def build_prompt(self, context: dict) -> str:
        """Build prompt from context"""
        pass
    
    @abstractmethod
    def parse_response(self, response: str) -> dict:
        """Parse LLM response into structured data"""
        pass

