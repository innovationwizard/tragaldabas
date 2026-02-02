# Tragaldabas - Module Architecture

## 1. Directory Structure

```
tragaldabas/
├── main.py                     # CLI entry point
├── config.py                   # Configuration & environment
├── orchestrator.py             # Pipeline coordinator
│
├── core/                       # Core abstractions
│   ├── __init__.py
│   ├── models.py               # Pydantic data models
│   ├── enums.py                # Enumerations
│   ├── exceptions.py           # Custom exceptions
│   └── interfaces.py           # Abstract base classes
│
├── stages/                     # Pipeline stages
│   ├── __init__.py
│   ├── s0_reception/
│   │   ├── __init__.py
│   │   ├── receiver.py         # Main stage coordinator
│   │   ├── validators.py       # File validation
│   │   └── parsers/
│   │       ├── __init__.py
│   │       ├── base.py         # Abstract parser
│   │       ├── excel.py        # Excel parser
│   │       ├── word.py         # Word parser
│   │       └── csv.py          # CSV parser
│   │
│   ├── s1_classification/
│   │   ├── __init__.py
│   │   ├── classifier.py       # Main stage coordinator
│   │   ├── domain_detector.py  # Domain classification
│   │   └── content_analyzer.py # Narrative vs structured
│   │
│   ├── s2_structure/
│   │   ├── __init__.py
│   │   ├── inferrer.py         # Main stage coordinator
│   │   ├── tabular.py          # Structured data inference
│   │   └── narrative.py        # Document structure inference
│   │
│   ├── s3_archaeology/
│   │   ├── __init__.py
│   │   ├── archaeologist.py    # Main stage coordinator
│   │   ├── boundary_detector.py# Find data start/end
│   │   ├── noise_filter.py     # Identify noise rows/cols
│   │   └── normalizer.py       # Column name normalization
│   │
│   ├── s4_reconciliation/
│   │   ├── __init__.py
│   │   ├── reconciler.py       # Main stage coordinator
│   │   ├── schema_builder.py   # Canonical schema construction
│   │   └── mapper.py           # Column mapping
│   │
│   ├── s5_etl/
│   │   ├── __init__.py
│   │   ├── etl_manager.py      # Main stage coordinator
│   │   ├── schema_designer.py  # Postgres schema design
│   │   ├── transformer.py      # Data transformations
│   │   ├── validator.py        # Data validation
│   │   └── persister.py        # Database persistence
│   │
│   ├── s6_analysis/
│   │   ├── __init__.py
│   │   ├── analyzer.py         # Main stage coordinator
│   │   ├── metrics.py          # KPI calculations
│   │   ├── patterns.py         # Pattern detection
│   │   └── insights.py         # Insight generation & filtering
│   │
│   ├── s7_output/
│   │   ├── __init__.py
│   │   ├── output_manager.py   # Main stage coordinator
│   │   ├── text_generator.py   # Text/markdown output
│   │   └── slide_builder.py    # PowerPoint generation
│   │
│   ├── s8_cell_classification/
│   │   ├── __init__.py
│   │   └── classifier.py       # Cell role classification
│   │
│   ├── s9_dependency_graph/
│   │   ├── __init__.py
│   │   └── builder.py          # Dependency graph construction
│   │
│   ├── s10_logic_extraction/
│   │   ├── __init__.py
│   │   └── extractor.py        # Formula parsing + rule extraction
│   │
│   ├── s11_code_generation/
│   │   ├── __init__.py
│   │   └── generator.py        # App code generation
│   │
│   └── s12_scaffold_deploy/
│       ├── __init__.py
│       └── scaffolder.py       # Local scaffold output
│
├── llm/                        # LLM integration
│   ├── __init__.py
│   ├── client.py               # Claude API client
│   ├── prompts/                # Prompt templates
│   │   ├── __init__.py
│   │   ├── classification.py
│   │   ├── archaeology.py
│   │   ├── analysis.py
│   │   └── insights.py
│   └── parsers.py              # LLM response parsing
│
├── db/                         # Database layer
│   ├── __init__.py
│   ├── connection.py           # Connection management
│   ├── schema.py               # Schema operations
│   └── loader.py               # Data loading
│
├── ui/                         # User interaction
│   ├── __init__.py
│   ├── progress.py             # Progress display
│   ├── prompts.py              # User prompts (Y/N)
│   └── reports.py              # Validation reports
│
├── utils/                      # Shared utilities
│   ├── __init__.py
│   ├── encoding.py             # Encoding detection
│   ├── fuzzy.py                # Fuzzy matching
│   ├── synonyms.py             # Synonym dictionary
│   └── formatting.py           # Text formatting
│
├── output/                     # Generated files (gitignored)
│   ├── schemas/
│   ├── data/
│   ├── insights/
│   └── presentations/
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures
    ├── fixtures/               # Test files
    │   ├── clean_excel.xlsx
    │   ├── dirty_excel.xlsx
    │   ├── multi_sheet.xlsx
    │   └── ...
    ├── unit/
    │   ├── test_parsers.py
    │   ├── test_archaeology.py
    │   └── ...
    └── integration/
        ├── test_pipeline.py
        └── ...
```

