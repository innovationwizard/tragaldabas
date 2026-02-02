"""
Tragaldabas - Stage 3: Data Archaeology Prototype
Finds signal in human-authored chaos.

Note: Stages 8-12 extend the pipeline to Excel-to-web-app generation.
See docs/EXCEL_TO_WEB_APP.md for the full extension architecture.

Usage:
    python archaeology_prototype.py <excel_file> [--sheet <name>]

Requirements:
    pip install pandas openpyxl anthropic rapidfuzz python-dotenv
"""

import os
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

import pandas as pd
from anthropic import Anthropic
from rapidfuzz import fuzz, process
from dotenv import load_dotenv

load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LLM_MODEL = "claude-sonnet-4-20250514"
MAX_PREVIEW_ROWS = 50
FUZZY_MATCH_THRESHOLD = 80


# ═══════════════════════════════════════════════════════════════════════════════
# SYNONYM DICTIONARY
# ═══════════════════════════════════════════════════════════════════════════════

COLUMN_SYNONYMS = {
    "date": ["fecha", "dt", "date:", "date_col", "period", "periodo", "dia", "day"],
    "amount": ["amt", "monto", "value", "total", "sum", "importe", "valor"],
    "description": ["desc", "descripcion", "detail", "detalle", "notes", "nota", "concepto"],
    "quantity": ["qty", "cantidad", "units", "count", "pieces", "unidades", "cant"],
    "price": ["precio", "unit_price", "rate", "tarifa", "costo", "cost"],
    "customer": ["cliente", "client", "buyer", "account", "cuenta"],
    "product": ["producto", "item", "sku", "article", "articulo"],
    "revenue": ["ingreso", "sales", "ventas", "income", "ingresos"],
    "expense": ["gasto", "cost", "costo", "egreso", "gastos"],
    "balance": ["saldo", "remaining", "outstanding", "remanente"],
    "name": ["nombre", "nm", "nombre_completo", "full_name"],
    "id": ["codigo", "code", "identifier", "clave", "numero", "number", "no", "num"],
    "month": ["mes", "monthly", "mensual"],
    "year": ["año", "anio", "yearly", "anual"],
    "category": ["categoria", "cat", "type", "tipo", "clasificacion"],
    "status": ["estado", "estatus", "situacion"],
    "comments": ["comentarios", "observaciones", "remarks", "obs"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ArchaeologyMap:
    """Extraction coordinates for a sheet"""
    sheet_name: str
    header_row: Optional[int] = None
    data_start_row: int = 0
    data_end_row: Optional[int] = None
    noise_rows: list[int] = field(default_factory=list)
    noise_columns: list[str] = field(default_factory=list)
    total_rows: list[int] = field(default_factory=list)
    has_header: bool = True
    confidence: float = 0.0
    llm_reasoning: str = ""


@dataclass 
class ArchaeologyResult:
    """Complete archaeology output"""
    original_shape: tuple[int, int]
    cleaned_shape: tuple[int, int]
    archaeology_map: ArchaeologyMap
    original_columns: list[str]
    cleaned_columns: list[str]
    normalized_columns: list[str]
    rows_removed: int
    columns_removed: int


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_snapshot(df: pd.DataFrame, max_rows: int = MAX_PREVIEW_ROWS) -> str:
    """
    Render DataFrame as text table for LLM analysis.
    Shows row numbers and column letters like Excel.
    """
    preview = df.head(max_rows).copy()
    
    # Generate Excel-style column letters
    def col_letter(n):
        result = ""
        while n >= 0:
            result = chr(n % 26 + ord('A')) + result
            n = n // 26 - 1
        return result
    
    col_letters = [col_letter(i) for i in range(len(preview.columns))]
    
    # Calculate column widths (max 25 chars)
    col_widths = []
    for i, col in enumerate(preview.columns):
        max_width = max(
            len(col_letters[i]),
            max((len(str(v)[:25]) for v in preview.iloc[:, i]), default=0)
        )
        col_widths.append(min(max_width, 25))
    
    lines = []
    
    # Header row with column letters
    header = "ROW  │ " + " │ ".join(
        col_letters[i].center(col_widths[i]) 
        for i in range(len(col_letters))
    )
    lines.append(header)
    lines.append("─" * len(header))
    
    # Data rows
    for row_idx in range(len(preview)):
        row_num = str(row_idx + 1).rjust(4)
        cells = []
        for col_idx in range(len(preview.columns)):
            val = preview.iloc[row_idx, col_idx]
            if pd.isna(val):
                cell_str = ""
            else:
                cell_str = str(val)[:25]
            cells.append(cell_str.ljust(col_widths[col_idx]))
        lines.append(f"{row_num} │ " + " │ ".join(cells))
    
    # Add indicator if truncated
    if len(df) > max_rows:
        lines.append(f"... ({len(df) - max_rows} more rows)")
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# LLM ARCHAEOLOGY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

ARCHAEOLOGY_PROMPT = """Analyze this spreadsheet snapshot and identify where the actual data lives.

CONTEXT:
- This is raw data exported from a human-created spreadsheet
- Humans often add titles, subtitles, blank rows, comments, totals
- Your job: find the real tabular data boundaries

SHEET: {sheet_name}
TOTAL DIMENSIONS: {total_rows} rows × {total_cols} columns

SNAPSHOT (first {preview_rows} rows):
{snapshot}

═══════════════════════════════════════════════════════════════════════════════

ANALYZE AND IDENTIFY:

1. HEADER ROW: Which row (1-indexed) contains column headers?
   - Look for: text labels, distinct values, no numbers, spans most columns
   - If no clear header exists, set to null

2. DATA START: Which row does actual data begin?
   - First row with consistent data pattern across columns

3. DATA END: Which row does data end? (null if goes to bottom)
   - Look for: summary rows, totals, footnotes after data

4. NOISE ROWS: Which rows are noise? (titles, subtitles, blanks, section headers)
   - Completely blank rows
   - Single-cell rows (titles/subtitles)
   - Section dividers

5. NOISE COLUMNS: Which columns (by letter) are noise?
   - Entirely blank columns
   - Comment/note columns (sparse, long text)

6. TOTAL/SUMMARY ROWS: Which rows contain totals or summaries?
   - Look for: "Total", "Sum", "Grand Total", "Subtotal" keywords
   - Rows that aggregate data from above

═══════════════════════════════════════════════════════════════════════════════

Respond with JSON only. No markdown, no explanation outside JSON:

{{
    "reasoning": "<brief explanation of what you see>",
    "header_row": <int 1-indexed or null if no header>,
    "data_start_row": <int 1-indexed>,
    "data_end_row": <int 1-indexed or null if data goes to end>,
    "noise_rows": [<int>, ...],
    "noise_columns": ["<letter>", ...],
    "total_rows": [<int>, ...],
    "has_header": <boolean>,
    "confidence": <float 0-1>
}}"""


def analyze_with_llm(
    df: pd.DataFrame, 
    sheet_name: str,
    client: Anthropic
) -> ArchaeologyMap:
    """Use Claude to analyze sheet structure"""
    
    snapshot = build_snapshot(df)
    
    prompt = ARCHAEOLOGY_PROMPT.format(
        sheet_name=sheet_name,
        total_rows=len(df),
        total_cols=len(df.columns),
        preview_rows=min(len(df), MAX_PREVIEW_ROWS),
        snapshot=snapshot
    )
    
    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Parse response
    response_text = response.content[0].text.strip()
    
    # Clean markdown if present
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    
    result = json.loads(response_text)
    
    return ArchaeologyMap(
        sheet_name=sheet_name,
        header_row=result.get("header_row"),
        data_start_row=result.get("data_start_row", 1),
        data_end_row=result.get("data_end_row"),
        noise_rows=result.get("noise_rows", []),
        noise_columns=result.get("noise_columns", []),
        total_rows=result.get("total_rows", []),
        has_header=result.get("has_header", True),
        confidence=result.get("confidence", 0.5),
        llm_reasoning=result.get("reasoning", "")
    )


# ═══════════════════════════════════════════════════════════════════════════════
# COLUMN NORMALIZER
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_column_name(raw_name: str) -> str:
    """
    Normalize a single column name:
    1. Lowercase
    2. Strip whitespace
    3. Replace spaces/special chars with underscore
    4. Fuzzy match to canonical synonym
    """
    if pd.isna(raw_name) or raw_name is None:
        return "unnamed"
    
    # Basic normalization
    name = str(raw_name).lower().strip()
    
    # Remove special characters, keep alphanumeric and underscore
    normalized = ""
    for char in name:
        if char.isalnum():
            normalized += char
        elif char in " -_":
            normalized += "_"
    
    # Collapse multiple underscores
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    
    normalized = normalized.strip("_")
    
    if not normalized:
        return "unnamed"
    
    # Fuzzy match against synonyms
    best_match = None
    best_score = 0
    
    for canonical, synonyms in COLUMN_SYNONYMS.items():
        # Check exact match first
        if normalized in synonyms or normalized == canonical:
            return canonical
        
        # Fuzzy match
        for synonym in synonyms:
            score = fuzz.ratio(normalized, synonym)
            if score > best_score and score >= FUZZY_MATCH_THRESHOLD:
                best_score = score
                best_match = canonical
    
    return best_match if best_match else normalized


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Normalize all column names, handling duplicates"""
    
    normalized = []
    seen = {}
    
    for col in df.columns:
        norm = normalize_column_name(col)
        
        # Handle duplicates
        if norm in seen:
            seen[norm] += 1
            norm = f"{norm}_{seen[norm]}"
        else:
            seen[norm] = 0
        
        normalized.append(norm)
    
    df_copy = df.copy()
    df_copy.columns = normalized
    
    return df_copy, normalized


# ═══════════════════════════════════════════════════════════════════════════════
# DATA EXTRACTOR
# ═══════════════════════════════════════════════════════════════════════════════

def col_letter_to_index(letter: str) -> int:
    """Convert Excel column letter to 0-indexed integer"""
    result = 0
    for char in letter.upper():
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result - 1


def extract_clean_data(
    df: pd.DataFrame, 
    arch_map: ArchaeologyMap
) -> pd.DataFrame:
    """Apply archaeology map to extract clean data"""
    
    # Convert 1-indexed to 0-indexed
    header_idx = arch_map.header_row - 1 if arch_map.header_row else None
    data_start_idx = arch_map.data_start_row - 1
    data_end_idx = arch_map.data_end_row - 1 if arch_map.data_end_row else len(df) - 1
    noise_rows_idx = [r - 1 for r in arch_map.noise_rows]
    total_rows_idx = [r - 1 for r in arch_map.total_rows]
    
    # Convert column letters to indices
    noise_col_indices = [col_letter_to_index(c) for c in arch_map.noise_columns]
    
    # Determine rows to keep
    rows_to_exclude = set(noise_rows_idx + total_rows_idx)
    if header_idx is not None:
        rows_to_exclude.add(header_idx)
    
    keep_rows = [
        i for i in range(data_start_idx, data_end_idx + 1)
        if i not in rows_to_exclude
    ]
    
    # Determine columns to keep
    keep_cols = [
        i for i in range(len(df.columns))
        if i not in noise_col_indices
    ]
    
    # Extract subset
    clean_df = df.iloc[keep_rows, keep_cols].copy()
    
    # Set header if present
    if arch_map.has_header and header_idx is not None:
        header_values = df.iloc[header_idx, keep_cols].values
        clean_df.columns = header_values
    
    # Reset index
    clean_df = clean_df.reset_index(drop=True)
    
    # Remove completely empty rows that might have slipped through
    clean_df = clean_df.dropna(how='all')
    
    return clean_df


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ARCHAEOLOGY PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_archaeology(
    file_path: str,
    sheet_name: Optional[str] = None,
    verbose: bool = True
) -> ArchaeologyResult:
    """
    Complete archaeology pipeline for a single sheet.
    
    Args:
        file_path: Path to Excel file
        sheet_name: Specific sheet to process (default: first sheet)
        verbose: Print progress
    
    Returns:
        ArchaeologyResult with cleaned data and metadata
    """
    
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set in environment")
    
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Load file
    if verbose:
        print(f"📂 Loading: {file_path}")
    
    xl = pd.ExcelFile(file_path)
    
    if sheet_name is None:
        sheet_name = xl.sheet_names[0]
    elif sheet_name not in xl.sheet_names:
        raise ValueError(f"Sheet '{sheet_name}' not found. Available: {xl.sheet_names}")
    
    # Read without assuming header
    df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
    original_shape = df.shape
    original_columns = list(df.columns)
    
    if verbose:
        print(f"📊 Sheet: {sheet_name}")
        print(f"   Original shape: {original_shape[0]} rows × {original_shape[1]} columns")
    
    # Build and display snapshot
    if verbose:
        print(f"\n{'═' * 70}")
        print("SNAPSHOT (first 30 rows):")
        print('═' * 70)
        print(build_snapshot(df, max_rows=30))
        print('═' * 70)
    
    # LLM Analysis
    if verbose:
        print(f"\n🔍 Analyzing structure with Claude...")
    
    arch_map = analyze_with_llm(df, sheet_name, client)
    
    if verbose:
        print(f"\n📋 Archaeology Map:")
        print(f"   Reasoning: {arch_map.llm_reasoning}")
        print(f"   Header row: {arch_map.header_row}")
        print(f"   Data rows: {arch_map.data_start_row} → {arch_map.data_end_row or 'end'}")
        print(f"   Noise rows: {arch_map.noise_rows}")
        print(f"   Noise columns: {arch_map.noise_columns}")
        print(f"   Total rows: {arch_map.total_rows}")
        print(f"   Has header: {arch_map.has_header}")
        print(f"   Confidence: {arch_map.confidence:.0%}")
    
    # Extract clean data
    if verbose:
        print(f"\n🧹 Extracting clean data...")
    
    clean_df = extract_clean_data(df, arch_map)
    cleaned_columns = list(clean_df.columns)
    
    # Normalize column names
    if verbose:
        print(f"🏷️  Normalizing column names...")
    
    clean_df, normalized_columns = normalize_columns(clean_df)
    
    cleaned_shape = clean_df.shape
    rows_removed = original_shape[0] - cleaned_shape[0]
    cols_removed = original_shape[1] - cleaned_shape[1]
    
    if verbose:
        print(f"\n✅ Archaeology complete:")
        print(f"   Cleaned shape: {cleaned_shape[0]} rows × {cleaned_shape[1]} columns")
        print(f"   Rows removed: {rows_removed}")
        print(f"   Columns removed: {cols_removed}")
        print(f"\n   Column mapping:")
        for orig, norm in zip(cleaned_columns, normalized_columns):
            if str(orig) != norm:
                print(f"      '{orig}' → '{norm}'")
            else:
                print(f"      '{orig}' (unchanged)")
    
    # Preview cleaned data
    if verbose:
        print(f"\n{'═' * 70}")
        print("CLEANED DATA (first 10 rows):")
        print('═' * 70)
        print(clean_df.head(10).to_string())
        print('═' * 70)
    
    return ArchaeologyResult(
        original_shape=original_shape,
        cleaned_shape=cleaned_shape,
        archaeology_map=arch_map,
        original_columns=original_columns,
        cleaned_columns=cleaned_columns,
        normalized_columns=normalized_columns,
        rows_removed=rows_removed,
        columns_removed=cols_removed
    ), clean_df


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Tragaldabas Data Archaeology - Find signal in chaos"
    )
    parser.add_argument("file", type=Path, help="Excel file to analyze")
    parser.add_argument("--sheet", type=str, help="Specific sheet name")
    parser.add_argument("--output", type=Path, help="Output cleaned CSV")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    
    args = parser.parse_args()
    
    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return 1
    
    try:
        result, clean_df = run_archaeology(
            str(args.file),
            sheet_name=args.sheet,
            verbose=not args.quiet
        )
        
        if args.output:
            clean_df.to_csv(args.output, index=False)
            print(f"\n💾 Saved cleaned data to: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())



# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
 ═══════════════════════════════════════════════════════════════════════════════
 # ═══════════════════════════════════════════════════════════════════════════════
 # ═══════════════════════════════════════════════════════════════════════════════
To test:
bash 
# Install dependencies
pip install pandas openpyxl anthropic rapidfuzz python-dotenv

# Set API key
export ANTHROPIC_API_KEY="your-key"

# Run on dirty Excel
python archaeology_prototype.py dirty_data.xlsx

# Specific sheet + save output
python archaeology_prototype.py chaos.xlsx --sheet "Q3 Data" --output cleaned.csv
