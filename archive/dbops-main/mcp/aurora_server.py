#!/usr/bin/env python3
"""
Aurora PostgreSQL MCP Server - Simplified for FastMCP
Provides real Aurora database metrics via MCP tools - No Mock Data (Project Rule #1)
"""

from fastmcp import FastMCP
from typing import Dict, Any, List
import psycopg2
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get AWS region from environment variable
AWS_REGION = os.environ.get('AWSREGION', 'us-west-2')

# Create Aurora MCP server instance
mcp = FastMCP("Aurora PostgreSQL Server")

# Add MCP prompts to guide LLM usage for Aurora PostgreSQL analysis
@mcp.prompt()
def aurora_tool_selection() -> str:
    """
    Smart tool selection guide for Aurora PostgreSQL MCP server
    
    Use this prompt to understand which Aurora database tools to use for different
    database analysis scenarios and performance troubleshooting situations.
    """
    return """
# Aurora PostgreSQL Tool Selection Guide

## 🎯 **Quick Tool Selection by Scenario**

### **"Database is slow / Performance issues"**
1. `get_slow_queries()` - Identify queries with high execution time
2. `get_table_stats()` - Check for high sequential scan ratios
3. `get_index_usage()` - Analyze index efficiency
4. `get_buffer_cache_stats()` - Check memory cache hit ratios
5. `get_wait_events()` - Identify what database is waiting for

### **"Database is hanging / Blocking issues"**
1. `get_active_sessions()` - See current database activity
2. `get_blocking_queries()` - Find queries blocking others
3. `get_wait_events()` - Analyze wait patterns
4. `get_connection_pool_stats()` - Check connection usage

### **"Need database health check"**
1. `test_connection()` - Verify database connectivity
2. `get_active_sessions()` - Check current activity levels
3. `get_buffer_cache_stats()` - Memory efficiency check
4. `get_connection_pool_stats()` - Connection health

### **"Index optimization needed"**
1. `get_index_usage()` - Current index usage patterns
2. `identify_unused_indexes()` - Find indexes to drop
3. `suggest_indexes()` - AI-powered index recommendations
4. `get_table_stats()` - Tables with high sequential scans

### **"Schema analysis / Discovery"**
1. `get_schemas()` - List all database schemas
2. `get_table_names()` - List all tables
3. `get_table_stats()` - Table usage and size information
4. `get_index_usage()` - Index structure analysis

### **"Connection issues"**
1. `test_connection()` - Basic connectivity test
2. `get_active_sessions()` - Current session analysis
3. `get_connection_pool_stats()` - Pool efficiency analysis
4. `get_blocking_queries()` - Check for connection blocks

## 🔧 **Tool Categories**

### **Connection & Health**
- `test_connection()` - Database connectivity verification
- `get_active_sessions()` - Real-time session monitoring
- `get_connection_pool_stats()` - Connection management analysis

### **Performance Analysis**
- `get_slow_queries()` - Query performance analysis (requires pg_stat_statements)
- `get_table_stats()` - Table access patterns and efficiency
- `get_buffer_cache_stats()` - Memory cache performance
- `get_wait_events()` - Database wait event analysis

### **Schema & Structure**
- `get_schemas()` - Database schema discovery
- `get_table_names()` - Table inventory
- `get_index_usage()` - Index usage and efficiency analysis

### **Optimization & Troubleshooting**
- `suggest_indexes()` - AI-powered index recommendations
- `identify_unused_indexes()` - Index cleanup opportunities
- `get_blocking_queries()` - Lock and blocking analysis

## ⚡ **Best Practices**

1. **Always start with connectivity**: Use `test_connection()` first
2. **Check active load**: Use `get_active_sessions()` to understand current activity
3. **Performance issues**: Start with `get_slow_queries()` then drill down
4. **Index analysis**: Combine `get_index_usage()` with `identify_unused_indexes()`
5. **Blocking issues**: Use `get_blocking_queries()` with `get_wait_events()`

## 📊 **Tool Output Interpretation**

### **Sequential Scan Ratios** (from `get_table_stats()`)
- < 10%: Excellent index usage
- 10-50%: Acceptable, monitor closely
- > 50%: Index optimization needed

### **Buffer Cache Hit Ratio** (from `get_buffer_cache_stats()`)
- > 95%: Excellent memory efficiency
- 90-95%: Good performance
- < 90%: Memory optimization needed

### **Index Scans** (from `get_index_usage()`)
- High scans: Well-utilized indexes
- Low/zero scans: Potential unused indexes
- Missing indexes: High sequential scans on tables

### **Active Sessions** (from `get_active_sessions()`)
- < 10: Normal load
- 10-50: Moderate load
- > 50: High load, investigate queries
"""