---

## 2. Core Models

```python
# core/models.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

# ─────────────────────────────────────────────────────────────
# Stage 0: Reception
# ─────────────────────────────────────────────────────────────

class FileMetadata(BaseModel):
    """Output of Stage 0"""
    file_path: str
    file_name: str
    file_type: "FileType"
    file_size_bytes: int
    encoding: Optional[str]
    sheets: list[str] = []  # For Excel
    page_count: Optional[int] = None  # For Word

class SheetPreview(BaseModel):
    """Raw preview of a sheet/document"""
    sheet_name: str
    row_count: int
    col_count: int
    preview_rows: list[list[any]]  # First N rows
    column_letters: list[str]

class ReceptionResult(BaseModel):
    """Complete Stage 0 output"""
    metadata: FileMetadata
    previews: list[SheetPreview]
    raw_data: dict[str, "DataFrame"]  # sheet_name -> data

# ─────────────────────────────────────────────────────────────
# Stage 1: Classification
# ─────────────────────────────────────────────────────────────

class ContentClassification(BaseModel):
    """Output of Stage 1"""
    primary_type: "ContentType"
    domain: "Domain"
    entity_name: Optional[str]
    time_period_start: Optional[datetime]
    time_period_end: Optional[datetime]
    confidence: float = Field(ge=0, le=1)
    user_confirmed: bool = False

# ─────────────────────────────────────────────────────────────
# Stage 2: Structure Inference
# ─────────────────────────────────────────────────────────────

class ColumnInference(BaseModel):
    """Inferred column metadata"""
    original_name: str
    canonical_name: str
    data_type: "DataType"
    semantic_role: "SemanticRole"
    sample_values: list[any]
    null_percentage: float
    unique_count: int

class SheetStructure(BaseModel):
    """Structure of a single sheet"""
    sheet_name: str
    columns: list[ColumnInference]
    grain_description: str
    row_count: int
    primary_key_candidates: list[str]

class StructureResult(BaseModel):
    """Complete Stage 2 output"""
    sheets: list[SheetStructure]
    sheet_relationships: list["SheetRelationship"]

# ─────────────────────────────────────────────────────────────
# Stage 3: Data Archaeology
# ─────────────────────────────────────────────────────────────

class ArchaeologyMap(BaseModel):
    """Extraction coordinates for a sheet"""
    sheet_name: str
    header_row: Optional[int]
    data_start_row: int
    data_end_row: Optional[int]
    noise_rows: list[int] = []
    noise_columns: list[str] = []
    total_rows: list[int] = []
    has_header: bool = True

class ArchaeologyResult(BaseModel):
    """Complete Stage 3 output"""
    maps: list[ArchaeologyMap]
    cleaned_data: dict[str, "DataFrame"]

# ─────────────────────────────────────────────────────────────
# Stage 4: Cross-Sheet Reconciliation
# ─────────────────────────────────────────────────────────────

class ColumnMapping(BaseModel):
    """Mapping from sheet column to canonical"""
    sheet_name: str
    original_column: str
    canonical_column: str
    confidence: float
    user_confirmed: bool = False

class CanonicalSchema(BaseModel):
    """Unified schema across sheets"""
    columns: list[ColumnInference]
    source_sheets: list[str]

class ReconciliationResult(BaseModel):
    """Complete Stage 4 output"""
    canonical_schema: CanonicalSchema
    mappings: list[ColumnMapping]
    unified_data: "DataFrame"

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
    columns: list[PostgresColumn]
    indexes: list[str] = []

class ValidationIssue(BaseModel):
    """Single validation failure"""
    row_number: int
    column: str
    value: any
    issue_type: "ValidationIssueType"
    message: str

class ETLResult(BaseModel):
    """Complete Stage 5 output"""
    schema: PostgresTable
    schema_sql: str
    data_file_path: str
    load_sql: str
    validation_issues: list[ValidationIssue]
    rows_valid: int
    rows_invalid: int

# ─────────────────────────────────────────────────────────────
# Stage 6: Analysis
# ─────────────────────────────────────────────────────────────

class Evidence(BaseModel):
    """Supporting data for an insight"""
    metric: str
    value: float
    comparison: Optional[str]
    delta: Optional[float]
    delta_percent: Optional[float]

class Insight(BaseModel):
    """Single analytical insight"""
    id: str
    headline: str = Field(max_length=100)
    detail: str = Field(max_length=300)
    evidence: Evidence
    implication: str
    severity: "Severity"
    visualization_hint: "VisualizationType"
    included: bool = True  # Passes relevancy filter

class AnalysisResult(BaseModel):
    """Complete Stage 6 output"""
    domain: "Domain"
    metrics_computed: list[str]
    patterns_detected: list[str]
    insights: list[Insight]

# ─────────────────────────────────────────────────────────────
# Stage 7: Output
# ─────────────────────────────────────────────────────────────

class OutputResult(BaseModel):
    """Complete Stage 7 output"""
    text_file_path: str
    markdown_file_path: str
    pptx_file_path: str
    pdf_file_path: Optional[str]
    slide_count: int
    insight_count: int
```

