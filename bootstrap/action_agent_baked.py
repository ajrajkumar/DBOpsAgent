from strands import Agent, tool
from strands.models import BedrockModel
import boto3
import psycopg2
import json
import os
import logging
from datetime import datetime
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection helper function
def get_database_connection():
    """Get database connection using AWS Secrets Manager"""
    secret_name = "apgpg-dat302-secret"
    region_name = os.getenv('AWS_REGION', 'us-west-2')
    
    # Get database credentials from AWS Secrets Manager
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        db_config = json.loads(secret)
        
        # Create database connection
        connection = psycopg2.connect(
            host=db_config['host'],
            port=db_config.get('port', 5432),
            database=db_config['dbname'],
            user=db_config['username'],
            password=db_config['password']
        )
        # Set autocommit for DDL operations
        connection.autocommit = True
        return connection
        
    except Exception as e:
        raise Exception(f"Error connecting to database: {str(e)}")

# Define the AI model
model = BedrockModel(
    model_id=os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0'),
    region_name=os.getenv('AWS_REGION', 'us-west-2'),
    temperature=0.3
)

# TOOL 1: Create index concurrently (production-safe)
@tool
def create_index_concurrently(table_name: str, column_names: str, 
                            index_name: Optional[str] = None) -> str:
    """
    Create an index concurrently (production-safe, no blocking).
    
    Args:
        table_name: Name of the table to create index on
        column_names: Comma-separated column names for the index
        index_name: Optional custom index name (auto-generated if not provided)
    """
    try:
        connection = get_database_connection()
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
            return f"❌ Error: Table '{table_name}' does not exist"
        
        # Check if index already exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE indexname = %s
            )
        """, (index_name,))
        
        if cursor.fetchone()[0]:
            return f"❌ Error: Index '{index_name}' already exists"
        
        # Create index concurrently (production-safe)
        create_sql = f"CREATE INDEX CONCURRENTLY {index_name} ON {table_name} ({column_names})"
        
        logger.info(f"Creating index concurrently: {create_sql}")
        start_time = datetime.now()
        
        cursor.execute(create_sql)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
            
            # Verify index was created successfully
        cursor.execute("""
                SELECT
                schemaname,
                relname AS table_name,
                indexrelname AS index_name,
                indisvalid "indexvalid",
                indisready,
                indislive
            FROM pg_catalog.pg_stat_all_indexes
            JOIN pg_catalog.pg_index USING (indexrelid)
            WHERE indexrelname = %s
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

# TOOL 2: Analyze table (update statistics)
@tool
def analyze_table(table_name: Optional[str] = None) -> str:
    """
    Analyze table(s) to update statistics (production-safe, no blocking).
    
    Args:
        table_name: Optional specific table name (analyzes all tables if not provided)
    """
    try:
        connection = get_database_connection()
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
                return f"❌ Error: Table '{table_name}' does not exist"
            
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
        
        result = f"✅ SUCCESS: Table Analysis Completed\n"
        result += f"Target: {target}\n"
        result += f"Duration: {duration:.2f} seconds\n"
        result += f"SQL Executed: {analyze_sql}\n"
        result += f"🛡️ Production Safe: ANALYZE does not block operations"
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze: {str(e)}")
        return f"❌ Error: Failed to analyze: {str(e)}"

# TOOL 3: Vacuum table (reclaim space)
@tool
def vacuum_table(table_name: str, analyze_after: bool = True) -> str:
    """
    Vacuum table to reclaim space (production-safe, no exclusive locks).
    
    Args:
        table_name: Name of the table to vacuum
        analyze_after: Whether to run ANALYZE after VACUUM (default: True)
    """
    try:
        connection = get_database_connection()
        cursor = connection.cursor()
        
        # Validate table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table_name,))
        
        if not cursor.fetchone()[0]:
            return f"❌ Error: Table '{table_name}' does not exist"
        
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
        
        result = f"✅ SUCCESS: Table Vacuum Completed\n"
        result += f"Table: {table_name}\n"
        result += f"Operation: {operation}\n"
        result += f"Duration: {duration:.2f} seconds\n"
        result += f"SQL Executed: {vacuum_sql}\n"
        result += f"🛡️ Production Safe: VACUUM (not VACUUM FULL) does not require exclusive locks"
        return result
        
    except Exception as e:
        logger.error(f"Failed to vacuum table: {str(e)}")
        return f"❌ Error: Failed to vacuum table: {str(e)}"