@mcp.prompt()
def query_performance_analysis() -> str:
    """
    Comprehensive query performance analysis workflow for Aurora PostgreSQL
    
    Use this prompt when you need to analyze slow queries, optimize performance,
    or investigate query-related performance issues.
    """
    return """
# Query Performance Analysis Guide

## 🔍 **Performance Analysis Workflow**

### Step 1: Identify Performance Issues
```
Primary Tool: get_slow_queries()
Purpose: Find queries with high execution time (>100ms mean)
Requirements: pg_stat_statements extension must be enabled
Look for: High total_exec_time, high mean_exec_time, frequent calls
```

### Step 2: Analyze Table Access Patterns
```
Primary Tool: get_table_stats()
Purpose: Identify tables with inefficient access patterns
Look for: High seq_scan_ratio (>50%), low idx_scan counts
Focus on: Tables with high sequential scan ratios
```

### Step 3: Review Index Efficiency
```
Primary Tool: get_index_usage()
Purpose: Understand current index utilization
Look for: Low idx_scan counts, unused indexes, missing indexes
Combine with: Table stats to identify optimization opportunities
```

### Step 4: Check Memory Efficiency
```
Primary Tool: get_buffer_cache_stats()
Purpose: Analyze memory cache performance
Target: >95% hit ratio for optimal performance
Low hit ratio: Indicates need for memory optimization or query tuning
```

### Step 5: Investigate Wait Events
```
Primary Tool: get_wait_events()
Purpose: Understand what queries are waiting for
Common waits: I/O waits, lock waits, CPU waits
Use with: get_blocking_queries() if lock waits are high
```

## 🎯 **Query Optimization Strategies**

### **High Sequential Scan Ratio**
1. Use `get_table_stats()` to identify problematic tables
2. Use `suggest_indexes()` for AI-powered recommendations
3. Analyze query patterns from `get_slow_queries()`
4. Create appropriate indexes based on WHERE clauses

### **Slow Query Patterns**
1. Identify from `get_slow_queries()` output
2. Look for queries with high mean_exec_time
3. Check if related tables have high seq_scan_ratio
4. Use `get_index_usage()` to verify index availability

### **Index Optimization**
1. Use `identify_unused_indexes()` to find cleanup opportunities
2. Use `get_index_usage()` to verify index efficiency
3. Use `suggest_indexes()` for new index recommendations
4. Balance between query performance and storage overhead

### **Memory Optimization**
1. Check `get_buffer_cache_stats()` for hit ratio
2. Low hit ratio may indicate:
   - Insufficient shared_buffers
   - Queries scanning too much data
   - Need for query optimization

## 🚨 **Performance Red Flags**

### **Critical Issues** (Investigate Immediately)
- Sequential scan ratio > 80% on large tables
- Buffer cache hit ratio < 90%
- Mean query execution time > 1000ms
- Active blocking queries present

### **Warning Signs** (Monitor Closely)
- Sequential scan ratio 50-80%
- Buffer cache hit ratio 90-95%
- Mean query execution time 100-1000ms
- High wait event counts

### **Optimization Opportunities**
- Unused indexes consuming storage
- Tables with moderate sequential scan ratios
- Queries with room for index optimization
- Connection pool inefficiencies

## 📋 **Analysis Report Structure**

### **Executive Summary**
- Overall query performance health
- Critical issues requiring immediate attention
- Key optimization opportunities

### **Slow Query Analysis**
- Top 10 slowest queries by total execution time
- Query patterns and frequency analysis
- Specific optimization recommendations

### **Index Analysis**
- Current index utilization efficiency
- Unused indexes for cleanup
- Missing index recommendations

### **Table Access Patterns**
- Tables with high sequential scan ratios
- Most accessed tables and their efficiency
- Storage and access optimization opportunities

### **System Resource Usage**
- Buffer cache efficiency
- Wait event analysis
- Connection pool utilization
"""

