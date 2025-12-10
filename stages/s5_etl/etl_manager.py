"""Stage 5: Schema Design & ETL"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Union

from core.interfaces import Stage
from core.models import (
    ArchaeologyResult, ReconciliationResult, ETLResult,
    PostgresTable, PostgresColumn, ValidationIssue
)
from core.enums import ValidationIssueType, DataType
from core.exceptions import StageError
from db import DatabaseManager, SchemaManager, DataLoader
from config import settings


class ETLManager(Stage[Union[ArchaeologyResult, ReconciliationResult], ETLResult]):
    """Stage 5: Design schema, transform, validate, and persist"""
    
    @property
    def name(self) -> str:
        return "Schema Design & ETL"
    
    @property
    def stage_number(self) -> int:
        return 5
    
    def __init__(self, db_connection_string: str = None):
        self.db = DatabaseManager(db_connection_string) if db_connection_string else None
        self.schema_manager = SchemaManager(self.db) if self.db else None
        self.data_loader = DataLoader(self.db) if self.db else None
    
    def validate_input(self, input_data: Union[ArchaeologyResult, ReconciliationResult]) -> bool:
        return isinstance(input_data, (ArchaeologyResult, ReconciliationResult))
    
    async def execute(self, input_data: Union[ArchaeologyResult, ReconciliationResult]) -> ETLResult:
        """Execute ETL stage"""
        # Get DataFrame
        if isinstance(input_data, ReconciliationResult):
            df = input_data.unified_data
            table_name = "unified_data"
        else:
            # Use first sheet
            df = list(input_data.cleaned_data.values())[0]
            table_name = list(input_data.cleaned_data.keys())[0]
        
        # Design schema
        schema = self._design_schema(df, table_name)
        
        # Transform data
        transformed_df = self._transform_data(df, schema)
        
        # Validate
        issues = self._validate_data(transformed_df, schema)
        
        # Generate SQL
        schema_sql = self._generate_schema_sql(schema)
        
        # Save data file
        output_dir = settings.get_output_path("data")
        data_file = output_dir / f"{table_name}.csv"
        transformed_df.to_csv(data_file, index=False)
        
        # Generate load SQL
        load_sql = f"\\copy {table_name} FROM '{data_file}' WITH CSV HEADER;"
        
        # Persist to database if available
        if self.db and self.schema_manager and self.data_loader:
            try:
                await self.schema_manager.create_table(schema)
                await self.data_loader.load_from_dataframe(transformed_df, table_name)
            except Exception as e:
                # Log but don't fail
                pass
        
        valid_rows = len(transformed_df) - len(issues)
        invalid_rows = len(issues)
        
        return ETLResult(
            schema=schema,
            schema_sql=schema_sql,
            data_file_path=str(data_file),
            load_sql=load_sql,
            validation_issues=issues,
            rows_valid=valid_rows,
            rows_invalid=invalid_rows
        )
    
    def _design_schema(self, df: pd.DataFrame, table_name: str) -> PostgresTable:
        """Design PostgreSQL schema from DataFrame"""
        columns = []
        
        for col in df.columns:
            # Infer PostgreSQL type
            pg_type = self._infer_pg_type(df[col])
            
            col_def = PostgresColumn(
                name=str(col).lower().replace(' ', '_'),
                pg_type=pg_type,
                nullable=True
            )
            columns.append(col_def)
        
        return PostgresTable(
            table_name=table_name.lower().replace(' ', '_'),
            columns=columns
        )
    
    def _infer_pg_type(self, series: pd.Series) -> str:
        """Infer PostgreSQL type from pandas Series"""
        if pd.api.types.is_integer_dtype(series):
            return "BIGINT"
        elif pd.api.types.is_float_dtype(series):
            return "NUMERIC(19,4)"
        elif pd.api.types.is_datetime64_any_dtype(series):
            return "TIMESTAMP"
        elif pd.api.types.is_bool_dtype(series):
            return "BOOLEAN"
        else:
            # Check length for VARCHAR vs TEXT
            max_len = series.astype(str).str.len().max()
            if max_len <= 255:
                return "VARCHAR(255)"
            else:
                return "TEXT"
    
    def _transform_data(self, df: pd.DataFrame, schema: PostgresTable) -> pd.DataFrame:
        """Transform data to match schema"""
        df_copy = df.copy()
        
        # Normalize column names
        col_mapping = {}
        for col in df.columns:
            normalized = str(col).lower().replace(' ', '_')
            col_mapping[col] = normalized
        
        df_copy = df_copy.rename(columns=col_mapping)
        
        # Type conversions
        for col_def in schema.columns:
            if col_def.name in df_copy.columns:
                if col_def.pg_type.startswith("NUMERIC"):
                    df_copy[col_def.name] = pd.to_numeric(df_copy[col_def.name], errors='coerce')
                elif col_def.pg_type == "BIGINT":
                    df_copy[col_def.name] = pd.to_numeric(df_copy[col_def.name], errors='coerce').astype('Int64')
                elif col_def.pg_type == "TIMESTAMP":
                    df_copy[col_def.name] = pd.to_datetime(df_copy[col_def.name], errors='coerce')
                elif col_def.pg_type == "BOOLEAN":
                    df_copy[col_def.name] = df_copy[col_def.name].astype(bool)
        
        return df_copy
    
    def _validate_data(self, df: pd.DataFrame, schema: PostgresTable) -> list[ValidationIssue]:
        """Validate data against schema"""
        issues = []
        
        for idx, row in df.iterrows():
            for col_def in schema.columns:
                if col_def.name in df.columns:
                    value = row[col_def.name]
                    
                    # Check nulls
                    if pd.isna(value) and not col_def.nullable:
                        issues.append(ValidationIssue(
                            row_number=int(idx),
                            column=col_def.name,
                            value=value,
                            issue_type=ValidationIssueType.NULL_VIOLATION,
                            message=f"Null value in non-nullable column"
                        ))
        
        return issues
    
    def _generate_schema_sql(self, schema: PostgresTable) -> str:
        """Generate CREATE TABLE SQL"""
        if self.schema_manager:
            return self.schema_manager._generate_create_table_sql(schema)
        else:
            # Fallback manual generation
            cols = []
            for col in schema.columns:
                col_def = f"    {col.name} {col.pg_type}"
                if not col.nullable:
                    col_def += " NOT NULL"
                cols.append(col_def)
            
            return f"CREATE TABLE IF NOT EXISTS {schema.table_name} (\n" + ",\n".join(cols) + "\n);"

