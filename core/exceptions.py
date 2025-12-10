"""Custom exceptions for Tragaldabas"""


class TragaldabasError(Exception):
    """Base exception for all Tragaldabas errors"""
    pass


class PipelineError(TragaldabasError):
    """Error in pipeline execution"""
    def __init__(self, message: str, stage: int = None):
        super().__init__(message)
        self.stage = stage


class StageError(TragaldabasError):
    """Error in a specific stage"""
    def __init__(self, stage: int, message: str):
        super().__init__(f"Stage {stage}: {message}")
        self.stage = stage
        self.message = message


class LLMError(TragaldabasError):
    """Error in LLM communication"""
    def __init__(self, message: str, provider: str = None, retries: int = 0):
        super().__init__(message)
        self.provider = provider
        self.retries = retries


class ValidationError(TragaldabasError):
    """Data validation error"""
    def __init__(self, message: str, row: int = None, column: str = None):
        super().__init__(message)
        self.row = row
        self.column = column


class FileParseError(TragaldabasError):
    """Error parsing file"""
    def __init__(self, message: str, file_path: str = None):
        super().__init__(message)
        self.file_path = file_path


class DatabaseError(TragaldabasError):
    """Database operation error"""
    pass

