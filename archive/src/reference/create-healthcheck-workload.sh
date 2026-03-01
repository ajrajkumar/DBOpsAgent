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

# Handle database setup based on database name
if [ "$DB_NAME" = "postgres" ]; then
  echo "Using default 'postgres' database - dropping existing tables..."
  psql -d $DB_NAME << 'SQL_DROP_TABLES_EOF'
-- Drop tables if they exist (in correct order due to foreign key constraints)
DROP TABLE IF EXISTS employee_projects CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
SQL_DROP_TABLES_EOF
else
  echo "Dropping and recreating database '$DB_NAME'..."
  psql -c "DROP DATABASE IF EXISTS $DB_NAME;"
  psql -c "CREATE DATABASE $DB_NAME;"
fi

# Create tables
echo "Creating tables..."
psql -d $DB_NAME << 'SQL_TABLES_EOF'
CREATE TABLE employees (
    emp_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    department_id INT,
    salary NUMERIC(10, 2)
);

CREATE TABLE departments (
    dept_id SERIAL PRIMARY KEY,
    dept_name VARCHAR(50)
);

CREATE TABLE projects (
    proj_id SERIAL PRIMARY KEY,
    proj_name VARCHAR(50),
    budget NUMERIC(12, 2)
);

CREATE TABLE employee_projects (
    emp_id INT,
    proj_id INT,
    PRIMARY KEY (emp_id, proj_id),
    FOREIGN KEY (emp_id) REFERENCES employees(emp_id) ON DELETE CASCADE,
    FOREIGN KEY (proj_id) REFERENCES projects(proj_id) ON DELETE CASCADE
);

-- Disable autovacuum temporarily
ALTER TABLE employees SET (autovacuum_enabled = off);
ALTER TABLE departments SET (autovacuum_enabled = off);
ALTER TABLE projects SET (autovacuum_enabled = off);
ALTER TABLE employee_projects SET (autovacuum_enabled = off);
SQL_TABLES_EOF

# Generate initial data with duplicate names
echo "Generating initial data with duplicate names (this may take a few minutes)..."
psql -d $DB_NAME << 'SQL_DATA_EOF'
-- Generate employees with duplicate first names (each name appears 3 times)
INSERT INTO employees (first_name, last_name, email, department_id, salary)
SELECT 
    'first_name_' || ((n-1)/3 + 1) AS first_name,
    'last_name_' || ((n-1)/3 + 1) || '_' || ((n-1)%3 + 1) AS last_name,
    'user' || n || '@company.com' AS email,
    (random() * 100)::INTEGER AS department_id,
    (random() * 100000)::NUMERIC(10,2) AS salary
FROM generate_series(1, 6000000) n;

-- Generate departments
INSERT INTO departments (dept_name)
SELECT 'dept_name_' || n
FROM generate_series(1, 100) n;

-- Generate projects  
INSERT INTO projects (proj_name, budget)
SELECT 
    'project_' || n,
    (random() * 1000000)::NUMERIC(12,2)
FROM generate_series(1, 1000000) n;

-- Generate employee_projects
INSERT INTO employee_projects (emp_id, proj_id)
SELECT DISTINCT
    (random() * 2999999 + 1)::INTEGER,
    (random() * 999999 + 1)::INTEGER
FROM generate_series(1, 3000000) n
ON CONFLICT DO NOTHING;

ANALYZE;
SQL_DATA_EOF

# Verify initial data load
echo "Verifying initial data load..."
psql -d $DB_NAME -c "
SELECT 
    'employees' as table_name, COUNT(*) as row_count 
FROM employees
UNION ALL
SELECT 'departments', COUNT(*) FROM departments
UNION ALL  
SELECT 'projects', COUNT(*) FROM projects
UNION ALL
SELECT 'employee_projects', COUNT(*) FROM employee_projects;"

# Create indexes (including duplicates)
echo "Creating indexes (including duplicates)..."
psql -d $DB_NAME << 'SQL_INDEXES_EOF'
-- Create useful indexes
CREATE INDEX idx_emp_department ON employees(department_id);
CREATE INDEX idx_emp_salary ON employees(salary);
CREATE INDEX idx_dept_name ON departments(dept_name);
CREATE INDEX idx_proj_budget ON projects(budget);
CREATE INDEX idx_emp_proj_emp_id ON employee_projects(emp_id);
CREATE INDEX idx_emp_proj_proj_id ON employee_projects(proj_id);