---

## 3. Core Enumerations

```python
# core/enums.py

from enum import Enum, auto

class FileType(str, Enum):
    EXCEL_XLSX = "xlsx"
    EXCEL_XLS = "xls"
    CSV = "csv"
    WORD_DOCX = "docx"

class ContentType(str, Enum):
    NARRATIVE = "narrative"
    STRUCTURED = "structured"
    MIXED = "mixed"

class Domain(str, Enum):
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    SALES = "sales"
    HR = "hr"
    INVENTORY = "inventory"
    GENERAL = "general"

class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"

class SemanticRole(str, Enum):
    IDENTIFIER = "identifier"
    DIMENSION = "dimension"
    MEASURE = "measure"
    METADATA = "metadata"
    UNKNOWN = "unknown"

class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class VisualizationType(str, Enum):
    TREND_LINE = "trend_line"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    TABLE = "table"
    METRIC_CALLOUT = "metric_callout"
    NONE = "none"

class ValidationIssueType(str, Enum):
    TYPE_MISMATCH = "type_mismatch"
    NULL_VIOLATION = "null_violation"
    DUPLICATE_KEY = "duplicate_key"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    BUSINESS_RULE = "business_rule"
    OUTLIER = "outlier"
```

---

## 4. Core Interfaces

```python
# core/interfaces.py

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
        pass
    
    @abstractmethod
    def parse(self, file_path: str) -> "ReceptionResult":
        pass
    
    @abstractmethod
    def detect_encoding(self, file_path: str) -> str:
        pass


class LLMTask(ABC):
    """Abstract base class for LLM-powered tasks"""
    
    @property
    @abstractmethod
    def prompt_template(self) -> str:
        pass
    
    @abstractmethod
    def build_prompt(self, context: dict) -> str:
        pass
    
    @abstractmethod
    def parse_response(self, response: str) -> dict:
        pass
```

---

## 5. Orchestrator

