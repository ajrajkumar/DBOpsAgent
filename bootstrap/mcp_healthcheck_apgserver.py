"""
MCP Database Server for Aurora PostgreSQL

This script creates an MCP server that provides database tools:
1. Get top 20 largest tables by disk size
2. Identify duplicate indexes
3. Identify unused indexes
4. Identify bloat in tables
5. Identify bloat in indexes
6. Get top 10 resource intensive queries with execution plans

"""

import json
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from fastmcp import FastMCP
from typing import List, Dict, Any
import re
import logging
import os

# Configure logging for better visibility
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mcp_database_server')

class DatabaseManager:
    def __init__(self, secret_name: str, region_name: str = os.getenv('AWS_REGION', 'us-west-2')):
        self.secret_name = secret_name
        self.region_name = region_name
        self._connection = None
        self._db_config = None
        self.default_limit = 10  # Default limit for queries
    
    def _get_secret(self):
        """Retrieve database credentials from AWS Secrets Manager"""
        if self._db_config:
            return self._db_config
            
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=self.region_name
        )
        
        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=self.secret_name
            )
            secret = get_secret_value_response['SecretString']
            self._db_config = json.loads(secret)
            logger.info(f"Successfully retrieved database credentials from secret: {self.secret_name}")
            return self._db_config
        except Exception as e:
            logger.error(f"Error retrieving secret: {str(e)}")
            raise Exception(f"Error retrieving secret: {str(e)}")
    
    def get_connection(self):
        """Get database connection"""
        if self._connection and not self._connection.closed:
            return self._connection
            
        config = self._get_secret()
        
        try:
            self._connection = psycopg2.connect(
                host=config['host'],
                port=config.get('port', 5432),
                database=config['dbname'],
                user=config['username'],
                password=config['password'],
                cursor_factory=RealDictCursor
            )
            # Set connection to read-only
            self._connection.set_session(readonly=True)
            logger.info(f"Successfully connected to database: {config['dbname']}@{config['host']}")
            return self._connection
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise Exception(f"Error connecting to database: {str(e)}")
    
    def close_connection(self):
        """Close database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Database connection closed")


def start_database_server(secret_name: str, region_name: str = os.getenv('AWS_REGION', 'us-west-2'), port: int = 8083):
    """
    Initialize and start an MCP database server.
    
    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        region_name: AWS region where the secret is stored
        port: Port number for the MCP server (default: 8083)
    """
    # Create an MCP server
    mcp = FastMCP("Database Server")
    
    # Initialize database manager
    db_manager = DatabaseManager(secret_name, region_name)
    

    @mcp.tool()
    def get_largest_tables() -> List[Dict[str, Any]]:
        """Get top 20 largest tables by disk size"""
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            query = """
            SELECT
                schemaname AS schema_name,
                tablename AS table_name,
                pg_size_pretty(total_bytes) AS total_size,
                pg_size_pretty(table_bytes) AS table_size,
                pg_size_pretty(index_bytes) AS index_size,
                pg_size_pretty(COALESCE(toast_bytes, 0)) AS toast_size
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
            LIMIT 20
            """
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            logger.info(f"Found {len(results)} tables")
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to list tables: {str(e)}")
            return [{"error": f"Failed to list tables: {str(e)}"}]

    @mcp.tool()
    def get_duplicate_indexes() -> List[Dict[str, Any]]:
        """Identify duplicate indexes"""
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            query = """
            SELECT
                indrelid::regclass AS "Associated Table Name"
                ,array_agg(indexrelid::regclass) AS "Duplicate Index Name"
            FROM pg_index
            GROUP BY
                indrelid
                ,indkey
            HAVING COUNT(*) > 1
            """
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            logger.info(f"Found {len(results)} tables")
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to list duplicate indexes: {str(e)}")
            return [{"error": f"Failed to list duplicate indexes: {str(e)}"}]
    @mcp.tool()
    def get_unused_indexes() -> List[Dict[str, Any]]:
        """Get unused indexes"""
        try:
            conn = db_manager.get_connection()
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
            
            logger.info(f"Found {len(results)} tables")
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to list unused indexes: {str(e)}")
            return [{"error": f"Failed to unused indexes: {str(e)}"}]

    @mcp.tool()
    def get_table_bloat() -> List[Dict[str, Any]]:
        """identify table bloat"""
        try:
            conn = db_manager.get_connection()
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
            
            logger.info(f"Found {len(results)} tables")
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to identify table bloat: {str(e)}")
            return [{"error": f"Failed to identify table bloat: {str(e)}"}]
    @mcp.tool()
    def get_index_bloat() -> List[Dict[str, Any]]:
        """Get index bloat"""
        try:
            conn = db_manager.get_connection()
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
            
            logger.info(f"Found {len(results)} tables")
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get index bloat: {str(e)}")
            return [{"error": f"Failed to get index bloat: {str(e)}"}]

    @mcp.tool()
    def get_top_queries() -> List[Dict[str, Any]]:
        """Get top 10 resource intensive queries with execution plans for optimization analysis"""
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            query = """
              SELECT  
                userid::regrole as user, 
                queryid as queryid,
                datname as DB_name,
                substring(query, 1, 200) AS short_query,
                round(( total_plan_time + total_exec_time )::numeric, 2) AS total_time,
                calls,explain_plan
            FROM  aurora_stat_plans(true) p, pg_database d
            WHERE p.dbid=d.oid
            ORDER BY total_time DESC
            LIMIT 10;
            """
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            logger.info(f"Found {len(results)} top 10 resource intensive queries")
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get top 10 queries: {str(e)}")
            return [{"error": f"Failed to get top 10 queries: {str(e)}"}]
  
   
    # Cleanup function
    def cleanup():
        logger.info("Cleaning up database connections")
        db_manager.close_connection()
    
    # Register cleanup
    import atexit
    atexit.register(cleanup)
    
    print(f"Starting MCP Database Server on http://localhost:{port}")
    print(f"Using secret: {secret_name} in region: {region_name}")
    logger.info(f"MCP Database Server starting up on port {port}")
    mcp.run(transport="streamable-http", port=port)


if __name__ == "__main__":
    # Configuration - update these values for your environment
    SECRET_NAME = "apgpg-dat302-secret"  # Replace with your secret name
    REGION_NAME = os.getenv('AWS_REGION', 'us-west-2')  # Get from environment or default
    PORT = 8083  # Default port for Database Health Check MCP server
    
    try:
        start_database_server(SECRET_NAME, REGION_NAME, PORT)
    except KeyboardInterrupt:
        print("Server shutting down...")
        logger.info("Server shutdown requested by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        logger.error(f"Error starting server: {e}")