-- Create duplicate indexes (for duplicate index detection)
CREATE INDEX idx_emp_department_dup1 ON employees(department_id);
CREATE INDEX idx_emp_salary_dup1 ON employees(salary);
CREATE INDEX idx_emp_salary_dup2 ON employees(salary);
CREATE INDEX idx_dept_name_dup1 ON departments(dept_name);
CREATE INDEX idx_proj_budget_dup1 ON projects(budget);
CREATE INDEX idx_emp_proj_emp_id_dup1 ON employee_projects(emp_id);
CREATE INDEX idx_emp_proj_proj_id_dup1 ON employee_projects(proj_id);

-- Create some unused indexes (that won't be used by any queries)
CREATE INDEX idx_emp_unused ON employees(first_name, last_name, salary);
CREATE INDEX idx_proj_unused ON projects(proj_name, budget);

ANALYZE;
SQL_INDEXES_EOF

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
FROM generate_series(1, 6000000) n;

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

# Verify duplicate names
echo "Verifying duplicate names..."
psql -d $DB_NAME -c "
SELECT COUNT(*) as occurrences, first_name 
FROM employees 
GROUP BY first_name 
HAVING COUNT(*) > 1 
ORDER BY COUNT(*) DESC 
LIMIT 10;"

# Create pgbench workload script
echo "Creating workload script..."
cat << 'WORKLOAD_SCRIPT_EOF' > /tmp/hr_workload_$$.sql
\set emp_id random(1, 6000000)
\set salary_increase random(100, 5000)
\set new_salary random(30000, 150000)
\set dept_id random(1, 100)

-- Update operations that don't change first_name
BEGIN;
UPDATE employees SET salary = salary + :salary_increase WHERE emp_id = :emp_id;
COMMIT;

BEGIN;
UPDATE employees SET department_id = :dept_id WHERE emp_id = :emp_id;
COMMIT;

BEGIN;
UPDATE employees SET last_name = last_name || '_u' WHERE emp_id = :emp_id AND length(last_name) < 45;
COMMIT;

-- Insert duplicate rows (maintains the pattern)
BEGIN;
INSERT INTO employees (first_name, last_name, email, department_id, salary)
SELECT first_name, last_name || '_dup', email || '_dup', department_id, :new_salary
FROM employees
WHERE emp_id = :emp_id;
COMMIT;

-- Delete some duplicate entries to create more bloat
BEGIN;
DELETE FROM employees 
WHERE emp_id IN (
    SELECT emp_id 
    FROM employees 
    WHERE last_name LIKE '%_dup%' 
    LIMIT 10
);
COMMIT;

-- Use indexes in select queries (except unused ones)
SELECT COUNT(*) FROM employees WHERE department_id = :dept_id;
SELECT COUNT(*) FROM employees WHERE salary > :new_salary;
SELECT COUNT(*) FROM employee_projects WHERE emp_id = :emp_id;

-- Email lookups that will be slow without index (for AI to detect)
SELECT emp_id, first_name, last_name, email FROM employees WHERE email = 'user' || :emp_id || '@company.com';
SELECT COUNT(*) FROM employees WHERE email = 'user' || :emp_id || '@company.com';

WORKLOAD_SCRIPT_EOF

# Run workload to create more bloat
echo "Running workload for $DURATION minutes to create additional bloat..."
pgbench -d $DB_NAME -f /tmp/hr_workload_$.sql -T $DURATION_SECONDS -c 10 -j 2 -q

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
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan;"

# Clean up
rm -f /tmp/hr_workload_$$.sql

echo ""
echo "========================================"
echo "Workload creation completed!"
echo "========================================"
echo ""
echo "Database $DB_NAME is now ready for health check testing with:"
echo "- Tables containing ~3M rows each with duplicate first names"
echo "- Duplicate indexes for detection"
echo "- Unused indexes (with 0 scans)"
echo "- Table bloat from DELETE/INSERT operations"
echo ""
echo "To run the health check:"
echo "bash postgres-healthcheck.sh --database $DB_NAME --top-tables --duplicate-indexes --unused-indexes --bloat-analysis"
echo ""
echo "Environment variables used:"
echo "  PGHOST=$PGHOST"
echo "  PGPORT=$PGPORT"
echo "  PGUSER=$PGUSER"
echo "  PGDATABASE=$DB_NAME"
echo ""