```python
# orchestrator.py

from dataclasses import dataclass
from typing import Optional
import asyncio

from core.models import *
from core.exceptions import PipelineError, StageError
from stages.s0_reception import Receiver
from stages.s1_classification import Classifier
from stages.s2_structure import StructureInferrer
from stages.s3_archaeology import Archaeologist
from stages.s4_reconciliation import Reconciler
from stages.s5_etl import ETLManager
from stages.s6_analysis import Analyzer
from stages.s7_output import OutputManager
from stages.s8_cell_classification import CellClassifier
from stages.s9_dependency_graph import DependencyGraphBuilder
from stages.s10_logic_extraction import LogicExtractor
from stages.s11_code_generation import CodeGenerator
from stages.s12_scaffold_deploy import Scaffolder
from ui.progress import ProgressTracker
from ui.prompts import UserPrompt


@dataclass
class PipelineContext:
    """Shared context passed through pipeline"""
    file_path: str
    reception: Optional[ReceptionResult] = None
    classification: Optional[ContentClassification] = None
    structure: Optional[StructureResult] = None
    archaeology: Optional[ArchaeologyResult] = None
    reconciliation: Optional[ReconciliationResult] = None
    etl: Optional[ETLResult] = None
    analysis: Optional[AnalysisResult] = None
    output: Optional[OutputResult] = None


class Orchestrator:
    """
    Pipeline coordinator.
    Executes stages in sequence, manages context, handles user interaction.
    """
    
    def __init__(
        self,
        progress: ProgressTracker,
        prompt: UserPrompt,
        db_connection_string: Optional[str] = None
    ):
        self.progress = progress
        self.prompt = prompt
        self.db_connection_string = db_connection_string
        
        # Initialize stages
        self.stages = {
            0: Receiver(),
            1: Classifier(),
            2: StructureInferrer(),
            3: Archaeologist(),
            4: Reconciler(),
            5: ETLManager(db_connection_string),
            6: Analyzer(),
            7: OutputManager(),
        }
    
    async def run(self, file_path: str) -> PipelineContext:
        """Execute full pipeline"""
        ctx = PipelineContext(file_path=file_path)
        
        try:
            # Stage 0: Reception
            ctx.reception = await self._execute_stage(0, file_path)
            
            # Stage 1: Classification
            ctx.classification = await self._execute_stage(1, ctx.reception)
            ctx.classification = await self._confirm_classification(ctx.classification)
            
            # Branch based on content type
            if ctx.classification.primary_type == ContentType.NARRATIVE:
                ctx = await self._narrative_path(ctx)
            else:
                ctx = await self._structured_path(ctx)
            
            # Stage 6: Analysis
            ctx.analysis = await self._execute_stage(6, {
                "data": ctx.etl or ctx.reconciliation,
                "domain": ctx.classification.domain
            })
            
            # Stage 7: Output
            ctx.output = await self._execute_stage(7, ctx.analysis)
            
            self.progress.complete()
            return ctx
            
        except StageError as e:
            self.progress.fail(e.stage, str(e))
            raise PipelineError(f"Pipeline failed at stage {e.stage}: {e}")
    
    async def _structured_path(self, ctx: PipelineContext) -> PipelineContext:
        """Process structured data (Excel, CSV)"""
        
        # Stage 2: Structure Inference
        ctx.structure = await self._execute_stage(2, ctx.reception)
        
        # Stage 3: Archaeology
        ctx.archaeology = await self._execute_stage(3, {
            "reception": ctx.reception,
            "structure": ctx.structure
        })
        ctx.archaeology = await self._confirm_archaeology(ctx.archaeology)
        
        # Stage 4: Reconciliation (if multi-sheet)
        if len(ctx.reception.previews) > 1:
            ctx.reconciliation = await self._execute_stage(4, ctx.archaeology)
            ctx.reconciliation = await self._confirm_mappings(ctx.reconciliation)
        
        # Stage 5: ETL
        etl_input = ctx.reconciliation or ctx.archaeology
        ctx.etl = await self._execute_stage(5, etl_input)
        ctx.etl = await self._confirm_validation(ctx.etl)
        
        return ctx
    
    async def _narrative_path(self, ctx: PipelineContext) -> PipelineContext:
        """Process narrative documents (Word)"""
        
        # Stage 2: Document structure
        ctx.structure = await self._execute_stage(2, ctx.reception)
        
        # Skip stages 3-4 (not applicable)
        # Stage 5: Extract facts, persist as structured
        ctx.etl = await self._execute_stage(5, {
            "reception": ctx.reception,
            "structure": ctx.structure,
            "narrative_mode": True
        })
        
        return ctx
    
    async def _execute_stage(self, stage_num: int, input_data) -> any:
        """Execute a single stage with progress tracking"""
        stage = self.stages[stage_num]
        
        self.progress.start_stage(stage_num, stage.name)
        
        if not stage.validate_input(input_data):
            raise StageError(stage_num, "Invalid input")
        
        result = await stage.execute(input_data)
        
        self.progress.complete_stage(stage_num)
        return result
    
    async def _confirm_classification(
        self, 
        classification: ContentClassification
    ) -> ContentClassification:
        """User checkpoint: confirm domain if low confidence"""
        if classification.confidence < 0.7:
            confirmed = await self.prompt.yes_no(
                f"I detected this as {classification.domain.value}. Correct?"
            )
            if not confirmed:
                new_domain = await self.prompt.select_domain()
                classification.domain = new_domain
            classification.user_confirmed = True
        return classification
    
    async def _confirm_archaeology(
        self,
        archaeology: ArchaeologyResult
    ) -> ArchaeologyResult:
        """User checkpoint: confirm header inference"""
        for arch_map in archaeology.maps:
            if not arch_map.has_header:
                confirmed = await self.prompt.yes_no(
                    f"No headers found in '{arch_map.sheet_name}'. "
                    "Should I infer column names from data?"
                )
                if not confirmed:
                    # User will provide headers manually
                    arch_map.header_row = await self.prompt.get_header_row()
        return archaeology
    
    async def _confirm_mappings(
        self,
        reconciliation: ReconciliationResult
    ) -> ReconciliationResult:
        """User checkpoint: confirm ambiguous column mappings"""
        for mapping in reconciliation.mappings:
            if mapping.confidence < 0.8 and not mapping.user_confirmed:
                confirmed = await self.prompt.yes_no(
                    f"Is '{mapping.original_column}' in sheet "
                    f"'{mapping.sheet_name}' the same as "
                    f"'{mapping.canonical_column}'?"
                )
                mapping.user_confirmed = True
                if not confirmed:
                    new_canonical = await self.prompt.select_canonical(
                        reconciliation.canonical_schema.columns
                    )
                    mapping.canonical_column = new_canonical
        return reconciliation
    
    async def _confirm_validation(
        self,
        etl: ETLResult
    ) -> ETLResult:
        """User checkpoint: proceed despite validation issues"""
        if etl.rows_invalid > 0:
            proceed = await self.prompt.yes_no(
                f"Found {etl.rows_invalid} invalid rows "
                f"({etl.rows_valid} valid). Proceed anyway?"
            )
            if not proceed:
                raise StageError(5, "User aborted due to validation issues")
        return etl
```

