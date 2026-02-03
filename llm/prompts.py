"""LLM prompt templates for various tasks"""

import json
import re
from typing import Dict, Any
from core.interfaces import LLMTask


class ClassificationPrompt(LLMTask):
    """Prompt for content classification (Stage 1)"""
    
    @property
    def prompt_template(self) -> str:
        return """Analyze this file and classify its content.

FILE: {file_name}
TYPE: {file_type}
SHEETS: {sheets}
PREVIEW ROWS: {preview_rows}

Analyze the content and determine:
1. Primary type: narrative (text documents), structured (tabular data), or mixed
2. Domain: financial, operational, sales, hr, inventory, or general
3. Entity name: company, department, product line, etc.
4. Time period: start and end dates if detectable

Respond with JSON only:
{{
    "primary_type": "narrative|structured|mixed",
    "domain": "financial|operational|sales|hr|inventory|general",
    "entity_name": "<string or null>",
    "time_period_start": "<ISO date or null>",
    "time_period_end": "<ISO date or null>",
    "confidence": <float 0-1>,
    "reasoning": "<brief explanation>"
}}"""
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        sheets_str = ", ".join(context.get("sheets", []))
        preview = context.get("preview", "")
        
        return self.prompt_template.format(
            file_name=context.get("file_name", "unknown"),
            file_type=context.get("file_type", "unknown"),
            sheets=sheets_str or "single sheet",
            preview_rows=preview[:2000]  # Limit preview size
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse classification response"""
        clean = self._clean_json_response(response)
        return self._robust_json_load(clean, response)


class StructurePrompt(LLMTask):
    """Prompt for structure inference (Stage 2)"""
    
    @property
    def prompt_template(self) -> str:
        return """Analyze the structure of this data.

SHEET: {sheet_name}
COLUMNS: {column_count}
ROWS: {row_count}

COLUMN PREVIEW:
{column_preview}

SAMPLE DATA (first 10 rows):
{sample_data}

For each column, determine:
1. Semantic meaning (what does it represent?)
2. Data type (string, integer, decimal, date, boolean, currency, percentage)
3. Semantic role (identifier, dimension, measure, metadata)
4. Sample values

Also identify:
- Grain: what does one row represent?
- Primary key candidates
- Relationships to other sheets (if applicable)

Respond with JSON only:
{{
    "columns": [
        {{
            "original_name": "<string>",
            "canonical_name": "<string>",
            "data_type": "<string|integer|decimal|date|datetime|boolean|currency|percentage>",
            "semantic_role": "<identifier|dimension|measure|metadata|unknown>",
            "sample_values": [<any>, ...],
            "null_percentage": <float>,
            "unique_count": <int>
        }},
        ...
    ],
    "grain_description": "<string>",
    "primary_key_candidates": ["<column_name>", ...],
    "relationships": [
        {{
            "sheet": "<sheet_name>",
            "shared_columns": ["<col>", ...],
            "relationship_type": "<string>"
        }},
        ...
    ]
}}"""
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        return self.prompt_template.format(
            sheet_name=context.get("sheet_name", "unknown"),
            column_count=context.get("column_count", 0),
            row_count=context.get("row_count", 0),
            column_preview=context.get("column_preview", ""),
            sample_data=context.get("sample_data", "")
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse structure inference response"""
        clean = self._clean_json_response(response)
        return self._robust_json_load(clean, response)


class ArchaeologyPrompt(LLMTask):
    """Prompt for data archaeology (Stage 3)"""
    
    @property
    def prompt_template(self) -> str:
        return """Analyze this spreadsheet snapshot and identify where the actual data lives.

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
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        return self.prompt_template.format(
            sheet_name=context.get("sheet_name", "unknown"),
            total_rows=context.get("total_rows", 0),
            total_cols=context.get("total_cols", 0),
            preview_rows=context.get("preview_rows", 50),
            snapshot=context.get("snapshot", "")
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse archaeology response"""
        clean = self._clean_json_response(response)
        return self._robust_json_load(clean, response)


class AnalysisPrompt(LLMTask):
    """Prompt for data analysis (Stage 6)"""
    
    @property
    def prompt_template(self) -> str:
        return """Analyze this dataset and generate insights.

DOMAIN: {domain}
TABLE: {table_name}
ROWS: {row_count}
COLUMNS: {columns}

DATA SUMMARY:
{data_summary}

Generate domain-specific analysis:
- Key metrics and KPIs
- Trends and patterns
- Anomalies and outliers
- Comparisons (YoY, MoM, benchmarks)
- Business implications

Respond with JSON:
{{
    "metrics_computed": ["<metric>", ...],
    "patterns_detected": ["<pattern>", ...],
    "preliminary_insights": [
        {{
            "headline": "<string ≤15 words>",
            "detail": "<string ≤50 words>",
            "metric": "<string>",
            "value": <number>,
            "comparison": "<string>",
            "delta": <number>,
            "delta_percent": <number>,
            "implication": "<string>",
            "severity": "info|warning|critical",
            "visualization_hint": "trend_line|bar_chart|pie_chart|table|metric_callout|none"
        }},
        ...
    ]
}}"""
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        return self.prompt_template.format(
            domain=context.get("domain", "general"),
            table_name=context.get("table_name", "unknown"),
            row_count=context.get("row_count", 0),
            columns=", ".join(context.get("columns", [])),
            data_summary=context.get("data_summary", "")
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse analysis response"""
        clean = self._clean_json_response(response)
        return self._robust_json_load(clean, response)


class InsightsPrompt(LLMTask):
    """Prompt for insight qualification and filtering (Stage 6)"""
    
    @property
    def prompt_template(self) -> str:
        return """Review these preliminary insights and filter for relevancy.

DOMAIN: {domain}
INSIGHTS: {insights}

Filter criteria:
- Include if: variance >10%, trend reversal, concentration risk (>50%), anomaly (>2 std dev), material value
- Exclude if: obvious from raw data, trivial variance, insufficient data

Respond with JSON:
{{
    "qualified_insights": [
        {{
            "id": "<unique_id>",
            "headline": "<string>",
            "detail": "<string>",
            "evidence": {{
                "metric": "<string>",
                "value": <number>,
                "comparison": "<string>",
                "delta": <number>,
                "delta_percent": <number>
            }},
            "implication": "<string>",
            "severity": "info|warning|critical",
            "visualization_hint": "<type>",
            "included": <boolean>
        }},
        ...
    ]
}}"""
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        insights_json = json.dumps(context.get("insights", []), indent=2)
        return self.prompt_template.format(
            domain=context.get("domain", "general"),
            insights=insights_json
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse insights response"""
        clean = self._clean_json_response(response)
        return self._robust_json_load(clean, response)
    
    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response from markdown or extra text"""
        clean = response.strip()
        
        # Remove markdown code blocks
        if clean.startswith("```"):
            parts = clean.split("```")
            if len(parts) >= 3:
                clean = parts[1]
                if clean.startswith("json"):
                    clean = clean[4:]
        
        # Try to extract JSON object
        start_idx = clean.find("{")
        end_idx = clean.rfind("}")
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean = clean[start_idx:end_idx + 1]
        
        return clean.strip()

    def _robust_json_load(self, primary: str, fallback: str) -> Dict[str, Any]:
        """Best-effort JSON parsing with recovery steps."""
        def _strip_trailing_commas(text: str) -> str:
            return re.sub(r",\s*([}\]])", r"\1", text)

        def _fix_backslashes(text: str) -> str:
            # Escape stray backslashes that break JSON parsing.
            return re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text)

        def _balanced_json(text: str) -> str:
            start = text.find("{")
            if start == -1:
                return text
            depth = 0
            for idx in range(start, len(text)):
                char = text[idx]
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start:idx + 1]
            return text[start:]

        def _find_first_json_object(text: str) -> Optional[Dict[str, Any]]:
            decoder = json.JSONDecoder()
            for idx, char in enumerate(text):
                if char != "{":
                    continue
                try:
                    parsed, _ = decoder.raw_decode(text[idx:])
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    continue
            return None

        attempts = [
            primary,
            _strip_trailing_commas(primary),
            _fix_backslashes(primary),
            _balanced_json(primary),
            _strip_trailing_commas(_balanced_json(primary)),
            _fix_backslashes(_balanced_json(primary)),
            _balanced_json(fallback),
            _strip_trailing_commas(_balanced_json(fallback)),
            _fix_backslashes(_balanced_json(fallback)),
        ]
        last_error = None
        for candidate in attempts:
            try:
                parsed = _find_first_json_object(candidate)
                if parsed is not None:
                    return parsed
            except Exception:
                pass
        for candidate in attempts:
            try:
                return json.loads(candidate)
            except Exception as exc:
                last_error = exc
                continue
        raise last_error or json.JSONDecodeError("Invalid JSON", primary, 0)


# Add helper method to all prompt classes
for cls in [ClassificationPrompt, StructurePrompt, ArchaeologyPrompt, AnalysisPrompt, InsightsPrompt]:
    cls._clean_json_response = InsightsPrompt._clean_json_response
    cls._robust_json_load = InsightsPrompt._robust_json_load

