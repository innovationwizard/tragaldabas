"""Core data models for Tragaldabas pipeline"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from .enums import (
    FileType, ContentType, Domain, DataType, SemanticRole,
    Severity, VisualizationType, ValidationIssueType
)


# ─────────────────────────────────────────────────────────────
# Stage 0: Reception
# ─────────────────────────────────────────────────────────────

class FileMetadata(BaseModel):
    """Output of Stage 0"""
    file_path: str
    file_name: str
    file_type: FileType
    file_size_bytes: int
    encoding: Optional[str] = None
    sheets: list[str] = []  # For Excel
    page_count: Optional[int] = None  # For Word


class SheetPreview(BaseModel):
    """Raw preview of a sheet/document"""
    sheet_name: str
    row_count: int
    col_count: int
    preview_rows: list[list[Any]]  # First N rows
    column_letters: list[str]


class ReceptionResult(BaseModel):
    """Complete Stage 0 output"""
    metadata: FileMetadata
    previews: list[SheetPreview]
    raw_data: dict[str, Any]  # sheet_name -> DataFrame (will be Any for now)


# ─────────────────────────────────────────────────────────────
# Stage 1: Classification
# ─────────────────────────────────────────────────────────────

class ContentClassification(BaseModel):
    """Output of Stage 1"""
    primary_type: ContentType
    domain: Domain
    entity_name: Optional[str] = None
    time_period_start: Optional[datetime] = None
    time_period_end: Optional[datetime] = None
    confidence: float = Field(ge=0, le=1)
    user_confirmed: bool = False


# ─────────────────────────────────────────────────────────────
# Stage 2: Structure Inference
# ─────────────────────────────────────────────────────────────

class ColumnInference(BaseModel):
    """Inferred column metadata"""
    original_name: str
    canonical_name: str
    data_type: DataType
    semantic_role: SemanticRole
    sample_values: list[Any] = []
    null_percentage: float = 0.0
    unique_count: int = 0


class SheetRelationship(BaseModel):
    """Relationship between sheets"""
    sheet_a: str
    sheet_b: str
    shared_columns: list[str] = []
    relationship_type: str = "unknown"  # foreign_key, lookup, etc.


class SheetStructure(BaseModel):
    """Structure of a single sheet"""
    sheet_name: str
    columns: list[ColumnInference] = []
    grain_description: str = ""
    row_count: int = 0
    primary_key_candidates: list[str] = []


class StructureResult(BaseModel):
    """Complete Stage 2 output"""
    sheets: list[SheetStructure] = []
    sheet_relationships: list[SheetRelationship] = []


# ─────────────────────────────────────────────────────────────
# Stage 3: Data Archaeology
# ─────────────────────────────────────────────────────────────

class ArchaeologyMap(BaseModel):
    """Extraction coordinates for a sheet"""
    sheet_name: str
    header_row: Optional[int] = None
    data_start_row: int = 0
    data_end_row: Optional[int] = None
    noise_rows: list[int] = []
    noise_columns: list[str] = []
    total_rows: list[int] = []
    has_header: bool = True
    confidence: float = Field(ge=0, le=1, default=0.0)
    llm_reasoning: str = ""


class ArchaeologyResult(BaseModel):
    """Complete Stage 3 output"""
    maps: list[ArchaeologyMap] = []
    cleaned_data: dict[str, Any] = {}  # sheet_name -> DataFrame


# ─────────────────────────────────────────────────────────────
# Stage 4: Cross-Sheet Reconciliation
# ─────────────────────────────────────────────────────────────

class ColumnMapping(BaseModel):
    """Mapping from sheet column to canonical"""
    sheet_name: str
    original_column: str
    canonical_column: str
    confidence: float = Field(ge=0, le=1)
    user_confirmed: bool = False


class CanonicalSchema(BaseModel):
    """Unified schema across sheets"""
    columns: list[ColumnInference] = []
    source_sheets: list[str] = []


class ReconciliationResult(BaseModel):
    """Complete Stage 4 output"""
    canonical_schema: CanonicalSchema
    mappings: list[ColumnMapping] = []
    unified_data: Any = None  # DataFrame


# ─────────────────────────────────────────────────────────────
# Stage 5: Schema & ETL
# ─────────────────────────────────────────────────────────────

class PostgresColumn(BaseModel):
    """Postgres column definition"""
    name: str
    pg_type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None
    default: Optional[str] = None


class PostgresTable(BaseModel):
    """Postgres table definition"""
    table_name: str
    columns: list[PostgresColumn] = []
    indexes: list[str] = []


class ValidationIssue(BaseModel):
    """Single validation failure"""
    row_number: int
    column: str
    value: Any
    issue_type: ValidationIssueType
    message: str


class ETLResult(BaseModel):
    """Complete Stage 5 output"""
    table_schema: PostgresTable  # Renamed from 'schema' to avoid shadowing BaseModel.schema
    schema_sql: str = ""
    data_file_path: str = ""
    load_sql: str = ""
    validation_issues: list[ValidationIssue] = []
    rows_valid: int = 0
    rows_invalid: int = 0


# ─────────────────────────────────────────────────────────────
# Stage 6: Analysis
# ─────────────────────────────────────────────────────────────

class Evidence(BaseModel):
    """Supporting data for an insight"""
    metric: str
    value: float
    comparison: Optional[str] = None
    delta: Optional[float] = None
    delta_percent: Optional[float] = None


class Insight(BaseModel):
    """Single analytical insight"""
    id: str
    headline: str = Field(max_length=100)
    detail: str = Field(max_length=300)
    evidence: Evidence
    implication: str
    severity: Severity
    visualization_hint: VisualizationType
    included: bool = True  # Passes relevancy filter


class AnalysisResult(BaseModel):
    """Complete Stage 6 output"""
    domain: Domain
    metrics_computed: list[str] = []
    patterns_detected: list[str] = []
    insights: list[Insight] = []


# ─────────────────────────────────────────────────────────────
# Stage 7: Output
# ─────────────────────────────────────────────────────────────

class OutputResult(BaseModel):
    """Complete Stage 7 output"""
    text_file_path: str = ""
    markdown_file_path: str = ""
    pptx_file_path: str = ""
    pdf_file_path: Optional[str] = None
    slide_count: int = 0
    insight_count: int = 0