---

## 6. Stage Implementation Example

```python
# stages/s3_archaeology/archaeologist.py

from core.interfaces import Stage
from core.models import (
    ReceptionResult, 
    StructureResult, 
    ArchaeologyResult,
    ArchaeologyMap
)
from .boundary_detector import BoundaryDetector
from .noise_filter import NoiseFilter
from .normalizer import ColumnNormalizer
from llm.client import LLMClient
from llm.prompts.archaeology import ArchaeologyPrompt


class Archaeologist(Stage[dict, ArchaeologyResult]):
    """
    Stage 3: Data Archaeology
    Finds signal in human-authored chaos.
    """
    
    @property
    def name(self) -> str:
        return "Data Archaeology"
    
    @property
    def stage_number(self) -> int:
        return 3
    
    def __init__(self):
        self.llm = LLMClient()
        self.prompt_builder = ArchaeologyPrompt()
        self.boundary_detector = BoundaryDetector()
        self.noise_filter = NoiseFilter()
        self.normalizer = ColumnNormalizer()
    
    def validate_input(self, input_data: dict) -> bool:
        return (
            "reception" in input_data 
            and "structure" in input_data
            and input_data["reception"] is not None
        )
    
    async def execute(self, input_data: dict) -> ArchaeologyResult:
        reception: ReceptionResult = input_data["reception"]
        structure: StructureResult = input_data["structure"]
        
        maps = []
        cleaned_data = {}
        
        for preview in reception.previews:
            # Build visual snapshot for LLM
            snapshot = self._build_snapshot(preview)
            
            # LLM analysis
            prompt = self.prompt_builder.build_prompt({
                "snapshot": snapshot,
                "sheet_name": preview.sheet_name,
                "row_count": preview.row_count,
                "col_count": preview.col_count
            })
            
            response = await self.llm.complete(prompt)
            coordinates = self.prompt_builder.parse_response(response)
            
            # Build archaeology map
            arch_map = ArchaeologyMap(
                sheet_name=preview.sheet_name,
                header_row=coordinates.get("header_row"),
                data_start_row=coordinates["data_start_row"],
                data_end_row=coordinates.get("data_end_row"),
                noise_rows=coordinates.get("noise_rows", []),
                noise_columns=coordinates.get("noise_columns", []),
                total_rows=coordinates.get("total_rows", []),
                has_header=coordinates.get("has_header", True)
            )
            
            # Apply extraction
            raw_df = reception.raw_data[preview.sheet_name]
            clean_df = self._extract_clean_data(raw_df, arch_map)
            
            # Normalize column names
            clean_df = self.normalizer.normalize(clean_df)
            
            maps.append(arch_map)
            cleaned_data[preview.sheet_name] = clean_df
        
        return ArchaeologyResult(
            maps=maps,
            cleaned_data=cleaned_data
        )
    
    def _build_snapshot(self, preview: SheetPreview) -> str:
        """Render preview as text table for LLM"""
        lines = []
        
        # Header with column letters
        header = "ROW | " + " | ".join(preview.column_letters)
        lines.append(header)
        lines.append("-" * len(header))
        
        # Data rows
        for i, row in enumerate(preview.preview_rows):
            row_num = str(i + 1).rjust(3)
            cells = [str(cell)[:20] if cell else "" for cell in row]
            lines.append(f"{row_num} | " + " | ".join(cells))
        
        return "\n".join(lines)
    
    def _extract_clean_data(
        self, 
        df: "DataFrame", 
        arch_map: ArchaeologyMap
    ) -> "DataFrame":
        """Apply archaeology map to extract clean data"""
        import pandas as pd
        
        # Remove noise rows
        keep_rows = [
            i for i in range(len(df))
            if i not in arch_map.noise_rows
            and i not in arch_map.total_rows
            and (arch_map.data_end_row is None or i <= arch_map.data_end_row)
            and i >= arch_map.data_start_row
        ]
        
        clean_df = df.iloc[keep_rows].copy()
        
        # Remove noise columns
        if arch_map.noise_columns:
            clean_df = clean_df.drop(columns=arch_map.noise_columns, errors="ignore")
        
        # Set header if present
        if arch_map.has_header and arch_map.header_row is not None:
            header_idx = arch_map.header_row - arch_map.data_start_row
            if header_idx >= 0:
                clean_df.columns = df.iloc[arch_map.header_row].values
                clean_df = clean_df.iloc[1:]  # Remove header from data
        
        # Reset index
        clean_df = clean_df.reset_index(drop=True)
        
        return clean_df
```

