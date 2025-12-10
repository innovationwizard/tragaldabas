# Tragaldabas - Software Design Document

**Version:** 1.0  
**Date:** December 2024  
**Status:** MVP Specification

---

## 1. Overview

### 1.1 Purpose

Tragaldabas is an AI-powered universal data ingestor that transforms raw, unstructured client files into actionable business intelligence. The system autonomously detects file structure, classifies content domain, infers semantic meaning, cleans and validates data, persists it into PostgreSQL, and generates executive-level insights with board-ready presentation slides.

### 1.2 Scope (MVP)

**In Scope:**
- Word documents (.docx)
- Excel files (.xlsx, .xls)
- CSV files (.csv)
- Single-file processing
- PostgreSQL persistence
- Text-based insights (downloadable, copy-pasteable)
- PowerPoint-ready slides (.pptx)

**Out of Scope (Future):**
- Binary formats (images, PDFs, audio, video)
- Nested/hierarchical data (JSON, XML, YAML)
- Multi-file archives
- Multi-tenant architecture
- Direct BITS integration

### 1.3 Design Principles

1. **Never fabricate data.** No sample data, mock data, or injected information.
2. **Relevancy over volume.** Insights are included only if material; no filler.
3. **Transparency.** User sees the system understanding and structuring data in real-time.
4. **Graceful uncertainty.** When ambiguous, ask yes/no questions rather than guess wrong.

---

## 2. Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              TRAGALDABAS                                │
├─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬────────────┤
│ Stage 0 │ Stage 1 │ Stage 2 │ Stage 3 │ Stage 4 │ Stage 5 │  Stage 6   │
│Reception│ Content │Structure│  Data   │ Schema  │ Analysis│ Executive  │
│         │ Classif.│Inference│Archaeol.│ & ETL   │& Insight│  Output    │
└────┬────┴────┬────┴────┬────┴────┬────┴────┬────┴────┬────┴─────┬──────┘
     │         │         │         │         │         │          │
     ▼         ▼         ▼         ▼         ▼         ▼          ▼
   [File]   [Domain]  [Struct]  [Clean]  [Postgres] [Insights] [Slides]
```

---

## 3. Stage Specifications

### 3.0 Stage 0: Reception

**Input:** Raw file upload  
**Output:** Validated file object with metadata

**Questions Answered:**
1. Can I read this file? (valid, not corrupted, encoding detected)
2. What file format is this? (docx, xlsx, xls, csv)
3. What is the raw structure? (page count, sheet count, row/column dimensions)

**Logic:**
```
IF file unreadable OR corrupted:
    RETURN error with specific failure reason
IF encoding uncertain:
    ATTEMPT multiple encodings (utf-8, latin-1, cp1252)
    SELECT highest-confidence decode
EXTRACT metadata:
    - file_type: enum(docx, xlsx, xls, csv)
    - sheets: list[str] (for Excel) or None
    - dimensions: {rows: int, cols: int} per sheet
    - raw_preview: first 50 rows per sheet
```

**User Checkpoint:** None (fully autonomous)

---

### 3.1 Stage 1: Content Classification

**Input:** File metadata + raw preview  
**Output:** Content classification object

**Questions Answered:**
1. Is this primarily narrative text or structured data?
2. What domain does this belong to?
3. What entity does this describe?
4. What time period does this cover?

**Classification Taxonomy:**

| Primary Type | Subtypes |
|--------------|----------|
| **Narrative** | Report, Contract, Manual, Correspondence, Creative Writing |
| **Structured** | Financial, Operational, HR, Inventory, Sales, Mixed |

**Domain Detection Signals:**

| Domain | Keywords/Patterns |
|--------|-------------------|
| Financial | revenue, income, expense, balance, P&L, assets, liabilities, EBITDA |
| Operational | units, production, output, efficiency, downtime, throughput |
| HR | employee, salary, headcount, payroll, hire date, department |
| Sales | customer, order, quantity, price, discount, region, SKU |
| Inventory | stock, warehouse, reorder, lead time, supplier |

**Logic:**
```
ANALYZE raw_preview with LLM:
    - Classify primary_type: narrative | structured | mixed
    - Classify domain: financial | operational | hr | sales | inventory | other
    - Extract entity_name: string (company, department, product line)
    - Extract time_period: {start: date, end: date} or null
    - confidence_score: float (0-1)

IF confidence_score < 0.7:
    ASK user: "I detected this as [domain]. Is this correct? (Y/N)"