@mcp.prompt()
def database_troubleshooting() -> str:
    """
    Database troubleshooting guide for Aurora PostgreSQL issues
    
    Use this prompt when investigating database problems, connection issues,
    blocking queries, or other operational problems.
    """
    return """
# Database Troubleshooting Guide

## 🚨 **Emergency Troubleshooting Workflow**

### Step 1: Verify Basic Connectivity
```
Tool: test_connection()
Purpose: Confirm database is accessible and responsive
Success: Returns version, database name, current user
Failure: Check network, credentials, database status
```

### Step 2: Check Current Database Activity
```
Tool: get_active_sessions()
Purpose: See what's currently running on the database
Look for: High session counts, long-running queries, unusual activity
Normal: < 20 active sessions for most workloads
```

### Step 3: Identify Blocking Issues
```
Tool: get_blocking_queries()
Purpose: Find queries that are blocking others
Critical: Any blocking queries indicate immediate attention needed
Follow up: Use get_wait_events() to understand wait patterns
```

### Step 4: Analyze Wait Events
```
Tool: get_wait_events()
Purpose: Understand what active sessions are waiting for
Common waits: Lock waits, I/O waits, CPU waits
Action: Address based on wait event type
```

## 🔧 **Common Problem Scenarios**

### **"Database is completely unresponsive"**
1. `test_connection()` - Basic connectivity test
2. `get_active_sessions()` - Check for runaway queries
3. `get_blocking_queries()` - Look for deadlocks
4. `get_wait_events()` - Identify system bottlenecks

### **"Queries are running very slowly"**
1. `get_slow_queries()` - Identify problematic queries
2. `get_active_sessions()` - Check current query load
3. `get_buffer_cache_stats()` - Memory efficiency check
4. `get_table_stats()` - Look for sequential scan issues

### **"Too many connections / Connection errors"**
1. `get_connection_pool_stats()` - Analyze connection usage
2. `get_active_sessions()` - Count current sessions
3. Check for connection leaks in application
4. Review connection pool configuration

### **"Database locks / Deadlocks"**
1. `get_blocking_queries()` - Identify blocking relationships
2. `get_wait_events()` - Analyze lock wait patterns
3. `get_active_sessions()` - See which sessions are involved
4. Review transaction patterns and duration

### **"High CPU / Resource usage"**
1. `get_slow_queries()` - Find CPU-intensive queries
2. `get_active_sessions()` - Check concurrent query load
3. `get_table_stats()` - Look for inefficient table scans
4. `get_index_usage()` - Verify index utilization

## 🎯 **Troubleshooting Decision Tree**

### **Connection Issues**
```
test_connection() FAILS
├── Network/DNS issues → Check connectivity
├── Authentication → Verify credentials
└── Database down → Check Aurora cluster status

test_connection() SUCCESS but slow
├── get_active_sessions() → Check load
├── get_blocking_queries() → Check locks
└── get_buffer_cache_stats() → Check memory
```

### **Performance Issues**
```
Slow performance reported
├── get_slow_queries() → Identify problem queries
├── get_table_stats() → Check scan ratios
├── get_index_usage() → Verify index efficiency
└── get_wait_events() → Identify bottlenecks
```

### **Blocking/Lock Issues**
```
Queries hanging/timing out
├── get_blocking_queries() → Find blockers
├── get_active_sessions() → See all activity
├── get_wait_events() → Analyze wait types
└── Consider killing blocking sessions
```

## 📊 **Diagnostic Metrics**

### **Session Analysis** (from `get_active_sessions()`)
- **Normal**: 5-20 active sessions
- **Busy**: 20-50 active sessions  
- **Overloaded**: >50 active sessions
- **Red flag**: Sessions with duration >300 seconds

### **Blocking Analysis** (from `get_blocking_queries()`)
- **Any blocking**: Requires immediate investigation
- **Multiple blocks**: Potential deadlock situation
- **Long blocks**: >30 seconds indicates serious issue

### **Wait Events** (from `get_wait_events()`)
- **Lock waits**: Blocking query issues
- **I/O waits**: Storage performance problems
- **CPU waits**: Query optimization needed

### **Connection Health** (from `get_connection_pool_stats()`)
- **High idle**: Potential connection leaks
- **High active**: Heavy workload or slow queries
- **Uneven distribution**: Pool configuration issues

## 🚀 **Resolution Actions**

### **Immediate Actions**
- Kill long-running blocking queries
- Restart connection pools if leaking
- Scale up if resource constrained

### **Short-term Fixes**
- Optimize identified slow queries
- Add missing indexes
- Adjust connection pool settings

### **Long-term Solutions**
- Query optimization program
- Index maintenance strategy
- Capacity planning and monitoring
"""

