# Aurora PostgreSQL Queries Reference

## All Queries Used in MCP Tools

### 1. Active Sessions (`get_active_sessions`)
```sql
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query,
    query_start,
    EXTRACT(EPOCH FROM (now() - query_start)) as duration_seconds,
    backend_start
FROM pg_stat_activity 
WHERE state != 'idle' 
AND pid != pg_backend_pid()
ORDER BY query_start DESC
LIMIT 50
```

### 2. Table Names (`get_table_names`)
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
```

### 3. Table Definition (`get_table_definition`)
```sql
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'TABLE_NAME' 
ORDER BY ordinal_position
```

### 4. Slow Queries (`get_slow_queries`)
**Extension Check:**
```sql
SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
```

**Slow Queries:**
```sql
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
WHERE mean_exec_time > 100
ORDER BY total_exec_time DESC 
LIMIT 50
```

### 5. Table Statistics (`get_table_stats`)
```sql
SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch
FROM pg_stat_user_tables
ORDER BY seq_scan DESC, n_live_tup DESC 
LIMIT 50
```

### 6. Index Usage (`get_index_usage`)
```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC 
LIMIT 100
```

### 7. Blocking Queries (`get_blocking_queries`)
```sql
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocked_activity.query AS blocked_query,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocking_activity.query AS blocking_query,
    EXTRACT(EPOCH FROM (now() - blocked_activity.query_start)) as wait_duration_seconds
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted 
ORDER BY wait_duration_seconds DESC
```

### 8. Index Suggestions (`suggest_indexes`)
**High Sequential Scan Tables:**
```sql
SELECT schemaname, tablename, seq_scan, idx_scan, n_live_tup
FROM pg_stat_user_tables 
WHERE seq_scan > idx_scan AND seq_scan > 100 AND n_live_tup > 1000
ORDER BY seq_scan DESC 
LIMIT 10
```

**Column Analysis:**
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = $1 AND table_name = $2
AND data_type IN ('integer', 'bigint', 'varchar', 'text', 'timestamp', 'date')
ORDER BY ordinal_position 
LIMIT 5
```

### 9. Buffer Cache Stats (`get_buffer_cache_stats`)
**Overall Cache Hit Ratio:**
```sql
SELECT 
    sum(heap_blks_hit) as heap_hit,
    sum(heap_blks_read) as heap_read,
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) * 100 as hit_ratio
FROM pg_statio_user_tables 
WHERE (heap_blks_hit + heap_blks_read) > 0
```

**Per-Table Cache Stats:**
```sql
SELECT 
    schemaname,
    tablename,
    heap_blks_hit,
    heap_blks_read,
    CASE WHEN (heap_blks_hit + heap_blks_read) > 0 
         THEN heap_blks_hit::float / (heap_blks_hit + heap_blks_read) * 100 
         ELSE 0 END as hit_ratio
FROM pg_statio_user_tables
WHERE (heap_blks_hit + heap_blks_read) > 100
ORDER BY (heap_blks_hit + heap_blks_read) DESC 
LIMIT 20
```

### 10. Wait Events (`get_wait_events`)
```sql
SELECT 
    wait_event_type,
    wait_event,
    count(*) as session_count,
    avg(EXTRACT(EPOCH FROM (now() - query_start))) as avg_wait_seconds
FROM pg_stat_activity 
WHERE wait_event IS NOT NULL AND state = 'active'
GROUP BY wait_event_type, wait_event
ORDER BY session_count DESC
```

### 11. Connection Pool Stats (`get_connection_pool_stats`)
```sql
SELECT 
    application_name,
    count(*) as connection_count,
    count(CASE WHEN state = 'active' THEN 1 END) as active_connections,
    count(CASE WHEN state = 'idle' THEN 1 END) as idle_connections,
    avg(EXTRACT(EPOCH FROM (now() - backend_start))) as avg_connection_age_seconds
FROM pg_stat_activity 
WHERE pid != pg_backend_pid()
GROUP BY application_name 
ORDER BY connection_count DESC
```

### 12. Unused Indexes (`identify_unused_indexes`)
```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    pg_relation_size(indexrelid) as size_bytes
FROM pg_stat_user_indexes
WHERE idx_scan < 10 AND indexname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC, idx_scan ASC
```

## Required PostgreSQL Extensions

### pg_stat_statements
- **Purpose**: Query performance statistics
- **Used by**: `get_slow_queries`
- **Check**: `SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'`

## System Views Used

- **pg_stat_activity**: Current database activity and sessions
- **pg_stat_user_tables**: Table-level statistics
- **pg_stat_user_indexes**: Index usage statistics  
- **pg_statio_user_tables**: Table I/O statistics
- **pg_locks**: Lock information for blocking query detection
- **information_schema.tables**: Table metadata
- **information_schema.columns**: Column metadata
- **pg_stat_statements**: Query execution statistics (extension)

## Validation Checklist

✅ **Basic Connectivity**
- Can connect to Aurora cluster
- Database and user permissions work

✅ **System Views Access**
- pg_stat_activity readable
- pg_stat_user_* views accessible
- information_schema accessible

✅ **Extensions**
- pg_stat_statements installed and enabled
- Extension permissions granted

✅ **Data Availability**
- Tables exist in public schema
- Statistics have been collected
- Realistic data for testing

## Testing Commands

```bash
# Test basic connectivity
psql -h hackathon-demo.cluster-c7leamkjhfqz.us-east-1.rds.amazonaws.com -p 5432 -d demodb -U postgres

# Check extensions
SELECT extname, extversion FROM pg_extension;

# Check statistics collection
SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables LIMIT 5;

# Verify permissions
SELECT has_table_privilege('pg_stat_activity', 'SELECT');
```
