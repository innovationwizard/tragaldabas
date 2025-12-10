"""Schema management operations"""

from typing import List
from core.models import PostgresTable, PostgresColumn
from core.exceptions import DatabaseError
from .connection import DatabaseManager


class SchemaManager:
    """PostgreSQL schema operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_table(self, table: PostgresTable, if_not_exists: bool = True) -> None:
        """Create table from PostgresTable model"""
        sql = self._generate_create_table_sql(table, if_not_exists)
        
        try:
            await self.db.execute_write(sql)
        except Exception as e:
            raise DatabaseError(f"Failed to create table {table.table_name}: {e}") from e
    
    async def drop_table(self, table_name: str, if_exists: bool = True) -> None:
        """Drop table"""
        sql = f"DROP TABLE {'IF EXISTS' if if_exists else ''} {table_name} CASCADE;"
        
        try:
            await self.db.execute_write(sql)
        except Exception as e:
            raise DatabaseError(f"Failed to drop table {table_name}: {e}") from e
    
    async def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = $1
            );
        """
        
        try:
            result = await self.db.execute_one(query, table_name)
            return result[0] if result else False
        except Exception:
            return False
    
    def _generate_create_table_sql(self, table: PostgresTable, if_not_exists: bool = True) -> str:
        """Generate CREATE TABLE SQL"""
        columns = []
        
        for col in table.columns:
            col_def = f"    {col.name} {col.pg_type}"
            
            if col.primary_key:
                col_def += " PRIMARY KEY"
            elif not col.nullable:
                col_def += " NOT NULL"
            
            if col.default:
                col_def += f" DEFAULT {col.default}"
            
            if col.foreign_key:
                col_def += f" REFERENCES {col.foreign_key}"
            
            columns.append(col_def)
        
        # Add indexes
        index_defs = []
        for index_col in table.indexes:
            index_name = f"idx_{table.table_name}_{index_col}"
            index_defs.append(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table.table_name} ({index_col});")
        
        sql = f"CREATE TABLE {'IF NOT EXISTS' if if_not_exists else ''} {table.table_name} (\n"
        sql += ",\n".join(columns)
        sql += "\n);\n\n"
        sql += "\n".join(index_defs)
        
        return sql