@mcp.prompt()
def index_optimization() -> str:
    """
    Index optimization and management guide for Aurora PostgreSQL
    
    Use this prompt when you need to optimize indexes, clean up unused indexes,
    or improve query performance through better indexing strategies.
    """
    return """
# Index Optimization Guide

## 🎯 **Index Analysis Workflow**

### Step 1: Current Index Assessment
```
Tool: get_index_usage()
Purpose: Understand current index utilization patterns
Look for: idx_scan counts, index sizes, usage efficiency
Focus on: Indexes with low scan counts relative to size
```

### Step 2: Identify Unused Indexes
```
Tool: identify_unused_indexes()
Purpose: Find indexes that are consuming storage without benefit
Criteria: < 10 scans and not primary keys
Action: Consider dropping after verification
```

### Step 3: Find Missing Index Opportunities
```
Tool: get_table_stats()
Purpose: Identify tables with high sequential scan ratios
Target: Tables with seq_scan_ratio > 50%
Follow up: Use suggest_indexes() for recommendations
```

### Step 4: AI-Powered Index Suggestions
```
Tool: suggest_indexes()
Purpose: Get intelligent index recommendations
Based on: Sequential scan patterns and query analysis
Validation: Cross-reference with actual query patterns
```

## 📊 **Index Optimization Strategies**

### **Cleanup Strategy** (Remove Unused Indexes)
1. **Identify candidates**: Use `identify_unused_indexes()`
2. **Verify safety**: Ensure not used by critical queries
3. **Storage impact**: Note size savings from removal
4. **Maintenance benefit**: Reduced overhead on DML operations

**Cleanup Criteria:**
- Index scan count < 10
- Not a primary key or unique constraint
- Significant storage consumption
- No recent usage pattern

### **Creation Strategy** (Add Missing Indexes)
1. **Find opportunities**: Use `get_table_stats()` for high seq_scan_ratio
2. **Get suggestions**: Use `suggest_indexes()` for recommendations
3. **Analyze queries**: Review `get_slow_queries()` for patterns
4. **Validate benefit**: Estimate performance improvement

**Creation Criteria:**
- Table sequential scan ratio > 50%
- Frequent slow queries on the table
- Clear WHERE clause patterns
- Significant query volume

### **Optimization Strategy** (Improve Existing Indexes)
1. **Usage analysis**: Use `get_index_usage()` for efficiency metrics
2. **Size vs benefit**: Compare index size to scan frequency
3. **Composite opportunities**: Combine multiple single-column indexes
4. **Partial index options**: Consider filtered indexes for specific conditions

## 🔍 **Index Analysis Metrics**

### **Index Efficiency Indicators**
```
From get_index_usage():
- idx_scan: Number of index scans performed
- idx_tup_read: Tuples read from index
- idx_tup_fetch: Tuples fetched using index
- index_size: Storage consumed by index
```

### **Efficiency Calculations**
- **Scan efficiency**: idx_tup_fetch / idx_tup_read (higher is better)
- **Usage frequency**: idx_scan / time_period
- **Storage efficiency**: idx_scan / index_size_mb
- **Fetch ratio**: idx_tup_fetch / idx_scan

### **Table Access Patterns**
```
From get_table_stats():
- seq_scan: Sequential scans performed
- idx_scan: Index scans performed  
- seq_scan_ratio: Percentage of sequential scans
- n_live_tup: Current row count
```

## 🎯 **Optimization Recommendations**

### **High Priority** (Immediate Action)
- **Drop unused indexes**: > 100MB size, < 10 scans
- **Add missing indexes**: seq_scan_ratio > 80% on large tables
- **Fix inefficient indexes**: Low fetch ratio, high storage cost

### **Medium Priority** (Plan for Implementation)
- **Composite index opportunities**: Multiple single-column indexes on same table
- **Partial index candidates**: Filtered conditions in WHERE clauses
- **Index maintenance**: REINDEX for bloated indexes

### **Low Priority** (Monitor and Evaluate)
- **Borderline unused indexes**: 10-100 scans, moderate size
- **Optimization opportunities**: seq_scan_ratio 30-50%
- **Storage optimization**: Small indexes with low usage

## 📋 **Index Optimization Report Structure**

### **Executive Summary**
- Total indexes analyzed
- Storage consumed by unused indexes
- Potential performance improvements
- Recommended immediate actions

### **Cleanup Opportunities**
- List of unused indexes with storage impact
- Safety verification for each index
- Estimated maintenance overhead reduction

### **Missing Index Recommendations**
- Tables with high sequential scan ratios
- Specific index suggestions with rationale
- Estimated performance improvement

### **Optimization Opportunities**
- Existing indexes with low efficiency
- Composite index consolidation options
- Partial index candidates

## 🚨 **Index Management Best Practices**

### **Before Dropping Indexes**
1. Verify no critical queries depend on the index
2. Check for unique constraints or foreign keys
3. Monitor for at least one full business cycle
4. Have rollback plan ready

### **Before Creating Indexes**
1. Analyze actual query patterns, not just statistics
2. Consider impact on INSERT/UPDATE/DELETE performance
3. Estimate storage requirements
4. Plan for maintenance windows

### **Ongoing Monitoring**
1. Regular index usage analysis (monthly)
2. Monitor query performance after changes
3. Track storage growth and cleanup opportunities
4. Maintain index creation/deletion log
"""

