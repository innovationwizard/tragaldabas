"""Database connection management"""

from typing import Optional
import asyncpg
from contextlib import asynccontextmanager

from core.exceptions import DatabaseError
from config import settings


class DatabaseManager:
    """PostgreSQL connection manager"""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or settings.DATABASE_URL
        
        if not self.connection_string:
            raise DatabaseError("No database connection string provided")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get async database connection"""
        try:
            conn = await asyncpg.connect(self.connection_string)
            try:
                yield conn
            finally:
                await conn.close()
        except Exception as e:
            raise DatabaseError(f"Database connection failed: {e}") from e
    
    async def execute(self, query: str, *args) -> list:
        """Execute query and return results"""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)
    
    async def execute_one(self, query: str, *args):
        """Execute query and return single result"""
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args)
    
    async def execute_write(self, query: str, *args) -> str:
        """Execute write query (INSERT, UPDATE, DELETE)"""
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)
    
    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

