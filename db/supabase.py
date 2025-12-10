"""Supabase-specific database utilities and helpers"""

from typing import Optional
import asyncpg
from contextlib import asynccontextmanager

from .connection import DatabaseManager
from core.exceptions import DatabaseError
from config import settings


class SupabaseManager(DatabaseManager):
    """Supabase-optimized database manager"""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize Supabase database manager
        
        Args:
            connection_string: Supabase connection string
                              If None, uses DATABASE_URL from settings
        """
        super().__init__(connection_string)
        
        # Ensure SSL is enabled for Supabase
        if "sslmode" not in self.connection_string:
            separator = "&" if "?" in self.connection_string else "?"
            self.connection_string = f"{self.connection_string}{separator}sslmode=require"
    
    async def create_pool(
        self,
        min_size: int = 5,
        max_size: int = 20,
        max_queries: int = 50000,
        max_inactive_connection_lifetime: float = 300.0
    ):
        """
        Create connection pool optimized for Supabase
        
        Args:
            min_size: Minimum pool size
            max_size: Maximum pool size (Supabase limit: 200 connections)
            max_queries: Maximum queries per connection
            max_inactive_connection_lifetime: Max idle time in seconds
        """
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=min_size,
                max_size=min(max_size, 200),  # Supabase limit
                max_queries=max_queries,
                max_inactive_connection_lifetime=max_inactive_connection_lifetime,
                timeout=10.0,
                command_timeout=30.0
            )
        except Exception as e:
            raise DatabaseError(f"Failed to create Supabase connection pool: {e}") from e
    
    async def get_pool_stats(self) -> dict:
        """
        Get connection pool statistics
        
        Returns:
            Dictionary with pool statistics
        """
        if not self.pool:
            return {"error": "Pool not initialized"}
        
        return {
            "size": self.pool.get_size(),
            "idle": self.pool.get_idle_size(),
            "active": self.pool.get_size() - self.pool.get_idle_size(),
            "max_size": self.pool.get_max_size(),
            "min_size": self.pool.get_min_size()
        }
    
    async def enable_rls(self, table_name: str, schema: str = "public") -> bool:
        """
        Enable Row Level Security on a table
        
        Args:
            table_name: Name of the table
            schema: Schema name (default: public)
            
        Returns:
            True if successful
        """
        query = f"ALTER TABLE {schema}.{table_name} ENABLE ROW LEVEL SECURITY;"
        try:
            await self.execute_write(query)
            return True
        except Exception as e:
            raise DatabaseError(f"Failed to enable RLS on {table_name}: {e}") from e
    
    async def create_rls_policy(
        self,
        table_name: str,
        policy_name: str,
        policy_definition: str,
        schema: str = "public"
    ) -> bool:
        """
        Create a Row Level Security policy
        
        Args:
            table_name: Name of the table
            policy_name: Name of the policy
            policy_definition: SQL policy definition
            schema: Schema name (default: public)
            
        Returns:
            True if successful
        """
        query = f"""
            CREATE POLICY "{policy_name}"
            ON {schema}.{table_name}
            {policy_definition}
        """
        try:
            await self.execute_write(query)
            return True
        except Exception as e:
            raise DatabaseError(f"Failed to create RLS policy: {e}") from e
    
    async def check_connection_health(self) -> dict:
        """
        Check database connection health
        
        Returns:
            Dictionary with health status
        """
        try:
            # Test basic connection
            result = await self.execute_one("SELECT version(), current_database(), current_user")
            
            # Check pool if available
            pool_stats = await self.get_pool_stats() if hasattr(self, 'pool') and self.pool else {}
            
            return {
                "status": "healthy",
                "postgres_version": result[0] if result else "unknown",
                "database": result[1] if result else "unknown",
                "user": result[2] if result else "unknown",
                "pool": pool_stats
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_table_size(self, table_name: str, schema: str = "public") -> dict:
        """
        Get table size information
        
        Args:
            table_name: Name of the table
            schema: Schema name
            
        Returns:
            Dictionary with size information
        """
        query = """
            SELECT 
                pg_size_pretty(pg_total_relation_size($1::regclass)) as total_size,
                pg_size_pretty(pg_relation_size($1::regclass)) as table_size,
                pg_size_pretty(pg_indexes_size($1::regclass)) as indexes_size,
                (SELECT COUNT(*) FROM $1::regclass) as row_count
        """
        
        full_table_name = f"{schema}.{table_name}"
        result = await self.execute_one(query, full_table_name)
        
        if result:
            return {
                "table": full_table_name,
                "total_size": result[0],
                "table_size": result[1],
                "indexes_size": result[2],
                "row_count": result[3]
            }
        return {}


def get_supabase_connection_string(
    project_ref: str,
    password: str,
    use_pooling: bool = True,
    port: Optional[int] = None
) -> str:
    """
    Generate Supabase connection string
    
    Args:
        project_ref: Supabase project reference
        password: Database password
        use_pooling: Use PgBouncer connection pooling
        port: Custom port (default: 6543 for pooling, 5432 for direct)
        
    Returns:
        Connection string
    """
    if use_pooling:
        port = port or 6543
        return f"postgresql://postgres.{project_ref}:{password}@db.{project_ref}.supabase.co:{port}/postgres?pgbouncer=true&sslmode=require"
    else:
        port = port or 5432
        return f"postgresql://postgres.{project_ref}:{password}@db.{project_ref}.supabase.co:{port}/postgres?sslmode=require"

