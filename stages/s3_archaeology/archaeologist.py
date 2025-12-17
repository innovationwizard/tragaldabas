"""Stage 3: Data Archaeology"""

import pandas as pd
from typing import Dict, Any

from core.interfaces import Stage
from core.models import (
    ReceptionResult, StructureResult, ArchaeologyResult, ArchaeologyMap
)
from core.exceptions import StageError
from llm.client import LLMClient
from llm.prompts import ArchaeologyPrompt
from utils.synonyms import normalize_column_name
from config import settings


class Archaeologist(Stage[Dict[str, Any], ArchaeologyResult]):
    """Stage 3: Data Archaeology - Find signal in chaos"""
    
    @property
    def name(self) -> str:
        return "Data Archaeology"
    
    @property
    def stage_number(self) -> int:
        return 3
    
    def __init__(self):
        self.llm = LLMClient()
        self.prompt_builder = ArchaeologyPrompt()
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input"""
        return (
            "reception" in input_data
            and "structure" in input_data
            and input_data["reception"] is not None
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> ArchaeologyResult:
        """Execute archaeology stage"""
        reception: ReceptionResult = input_data["reception"]
        structure: StructureResult = input_data.get("structure")
        
        maps = []
        cleaned_data = {}
        
        for preview in reception.previews:
            # Get raw DataFrame
            df = reception.raw_data.get(preview.sheet_name)
            if df is None or not isinstance(df, pd.DataFrame):
                continue
            
            # Build snapshot for LLM
            snapshot = self._build_snapshot(df)
            
            # LLM analysis
            context = {
                "sheet_name": preview.sheet_name,
                "total_rows": len(df),
                "total_cols": len(df.columns),
                "preview_rows": min(len(df), settings.ARCHAEOLOGY_MAX_PREVIEW_ROWS),
                "snapshot": snapshot
            }
            
            prompt = self.prompt_builder.build_prompt(context)
            response = await self.llm.complete(prompt)
            result = self.prompt_builder.parse_response(response)
            
            # Build archaeology map
            # Handle None values - .get() only uses default if key doesn't exist, not if value is None
            data_start_row = result.get("data_start_row")
            if data_start_row is None:
                data_start_row = 1
            
            arch_map = ArchaeologyMap(
                sheet_name=preview.sheet_name,
                header_row=result.get("header_row"),
                data_start_row=data_start_row,
                data_end_row=result.get("data_end_row"),
                noise_rows=result.get("noise_rows", []),
                noise_columns=result.get("noise_columns", []),
                total_rows=result.get("total_rows", []),
                has_header=result.get("has_header", True),
                confidence=result.get("confidence", 0.5),
                llm_reasoning=result.get("reasoning", "")
            )
            
            # Extract clean data
            clean_df = self._extract_clean_data(df, arch_map)
            
            # Normalize column names
            clean_df = self._normalize_columns(clean_df)
            
            maps.append(arch_map)
            cleaned_data[preview.sheet_name] = clean_df
        
        return ArchaeologyResult(maps=maps, cleaned_data=cleaned_data)
    
    def _build_snapshot(self, df: pd.DataFrame) -> str:
        """Build text snapshot for LLM"""
        preview = df.head(settings.ARCHAEOLOGY_MAX_PREVIEW_ROWS).copy()
        
        # Generate column letters
        col_letters = []
        for i in range(len(preview.columns)):
            result = ""
            n = i
            while n >= 0:
                result = chr(n % 26 + ord('A')) + result
                n = n // 26 - 1
            col_letters.append(result)
        
        # Calculate column widths
        col_widths = []
        for i in range(len(preview.columns)):
            max_width = max(
                len(col_letters[i]),
                max((len(str(v)[:25]) for v in preview.iloc[:, i]), default=0)
            )
            col_widths.append(min(max_width, 25))
        
        lines = []
        
        # Header
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
        
        if len(df) > settings.ARCHAEOLOGY_MAX_PREVIEW_ROWS:
            lines.append(f"... ({len(df) - settings.ARCHAEOLOGY_MAX_PREVIEW_ROWS} more rows)")
        
        return "\n".join(lines)
    
    def _extract_clean_data(self, df: pd.DataFrame, arch_map: ArchaeologyMap) -> pd.DataFrame:
        """Extract clean data using archaeology map"""
        # Convert 1-indexed to 0-indexed
        header_idx = arch_map.header_row - 1 if arch_map.header_row else None
        data_start_idx = arch_map.data_start_row - 1
        data_end_idx = arch_map.data_end_row - 1 if arch_map.data_end_row else len(df)
        noise_rows_idx = [r - 1 for r in arch_map.noise_rows]
        total_rows_idx = [r - 1 for r in arch_map.total_rows]
        
        # Convert column letters to indices
        noise_col_indices = []
        for letter in arch_map.noise_columns:
            idx = 0
            for char in letter.upper():
                idx = idx * 26 + (ord(char) - ord('A') + 1)
            noise_col_indices.append(idx - 1)
        
        # Determine rows to keep
        rows_to_exclude = set(noise_rows_idx + total_rows_idx)
        if header_idx is not None:
            rows_to_exclude.add(header_idx)
        
        keep_rows = [
            i for i in range(data_start_idx, data_end_idx)
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
            clean_df.columns = [str(v) for v in header_values]
        
        # Remove completely empty rows
        clean_df = clean_df.dropna(how='all')
        
        return clean_df.reset_index(drop=True)
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names"""
        normalized = []
        seen = {}
        
        for col in df.columns:
            norm = normalize_column_name(str(col))
            
            # Handle duplicates
            if norm in seen:
                seen[norm] += 1
                norm = f"{norm}_{seen[norm]}"
            else:
                seen[norm] = 0
            
            normalized.append(norm)
        
        df_copy = df.copy()
        df_copy.columns = normalized
        return df_copy

