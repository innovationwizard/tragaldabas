# Tragaldabas - Technical Documentation

**Version:** 2.0  
**Last Updated:** January 2025  
**Status:** Production System

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Pipeline Architecture](#pipeline-architecture)
5. [Web Application Architecture](#web-application-architecture)
6. [Supabase Integration](#supabase-integration)
7. [Authentication System](#authentication-system)
8. [Data Models](#data-models)
9. [API Reference](#api-reference)
10. [Frontend Architecture](#frontend-architecture)
11. [Deployment Architecture](#deployment-architecture)
12. [Configuration](#configuration)
13. [Error Handling](#error-handling)

---

## Overview

### Purpose

Tragaldabas is a Universal Data Ingestor that transforms raw files (Excel, CSV, Word documents) into actionable business intelligence. The system autonomously detects file structure, classifies content domain, infers semantic meaning, cleans and validates data, and generates executive-level insights with board-ready presentation slides.

### Key Features

- **7-Stage Processing Pipeline**: Reception → Classification → Structure → Archaeology → Reconciliation → ETL → Analysis → Output
- **Multi-Format Support**: Excel (.xlsx, .xls), CSV, Word (.docx)
- **LLM-Powered Intelligence**: Multi-provider support (Claude, OpenAI, Gemini) with automatic fallback
- **Data Archaeology**: Automatically finds signal in messy human-created spreadsheets
- **PostgreSQL Integration**: Direct database connection with schema generation
- **Executive Output**: Generates PowerPoint presentations and text summaries
- **Web Application**: Modern React frontend with FastAPI backend
- **Supabase Integration**: Authentication, database, and storage
- **Real-time Progress Tracking**: WebSocket-based progress updates

### Design Principles

1. **Never fabricate data** - No sample or mock data
2. **Relevancy over volume** - Only material insights
3. **Transparency** - Real-time progress visibility
4. **Graceful uncertainty** - Ask yes/no questions when ambiguous

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  React Frontend (Vite)                                   │  │
│  │  - Authentication UI                                     │  │
│  │  - File Upload                                           │  │
│  │  - Progress Tracking                                     │  │
│  │  - Results Dashboard                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (Vercel)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application (web/api.py)                        │  │
│  │  - Authentication Endpoints                               │  │
│  │  - File Upload & Job Management                          │  │
│  │  - Progress Polling                                      │  │
│  │  - Result Retrieval                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Triggers
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  SUPABASE EDGE FUNCTION                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  process-pipeline/index.ts                               │  │
│  │  - Job Queue Management                                   │  │
│  │  - Worker Orchestration                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP POST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WORKER SERVICE (Railway)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Pipeline Worker (worker.py)                             │  │
│  │  - Heavy Dependencies (pandas, numpy, LLM libs)        │  │
│  │  - Pipeline Execution                                    │  │
│  │  - Progress Updates                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Storage & Database
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SUPABASE SERVICES                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Auth      │  │  Database    │  │   Storage    │         │
│  │  (JWT)      │  │ (PostgreSQL) │  │  (S3-like)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

1. **Frontend (React)**: User interface, authentication, file upload, progress visualization
2. **API Layer (FastAPI/Vercel)**: REST API, authentication, job management, file serving
3. **Edge Function (Supabase)**: Job queue management, worker orchestration
4. **Worker Service (Railway)**: Heavy pipeline processing, LLM calls, data transformation
5. **Supabase**: Authentication, database persistence, file storage

---

## Technology Stack

### Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Runtime | Python | 3.11+ |
| Web Framework | FastAPI | Latest |
| File Parsing | pandas, openpyxl, python-docx | Latest |
| LLM Integration | anthropic, openai, google-genai | Latest |
| Database | PostgreSQL (via Supabase) | 15+ |
| ORM | SQLAlchemy | Latest |
| Presentation | python-pptx | Latest |
| Encoding Detection | chardet | Latest |
| Fuzzy Matching | rapidfuzz | Latest |

### Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | 18.2+ |
| Build Tool | Vite | 7.3+ |
| Routing | React Router | 6.20+ |
| HTTP Client | Axios | 1.6+ |
| Styling | Tailwind CSS | 3.3+ |
| Icons | Lucide React | 0.294+ |
| Supabase Client | @supabase/supabase-js | 2.39+ |

### Infrastructure

| Service | Provider | Purpose |
|---------|----------|---------|
| Frontend/API | Vercel | Static hosting & serverless functions |
| Worker | Railway | Heavy processing service |
| Database | Supabase | PostgreSQL database |
| Auth | Supabase Auth | JWT-based authentication |
| Storage | Supabase Storage | File storage (S3-like) |
| Edge Functions | Supabase | Serverless job orchestration |

---

## Pipeline Architecture

### Pipeline Stages

The pipeline consists of 7 sequential stages, each transforming data and passing results to the next stage:

```
Stage 0: Reception
    ↓
Stage 1: Classification
    ↓
Stage 2: Structure Inference
    ↓
Stage 3: Data Archaeology
    ↓
Stage 4: Reconciliation (if multi-sheet)
    ↓
Stage 5: ETL
    ↓
Stage 6: Analysis
    ↓
Stage 7: Output
    ↓
Stage 8: Cell Classification
    ↓
Stage 9: Dependency Graph
    ↓
Stage 10: Logic Extraction
    ↓
Stage 11: Code Generation
    ↓
Stage 12: Scaffold & Deploy
```

### Stage 0: Reception

**Purpose**: Parse and validate input file

**Input**: Raw file path

**Output**: `ReceptionResult`
- File metadata (type, size, encoding)
- Sheet previews (for Excel)
- Raw data (DataFrames per sheet)

**Key Components**:
- `stages/s0_reception/receiver.py`: Main coordinator
- `stages/s0_reception/parsers/`: Format-specific parsers
  - `excel.py`: Excel parsing (openpyxl)
  - `csv.py`: CSV parsing (pandas)
  - `word.py`: Word parsing (python-docx)

**Process**:
1. Detect file type from extension
2. Validate file exists and is readable
3. Detect encoding (UTF-8, Latin-1, CP1252)
4. Parse file into structured data
5. Extract metadata (sheet names, dimensions)
6. Generate previews (first N rows)

### Stage 1: Classification

**Purpose**: Detect content type and domain

**Input**: `ReceptionResult`

**Output**: `ContentClassification`
- Primary type (narrative, structured, mixed)
- Domain (financial, operational, sales, HR, inventory)
- Entity name
- Time period
- Confidence score

**Key Components**:
- `stages/s1_classification/classifier.py`: Main coordinator
- `llm/client.py`: LLM client for classification

**Process**:
1. Analyze raw preview with LLM
2. Classify content type (narrative vs structured)
3. Detect domain from keywords/patterns
4. Extract entity name and time period
5. Calculate confidence score
6. If confidence < threshold, prompt user for confirmation

**LLM Prompt**: Analyzes file preview to determine domain, entity, and time period

### Stage 2: Structure Inference

**Purpose**: Infer column semantics and data grain

**Input**: `ReceptionResult` + `ContentClassification`

**Output**: `StructureResult`
- Column inferences (semantic roles, data types)
- Sheet relationships (for multi-sheet files)
- Grain description (what one row represents)

**Key Components**:
- `stages/s2_structure/inferrer.py`: Main coordinator
- `llm/client.py`: LLM client for structure analysis

**Process**:
1. For each sheet:
   - Analyze columns with LLM
   - Infer data types (string, integer, decimal, date, etc.)
   - Determine semantic roles (identifier, dimension, measure, metadata)
   - Normalize column names
   - Identify primary key candidates
   - Determine grain (what one row represents)
2. Detect relationships between sheets (shared columns, foreign keys)

**LLM Prompt**: Analyzes column names and sample data to infer semantics

### Stage 3: Data Archaeology

**Purpose**: Find signal in human-authored chaos

**Input**: `ReceptionResult` + `StructureResult`

**Output**: `ArchaeologyResult`
- Archaeology maps (data boundaries per sheet)
- Cleaned data (DataFrames with noise removed)

**Key Components**:
- `stages/s3_archaeology/archaeologist.py`: Main coordinator
- `llm/client.py`: LLM client for archaeology analysis
- `utils/fuzzy.py`: Fuzzy matching for column normalization
- `utils/synonyms.py`: Synonym dictionary

**Process**:
1. Build visual snapshot (first 50 rows as text table)
2. Analyze with LLM to identify:
   - Header row location
   - Data start/end rows
   - Noise rows (titles, blanks, section headers)
   - Noise columns (comments, entirely blank)
   - Total/summary rows
3. Extract clean data using archaeology map
4. Normalize column names (fuzzy matching + synonyms)

**LLM Prompt**: Analyzes spreadsheet snapshot to find data boundaries

**Noise Detection Patterns**:
- Title rows: Single cell populated, top of sheet
- Blank separator rows: All cells null or whitespace
- Section headers: One cell populated mid-sheet
- Comment columns: Sparse population, long text strings
- Total rows: Keywords (Total, Sum, Grand Total)

### Stage 4: Reconciliation

**Purpose**: Unify multi-sheet files into canonical schema

**Input**: `ArchaeologyResult` (multi-sheet)

**Output**: `ReconciliationResult`
- Canonical schema (unified column definitions)
- Column mappings (sheet column → canonical column)
- Unified data (stacked DataFrame)

**Key Components**:
- `stages/s4_reconciliation/reconciler.py`: Main coordinator
- `utils/fuzzy.py`: Column name matching

**Process**:
1. Cluster sheets by structural similarity
2. Build canonical schema (union of all columns)
3. Map each sheet's columns to canonical:
   - Exact match
   - Fuzzy match (Levenshtein distance)
   - LLM semantic match (for ambiguous cases)
4. Stack data with provenance columns (`_source_sheet`, `_source_row`)
5. If mapping confidence < threshold, prompt user

**Trigger**: Only runs if file has multiple sheets

### Stage 5: ETL

**Purpose**: Design schema, transform data, validate, persist

**Input**: `ArchaeologyResult` or `ReconciliationResult`

**Output**: `ETLResult`
- PostgreSQL schema definition
- Schema SQL (CREATE TABLE statements)
- Transformed data file (CSV/TSV)
- Load SQL (COPY commands)
- Validation issues report

**Key Components**:
- `stages/s5_etl/etl_manager.py`: Main coordinator
- `db/schema.py`: Schema generation
- `db/loader.py`: Data loading

**Process**:
1. **Schema Design**:
   - Generate table name (snake_case, singular)
   - Map data types to PostgreSQL types
   - Define constraints (primary keys, not null, foreign keys)
   - Generate indexes
2. **Data Transformation**:
   - Type casting (with error capture)
   - Null handling (empty string → NULL)
   - Whitespace trimming
   - Domain-specific normalization:
     - Dates: Parse multiple formats, normalize to ISO
     - Currency: Strip symbols, normalize decimal separator
     - Percentages: Convert to decimal (50% → 0.5)
3. **Validation**:
   - Type conformance
   - Uniqueness (primary keys)
   - Referential integrity (foreign keys)
   - Business rules (domain-specific)
4. **Persistence**:
   - Generate schema SQL
   - Export data to CSV/TSV
   - Generate load SQL (COPY commands)
   - If database URL provided, execute schema creation and data loading

**PostgreSQL Type Mapping**:
- Integers → `BIGINT`
- Decimals → `NUMERIC(precision, scale)`
- Dates → `DATE` or `TIMESTAMP`
- Booleans → `BOOLEAN`
- Text (≤255 chars) → `VARCHAR(255)`
- Text (>255 chars) → `TEXT`
- Currency → `NUMERIC(19,4)`

### Stage 6: Analysis

**Purpose**: Generate insights and metrics

**Input**: `ETLResult` + Domain

**Output**: `AnalysisResult`
- Domain-specific metrics
- Detected patterns
- Qualified insights

**Key Components**:
- `stages/s6_analysis/analyzer.py`: Main coordinator
- `llm/client.py`: LLM client for insight generation

**Process**:
1. **Metrics Computation**:
   - Domain-specific KPIs (revenue trends, margin analysis, etc.)
   - Statistical measures (mean, median, variance, etc.)
   - Comparisons (YoY, MoM, benchmarks)
2. **Pattern Detection**:
   - Trend reversals
   - Anomalies (>2 std dev)
   - Concentration risks (top N = >50% of total)
3. **Insight Generation** (LLM-powered):
   - Analyze metrics and patterns
   - Generate insights with evidence
   - Filter by relevancy (variance > 10%, material value, etc.)
4. **Insight Structure**:
   - Headline (≤15 words)
   - Detail (≤50 words)
   - Evidence (metric, value, comparison, delta)
   - Implication ("so what?")
   - Severity (info, warning, critical)
   - Visualization hint

**Domain-Specific Analyses**:
- **Financial**: Revenue trends, margin analysis, expense breakdown, liquidity ratios
- **Operational**: Throughput trends, efficiency metrics, capacity utilization
- **Sales**: Revenue by segment, top customers, growth rates, seasonality
- **HR**: Headcount trends, turnover rate, compensation distribution
- **Inventory**: Stock levels, turnover rate, aging, stockout frequency

**Insight Qualification**:
- Include if: Variance > 10%, trend reversal, concentration risk, anomaly, material value
- Exclude if: Obvious from raw data, trivial variance, insufficient data

### Stage 7: Output

**Purpose**: Generate executive output files

**Input**: `AnalysisResult`

**Output**: `OutputResult`
- Text file (plain text insights)
- Markdown file (formatted insights)
- PowerPoint file (presentation slides)
- File paths

**Key Components**:
- `stages/s7_output/output_manager.py`: Main coordinator
- `stages/s7_output/text_generator.py`: Text/markdown generation
- `stages/s7_output/slide_builder.py`: PowerPoint generation

**Process**:
1. **Text Generation**:
   - Format insights as plain text
   - Generate markdown version
2. **Slide Deck Generation**:
   - Title slide (document name, time period, generated date)
   - Executive summary (3-5 bullet points, critical findings)
   - Individual insight slides (one per insight):
     - Headline (≤10 words)
     - Visualization or key metric callout
     - Supporting text (≤30 words)
     - Implication/action item
   - Data quality notes (if applicable)
3. **Design Specifications**:
   - Minimalist, corporate style
   - Neutral palette (navy, gray, white) + accent color
   - Sans-serif fonts (Arial, Helvetica, Calibri)
   - Clean charts (no 3D, minimal gridlines)
   - High contrast text (≥18pt body, ≥24pt headlines)

**Output Files**:
- `insights.txt`: Plain text, copy-pasteable
- `insights.md`: Markdown formatted
- `presentation.pptx`: PowerPoint file

### Stage 8: Cell Classification

**Purpose**: Categorize every cell and extract validation, conditional formatting, and macros.

**Output**: `CellClassificationResult`
- Classified cells (inputs, outputs, labels, structural)
- Validation rules (including list ranges)
- Conditional formatting hints (severity + color)
- Pivot table metadata
- VBA macro extraction

### Stage 9: Dependency Graph

**Purpose**: Build the full calculation graph and execution order.

**Output**: `DependencyGraph`
- Nodes and edges with topological ordering
- Calculation clusters
- Semantic purpose inference

### Stage 10: Logic Extraction

**Purpose**: Parse formulas into AST, infer types, and build business rules.

**Output**: `LogicExtractionResult`
- Parsed formulas + AST
- Business rules with LLM-enriched naming/description
- Test suite with seeded cases

### Stage 11: Code Generation

**Purpose**: Generate a Next.js + Prisma app.

**Output**: `GeneratedProject`
- App scaffold + calculation engine
- Prisma schema generated from inputs/outputs
- Scenario CRUD routes + UI

### Stage 12: Scaffold & Deploy

**Purpose**: Write the generated project to disk and provide manual deployment steps.

**Output**: `ScaffoldResult`
- Local project path
- Manual instructions: `docs/STAGE12_MANUAL_DEPLOY.md`

---

## Web Application Architecture

### Backend (FastAPI)

**Main Application**: `web/api.py`

**Key Features**:
- RESTful API endpoints
- Supabase Auth integration
- File upload handling
- Job management
- Progress polling
- Result retrieval
- Static file serving (frontend build)

**Architecture Patterns**:
- Lazy imports for heavy dependencies (reduces serverless function size)
- Async/await for non-blocking operations
- Database operations via Supabase client
- File storage in Supabase Storage (persistent, accessible from worker)

### Frontend (React)

**Framework**: React 18 with Vite

**Key Features**:
- Dark mode UI ("The Alchemist" color palette)
- Authentication (Supabase Auth)
- File upload (drag-and-drop)
- Real-time progress tracking (polling-based)
- Results dashboard (tabbed interface)
- Responsive design

**Key Components**:
- `App.jsx`: Main application component
- `AuthContextSupabase.jsx`: Authentication context
- Pages:
  - `Landing.jsx`: Landing page
  - `Login.jsx`: Login page
  - `Register.jsx`: Registration page
  - `Dashboard.jsx`: Job list
  - `Upload.jsx`: File upload
  - `Pipeline.jsx`: Progress tracking
  - `Results.jsx`: Results dashboard

**State Management**:
- React Context for authentication
- Local state for component-specific data
- Polling for progress updates (no WebSocket currently)

**Styling**:
- Tailwind CSS with custom brand palette
- Obsidian (#0C0A09): Main background
- Basalt (#1C1917): Cards, surfaces
- Iron (#44403C): Borders
- Molten (#F59E0B): Primary actions, accents
- Parchment (#E7E5E4): Primary text
- Ash (#A8A29E): Muted text

---

## Supabase Integration

### Authentication (Supabase Auth)

**Implementation**: JWT-based authentication via Supabase Auth

**Features**:
- User registration
- Email/password login
- Session management
- Token refresh
- User metadata storage

**Backend Integration**:
- `get_current_user()`: Verifies JWT token from Authorization header
- Uses Supabase service role key for token verification
- Returns user object with `id`, `email`, `user_metadata`

**Frontend Integration**:
- `@supabase/supabase-js` client
- `AuthContextSupabase.jsx`: Manages auth state
- Token stored in localStorage (consider httpOnly cookies for production)
- Automatic token refresh

### Database (PostgreSQL via Supabase)

**Schema**: `pipeline_jobs` table

**Columns**:
- `id`: UUID (primary key)
- `user_id`: UUID (foreign key to auth.users)
- `filename`: String
- `status`: Enum (pending, running, completed, failed)
- `current_stage`: Integer (0-7)
- `current_stage_name`: String
- `completed_stages`: Integer array
- `questions`: JSON array (user prompts)
- `storage_path`: String (Supabase Storage path)
- `app_generation`: Boolean
- `batch_id`: String (group id for multi-file uploads)
- `batch_order`: Integer (ordering within batch)
- `batch_total`: Integer (batch size)
- `etl_status`: String (pending, running, completed, failed)
- `etl_target_db_url`: String (target database connection for ETL)
- `etl_error`: String (ETL error message)
- `etl_result`: JSON (ETL output metadata)
- `etl_started_at`: Timestamp
- `etl_completed_at`: Timestamp
- `result`: JSON (pipeline results)
- `error`: String (error message if failed)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Row Level Security (RLS)**:
- Users can only access their own jobs
- Service role key bypasses RLS (for worker/edge functions)

### Storage (Supabase Storage)

**Buckets**:
- `uploads`: User-uploaded files and output files

**Path Structure**:
- Input files: `{user_id}/{job_id}/{filename}`
- Output files: `{user_id}/{job_id}/outputs/{filename}`

**Features**:
- Public read access (with RLS)
- Private write access (authenticated users only)
- Automatic cleanup (optional, via policies)

### Edge Functions

**Function**: `process-pipeline`

**Purpose**: Orchestrate pipeline job processing

**Trigger**: Called by API after file upload

**Process**:
1. Receives `job_id` in request body
2. Fetches job from database
3. Checks job status (skip if already processing/completed)
4. Calls worker service endpoint (`/process/{job_id}`)
5. Returns immediately (fire-and-forget)
6. Worker updates job status when complete

**Configuration**:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key
- `VERCEL_API_URL`: Vercel API URL (fallback)
- `WORKER_URL`: Railway worker URL (preferred)
- `RAILWAY_API_KEY`: Railway API key for worker authentication

---

## Authentication System

### Flow

1. **Registration**:
   - User submits email/password via `/api/auth/register`
   - Supabase Auth creates user account
   - Returns user object with JWT tokens

2. **Login**:
   - User submits username/password via `/api/auth/login`
   - Username mapped to email (for test users)
   - Supabase Auth validates credentials
   - Returns access token and refresh token

3. **Token Usage**:
   - Frontend stores tokens in localStorage
   - Includes `Authorization: Bearer <token>` header in API requests
   - Backend verifies token via `get_current_user()` dependency

4. **Logout**:
   - User calls `/api/auth/logout`
   - Supabase Auth signs out user
   - Frontend clears tokens from localStorage

### Security Features

- JWT-based authentication
- Token expiration (1 hour access, 30 days refresh)
- Secure password hashing (handled by Supabase)
- Row Level Security (RLS) for data isolation
- Service role key for server-side operations

### Test Users

Username-to-email mapping (for development):
- `condor` → `condor@example.com`
- `estefani` → `estefani@example.com`
- `marco` → `marco@example.com`

---

## Data Models

### Core Models (Pydantic)

All models defined in `core/models.py`:

**Stage 0: Reception**
- `FileMetadata`: File information
- `SheetPreview`: Sheet preview data
- `ReceptionResult`: Complete reception output

**Stage 1: Classification**
- `ContentClassification`: Content type and domain

**Stage 2: Structure**
- `ColumnInference`: Column metadata
- `SheetStructure`: Sheet structure
- `StructureResult`: Complete structure output

**Stage 3: Archaeology**
- `ArchaeologyMap`: Data extraction coordinates
- `ArchaeologyResult`: Complete archaeology output

**Stage 4: Reconciliation**
- `ColumnMapping`: Column mapping
- `CanonicalSchema`: Unified schema
- `ReconciliationResult`: Complete reconciliation output

**Stage 5: ETL**
- `PostgresColumn`: PostgreSQL column definition
- `PostgresTable`: PostgreSQL table definition
- `ValidationIssue`: Validation error
- `ETLResult`: Complete ETL output

**Stage 6: Analysis**
- `Evidence`: Supporting data for insight
- `Insight`: Single analytical insight
- `AnalysisResult`: Complete analysis output

**Stage 7: Output**
- `OutputResult`: Complete output (file paths)

### Enumerations (`core/enums.py`)

- `FileType`: xlsx, xls, csv, docx
- `ContentType`: narrative, structured, mixed
- `Domain`: financial, operational, sales, hr, inventory, general
- `DataType`: string, integer, decimal, date, datetime, boolean, currency, percentage
- `SemanticRole`: identifier, dimension, measure, metadata, unknown
- `Severity`: info, warning, critical
- `VisualizationType`: trend_line, bar_chart, pie_chart, table, metric_callout, none
- `ValidationIssueType`: type_mismatch, null_violation, duplicate_key, referential_integrity, business_rule, outlier
- `LLMProvider`: anthropic, openai, gemini

---

## API Reference

### Authentication Endpoints

**POST `/api/auth/register`**
- Register new user
- Body: `{email, password, username?, full_name?}`
- Returns: User object with tokens

**POST `/api/auth/login`**
- Login user (username-based for test users)
- Body: `{username, password}`
- Returns: Access token, refresh token, user object

**POST `/api/auth/logout`**
- Logout user
- Requires: Authentication
- Returns: Success message

**GET `/api/auth/me`**
- Get current user info
- Requires: Authentication
- Returns: User object

### Pipeline Endpoints

**POST `/api/pipeline/upload`**
- Upload file and start pipeline
- Requires: Authentication
- Body: Multipart form data with file
- Returns: `{job_id, status, message}`

**GET `/api/pipeline/jobs`**
- List user's pipeline jobs
- Requires: Authentication
- Returns: `{jobs: [...]}`

**GET `/api/pipeline/jobs/{job_id}`**
- Get pipeline job details
- Requires: Authentication
- Returns: Job object with results

**GET `/api/pipeline/jobs/{job_id}/status`**
- Get current job status (for polling)
- Requires: Authentication
- Returns: `{id, status, current_stage, current_stage_name, completed_stages, error}`

**POST `/api/pipeline/jobs/{job_id}/retry`**
- Manually trigger processing for stuck job
- Requires: Authentication
- Returns: Success message

**GET `/api/pipeline/jobs/{job_id}/download/{file_type}`**
- Download output files (txt, pptx, md)
- Requires: Authentication
- Returns: File download

**POST `/api/pipeline/process/{job_id}`**
- Process pipeline job (called by worker/edge function)
- Requires: Service role key or user token
- Returns: Success message

---

## Frontend Architecture

### Project Structure

```
frontend/
├── src/
│   ├── App.jsx              # Main app component
│   ├── main.jsx             # Entry point
│   ├── index.css             # Global styles
│   ├── components/           # Reusable components
│   │   ├── Layout.jsx       # App layout
│   │   └── PrivateRoute.jsx # Protected route wrapper
│   ├── contexts/            # React contexts
│   │   └── AuthContextSupabase.jsx  # Auth state
│   ├── pages/                # Page components
│   │   ├── Landing.jsx
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Upload.jsx
│   │   ├── Pipeline.jsx
│   │   └── Results.jsx
│   └── lib/                  # Utilities
│       └── supabase.js       # Supabase client
├── public/                   # Static assets
├── package.json
├── vite.config.js
└── tailwind.config.js
```

### Routing

React Router configuration:
- `/`: Landing page
- `/login`: Login page
- `/register`: Registration page
- `/dashboard`: Job list (protected)
- `/upload`: File upload (protected)
- `/pipeline/:jobId`: Progress tracking (protected)
- `/results/:jobId`: Results dashboard (protected)

### State Management

- **Authentication**: `AuthContextSupabase` context
- **Job Progress**: Polling via `/api/pipeline/jobs/{job_id}/status`
- **Local State**: Component-level state for UI

### API Integration

- **HTTP Client**: Axios
- **Base URL**: Environment variable (`VITE_API_URL` or default to same origin)
- **Auth Headers**: Automatically added via axios interceptor
- **Error Handling**: Centralized error handling

---

## Deployment Architecture

### Components

1. **Frontend/API (Vercel)**
   - Static frontend build served by FastAPI
   - API endpoints as serverless functions
   - Environment variables: Supabase keys, LLM keys

2. **Worker Service (Railway)**
   - Heavy processing service
   - Runs `worker.py` (FastAPI app)
   - Environment variables: All API keys, database URL
   - Dockerfile-based deployment

3. **Supabase**
   - Database (PostgreSQL)
   - Authentication (Supabase Auth)
   - Storage (Supabase Storage)
   - Edge Functions (Deno runtime)

### Deployment Flow

1. **File Upload**:
   - User uploads file via frontend
   - API receives file, uploads to Supabase Storage
   - Creates job record in database
   - Triggers Supabase Edge Function

2. **Job Processing**:
   - Edge Function calls worker service
   - Worker downloads file from Supabase Storage
   - Worker executes pipeline
   - Worker updates job status in database
   - Worker uploads output files to Supabase Storage

3. **Progress Tracking**:
   - Frontend polls `/api/pipeline/jobs/{job_id}/status`
   - API reads job status from database
   - Frontend displays progress

4. **Result Retrieval**:
   - Frontend requests job details
   - API returns job with results
   - Frontend displays results
   - User downloads output files

### Environment Variables

**Vercel (Frontend/API)**:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `DATABASE_URL`: PostgreSQL connection string (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `GOOGLE_API_KEY`: Google/Gemini API key (optional)
- `CORS_ORIGINS`: Allowed CORS origins

**Railway (Worker)**:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `DATABASE_URL`: PostgreSQL connection string
- `ANTHROPIC_API_KEY`: Anthropic API key
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `GOOGLE_API_KEY`: Google/Gemini API key (optional)
- `RAILWAY_API_KEY`: Railway API key (for worker authentication)
- `OUTPUT_DIR`: Output directory path

**Supabase Edge Function**:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `VERCEL_API_URL`: Vercel API URL
- `WORKER_URL`: Railway worker URL
- `RAILWAY_API_KEY`: Railway API key

---

## Configuration

### Configuration File (`config.py`)

Pydantic-based settings with environment variable support:

**LLM Configuration**:
- `ANTHROPIC_API_KEY`: Anthropic API key
- `OPENAI_API_KEY`: OpenAI API key
- `GOOGLE_API_KEY`: Google/Gemini API key
- `LLM_PROVIDER_PRIORITY`: Provider priority (comma-separated)
- `ANTHROPIC_MODEL`: Anthropic model name
- `OPENAI_MODEL`: OpenAI model name
- `GEMINI_MODEL_ID`: Primary Gemini model
- `GEMINI_FALLBACK_MODEL_ID`: Fallback Gemini model
- `LLM_MAX_TOKENS`: Maximum tokens per request
- `LLM_MAX_RETRIES`: Maximum retry attempts
- `LLM_RETRY_DELAY`: Retry delay (seconds)
- `LLM_TIMEOUT`: Request timeout (seconds)

**Database Configuration**:
- `DATABASE_URL`: PostgreSQL connection string

**Supabase Configuration**:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key

**Processing Configuration**:
- `OUTPUT_DIR`: Output directory path
- `MAX_PREVIEW_ROWS`: Maximum preview rows
- `CONFIDENCE_THRESHOLD`: Classification confidence threshold
- `VALIDATION_FAILURE_THRESHOLD`: Validation failure threshold
- `MIN_VARIANCE_FOR_INSIGHT`: Minimum variance for insight inclusion
- `MAX_INSIGHTS_PER_ANALYSIS`: Maximum insights per analysis

**Archaeology Configuration**:
- `ARCHAEOLOGY_MAX_PREVIEW_ROWS`: Maximum rows for archaeology preview
- `FUZZY_MATCH_THRESHOLD`: Fuzzy matching threshold (0-100)

### LLM Provider Priority

Default priority: `anthropic,openai,gemini`

The system tries providers in order, falling back to the next if a request fails.

---

## Error Handling

### Error Types

1. **File Errors**:
   - Corrupted file → Abort with clear message
   - Unsupported format → Abort, list supported formats
   - Encoding failure → Try fallback encodings

2. **LLM Errors**:
   - Timeout → Retry with exponential backoff (3 attempts)
   - Rate limit → Retry with backoff
   - Provider failure → Fallback to next provider
   - All providers fail → Raise `LLMError`

3. **Pipeline Errors**:
   - Stage failure → Update job status to "failed", store error message
   - Validation failures → Report issues, allow user to proceed or abort
   - Empty data → Abort with "No data found" message

4. **Database Errors**:
   - Connection failure → Generate files only, skip persistence
   - Query failure → Log error, return error response

5. **Storage Errors**:
   - Upload failure → Log error, return error response
   - Download failure → Return 404, suggest retry

### Error Response Format

```json
{
  "error": "Error message",
  "details": "Additional details (optional)",
  "status_code": 500
}
```

### Logging

- Backend: Python `logging` module
- Frontend: Console logging (consider structured logging for production)
- Worker: Print statements with flush (for Railway logs)
- Edge Function: `console.log` (for Supabase logs)

---

## Additional Notes

### Performance Considerations

- **Lazy Imports**: Heavy dependencies imported only when needed (reduces serverless function size)
- **Async Operations**: Non-blocking I/O for database and storage operations
- **Polling**: Progress updates via polling (consider WebSocket for real-time updates)
- **File Storage**: Files stored in Supabase Storage (persistent, accessible from worker)
- **Worker Separation**: Heavy processing separated from API layer (avoids Vercel timeout limits)

### Security Considerations

- **Authentication**: JWT-based authentication via Supabase Auth
- **Authorization**: Row Level Security (RLS) for data isolation
- **API Keys**: Service role key used only server-side
- **CORS**: Configured for specific origins
- **File Validation**: File type and size validation
- **SQL Injection**: Parameterized queries via Supabase client

### Scalability Considerations

- **Stateless API**: API layer is stateless (scales horizontally)
- **Worker Scaling**: Worker can be scaled independently
- **Database**: PostgreSQL via Supabase (scales with Supabase plan)
- **Storage**: Supabase Storage (S3-like, scales automatically)
- **Edge Functions**: Serverless, auto-scales

### Future Enhancements

- WebSocket support for real-time progress updates
- Multi-file processing
- PDF support
- Image OCR
- JSON/XML support
- Multi-tenant architecture
- Direct BITS integration
- Excel to web app generator (Stages 8-12). See `docs/EXCEL_TO_WEB_APP.md`.
- Manual deployment guide for Stage 12: `docs/STAGE12_MANUAL_DEPLOY.md`.

---

**End of Technical Documentation**