def get_aurora_config() -> Dict[str, Any]:
    """
    Get Aurora configuration from Secrets Manager (Project Rule #2)
    
    WHAT IT IS:
    This function retrieves all Aurora PostgreSQL connection parameters from
    AWS Secrets Manager. No hardcoded credentials or connection details.
    
    WHERE WE USE IT:
    - Database connections: All MCP tools use this for Aurora access
    - Connection pooling: Ensures consistent connection parameters
    - Security compliance: Centralized credential management
    
    Returns:
        Dict[str, Any]: Aurora connection parameters from Secrets Manager
        
    Raises:
        Exception: If Secrets Manager access fails
    """
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config.secrets import SecretsManager
        
        secrets_manager = SecretsManager()
        config = secrets_manager.get_aurora_config()
        
        if not config:
            raise Exception("No Aurora configuration found in Secrets Manager")
            
        logger.info("Aurora configuration retrieved from Secrets Manager")
        return config
        
    except Exception as e:
        logger.error(f"Failed to get Aurora config from Secrets Manager: {e}")
        raise Exception(f"Secrets Manager error: {e}")

def execute_query(query: str) -> List:
    """
    Execute SQL query on Aurora database with proper error handling
    
    WHAT IT IS:
    This function executes PostgreSQL queries on the Aurora cluster using
    connection parameters from Secrets Manager. Handles connection lifecycle.
    
    WHERE WE USE IT:
    - All MCP tools: Database introspection and performance analysis
    - Session monitoring: Real-time database activity queries
    - Performance metrics: Query execution statistics and analysis
    
    Args:
        query (str): SQL query to execute on Aurora PostgreSQL
        
    Returns:
        List: Query results as list of tuples
        
    Raises:
        Exception: If database connection or query execution fails
    """
    try:
        config = get_aurora_config()
        
        # Validate required connection parameters
        required_params = ['host', 'port', 'database', 'user', 'password']
        for param in required_params:
            if not config.get(param):
                raise Exception(f"Missing required parameter '{param}' in Secrets Manager")
        
        conn = psycopg2.connect(
            host=config['host'], port=config['port'], database=config['database'],
            user=config['user'], password=config['password']
        )
        
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise Exception(f"Database error: {e}")

