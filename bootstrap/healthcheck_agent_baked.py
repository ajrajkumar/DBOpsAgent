from strands import Agent, tool
from strands.models import BedrockModel
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os

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
            password=db_config['password'],
            cursor_factory=RealDictCursor
        )
        # Set to read-only for safety
        connection.set_session(readonly=True)
        return connection
        
    except Exception as e:
        raise Exception(f"Error connecting to database: {str(e)}")

# Define the AI model
model = BedrockModel(
    model_id=os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0'),
    region_name=os.getenv('AWS_REGION', 'us-west-2'),
    temperature=0.3
)

# TOOL 1: Get largest tables
@tool
def get_largest_tables() -> str:
    """
    Find the top 20 largest tables by disk usage.
    This helps with capacity planning and identifying storage hogs.
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT
            schemaname AS schema_name,
            tablename AS table_name,
            pg_size_pretty(total_bytes) AS total_size,
            pg_size_pretty(table_bytes) AS table_size,
            pg_size_pretty(index_bytes) AS index_size
        FROM (
            SELECT *,
                total_bytes - index_bytes - COALESCE(toast_bytes, 0) AS table_bytes
            FROM (
                SELECT c.oid,
                        nspname AS schemaname,
                        relname AS tablename,
                        pg_total_relation_size(c.oid) AS total_bytes,
                        pg_indexes_size(c.oid) AS index_bytes,
                        pg_total_relation_size(c.reltoastrelid) AS toast_bytes
                FROM pg_class c
                            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'r'
                    AND n.nspname NOT IN ('information_schema', 'pg_catalog')
            ) a
        ) a
        ORDER BY total_bytes DESC
        LIMIT 10
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(row) for row in results]
    except Exception as e:
        return f"Error retrieving largest tables: {str(e)}"

# TOOL 2: Find unused indexes
@tool
def get_unused_indexes() -> str:
    """
    Find indexes that are never used by queries.
    These consume storage and slow down writes but provide no benefit.
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        query = """
                SELECT schemaname,
                    relname AS table_name,
                    indexrelname AS index_name,
                    pg_size_pretty(pg_relation_size(i.indexrelid)) AS index_size,
                    idx_scan AS index_scans
                FROM pg_stat_user_indexes ui
                        JOIN pg_index i ON ui.indexrelid = i.indexrelid
                WHERE idx_scan < 1
                AND pg_relation_size(i.indexrelid) > 10240
                ORDER BY pg_relation_size(i.indexrelid) DESC
                    """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [dict(row) for row in results]
    except Exception as e:
        return f"Error finding unused indexes: {str(e)}"

