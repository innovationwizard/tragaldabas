"""Stage 2: Structure Inference"""

import pandas as pd
from typing import Dict, Any

from core.interfaces import Stage
from core.models import ReceptionResult, StructureResult, SheetStructure, ColumnInference, SheetRelationship
from core.enums import DataType, SemanticRole
from core.exceptions import StageError
from llm.client import LLMClient
from llm.prompts import StructurePrompt


class StructureInferrer(Stage[ReceptionResult, StructureResult]):
    """Stage 2: Infer data structure and column semantics"""
    
    @property
    def name(self) -> str:
        return "Structure Inference"
    
    @property
    def stage_number(self) -> int:
        return 2
    
    def __init__(self):
        self.llm = LLMClient()
        self.prompt_builder = StructurePrompt()
    
    def validate_input(self, input_data: ReceptionResult) -> bool:
        return isinstance(input_data, ReceptionResult) and input_data.previews
    
    async def execute(self, input_data: ReceptionResult) -> StructureResult:
        """Execute structure inference"""
        sheets = []
        relationships = []
        
        for preview in input_data.previews:
            df = input_data.raw_data.get(preview.sheet_name)
            if df is None or not isinstance(df, pd.DataFrame):
                continue
            
            # Build context for LLM
            column_preview = ", ".join([str(c) for c in df.columns[:10]])
            sample_data = df.head(10).to_string(max_rows=10, max_cols=10)
            
            context = {
                "sheet_name": preview.sheet_name,
                "column_count": len(df.columns),
                "row_count": len(df),
                "column_preview": column_preview,
                "sample_data": sample_data
            }
            
            prompt = self.prompt_builder.build_prompt(context)
            response = await self.llm.complete(prompt)
            result = self.prompt_builder.parse_response(response)
            
            # Build column inferences
            columns = []
            for col_data in result.get("columns", []):
                # Handle data type enum conversion
                data_type_str = col_data.get("data_type", "string")
                try:
                    data_type = DataType(data_type_str)
                except ValueError:
                    data_type = DataType.STRING
                
                # Handle semantic role enum conversion
                role_str = col_data.get("semantic_role", "unknown")
                try:
                    semantic_role = SemanticRole(role_str)
                except ValueError:
                    semantic_role = SemanticRole.UNKNOWN
                
                col_inf = ColumnInference(
                    original_name=col_data.get("original_name", ""),
                    canonical_name=col_data.get("canonical_name", ""),
                    data_type=data_type,
                    semantic_role=semantic_role,
                    sample_values=col_data.get("sample_values", []),
                    null_percentage=col_data.get("null_percentage", 0.0),
                    unique_count=col_data.get("unique_count", 0)
                )
                columns.append(col_inf)
            
            sheet_struct = SheetStructure(
                sheet_name=preview.sheet_name,
                columns=columns,
                grain_description=result.get("grain_description", ""),
                row_count=len(df),
                primary_key_candidates=result.get("primary_key_candidates", [])
            )
            sheets.append(sheet_struct)
        
        return StructureResult(sheets=sheets, sheet_relationships=relationships)

