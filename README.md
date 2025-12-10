# Tragaldabas - Universal Data Ingestor

AI-powered universal data ingestor that transforms raw, unstructured client files into actionable business intelligence.

## Features

- **7-Stage Pipeline**: Reception → Classification → Structure → Archaeology → Reconciliation → ETL → Analysis → Output
- **Multi-Format Support**: Excel (.xlsx, .xls), CSV, Word (.docx)
- **LLM-Powered**: Multi-provider support (Claude, OpenAI, Gemini) with automatic fallback
- **Data Archaeology**: Automatically finds signal in messy human-created spreadsheets
- **PostgreSQL Integration**: Direct database connection with schema generation
- **Executive Output**: Generates PowerPoint presentations and text summaries

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Create a `.env` file with at least one LLM API key:

```env
ANTHROPIC_API_KEY=your-key-here
# OR
OPENAI_API_KEY=your-key-here
# OR
GOOGLE_API_KEY=your-key-here
GEMINI_MODEL_ID=gemini-1.5-pro
GEMINI_FALLBACK_MODEL_ID=gemini-2.5-flash

# Optional: Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/database
```

## Usage

```bash
# Process a file
python main.py data/file.xlsx

# With database connection
python main.py data/file.xlsx --db postgresql://user:pass@localhost/db

# Custom output directory
python main.py data/file.xlsx --output-dir ./my_output
```

## Pipeline Stages

1. **Reception**: Parse and validate input file
2. **Classification**: Detect content type and domain (LLM-powered)
3. **Structure Inference**: Infer column semantics and data grain (LLM-powered)
4. **Data Archaeology**: Find data boundaries, remove noise (LLM-powered)
5. **Reconciliation**: Unify multi-sheet files into canonical schema
6. **Schema & ETL**: Design PostgreSQL schema, transform, validate, persist
7. **Analysis**: Generate insights and metrics (LLM-powered)
8. **Output**: Create PowerPoint slides and text summaries

## Output Structure

```
output/
├── data/              # Cleaned CSV files
├── insights/           # Text and markdown summaries
├── presentations/     # PowerPoint files
└── sql/               # Schema SQL files
```

## Architecture

- **Core**: Models, enums, interfaces, exceptions
- **Stages**: 7-stage pipeline implementation
- **LLM**: Multi-provider client with fallback
- **DB**: PostgreSQL connection and schema management
- **UI**: Progress tracking and user prompts
- **Utils**: Encoding detection, fuzzy matching, synonyms

## Design Principles

1. **Never fabricate data** - No sample or mock data
2. **Relevancy over volume** - Only material insights
3. **Transparency** - Real-time progress visibility
4. **Graceful uncertainty** - Ask yes/no questions when ambiguous

## Requirements

- Python 3.11+
- PostgreSQL 15+ (optional, for direct database connection)
- At least one LLM API key (Anthropic, OpenAI, or Gemini)

## Supabase Integration

For Supabase-specific setup and best practices, see [docs/SUPABASE.md](docs/SUPABASE.md).

Quick setup:
```bash
# Configure Supabase connection in .env
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true

# Run setup script
python scripts/setup_supabase.py --all
```

## License

See LICENSE file for details.
