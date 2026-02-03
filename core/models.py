"""Core data models for Tragaldabas pipeline"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime
from .enums import (
    FileType, ContentType, Domain, DataType, SemanticRole,
    Severity, VisualizationType, ValidationIssueType,
    CellRole, InputType, SemanticType
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
    audio_duration_seconds: Optional[float] = None  # For audio
    transcript_language: Optional[str] = None  # For audio transcripts
    transcript_language_confirmed: Optional[bool] = None  # For audio transcripts


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


# ─────────────────────────────────────────────────────────────
# Stage 8: Cell Classification
# ─────────────────────────────────────────────────────────────

class DataValidation(BaseModel):
    """Excel data validation rule"""
    address: Optional[str] = None
    validation_type: str
    operator: Optional[str] = None
    formula1: Optional[str] = None
    formula2: Optional[str] = None
    allow_blank: bool = False
    options: List[str] = []
    error_message: Optional[str] = None
    prompt_title: Optional[str] = None
    prompt_message: Optional[str] = None


class CellFormatting(BaseModel):
    """Simplified formatting metadata"""
    number_format: Optional[str] = None
    font_bold: Optional[bool] = None
    font_italic: Optional[bool] = None
    font_color: Optional[str] = None
    fill_color: Optional[str] = None


class NamedRange(BaseModel):
    name: str
    ref: str


class VBAMacro(BaseModel):
    name: str
    code: str


class ConditionalFormat(BaseModel):
    range: str
    rule: str
    format_type: Optional[str] = None
    format_color: Optional[str] = None
    severity: Optional[str] = None


class PivotTableDefinition(BaseModel):
    name: str
    source_range: str
    rows: List[str] = []
    columns: List[str] = []
    values: List[str] = []
    filters: List[str] = []


class ClassifiedCell(BaseModel):
    address: str
    role: CellRole
    input_type: Optional[InputType] = None
    label: Optional[str] = None
    formula: Optional[str] = None
    value: Any = None
    validation: Optional[DataValidation] = None
    formatting: Optional[CellFormatting] = None
    referenced_by: List[str] = []
    references: List[str] = []


class InputGroup(BaseModel):
    name: str
    cells: List[str] = []


class OutputGroup(BaseModel):
    name: str
    cells: List[str] = []


class SheetSection(BaseModel):
    name: str
    cells: List[str] = []


class SheetClassification(BaseModel):
    name: str
    cells: List[ClassifiedCell] = []
    input_groups: List[InputGroup] = []
    output_groups: List[OutputGroup] = []
    sections: List[SheetSection] = []


class CellClassificationResult(BaseModel):
    sheets: List[SheetClassification] = []
    named_ranges: List[NamedRange] = []
    vba_macros: List[VBAMacro] = []
    data_validations: List[DataValidation] = []
    conditional_formats: List[ConditionalFormat] = []
    pivot_tables: List[PivotTableDefinition] = []


# ─────────────────────────────────────────────────────────────
# Stage 9: Dependency Graph
# ─────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    address: str
    role: CellRole
    formula: Optional[str] = None
    in_degree: int = 0
    out_degree: int = 0
    depth: int = 0
    cluster: Optional[str] = None


class Edge(BaseModel):
    source: str
    target: str
    edge_type: str = "direct"


class CalculationCluster(BaseModel):
    id: str
    inputs: List[str] = []
    outputs: List[str] = []
    intermediates: List[str] = []
    semantic_purpose: Optional[str] = None


class CircularRef(BaseModel):
    cycle: List[str] = []
    ref_type: str = "error"
    max_iterations: Optional[int] = None
    convergence_threshold: Optional[float] = None


class DependencyGraph(BaseModel):
    nodes: Dict[str, GraphNode] = {}
    edges: List[Edge] = []
    execution_order: List[str] = []
    clusters: List[CalculationCluster] = []
    circular_refs: List[CircularRef] = []


# ─────────────────────────────────────────────────────────────
# Stage 10: Business Logic Extraction
# ─────────────────────────────────────────────────────────────

class ParsedFormula(BaseModel):
    raw: str
    ast: Any = None
    functions: List[str] = []
    references: List[str] = []
    constants: List[Any] = []
    semantic_type: Optional[SemanticType] = None


class RuleInput(BaseModel):
    name: str
    data_type: Optional[str] = None
    description: Optional[str] = None


class RuleOutput(BaseModel):
    name: str
    data_type: Optional[str] = None
    description: Optional[str] = None


class LogicRepresentation(BaseModel):
    pseudocode: str = ""
    typescript: str = ""
    validation: str = ""


class TestCase(BaseModel):
    name: str
    inputs: Dict[str, Any] = {}
    expected: Dict[str, Any] = {}


class BusinessRule(BaseModel):
    id: str
    name: str
    description: str
    inputs: List[RuleInput] = []
    outputs: List[RuleOutput] = []
    logic: LogicRepresentation = LogicRepresentation()
    constraints: List[str] = []
    test_cases: List[TestCase] = []


class CalculationUnit(BaseModel):
    id: str
    name: str
    formulas: List[ParsedFormula] = []
    inputs: List[str] = []
    outputs: List[str] = []


class LookupTable(BaseModel):
    name: str
    source_range: str
    key_column: Optional[str] = None
    columns: List[str] = []
    row_count: int = 0


class PivotDefinition(BaseModel):
    source_range: str
    rows: List[str] = []
    columns: List[str] = []
    values: List[str] = []


class UIHint(BaseModel):
    name: str
    condition: str
    action: str
    severity: str = "info"


class UnsupportedFeature(BaseModel):
    feature_type: str
    cell_address: str
    formula: str
    explanation: str
    suggested_fix: str


class LogicExtractionResult(BaseModel):
    business_rules: List[BusinessRule] = []
    calculations: List[CalculationUnit] = []
    lookup_tables: List[LookupTable] = []
    pivot_definitions: List[PivotDefinition] = []
    ui_hints: List[UIHint] = []
    unsupported_features: List[UnsupportedFeature] = []
    test_suite: List[TestCase] = []


class AppGenerationContext(BaseModel):
    cell_classification: CellClassificationResult
    logic_extraction: LogicExtractionResult
    dependency_graph: DependencyGraph


# ─────────────────────────────────────────────────────────────
# Stage 11: Code Generation
# ─────────────────────────────────────────────────────────────

class GeneratedProject(BaseModel):
    files: Dict[str, str] = {}
    dependencies: Dict[str, str] = {}
    prisma_schema: str = ""
    test_suite: List[TestCase] = []


# ─────────────────────────────────────────────────────────────
# Stage 12: Scaffold & Deploy
# ─────────────────────────────────────────────────────────────

class TestFailure(BaseModel):
    name: str
    message: str


class TestResults(BaseModel):
    passed: int = 0
    failed: int = 0
    failures: List[TestFailure] = []


class GenerationReport(BaseModel):
    total_inputs: int = 0
    total_outputs: int = 0
    business_rules: int = 0
    unsupported_features: List[UnsupportedFeature] = []
    manual_review_required: List[str] = []


class ScaffoldResult(BaseModel):
    project_path: str
    github_url: str
    deployment_url: str
    database_url: str
    test_results: TestResults
    generation_report: GenerationReport

