"""Core enumerations for Tragaldabas"""

from enum import Enum


class FileType(str, Enum):
    """Supported file types"""
    EXCEL_XLSX = "xlsx"
    EXCEL_XLS = "xls"
    CSV = "csv"
    WORD_DOCX = "docx"


class ContentType(str, Enum):
    """Primary content type classification"""
    NARRATIVE = "narrative"
    STRUCTURED = "structured"
    MIXED = "mixed"


class Domain(str, Enum):
    """Business domain classification"""
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    SALES = "sales"
    HR = "hr"
    INVENTORY = "inventory"
    GENERAL = "general"


class DataType(str, Enum):
    """Data type inference"""
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"


class SemanticRole(str, Enum):
    """Semantic role of a column"""
    IDENTIFIER = "identifier"
    DIMENSION = "dimension"
    MEASURE = "measure"
    METADATA = "metadata"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    """Insight severity level"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class VisualizationType(str, Enum):
    """Visualization type for insights"""
    TREND_LINE = "trend_line"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    TABLE = "table"
    METRIC_CALLOUT = "metric_callout"
    NONE = "none"


class ValidationIssueType(str, Enum):
    """Type of validation issue"""
    TYPE_MISMATCH = "type_mismatch"
    NULL_VIOLATION = "null_violation"
    DUPLICATE_KEY = "duplicate_key"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    BUSINESS_RULE = "business_rule"
    OUTLIER = "outlier"


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"

