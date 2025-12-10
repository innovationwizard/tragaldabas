"""Data loading operations"""

import io
from typing import Any
import pandas as pd

from core.exceptions import DatabaseError
from .connection import DatabaseManager


class DataLoader:
    """Load data into PostgreSQL"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def load_from_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        truncate: bool = False
    ) -> int:
        """
        Load DataFrame into PostgreSQL table using batch INSERT
        
        Args:
            df: DataFrame to load
            table_name: Target table name
            truncate: Whether to truncate table before loading
            
        Returns:
            Number of rows loaded
        """
        if truncate:
            await self.db.execute_write(f"TRUNCATE TABLE {table_name};")
        
        # Use batch INSERT for simplicity
        async with self.db.get_connection() as conn:
            # Prepare columns
            columns = list(df.columns)
            col_names = ', '.join(columns)
            
            # Insert in batches
            batch_size = 1000
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                values_list = []
                for _, row in batch.iterrows():
                    values = tuple(None if pd.isna(val) else val for val in row)
                    values_list.append(values)
                
                # Build query with proper placeholders
                placeholders = ', '.join([f'${j+1}' for j in range(len(columns))])
                query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
                await conn.executemany(query, values_list)
        
        return len(df)
    
    async def load_from_file(
        self,
        file_path: str,
        table_name: str,
        truncate: bool = False
    ) -> int:
        """
        Load data from file into PostgreSQL table
        
        Args:
            file_path: Path to CSV/TSV file
            table_name: Target table name
            truncate: Whether to truncate table before loading
            
        Returns:
            Number of rows loaded
        """
        if truncate:
            await self.db.execute_write(f"TRUNCATE TABLE {table_name};")
        
        # Read file and determine format
        if file_path.endswith('.tsv'):
            df = pd.read_csv(file_path, sep='\t', na_values=['\\N'])
        else:
            df = pd.read_csv(file_path, na_values=['\\N'])
        
        return await self.load_from_dataframe(df, table_name, truncate=False)