```

**User Checkpoint:** Domain confirmation if confidence < 70%

---

### 3.2 Stage 2: Structure Inference

**Input:** Classification + raw data  
**Output:** Structural schema (pre-cleaning)

#### 3.2.1 Structured Data Path

**Questions Answered:**
1. What does each column represent semantically?
2. What are relationships between sheets? (if multi-sheet)
3. What is the grain? (one row = what?)
4. What are dimensions vs. measures?
5. Are there obvious data quality issues?

**Logic:**
```
FOR each sheet:
    DETECT column_semantics via LLM:
        - column_name: raw name
        - canonical_name: normalized name
        - data_type: string | integer | decimal | date | boolean
        - semantic_role: dimension | measure | identifier | metadata
        - sample_values: list[5]
    
    INFER grain:
        - Identify unique key candidates
        - Determine what one row represents
    
    DETECT relationships (multi-sheet):
        - Shared columns across sheets
        - Foreign key candidates

REPORT initial_quality:
    - null_percentage per column
    - duplicate_rows count
    - type_violations count
```

#### 3.2.2 Narrative Path

**Questions Answered:**
1. What document type is this?
2. What is the internal structure?
3. What key entities are mentioned?
4. What extractable facts/numbers exist?

**Logic:**
```
ANALYZE document with LLM:
    - document_type: report | contract | manual | correspondence | other
    - structure: list[{section_title, page_range}]
    - entities: list[{name, type, mentions}]
    - extractable_facts: list[{claim, value, context}]
```

**User Checkpoint:** None (proceed to archaeology)

---

### 3.3 Stage 3: Data Archaeology

**Purpose:** Find the signal in human-authored chaos.

**Input:** Raw sheet data + structural inference  
**Output:** Cleaned coordinate map for extraction

**Questions Answered:**
1. Where does actual data begin?
2. Where does actual data end?
3. Which columns are data vs. noise?
4. Which rows are data vs. formatting?
5. What is the canonical column name?
6. Is there a header row at all?

**Noise Patterns to Detect:**

| Pattern | Detection Heuristic |
|---------|---------------------|
| Title rows | Single cell populated, top of sheet |
| Subtitle rows | Single cell, row 2-3, often italicized/smaller |
| Blank separator rows | All cells null or whitespace |
| Section headers | One cell populated mid-sheet, different style |
| Comment columns | Sparse population, long text strings |
| Total/Summary rows | Keywords (Total, Sum, Grand Total), follows blank row |
| Repeated headers | Identical to detected header, mid-sheet |
| Footnotes | Bottom rows, sparse, long text |

**Logic:**
```
RENDER visual snapshot (first 50 rows, all columns)

LLM_ANALYZE snapshot:
    RETURN {
        header_row: int | null,
        data_start_row: int,
        data_end_row: int | null,
        noise_rows: list[int],
        noise_columns: list[str],
        total_rows: list[int],
        has_header: boolean
    }

IF has_header == false:
    ASK user: "I don't see column headers. Should I infer them from data patterns? (Y/N)"

APPLY extraction using coordinates:
    - Skip noise_rows
    - Skip noise_columns
    - Extract header_row as column names (or infer)
    - Extract data_start_row to data_end_row as data
```

**Column Name Normalization:**
```
FUNCTION normalize_column(raw_name):
    - lowercase
    - strip whitespace
    - remove special characters except underscore
    - fuzzy match against synonym dictionary:
        {"date": ["fecha", "dt", "date:", "date_col"],
         "amount": ["amt", "monto", "value", "total"],
         "description": ["desc", "descripcion", "detail"]}
    - RETURN canonical_name
```

**User Checkpoint:** Header inference confirmation

---

### 3.4 Stage 4: Cross-Sheet Reconciliation

**Trigger:** Multi-sheet files where sheets share semantic structure

**Input:** Archaeology results per sheet  
**Output:** Unified canonical schema + stacked dataset

**Questions Answered:**
1. Do these sheets share semantic structure?
2. What is the canonical schema?
3. How do sheet columns map to canonical?

**Logic:**
```
CLUSTER sheets by structural similarity:
    - Column count within ±2
    - Column types match ≥70%
    - Fuzzy column name overlap ≥50%

FOR each cluster:
    BUILD canonical_schema:
        - Union of all detected columns
        - Resolve type conflicts (prefer most specific)
    
    MAP each sheet's columns to canonical:
        - Exact match
        - Fuzzy match (Levenshtein ≤ 2)
        - LLM semantic match for ambiguous
    
    STACK data:
        - Add _source_sheet column for provenance
        - Add _source_row column for traceability

IF mapping confidence < 0.8 for any column:
    ASK user: "Column [X] in sheet [Y] - is this [canonical_A] or [canonical_B]?"