---

## 7. LLM Integration

```python
# llm/client.py

import anthropic
from config import settings
from core.exceptions import LLMError


class LLMClient:
    """Claude API client with retry logic"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.LLM_MODEL
        self.max_retries = 3
    
    async def complete(
        self, 
        prompt: str, 
        system: str = None,
        max_tokens: int = 4096
    ) -> str:
        """Send completion request with retry"""
        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system or self._default_system(),
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
                
            except anthropic.RateLimitError:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise LLMError("Rate limit exceeded after retries")
            
            except anthropic.APIError as e:
                raise LLMError(f"API error: {e}")
    
    def _default_system(self) -> str:
        return (
            "You are a data analysis expert. "
            "Respond only with valid JSON. "
            "No explanations or markdown."
        )
```

```python
# llm/prompts/archaeology.py

import json
from core.interfaces import LLMTask


class ArchaeologyPrompt(LLMTask):
    """Prompt for data archaeology analysis"""
    
    @property
    def prompt_template(self) -> str:
        return """Analyze this spreadsheet snapshot and identify the data structure.

SHEET: {sheet_name}
DIMENSIONS: {row_count} rows × {col_count} columns

SNAPSHOT:
{snapshot}

Identify:
1. Which row contains column headers (if any)?
2. Which row does actual data start?
3. Which row does data end (if there are totals/footnotes)?
4. Which rows are noise (titles, blanks, section headers)?
5. Which columns are noise (comments, entirely blank)?
6. Which rows are summary/total rows?

Respond with JSON only:
{{
    "header_row": <int or null>,
    "data_start_row": <int>,
    "data_end_row": <int or null>,
    "noise_rows": [<int>, ...],
    "noise_columns": ["<letter>", ...],
    "total_rows": [<int>, ...],
    "has_header": <boolean>
}}"""
    
    def build_prompt(self, context: dict) -> str:
        return self.prompt_template.format(**context)
    
    def parse_response(self, response: str) -> dict:
        # Strip any markdown code blocks
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        
        return json.loads(clean)
```

