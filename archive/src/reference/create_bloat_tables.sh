#!/bin/bash

# Script: create-healthcheck-workload.sh
# Purpose: Create HR schema with duplicate names, bloat, and unused indexes for PostgreSQL health check testing
# Version: 3.0 - Uses PostgreSQL environment variables

# Function to display usage information
usage() {
  echo "Usage: $0 [--duration <MINUTES>] [--database <DB_NAME>] [--help]"
  echo
  echo "This script uses PostgreSQL environment variables from ~/.bashrc:"
  echo "  PGHOST      - Database host"
  echo "  PGPORT      - Database port (default: 5432)"
  echo "  PGUSER      - Database user"
  echo "  PGPASSWORD  - Database password"
  echo "  PGDATABASE  - Default database (can be overridden with --database)"
  echo
  echo "Options:"
  echo "  --duration <MINUTES>   Duration for workload in minutes (default: 5)"
  echo "  --database <DB_NAME>   Override database name (default: uses PGDATABASE)"
  echo "  --help                 Display this help message"
  echo
  echo "Example:"
  echo "  $0 --duration 10 --database hr_messy"
  echo "  $0  # Uses all environment variables with defaults"
  exit 1
}

# Default values
DURATION=5
DB_NAME=${PGDATABASE:-"hr_messy"}

# Parse input flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --duration)
      DURATION=$2
      shift 2
      ;;
    --database)
      DB_NAME=$2
      shift 2
      ;;
    --help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Check if required environment variables are set
if [ -z "$PGHOST" ] || [ -z "$PGUSER" ] || [ -z "$PGPASSWORD" ]; then
  echo "Error: Required PostgreSQL environment variables are not set"
  echo "Please ensure the following are set in ~/.bashrc:"
  echo "  export PGHOST=your-db-host"
  echo "  export PGUSER=your-db-user"
  echo "  export PGPASSWORD=your-db-password"
  echo "  export PGDATABASE=your-default-db (optional)"
  echo "  export PGPORT=5432 (optional, defaults to 5432)"
  echo ""
  echo "Then run: source ~/.bashrc"
  exit 1
fi

# Set defaults for optional environment variables
PGPORT=${PGPORT:-5432}

# Convert duration to seconds for pgbench
DURATION_SECONDS=$((DURATION * 60))

echo "========================================"
echo "Creating HR schema with duplicate names and bloat"
echo "========================================"
echo "Host: $PGHOST"
echo "Port: $PGPORT"
echo "User: $PGUSER"
echo "Database: $DB_NAME"
echo "Duration: $DURATION minutes"
echo ""

# Test connection first
echo "Testing database connection..."
psql -c '\q' 2>/dev/null
if [ $? -ne 0 ]; then
  echo "Error: Unable to connect to database. Please check your environment variables:"
  echo "  PGHOST=$PGHOST"
  echo "  PGPORT=$PGPORT"
  echo "  PGUSER=$PGUSER"
  echo "  PGPASSWORD=[hidden]"
  exit 1
fi


# Create bloat by deleting and reloading data
echo "Creating table bloat (deleting and reloading data)..."
for cycle in 1 2; do
  echo "  Bloat cycle $cycle of 2..."
  
  # Delete all data
  psql -d $DB_NAME -q << 'SQL_DELETE_EOF'
DELETE FROM employee_projects;
DELETE FROM employees;
DELETE FROM projects;
DELETE FROM departments;
ALTER SEQUENCE employees_emp_id_seq RESTART WITH 1;
ALTER SEQUENCE departments_dept_id_seq RESTART WITH 1;
ALTER SEQUENCE projects_proj_id_seq RESTART WITH 1;
SQL_DELETE_EOF

  # Reload data
  psql -d $DB_NAME -q << 'SQL_RELOAD_EOF'
-- Reload employees with duplicate first names
INSERT INTO employees (first_name, last_name, email, department_id, salary)
SELECT 
    'first_name_' || ((n-1)/3 + 1) AS first_name,
    'last_name_' || ((n-1)/3 + 1) || '_' || ((n-1)%3 + 1) AS last_name,
    'user' || n || '@company.com' AS email,
    (random() * 100)::INTEGER AS department_id,
    (random() * 100000)::NUMERIC(10,2) AS salary
FROM generate_series(1, 3000000) n;

-- Reload departments
INSERT INTO departments (dept_name)
SELECT 'dept_name_' || n
FROM generate_series(1, 100) n;

-- Reload projects  
INSERT INTO projects (proj_name, budget)
SELECT 
    'project_' || n,
    (random() * 1000000)::NUMERIC(12,2)
FROM generate_series(1, 1000000) n;

-- Reload employee_projects
INSERT INTO employee_projects (emp_id, proj_id)
SELECT DISTINCT
    (random() * 2999999 + 1)::INTEGER,
    (random() * 999999 + 1)::INTEGER
FROM generate_series(1, 3000000) n
ON CONFLICT DO NOTHING;

ANALYZE;
SQL_RELOAD_EOF
done

# Re-enable autovacuum
echo "Re-enabling autovacuum..."
psql -d $DB_NAME -q << 'SQL_VACUUM_EOF'
ALTER TABLE employees SET (autovacuum_enabled = on);
ALTER TABLE departments SET (autovacuum_enabled = on);
ALTER TABLE projects SET (autovacuum_enabled = on);
ALTER TABLE employee_projects SET (autovacuum_enabled = on);
SQL_VACUUM_EOF

# Final verification
echo ""
echo "========================================"
echo "Final Statistics"
echo "========================================"

# Show final duplicate count
echo "Final duplicate name count:"
psql -d $DB_NAME -c "
SELECT COUNT(*) as occurrences, first_name 
FROM employees 
GROUP BY first_name 
HAVING COUNT(*) > 1 
ORDER BY COUNT(*) DESC 
LIMIT 20;"

# Show table sizes
echo ""
echo "Table sizes:"
psql -d $DB_NAME -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Show index usage stats
echo ""
echo "Index usage (unused indexes will have 0 scans):"
psql -d $DB_NAME -c "
SELECT 
    schemaname,
    relname,
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan;"


echo ""
echo "========================================"
echo "Benchmark completed!"
echo "========================================"
echo ""
echo "Database $DB_NAME is now ready for health check testing with:"
echo "- Tables containing ~3M rows each with duplicate first names"
echo "- Duplicate indexes for detection"
echo "- Unused indexes (with 0 scans)"
echo "- Table bloat from DELETE/INSERT operations"
echo ""
echo "To run the health check:"
echo "bash src/postgres-healthcheck.sh --database $DB_NAME --top-tables --duplicate-indexes --unused-indexes --bloat-analysis"
echo ""
echo "Environment variables used:"
echo "  PGHOST=$PGHOST"
echo "  PGPORT=$PGPORT"
echo "  PGUSER=$PGUSER"
echo "  PGDATABASE=$DB_NAME"
echo ""