```

**User Checkpoint:** Ambiguous column mapping

---

### 3.5 Stage 5: Schema Design & Transformation

**Input:** Clean, reconciled data  
**Output:** PostgreSQL schema + validated data + load scripts

**Questions Answered:**
1. What Postgres table(s) best represent this data?
2. What transformations are required?
3. What validation rules apply?
4. Is data clean enough to persist?

**Schema Design Rules:**
```
TABLE naming:
    - snake_case
    - singular nouns (sale, not sales)
    - prefix with domain if ambiguous (fin_transaction, hr_employee)

COLUMN naming:
    - snake_case
    - no abbreviations unless standard (id, qty, amt)
    - suffix with unit if numeric (revenue_usd, weight_kg)

TYPE mapping:
    - Integers: no decimals detected → BIGINT
    - Decimals: → NUMERIC(precision, scale)
    - Dates: → DATE or TIMESTAMP
    - Booleans: → BOOLEAN
    - Text: length ≤ 255 → VARCHAR(255), else TEXT
    - Currency: → NUMERIC(19,4)

CONSTRAINTS:
    - Primary key: auto-detect or generate surrogate
    - Not null: if null_percentage == 0
    - Foreign keys: if reference detected
```

**Transformation Pipeline:**
```
FOR each column:
    APPLY type_cast (with error capture)
    APPLY null_handling (empty string → NULL)
    APPLY trim (whitespace)
    APPLY domain_specific:
        - Dates: parse multiple formats, normalize to ISO
        - Currency: strip symbols, normalize decimal separator
        - Percentages: convert to decimal (50% → 0.5)
        - Phone: normalize to E.164 if detectable
```

**Validation Rules:**
```
VALIDATE:
    - Type conformance: all values match declared type
    - Uniqueness: PKs have no duplicates
    - Referential: FKs reference valid values
    - Business rules (domain-specific):
        - Financial: debits = credits (if double-entry)
        - Dates: end_date ≥ start_date
        - Quantities: ≥ 0 unless explicitly signed
```

**Output Artifacts:**
```
1. schema.sql - CREATE TABLE statements
2. data.tsv - PostgreSQL COPY format
3. load.sql - COPY commands with transaction wrapper
4. validation_report.json - issues found
```

**User Checkpoint:** If validation failures > threshold, present issues and ask to proceed or abort.

---

### 3.6 Stage 6: Analysis & Insight Generation

**Input:** Persisted, validated data  
**Output:** Structured insights object

**Questions Answered:**
1. What is this data typically used to answer?
2. What are the most relevant metrics/KPIs?
3. What patterns exist?
4. What comparisons are meaningful?
5. What are outliers or red flags?
6. What's the "so what"?

**Analysis Framework by Domain:**

| Domain | Standard Analyses |
|--------|-------------------|
| Financial | Revenue trends, margin analysis, expense breakdown, liquidity ratios, YoY/MoM comparison |
| Operational | Throughput trends, efficiency metrics, capacity utilization, bottleneck identification |
| Sales | Revenue by segment, top customers, growth rates, seasonality, concentration risk |
| HR | Headcount trends, turnover rate, compensation distribution, tenure analysis |
| Inventory | Stock levels, turnover rate, aging, stockout frequency |

**Insight Qualification Criteria:**
```
INCLUDE insight IF:
    - Variance from expected/benchmark > 10%
    - Trend reversal detected
    - Concentration risk (top N = >50% of total)
    - Anomaly detected (>2 std dev)
    - Material absolute value (context-dependent)

EXCLUDE insight IF:
    - Obvious from raw data (no analytical value-add)
    - Trivial variance
    - Insufficient data to support claim
```

**Insight Structure:**
```json
{
    "headline": "string (≤15 words)",
    "detail": "string (≤50 words)",
    "evidence": {
        "metric": "string",
        "value": "number",
        "comparison": "string",
        "delta": "number"
    },
    "implication": "string (so what?)",
    "severity": "info | warning | critical",
    "visualization_hint": "trend_line | bar_chart | pie_chart | table | none"
}
```

**User Checkpoint:** None (autonomous)

---

### 3.7 Stage 7: Executive Output

**Input:** Qualified insights  
**Output:** Text summary + PowerPoint slides

**Questions Answered:**
1. What insights pass the relevancy threshold?
2. What is the optimal narrative arc?
3. What visualization best conveys each insight?
4. What is the single-sentence takeaway per slide?

**Slide Deck Structure:**
```
Slide 1: Title
    - Document/dataset name
    - Time period covered
    - Generated date