---

## 8. Configuration

```python
# config.py

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration"""
    
    # LLM
    ANTHROPIC_API_KEY: str
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # Output
    OUTPUT_DIR: str = "./output"
    
    # Processing
    MAX_PREVIEW_ROWS: int = 50
    CONFIDENCE_THRESHOLD: float = 0.7
    VALIDATION_FAILURE_THRESHOLD: float = 0.1  # 10%
    
    # Insights
    MIN_VARIANCE_FOR_INSIGHT: float = 0.1  # 10%
    MAX_INSIGHTS_PER_ANALYSIS: int = 10
    
    class Config:
        env_file = ".env"


settings = Settings()
```

---

## 9. Module Dependency Graph

```
                              main.py
                                 │
                                 ▼
                          orchestrator.py
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
         ui/progress        stages/*           llm/client
         ui/prompts             │              llm/prompts
              │                 │                  │
              │    ┌────────────┼────────────┐     │
              │    │            │            │     │
              │    ▼            ▼            ▼     │
              │  s0_reception s3_archaeology ...   │
              │    │            │            │     │
              │    └────────────┼────────────┘     │
              │                 │                  │
              │                 ▼                  │
              │            core/models             │
              │            core/enums              │
              │            core/interfaces         │
              │                 │                  │
              └────────────────►│◄─────────────────┘
                                │
                                ▼
                           utils/*
                          (shared)
```

---

## 10. Entry Point

```python
# main.py

import asyncio
import argparse
from pathlib import Path

from orchestrator import Orchestrator
from ui.progress import ConsoleProgress
from ui.prompts import ConsolePrompt
from config import settings


def main():
    parser = argparse.ArgumentParser(
        description="Tragaldabas - Universal Data Ingestor"
    )
    parser.add_argument("file", type=Path, help="Input file path")
    parser.add_argument(
        "--db", 
        type=str, 
        default=settings.DATABASE_URL,
        help="PostgreSQL connection string"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.OUTPUT_DIR,
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return 1
    
    progress = ConsoleProgress()
    prompt = ConsolePrompt()
    
    orchestrator = Orchestrator(
        progress=progress,
        prompt=prompt,
        db_connection_string=args.db
    )
    
    try:
        ctx = asyncio.run(orchestrator.run(str(args.file)))
        
        print(f"\n✓ Pipeline complete")
        print(f"  Insights: {args.output_dir}/insights/")
        print(f"  Presentation: {ctx.output.pptx_file_path}")
        print(f"  Schema: {args.output_dir}/schemas/")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
```

---

## 11. Testing Strategy

| Layer | Tool | Focus |
|-------|------|-------|
| Unit | pytest | Individual functions, parsers, normalizers |
| Integration | pytest + fixtures | Stage-to-stage data flow |
| LLM | pytest + mocks | Prompt/response parsing (mock LLM responses) |
| E2E | pytest + real files | Full pipeline with test datasets |

```python
# tests/conftest.py

import pytest
from pathlib import Path

@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def clean_excel(fixtures_dir):
    return fixtures_dir / "clean_excel.xlsx"

@pytest.fixture
def dirty_excel(fixtures_dir):
    return fixtures_dir / "dirty_excel.xlsx"

@pytest.fixture
def multi_sheet_chaos(fixtures_dir):
    """The nightmare scenario: same data, N layouts"""
    return fixtures_dir / "multi_sheet_chaos.xlsx"

@pytest.fixture
def mock_llm_response():
    """Mock LLM responses for deterministic testing"""
    return {
        "archaeology": {
            "header_row": 3,
            "data_start_row": 4,
            "noise_rows": [0, 1, 2],
            "has_header": True
        }
    }
```