# TOOL 3: Detect table bloat
@tool
def get_table_bloat() -> str:
    """
    Identify tables with excessive dead space (bloat).
    Bloated tables waste storage and hurt query performance.
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        query = """
                WITH constants AS (
                    SELECT current_setting('block_size')::numeric AS bs, 23 AS hdr, 8 AS ma
                ),
                no_stats AS (
                    SELECT table_schema, table_name,
                        n_live_tup::numeric as est_rows,
                        pg_table_size(relid)::numeric as table_size
                    FROM information_schema.columns
                        JOIN pg_stat_user_tables as psut
                        ON table_schema = psut.schemaname
                        AND table_name = psut.relname
                        LEFT OUTER JOIN pg_stats
                        ON table_schema = pg_stats.schemaname
                            AND table_name = pg_stats.tablename
                            AND column_name = attname
                    WHERE attname IS NULL
                        AND table_schema NOT IN ('pg_catalog', 'information_schema')
                    GROUP BY table_schema, table_name, relid, n_live_tup
                ),
                null_headers AS (
                    SELECT
                        hdr+1+(sum(case when null_frac <> 0 THEN 1 else 0 END)/8) as nullhdr,
                        SUM((1-null_frac)*avg_width) as datawidth,
                        MAX(null_frac) as maxfracsum,
                        schemaname,
                        tablename,
                        hdr, ma, bs
                    FROM pg_stats CROSS JOIN constants
                        LEFT OUTER JOIN no_stats
                            ON schemaname = no_stats.table_schema
                            AND tablename = no_stats.table_name
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                        AND no_stats.table_name IS NULL
                        AND EXISTS ( SELECT 1
                            FROM information_schema.columns
                                WHERE schemaname = columns.table_schema
                                    AND tablename = columns.table_name )
                    GROUP BY schemaname, tablename, hdr, ma, bs
                ),
                data_headers AS (
                    SELECT
                        ma, bs, hdr, schemaname, tablename,
                        (datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma ELSE hdr%ma END)))::numeric AS datahdr,
                        (maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma ELSE nullhdr%ma END))) AS nullhdr2
                    FROM null_headers
                ),
                table_estimates AS (
                    SELECT schemaname, tablename, bs,
                        reltuples::numeric as est_rows, relpages * bs as table_bytes,
                    CEIL((reltuples*
                            (datahdr + nullhdr2 + 4 + ma -
                                (CASE WHEN datahdr%ma=0
                                    THEN ma ELSE datahdr%ma END)
                                )/(bs-20))) * bs AS expected_bytes,
                        reltoastrelid
                    FROM data_headers
                        JOIN pg_class ON tablename = relname
                        JOIN pg_namespace ON relnamespace = pg_namespace.oid
                            AND schemaname = nspname
                    WHERE pg_class.relkind = 'r'
                ),
                estimates_with_toast AS (
                    SELECT schemaname, tablename,
                        TRUE as can_estimate,
                        est_rows,
                        table_bytes + ( coalesce(toast.relpages, 0) * bs ) as table_bytes,
                        expected_bytes + ( ceil( coalesce(toast.reltuples, 0) / 4 ) * bs ) as expected_bytes
                    FROM table_estimates LEFT OUTER JOIN pg_class as toast
                        ON table_estimates.reltoastrelid = toast.oid
                            AND toast.relkind = 't'
                ),
                table_estimates_plus AS (
                    SELECT current_database() as databasename,
                            schemaname, tablename, can_estimate,
                            est_rows,
                            CASE WHEN table_bytes > 0
                                THEN table_bytes::NUMERIC
                                ELSE NULL::NUMERIC END
                                AS table_bytes,
                            CASE WHEN expected_bytes > 0
                                THEN expected_bytes::NUMERIC
                                ELSE NULL::NUMERIC END
                                    AS expected_bytes,
                            CASE WHEN expected_bytes > 0 AND table_bytes > 0
                                AND expected_bytes <= table_bytes
                                THEN (table_bytes - expected_bytes)::NUMERIC
                                ELSE 0::NUMERIC END AS bloat_bytes
                    FROM estimates_with_toast
                    UNION ALL
                    SELECT current_database() as databasename,
                        table_schema, table_name, FALSE,
                        est_rows, table_size,
                        NULL::NUMERIC, NULL::NUMERIC
                    FROM no_stats
                ),
                bloat_data AS (
                    SELECT current_database() as databasename,
                        schemaname, tablename, can_estimate,
                        table_bytes, round(table_bytes/(1024^2)::NUMERIC,3) as table_mb,
                        expected_bytes, round(expected_bytes/(1024^2)::NUMERIC,3) as expected_mb,
                        round(bloat_bytes*100/table_bytes) as pct_bloat,
                        round(bloat_bytes/(1024::NUMERIC^2),2) as mb_bloat,
                        table_bytes, expected_bytes, est_rows
                    FROM table_estimates_plus
                )
                SELECT databasename, schemaname, tablename,
                    can_estimate,
                    est_rows,
                    pct_bloat, mb_bloat,
                    table_mb
                FROM bloat_data
                WHERE ( pct_bloat >= 50 AND mb_bloat >= 20 )
                    OR ( pct_bloat >= 25 AND mb_bloat >= 1000 )
                ORDER BY pct_bloat DESC;
            """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(row) for row in results]
        
    except Exception as e:
        return f"Error detecting table bloat: {str(e)}"

# TOOL 4: Detect index bloat
@tool
def get_index_bloat() -> str:
    """
    Identify index bloat.
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        query = """
                WITH index_stats AS (
                    SELECT
                        current_database() AS database_name,
                        ns.nspname AS schema_name,
                        ic.relname AS index_name,
                        pg_size_pretty(pg_relation_size(ic.oid)) AS index_size,
                        pg_relation_size(ic.oid) AS index_size_bytes,
                        idx.indisunique AS is_unique,
                        idx.indisprimary AS is_primary,
                        COALESCE(NULLIF(pg_stat_user_indexes.idx_tup_read, 0), 0) AS estimated_row_count,
                        (pg_relation_size(ic.oid)::bigint -
                        COALESCE(
                            NULLIF(pg_stat_user_indexes.idx_tup_read::bigint, 0) *
                            NULLIF(pg_stat_user_indexes.idx_scan::bigint, 1),
                            0
                        )::bigint) AS estimated_bloat_bytes
                    FROM pg_class ic
                    JOIN pg_namespace ns ON ic.relnamespace = ns.oid
                    JOIN pg_index idx ON ic.oid = idx.indexrelid
                    JOIN pg_stat_user_indexes ON ic.oid = pg_stat_user_indexes.indexrelid
                    WHERE ic.relkind = 'i'
                    AND ns.nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ),
                index_bloat AS (
                    SELECT
                        database_name,
                        schema_name,
                        index_name,
                        CASE
                            WHEN index_size_bytes > estimated_bloat_bytes THEN 'y'
                            ELSE 'n'
                        END AS can_estimate_bloat,
                        estimated_row_count,
                        pg_size_pretty(GREATEST(estimated_bloat_bytes, 0)) AS index_bloat_size,
                        ROUND(
                            100 *
                            GREATEST(estimated_bloat_bytes::numeric, 0) / NULLIF(index_size_bytes::numeric, 0),
                            2
                        ) AS index_bloat_percent,
                        pg_size_pretty(index_size_bytes) AS index_size
                    FROM index_stats
                )
                SELECT
                    database_name,
                    schema_name,
                    index_name,
                    can_estimate_bloat,
                    estimated_row_count,
                    index_bloat_percent,
                    index_bloat_size,
                    index_size
                FROM index_bloat
                WHERE can_estimate_bloat='y'
                ORDER BY schema_name, index_name
            """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(row) for row in results]
        
    except Exception as e:
        return f"Error detecting index bloat: {str(e)}"