Slide 2: Executive Summary
    - 3-5 bullet points, most critical findings
    - One sentence overall assessment

Slides 3-N: Individual Insights
    - One insight per slide
    - Headline (≤10 words)
    - Single visualization or key metric callout
    - Brief supporting text (≤30 words)
    - Implication/action item

Final Slide: Data Quality Notes (if applicable)
    - Issues detected
    - Caveats on analysis
```

**Design Specifications:**
```
Style: Minimalist, corporate
Colors: Neutral palette (navy, gray, white) + one accent
Fonts: Sans-serif (Arial, Helvetica, Calibri)
Charts: Clean, no 3D, no excessive gridlines
Text: High contrast, ≥18pt body, ≥24pt headlines
```

**Output Formats:**
```
1. insights.txt - Plain text, copy-pasteable
2. insights.md - Markdown formatted
3. presentation.pptx - PowerPoint file
4. presentation.pdf - PDF export
```

**User Checkpoint:** None (final delivery)

---

## 4. User Interaction Model

### 4.1 Checkpoint Questions

All user checkpoints are binary (Yes/No) to minimize friction:

| Stage | Trigger | Question Format |
|-------|---------|-----------------|
| 1 | Confidence < 70% | "I detected this as [domain]. Correct? (Y/N)" |
| 3 | No header detected | "No column headers found. Infer from data? (Y/N)" |
| 4 | Ambiguous mapping | "Is [Sheet.Column] the same as [canonical]? (Y/N)" |
| 5 | Validation failures | "Found [N] issues. Proceed anyway? (Y/N)" |

### 4.2 Progress Visibility

User sees real-time status:
```
[✓] Stage 0: File received - Excel, 5 sheets, 12,847 rows total
[✓] Stage 1: Classified as Financial > Income Statement
[◉] Stage 2: Analyzing structure... (Sheet 3 of 5)
[ ] Stage 3: Data archaeology
[ ] Stage 4: Cross-sheet reconciliation
[ ] Stage 5: Schema design & ETL
[ ] Stage 6: Generating insights
[ ] Stage 7: Building presentation
```

---

## 5. Technology Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.11+ |
| File Parsing | openpyxl (Excel), python-docx (Word), pandas (CSV) |
| LLM Integration | Claude API (Anthropic) |
| Database | PostgreSQL 15+ |
| ORM | SQLAlchemy (schema generation) |
| Presentation | python-pptx |
| Encoding Detection | chardet |
| Fuzzy Matching | rapidfuzz |

---

## 6. Data Flow Diagram

```
                                    ┌─────────────┐
                                    │  User File  │
                                    └──────┬──────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STAGE 0: RECEPTION                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                       │
│  │ Validate    │→ │ Detect      │→ │ Extract     │                       │
│  │ File        │  │ Format      │  │ Metadata    │                       │
│  └─────────────┘  └─────────────┘  └─────────────┘                       │
└──────────────────────────────────────────┬───────────────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: CLASSIFICATION                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         LLM Analysis                                │ │
│  │  Input: Raw preview    Output: Domain, Entity, Time Period          │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│                         [Confidence < 70%?]                              │
│                           /              \                               │
│                         Yes              No                              │
│                          ↓                ↓                              │
│                    ┌──────────┐     Continue                             │
│                    │ ASK USER │                                          │
│                    └──────────┘                                          │
└──────────────────────────────────────────┬───────────────────────────────┘
                                           │
                          ┌────────────────┴────────────────┐
                          │                                 │
                          ▼                                 ▼
                    [Structured]                      [Narrative]
                          │                                 │
                          ▼                                 ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────┐
│  STAGE 2: STRUCTURE INFERENCE       │   │  STAGE 2: DOCUMENT ANALYSIS     │
│  - Column semantics                 │   │  - Document type                │
│  - Grain detection                  │   │  - Section structure            │
│  - Dimension vs. measure            │   │  - Entity extraction            │
│  - Sheet relationships              │   │  - Fact extraction              │
└──────────────────┬──────────────────┘   └──────────────────┬──────────────┘
                   │                                         │
                   ▼                                         │
┌─────────────────────────────────────┐                      │
│  STAGE 3: DATA ARCHAEOLOGY          │                      │
│  - Find data boundaries             │                      │
│  - Identify noise rows/columns      │                      │
│  - Normalize column names           │                      │
│  - Handle missing headers           │                      │
└──────────────────┬──────────────────┘                      │
                   │                                         │
                   ▼                                         │
