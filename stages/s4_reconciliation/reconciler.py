"""Stage 4: Cross-Sheet Reconciliation"""

import pandas as pd
from typing import Dict, Any

from core.interfaces import Stage
from core.models import ArchaeologyResult, ReconciliationResult, CanonicalSchema, ColumnMapping, ColumnInference
from core.exceptions import StageError
from utils.fuzzy import fuzzy_match_column
from utils.synonyms import COLUMN_SYNONYMS


class Reconciler(Stage[ArchaeologyResult, ReconciliationResult]):
    """Stage 4: Reconcile multiple sheets into canonical schema"""
    
    @property
    def name(self) -> str:
        return "Cross-Sheet Reconciliation"
    
    @property
    def stage_number(self) -> int:
        return 4
    
    def validate_input(self, input_data: ArchaeologyResult) -> bool:
        return isinstance(input_data, ArchaeologyResult) and len(input_data.maps) > 1
    
    async def execute(self, input_data: ArchaeologyResult) -> ReconciliationResult:
        """Execute reconciliation"""
        if len(input_data.maps) <= 1:
            # Single sheet, no reconciliation needed
            df = list(input_data.cleaned_data.values())[0]
            return ReconciliationResult(
                canonical_schema=CanonicalSchema(
                    columns=[],
                    source_sheets=list(input_data.cleaned_data.keys())
                ),
                mappings=[],
                unified_data=df
            )
        
        # Build canonical schema from all sheets
        all_columns = set()
        for df in input_data.cleaned_data.values():
            all_columns.update(df.columns)
        
        # Create mappings
        mappings = []
        canonical_columns = []
        
        for sheet_name, df in input_data.cleaned_data.items():
            for col in df.columns:
                # Try to find canonical match
                canonical = fuzzy_match_column(str(col), COLUMN_SYNONYMS) or str(col).lower()
                
                mapping = ColumnMapping(
                    sheet_name=sheet_name,
                    original_column=str(col),
                    canonical_column=canonical,
                    confidence=0.8 if canonical != str(col).lower() else 1.0
                )
                mappings.append(mapping)
                
                if canonical not in [c.original_name for c in canonical_columns]:
                    from core.enums import DataType, SemanticRole
                    canonical_columns.append(ColumnInference(
                        original_name=canonical,
                        canonical_name=canonical,
                        data_type=DataType.STRING,  # Default, will be inferred later
                        semantic_role=SemanticRole.UNKNOWN  # Default, will be inferred later
                    ))
        
        # Stack all dataframes
        unified_dfs = []
        for sheet_name, df in input_data.cleaned_data.items():
            df_copy = df.copy()
            df_copy['_source_sheet'] = sheet_name
            df_copy['_source_row'] = range(len(df_copy))
            unified_dfs.append(df_copy)
        
        unified = pd.concat(unified_dfs, ignore_index=True)
        
        return ReconciliationResult(
            canonical_schema=CanonicalSchema(
                columns=canonical_columns,
                source_sheets=list(input_data.cleaned_data.keys())
            ),
            mappings=mappings,
            unified_data=unified
        )