# TOOL 5: Get top queries by execution time (YOU'LL COMPLETE THIS)
@tool
def get_top_queries() -> str:
    """
    Get top 10 queries by run time with execution plans.
    This helps identify performance bottlenecks and optimization opportunities.
    
    TODO: Replace the placeholder SQL with the actual query!
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # TODO: Replace this placeholder with the actual SQL query
        query = """
        SELECT  
    userid::regrole as user, 
    queryid as queryid,
    datname as DB_name,
    substring(query, 1, 200) AS short_query,
    round(( total_plan_time + total_exec_time )::numeric, 2) AS total_time,
    calls,
    explain_plan
FROM aurora_stat_plans(true) p, pg_database d
WHERE p.dbid=d.oid
ORDER BY total_time DESC
LIMIT 10;
        """
        

            
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(row) for row in results]
        
    except Exception as e:
        return f"Error retrieving top queries: {str(e)}"

# Create the system prompt that guides the agent's behavior
system_prompt = """You are a database health assistant that specializes in Aurora PostgreSQL analysis.

You have these database health monitoring tools:
- get_largest_tables: Analyze top tables by disk usage for capacity planning
- get_unused_indexes: Find indexes consuming storage without providing value
- get_table_bloat: Detect tables with excessive dead space affecting performance
- get_top_queries: Identify resource intensive queries with execution plans

Always provide actionable insights and recommendations based on the data you retrieve.
Keep responses clear and focused on practical database optimization."""

# Create an agent with database health monitoring tools
agent = Agent(
    system_prompt=system_prompt, 
    model=model, 
    tools=[
        get_largest_tables,
        get_unused_indexes,
        get_table_bloat,
        get_top_queries
    ]
)

if __name__ == "__main__":
    print("🔍 Database Health Check Agent Ready!")
    print("Ask questions about your database health. Type 'exit' to quit.")
    print("\nExample questions:")
    print("- What are the largest tables in my database?")
    print("- Find any unused indexes I can clean up")
    print("- Check for table bloat in my database")
    print("- Show me the top queries")

    while True:
        user_input = input("\n💬 Your question: ")
        if user_input.lower() in ['exit', 'quit']:
            print("👋 Goodbye!")
            break
        
        print("🔄 Analyzing...")
        try:
            response = agent(user_input)
            print(f"\n📊 Analysis: {response}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        print("-" * 50)