┌─────────────────────────────────────┐                      │
│  STAGE 4: CROSS-SHEET RECONCILE     │                      │
│  (if multi-sheet)                   │                      │
│  - Build canonical schema           │                      │
│  - Map columns                      │                      │
│  - Stack data with provenance       │                      │
└──────────────────┬──────────────────┘                      │
                   │                                         │
                   └──────────────────┬──────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: SCHEMA DESIGN & ETL                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Design      │→ │ Transform   │→ │ Validate    │→ │ Persist     │     │
│  │ Schema      │  │ Data        │  │ Data        │  │ to Postgres │     │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                           │                              │
│                                  [Validation Failures?]                  │
│                                     /            \                       │
│                                   Yes            No                      │
│                                    ↓              ↓                      │
│                              ┌──────────┐   Continue                     │
│                              │ ASK USER │                                │
│                              └──────────┘                                │
└──────────────────────────────────────────┬───────────────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STAGE 6: ANALYSIS & INSIGHTS                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         LLM Analysis                                │ │
│  │  - Domain-specific KPIs                                             │ │
│  │  - Pattern detection (trends, anomalies, concentrations)            │ │
│  │  - Comparisons (YoY, MoM, benchmarks)                               │ │
│  │  - Implication synthesis                                            │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│                          [Relevancy Filter]                              │
│                                    │                                     │
│                         Qualified Insights Only                          │
└──────────────────────────────────────────┬───────────────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STAGE 7: EXECUTIVE OUTPUT                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Structure   │→ │ Generate    │→ │ Build       │→ │ Export      │     │
│  │ Narrative   │  │ Text        │  │ Slides      │  │ Files       │     │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
└──────────────────────────────────────────┬───────────────────────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │  DELIVERABLES           │
                              │  - insights.txt         │
                              │  - insights.md          │
                              │  - presentation.pptx    │
                              │  - schema.sql           │
                              │  - data.tsv             │
                              │  - load.sql             │
                              │  - validation_report    │
                              └─────────────────────────┘
```

---

## 7. Error Handling

| Error Type | Handling |
|------------|----------|
| Corrupted file | Abort with clear message |
| Unsupported format | Abort, list supported formats |
| Encoding failure | Try fallback encodings, ask user if all fail |
| LLM timeout | Retry with exponential backoff (3 attempts) |
| LLM refusal | Log and proceed with rule-based fallback |
| Empty data | Abort with "No data found" message |
| All rows invalid | Abort, provide validation report |
| Postgres connection failure | Generate files only, skip persistence |

---

## 8. Future Roadmap

| Phase | Capabilities |
|-------|--------------|
| MVP | Word, Excel, CSV → Insights + Slides |
| Phase 2 | PDF support, image OCR |
| Phase 3 | JSON, XML, nested structures |
| Phase 4 | API endpoints, webhook triggers |
| Phase 5 | BITS integration (books → forecasts) |
| Phase 6 | Multi-tenant, per-client schemas |

---

## 9. Appendix

### 9.1 Synonym Dictionary (Seed)

```python
COLUMN_SYNONYMS = {
    "date": ["fecha", "dt", "date:", "date_col", "period", "periodo"],
    "amount": ["amt", "monto", "value", "total", "sum", "importe"],
    "description": ["desc", "descripcion", "detail", "detalle", "notes"],
    "quantity": ["qty", "cantidad", "units", "count", "pieces"],
    "price": ["precio", "unit_price", "rate", "tarifa"],
    "customer": ["cliente", "client", "buyer", "account"],
    "product": ["producto", "item", "sku", "article"],
    "revenue": ["ingreso", "sales", "ventas", "income"],
    "expense": ["gasto", "cost", "costo", "egreso"],
    "balance": ["saldo", "remaining", "outstanding"],
}
```

### 9.2 Domain Detection Keywords

```python
DOMAIN_KEYWORDS = {
    "financial": [
        "revenue", "income", "expense", "balance", "p&l", "profit", "loss",
        "assets", "liabilities", "equity", "ebitda", "margin", "cash flow",
        "accounts receivable", "accounts payable", "depreciation"
    ],
    "operational": [
        "production", "output", "throughput", "efficiency", "capacity",
        "downtime", "yield", "scrap", "cycle time", "utilization"
    ],
    "sales": [
        "customer", "order", "quantity", "discount", "region", "territory",
        "pipeline", "conversion", "churn", "retention", "quota"
    ],
    "hr": [
        "employee", "salary", "headcount", "payroll", "hire date", "termination",
        "department", "title", "compensation", "benefits", "tenure"
    ],
    "inventory": [
        "stock", "warehouse", "reorder", "lead time", "supplier", "sku",
        "on hand", "committed", "available", "backorder"
    ]
}
```
