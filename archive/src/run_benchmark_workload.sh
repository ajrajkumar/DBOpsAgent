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


# Create pgbench workload script
echo "Creating workload script..."
cat << 'WORKLOAD_SCRIPT_EOF' > /tmp/hr_workload_$$.sql

\set emp_id random(1, 3000000)
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
SELECT first_name, 'dup_' || last_name, 'dup_' || email, department_id, :new_salary
FROM employees
WHERE emp_id = :emp_id;
COMMIT;

-- Delete some duplicate entries to create more bloat
BEGIN;
DELETE FROM employees 
WHERE emp_id IN (
    SELECT emp_id 
    FROM employees 
    WHERE last_name LIKE 'dup_%' 
    FOR UPDATE SKIP LOCKED
    LIMIT 10
);
COMMIT;

-- Use indexes in select queries (except unused ones)
-- SELECT COUNT(*) FROM employees WHERE department_id = :dept_id;
SELECT COUNT(*) FROM employee_projects WHERE emp_id = :emp_id;

-- Email lookups that will be slow without index 
SELECT emp_id, first_name, last_name, email FROM employees WHERE email = 'user' || :emp_id || '@company.com';
SELECT COUNT(*) FROM employees WHERE email = 'user' || :emp_id || '@company.com';

WORKLOAD_SCRIPT_EOF

# Run workload to create more bloat
echo "Running workload for $DURATION minutes to create additional bloat..."

pgbench -f /tmp/hr_workload_$$.sql -T "$DURATION_SECONDS" -c 10 -j 2 "$DB_NAME" 1> /dev/null 2>&1 

# Re-enable autovacuum
echo "Re-enabling autovacuum..."
psql -d $DB_NAME -q << 'SQL_VACUUM_EOF'
ALTER TABLE employees SET (autovacuum_enabled = on);
ALTER TABLE departments SET (autovacuum_enabled = on);
ALTER TABLE projects SET (autovacuum_enabled = on);
ALTER TABLE employee_projects SET (autovacuum_enabled = on);
SQL_VACUUM_EOF


# Clean up
rm -f /tmp/hr_workload_$$.sql

echo "To run the health check:"
echo "bash /workshop/src/postgres-healthcheck.sh --database $DB_NAME --top-tables --duplicate-indexes --unused-indexes --bloat-analysis"
echo ""
echo ""
echo "========================================"
echo "Benchmark completed!"
echo "========================================"
