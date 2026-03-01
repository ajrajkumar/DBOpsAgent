

"""
Database Action MCP Server

This script creates an MCP server that provides production-safe database action tools.
All operations are designed for minimal impact on production systems:
- CREATE INDEX CONCURRENTLY (no blocking)
- ANALYZE (updates statistics safely)
- VACUUM (reclaims space without exclusive locks)
- No VACUUM FULL or exclusive lock operations

Key safety features:
- Read-only validation before execution
- Production-safe operations only
- Comprehensive error handling and logging
"""

import json
import boto3
import logging
import psycopg2
from datetime import datetime
from fastmcp import FastMCP
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('database_action_server')

class DatabaseActionManager:
    def __init__(self, secret_name: str, region_name: str = os.getenv('AWS_REGION', 'us-west-2')):
        self.secret_name = secret_name
        self.region_name = region_name
        self._secrets_client = None
        self._connection = None
        self._db_config = None
        
    def get_secrets_client(self):
        """Get AWS Secrets Manager client"""
        if not self._secrets_client:
            try:
                self._secrets_client = boto3.client('secretsmanager', region_name=self.region_name)
                logger.info(f"Successfully created Secrets Manager client for region: {self.region_name}")
            except NoCredentialsError:
                logger.error("AWS credentials not found")
                raise Exception("AWS credentials not configured")
            except Exception as e:
                logger.error(f"Error creating Secrets Manager client: {str(e)}")
                raise Exception(f"Error creating Secrets Manager client: {str(e)}")
        return self._secrets_client
    
    def _get_secret(self):
        """Retrieve database credentials from AWS Secrets Manager"""
        if self._db_config:
            return self._db_config
            
        try:
            secrets_client = self.get_secrets_client()
            response = secrets_client.get_secret_value(SecretId=self.secret_name)
            secret = json.loads(response['SecretString'])
            self._db_config = secret
            logger.info(f"Successfully retrieved database credentials from secret: {self.secret_name}")
            return self._db_config
        except Exception as e:
            logger.error(f"Error retrieving secret: {str(e)}")
            raise Exception(f"Error retrieving secret: {str(e)}")
    
    def get_database_connection(self):
        """Get database connection using AWS Secrets Manager"""
        if self._connection and not self._connection.closed:
            return self._connection
            
        config = self._get_secret()
        
        try:
            self._connection = psycopg2.connect(
                host=config['host'],
                port=config.get('port', 5432),
                database=config['dbname'],
                user=config['username'],
                password=config['password']
            )
            
            # Set autocommit for DDL operations
            self._connection.autocommit = True
            
            logger.info(f"Successfully connected to database: {config['dbname']}@{config['host']}")
            return self._connection
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise Exception(f"Failed to connect to database: {str(e)}")
    
    def close_connection(self):
        """Close database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Database connection closed")

def start_action_server(secret_name: str, region_name: str = os.getenv('AWS_REGION', 'us-west-2'), port: int = 8084):
    """
    Initialize and start a Database Action MCP server.
    
    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        region_name: AWS region name
        port: Port number for the MCP server (default: 8084)
    """
    # Create an MCP server
    mcp = FastMCP("Database Action Server")
    
    # Initialize action manager
    action_manager = DatabaseActionManager(secret_name, region_name)
    
    @mcp.tool()
    def create_index_concurrently(table_name: str, column_names: str, 
                                index_name: Optional[str] = None) -> Dict[str, Any]:
        """Create an index concurrently (production-safe, no blocking)
        
        Args:
            table_name: Name of the table to create index on
            column_names: Comma-separated column names for the index
            index_name: Optional custom index name (auto-generated if not provided)
        """
        try:
            connection = action_manager.get_database_connection()
            cursor = connection.cursor()
            
            # Generate index name if not provided
            if not index_name:
                clean_columns = column_names.replace(' ', '').replace(',', '_')
                index_name = f"idx_{table_name}_{clean_columns}"
            
            # Validate table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            
            if not cursor.fetchone()[0]:
                return {"error": f"Table '{table_name}' does not exist"}
            
            # Check if index already exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE indexname = %s
                )
            """, (index_name,))
            
            if cursor.fetchone()[0]:
                return {"error": f"Index '{index_name}' already exists"}
            
            # Create index concurrently (production-safe)
            create_sql = f"CREATE INDEX CONCURRENTLY {index_name} ON {table_name} ({column_names})"
            
            logger.info(f"Creating index concurrently: {create_sql}")
            start_time = datetime.now()
            
            cursor.execute(create_sql)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Verify index was created successfully
            cursor.execute("""
                SELECT schemaname, tablename, indexname, indexdef 
                FROM pg_indexes 
                WHERE indexname = %s
            """, (index_name,))
            
            index_info = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            if index_info:
                return {
                    "success": True,
                    "index_name": index_name,
                    "table_name": table_name,
                    "columns": column_names,
                    "duration_seconds": duration,
                    "sql_executed": create_sql,
                    "index_definition": index_info[3],
                    "message": f"Index '{index_name}' created successfully using CREATE INDEX CONCURRENTLY"
                }
            else:
                return {"error": f"Index creation may have failed - index '{index_name}' not found after creation"}
            
        except Exception as e:
            logger.error(f"Failed to create index: {str(e)}")
            return {"error": f"Failed to create index: {str(e)}"}
    
    @mcp.tool()
    def analyze_table(table_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyze table(s) to update statistics (production-safe, no blocking)
        
        Args:
            table_name: Optional specific table name (analyzes all tables if not provided)
        """
        try:
            connection = action_manager.get_database_connection()
            cursor = connection.cursor()
            
            if table_name:
                # Validate table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, (table_name,))
                
                if not cursor.fetchone()[0]:
                    return {"error": f"Table '{table_name}' does not exist"}
                
                analyze_sql = f"ANALYZE {table_name}"
                target = f"table '{table_name}'"
            else:
                analyze_sql = "ANALYZE"
                target = "all tables"
            
            logger.info(f"Analyzing {target}: {analyze_sql}")
            start_time = datetime.now()
            
            cursor.execute(analyze_sql)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            cursor.close()
            connection.close()
            
            return {
                "success": True,
                "target": target,
                "duration_seconds": duration,
                "sql_executed": analyze_sql,
                "message": f"Successfully analyzed {target} - statistics updated"
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze: {str(e)}")
            return {"error": f"Failed to analyze: {str(e)}"}
    
    @mcp.tool()
    def vacuum_table(table_name: str, analyze_after: bool = True) -> Dict[str, Any]:
        """Vacuum table to reclaim space (production-safe, no exclusive locks)
        
        Args:
            table_name: Name of the table to vacuum
            analyze_after: Whether to run ANALYZE after VACUUM (default: True)
        """
        try:
            connection = action_manager.get_database_connection()
            cursor = connection.cursor()
            
            # Validate table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            
            if not cursor.fetchone()[0]:
                return {"error": f"Table '{table_name}' does not exist"}
            
            # Use VACUUM (not VACUUM FULL) for production safety
            if analyze_after:
                vacuum_sql = f"VACUUM ANALYZE {table_name}"
                operation = "VACUUM ANALYZE"
            else:
                vacuum_sql = f"VACUUM {table_name}"
                operation = "VACUUM"
            
            logger.info(f"Running {operation} on table '{table_name}': {vacuum_sql}")
            start_time = datetime.now()
            
            cursor.execute(vacuum_sql)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            cursor.close()
            connection.close()
            
            return {
                "success": True,
                "table_name": table_name,
                "operation": operation,
                "duration_seconds": duration,
                "sql_executed": vacuum_sql,
                "message": f"Successfully completed {operation} on table '{table_name}'"
            }
            
        except Exception as e:
            logger.error(f"Failed to vacuum table: {str(e)}")
            return {"error": f"Failed to vacuum table: {str(e)}"}
    
    @mcp.tool()
    def validate_sql_syntax(sql_query: str) -> Dict[str, Any]:
        """Validate SQL syntax without executing (read-only validation)
        
        Args:
            sql_query: SQL query to validate
        """
        try:
            # Basic SQL syntax validation
            sql_query = sql_query.strip()
            
            if not sql_query:
                return {"error": "Empty SQL query provided"}
            
            # Check for dangerous operations
            dangerous_keywords = [
                'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'UPDATE',
                'VACUUM FULL', 'REINDEX', 'CLUSTER'
            ]
            
            sql_upper = sql_query.upper()
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    return {
                        "valid": False,
                        "error": f"Dangerous operation detected: {keyword}",
                        "message": "Only production-safe operations are allowed"
                    }
            
            # Check for allowed operations
            allowed_operations = [
                'CREATE INDEX CONCURRENTLY',
                'ANALYZE',
                'VACUUM',
                'SELECT',
                'EXPLAIN'
            ]
            
            is_allowed = False
            for operation in allowed_operations:
                if operation in sql_upper:
                    is_allowed = True
                    break
            
            if not is_allowed:
                return {
                    "valid": False,
                    "error": "Operation not in allowed list",
                    "allowed_operations": allowed_operations
                }
            
            return {
                "valid": True,
                "sql_query": sql_query,
                "message": "SQL syntax appears valid and uses allowed operations"
            }
            
        except Exception as e:
            logger.error(f"Failed to validate SQL: {str(e)}")
            return {"error": f"Failed to validate SQL: {str(e)}"}
    
    # Cleanup function
    def cleanup():
        logger.info("Cleaning up database action connections")
        action_manager.close_connection()
    
    # Register cleanup
    import atexit
    atexit.register(cleanup)
    
    print(f"Starting Database Action MCP Server on http://localhost:{port}")
    print(f"Using secret: {secret_name} in region: {region_name}")
    print("Production-safe operations: CREATE INDEX CONCURRENTLY, ANALYZE, VACUUM")
    logger.info(f"Database Action MCP Server starting up on port {port}")
    mcp.run(transport="streamable-http", port=port)


if __name__ == "__main__":
    # Configuration - update these values for your environment
    SECRET_NAME = "apgpg-dat302-secret"  # Replace with your secret name
    REGION_NAME = os.getenv('AWS_REGION', 'us-west-2')  # Get from environment or default
    PORT = 8084  # Port for Database Action MCP server
    
    try:
        start_action_server(SECRET_NAME, REGION_NAME, PORT)
    except KeyboardInterrupt:
        print("Server shutting down...")
        logger.info("Server shutdown requested by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        logger.error(f"Error starting server: {e}")