@mcp.tool()
def test_connection() -> Dict[str, Any]:
    """
    Test Aurora database connection and retrieve basic database information
    
    WHAT IT IS:
    This tool validates connectivity to the Aurora PostgreSQL cluster and
    retrieves essential database metadata for connection verification.
    
    WHERE WE USE IT:
    - Agent initialization: Verify database connectivity before analysis
    - Health checks: Ensure Aurora cluster is accessible and responsive
    - Troubleshooting: Diagnose connection issues and database status
    
    Returns:
        Dict[str, Any]: Connection status with database version, name, and user
    """
    try:
        results = execute_query("SELECT version(), current_database(), current_user")
        if results:
            return {
                "status": "success",
                "version": results[0][0],
                "database": results[0][1], 
                "user": results[0][2]
            }
        return {"status": "error", "error": "No results from connection test"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_active_sessions() -> Dict[str, Any]:
    """
    Get real active sessions from Aurora PostgreSQL for performance monitoring
    
    WHAT IT IS:
    This tool queries pg_stat_activity to retrieve current database sessions,
    excluding idle connections to focus on active database workload.
    
    WHERE WE USE IT:
    - Performance analysis: Identify active queries and session patterns
    - Capacity planning: Monitor concurrent session usage
    - Troubleshooting: Detect long-running or problematic sessions
    
    Returns:
        Dict[str, Any]: List of active sessions with PID, user, state, duration
    """
    try:
        query = """
        SELECT pid, usename, application_name, client_addr, state, 
               EXTRACT(EPOCH FROM (now() - query_start)) as duration_seconds
        FROM pg_stat_activity 
        WHERE state != 'idle' AND pid != pg_backend_pid()
        ORDER BY query_start DESC LIMIT 20
        """
        
        results = execute_query(query)
        sessions = []
        
        for row in results:
            sessions.append({
                'pid': row[0], 'username': row[1], 'application': row[2],
                'client_addr': str(row[3]) if row[3] else 'local',
                'state': row[4], 'duration_seconds': float(row[5]) if row[5] else 0
            })
        
        return {"status": "success", "data": sessions, "count": len(sessions)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_table_names() -> Dict[str, Any]:
    """
    Get all table names from public schema for database structure analysis
    
    WHAT IT IS:
    This tool queries information_schema to retrieve all user tables in the
    public schema, providing database structure overview.
    
    WHERE WE USE IT:
    - Schema analysis: Understand database structure and table organization
    - Query optimization: Identify tables involved in performance issues
    - Capacity planning: Analyze table count and database complexity
    
    Returns:
        Dict[str, Any]: List of table names in public schema
    """
    try:
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        results = execute_query(query)
        tables = [row[0] for row in results]
        
        return {"status": "success", "data": tables, "count": len(tables)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_slow_queries() -> Dict[str, Any]:
    """
    Get slow queries from pg_stat_statements for performance optimization
    
    WHAT IT IS:
    This tool analyzes pg_stat_statements extension data to identify queries
    with high execution time, essential for database performance tuning.
    
    WHERE WE USE IT:
    - Performance optimization: Identify queries requiring optimization
    - Index recommendations: Find queries that would benefit from indexes
    - Resource analysis: Understand query resource consumption patterns
    
    Returns:
        Dict[str, Any]: List of slow queries with execution statistics
    """
    try:
        # Check if extension exists
        ext_check = execute_query("SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'")
        if not ext_check:
            return {"status": "error", "error": "pg_stat_statements extension not available"}
        
        query = """
        SELECT query, calls, total_exec_time, mean_exec_time, rows
        FROM pg_stat_statements 
        WHERE mean_exec_time > 100
        ORDER BY total_exec_time DESC LIMIT 20
        """
        
        results = execute_query(query)
        queries = []
        
        for row in results:
            queries.append({
                'query': row[0][:300] if row[0] else '',
                'calls': int(row[1]) if row[1] else 0,
                'total_exec_time_ms': float(row[2]) if row[2] else 0,
                'mean_exec_time_ms': float(row[3]) if row[3] else 0,
                'rows_affected': int(row[4]) if row[4] else 0
            })
        
        return {"status": "success", "data": queries, "count": len(queries)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_table_stats() -> Dict[str, Any]:
    """
    Get table usage statistics for performance analysis and optimization
    
    WHAT IT IS:
    This tool queries pg_stat_user_tables to analyze table access patterns,
    sequential scan ratios, and overall table performance characteristics.
    
    WHERE WE USE IT:
    - Index optimization: Identify tables with high sequential scan ratios
    - Performance tuning: Understand table access patterns and efficiency
    - Capacity planning: Analyze table size and usage for resource planning
    
    Returns:
        Dict[str, Any]: Table statistics with scan ratios and access patterns
    """
    try:
        query = """
        SELECT schemaname, relname as tablename, n_live_tup, seq_scan, idx_scan,
               CASE WHEN (seq_scan + idx_scan) > 0 
                    THEN seq_scan::float / (seq_scan + idx_scan) * 100 
                    ELSE 0 END as seq_scan_ratio
        FROM pg_stat_user_tables
        ORDER BY seq_scan DESC LIMIT 20
        """
        
        results = execute_query(query)
        tables = []
        
        for row in results:
            tables.append({
                'schema': row[0], 'table_name': row[1], 'live_rows': int(row[2]) if row[2] else 0,
                'seq_scans': int(row[3]) if row[3] else 0, 'idx_scans': int(row[4]) if row[4] else 0,
                'seq_scan_ratio_percent': round(float(row[5]), 2) if row[5] else 0
            })
        
        return {"status": "success", "data": tables, "count": len(tables)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_schemas() -> Dict[str, Any]:
    """Get all schemas in the database"""
    try:
        query = """
        SELECT schema_name FROM information_schema.schemata 
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
        ORDER BY schema_name
        """
        results = execute_query(query)
        schemas = [row[0] for row in results]
        return {"status": "success", "data": schemas, "count": len(schemas)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_index_usage() -> Dict[str, Any]:
    """Get index usage statistics"""
    try:
        query = """
        SELECT schemaname, relname as tablename, indexrelname as indexname, idx_scan, idx_tup_read, idx_tup_fetch,
               pg_size_pretty(pg_relation_size(indexrelid)) as index_size
        FROM pg_stat_user_indexes ORDER BY idx_scan ASC LIMIT 50
        """
        results = execute_query(query)
        indexes = []
        for row in results:
            indexes.append({
                'schema': row[0], 'table_name': row[1], 'index_name': row[2],
                'scans': int(row[3]) if row[3] else 0, 'rows_read': int(row[4]) if row[4] else 0,
                'rows_fetched': int(row[5]) if row[5] else 0, 'size': row[6]
            })
        return {"status": "success", "data": indexes, "count": len(indexes)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_blocking_queries() -> Dict[str, Any]:
    """Get blocking queries"""
    try:
        query = """
        SELECT blocked_locks.pid AS blocked_pid, blocked_activity.usename AS blocked_user,
               blocked_activity.query AS blocked_query, blocking_locks.pid AS blocking_pid,
               blocking_activity.usename AS blocking_user, blocking_activity.query AS blocking_query
        FROM pg_catalog.pg_locks blocked_locks
        JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
        JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
            AND blocking_locks.pid != blocked_locks.pid
        JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
        WHERE NOT blocked_locks.granted LIMIT 20
        """
        results = execute_query(query)
        blocking = []
        for row in results:
            blocking.append({
                'blocked_pid': int(row[0]), 'blocked_user': row[1], 'blocked_query': row[2][:200] if row[2] else '',
                'blocking_pid': int(row[3]), 'blocking_user': row[4], 'blocking_query': row[5][:200] if row[5] else ''
            })
        return {"status": "success", "data": blocking, "count": len(blocking)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def suggest_indexes() -> Dict[str, Any]:
    """AI-powered index suggestions"""
    try:
        query = """
        SELECT schemaname, relname as tablename, seq_scan, idx_scan, n_live_tup
        FROM pg_stat_user_tables WHERE seq_scan > idx_scan AND seq_scan > 100
        ORDER BY seq_scan DESC LIMIT 10
        """
        results = execute_query(query)
        suggestions = []
        for row in results:
            suggestions.append({
                'table': f"{row[0]}.{row[1]}", 'seq_scans': int(row[2]), 'idx_scans': int(row[3]),
                'recommendation': f"Consider adding index to {row[0]}.{row[1]} - high sequential scans"
            })
        return {"status": "success", "data": suggestions, "count": len(suggestions)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_buffer_cache_stats() -> Dict[str, Any]:
    """Get buffer cache statistics"""
    try:
        query = """
        SELECT sum(heap_blks_hit) as heap_hit, sum(heap_blks_read) as heap_read,
               sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) * 100 as hit_ratio
        FROM pg_statio_user_tables WHERE (heap_blks_hit + heap_blks_read) > 0
        """
        results = execute_query(query)
        if results:
            row = results[0]
            return {
                "status": "success", 
                "heap_blocks_hit": int(row[0]) if row[0] else 0,
                "heap_blocks_read": int(row[1]) if row[1] else 0,
                "hit_ratio_percent": round(float(row[2]), 2) if row[2] else 0
            }
        return {"status": "success", "data": {}}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_wait_events() -> Dict[str, Any]:
    """Get wait event analysis"""
    try:
        query = """
        SELECT wait_event_type, wait_event, count(*) as session_count
        FROM pg_stat_activity WHERE wait_event IS NOT NULL AND state = 'active'
        GROUP BY wait_event_type, wait_event ORDER BY session_count DESC
        """
        results = execute_query(query)
        events = []
        for row in results:
            events.append({
                'wait_event_type': row[0], 'wait_event': row[1], 'session_count': int(row[2])
            })
        return {"status": "success", "data": events, "count": len(events)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_connection_pool_stats() -> Dict[str, Any]:
    """Get connection pool statistics"""
    try:
        query = """
        SELECT application_name, count(*) as connection_count,
               count(CASE WHEN state = 'active' THEN 1 END) as active_connections,
               count(CASE WHEN state = 'idle' THEN 1 END) as idle_connections
        FROM pg_stat_activity WHERE pid != pg_backend_pid()
        GROUP BY application_name ORDER BY connection_count DESC
        """
        results = execute_query(query)
        stats = []
        for row in results:
            stats.append({
                'application_name': row[0] or 'unknown', 'total_connections': int(row[1]),
                'active_connections': int(row[2]) if row[2] else 0, 'idle_connections': int(row[3]) if row[3] else 0
            })
        return {"status": "success", "data": stats, "count": len(stats)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def identify_unused_indexes() -> Dict[str, Any]:
    """Identify unused indexes"""
    try:
        query = """
        SELECT schemaname, relname as tablename, indexrelname as indexname, idx_scan,
               pg_size_pretty(pg_relation_size(indexrelid)) as index_size
        FROM pg_stat_user_indexes WHERE idx_scan < 10 AND indexrelname NOT LIKE '%_pkey'
        ORDER BY pg_relation_size(indexrelid) DESC LIMIT 20
        """
        results = execute_query(query)
        unused = []
        for row in results:
            unused.append({
                'schema': row[0], 'table_name': row[1], 'index_name': row[2],
                'scan_count': int(row[3]) if row[3] else 0, 'size': row[4]
            })
        return {"status": "success", "data": unused, "count": len(unused)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    print("🚀 Starting Aurora MCP Server...")
    print("📊 Available tools: 13 total (test_connection, get_active_sessions, get_table_names, get_slow_queries, get_table_stats, get_schemas, get_index_usage, get_blocking_queries, suggest_indexes, get_buffer_cache_stats, get_wait_events, get_connection_pool_stats, identify_unused_indexes)")
    print("🌐 Starting on http://localhost:8081/mcp")
    
    try:
        mcp.run(transport="streamable-http", port=8081)
    except KeyboardInterrupt:
        print("\n👋 Aurora MCP Server stopped")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        import traceback
        traceback.print_exc()