# TOOL 4: Validate SQL syntax (YOU'LL COMPLETE THIS)
@tool
def validate_sql_syntax(sql_query: str) -> str:
    """
    Validate SQL syntax without executing (read-only validation).
    
    Args:
        sql_query: SQL query to validate
        
    TODO: Replace the placeholder with the actual validation logic!
    """
    try:
        # Basic SQL syntax validation
        sql_query = sql_query.strip()
        
        if not sql_query:
            return "❌ Error: Empty SQL query provided"
        
        # TODO: Replace this placeholder with the actual validation logic
        validation_logic = """
        # Check for dangerous operations
dangerous_keywords = [
    'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'UPDATE',
    'VACUUM FULL', 'REINDEX', 'CLUSTER'
]

sql_upper = sql_query.upper()
for keyword in dangerous_keywords:
    if keyword in sql_upper:
        return f"❌ VALIDATION FAILED: Dangerous operation detected: {keyword}"

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
    return f"❌ VALIDATION FAILED: Operation not in allowed list"

return f"✅ VALIDATION PASSED: SQL is production-safe"
        """
        
        return f"✅ VALIDATION PASSED: SQL is production-safe"
        
    except Exception as e:
        logger.error(f"Failed to validate SQL: {str(e)}")
        return f"❌ Error: Failed to validate SQL: {str(e)}"

# Create the system prompt that guides the agent's behavior
system_prompt = """You are a database action specialist that can safely implement database improvements.

⚠️ CRITICAL PRODUCTION SAFETY: You can ONLY use production-safe operations that have MINIMAL IMPACT:

AVAILABLE SAFE OPERATIONS:
- create_index_concurrently: Creates indexes without blocking reads/writes (NEVER use regular CREATE INDEX)
- analyze_table: Updates table statistics safely without blocking operations
- vacuum_table: Reclaims space using VACUUM (NEVER VACUUM FULL) without exclusive locks
- validate_sql_syntax: Validates SQL before execution for safety

PRODUCTION SAFETY RULES:
- ALWAYS use CREATE INDEX CONCURRENTLY (never regular CREATE INDEX)
- ALWAYS use VACUUM (never VACUUM FULL which requires exclusive locks)
- ALWAYS validate operations before execution
- NEVER perform operations that require exclusive locks
- NEVER use DROP, DELETE, TRUNCATE, or other destructive operations
- ALWAYS explain the safety of each operation before executing

Always provide clear explanations of why each operation is production-safe."""

# Create an agent with database action tools
agent = Agent(
    system_prompt=system_prompt, 
    model=model, 
    tools=[
        create_index_concurrently,
        analyze_table,
        vacuum_table,
        validate_sql_syntax
    ]
)

if __name__ == "__main__":
    print("🔧 Database Action Agent Ready!")
    print("Ask for database actions to implement safely. Type 'exit' to quit.")
    print("\nExample actions:")
    print("- Create an index on the employees table for the email column")
    print("- Analyze the projects table to update statistics")
    print("- Vacuum the orders table to reclaim space")
    print("- Validate this SQL: CREATE INDEX CONCURRENTLY idx_test ON users (name)")

    while True:
        user_input = input("\n💬 Action Request: ")
        if user_input.lower() in ['exit', 'quit']:
            print("👋 Goodbye!")
            break
        
        print("🔄 Analyzing action request...")
        try:
            response = agent(user_input)
            print(f"\n📊 Action Result:\n{response}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        print("-" * 50)