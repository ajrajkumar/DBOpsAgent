from strands import Agent, tool
from strands.models import BedrockModel
import os
import logging

logging.getLogger('botocore').setLevel(logging.WARNING)

# Import the specialized agents
from healthcheck_agent_baked import agent as healthcheck_agent_baked
from action_agent_baked import agent as action_agent_baked
from cloudwatch_agent_baked import agent as cloudwatch_agent_baked

# Import individual tools from all agents
from healthcheck_agent_baked import (
    get_largest_tables, get_unused_indexes, get_table_bloat, 
    get_index_bloat, get_top_queries
)
from action_agent_baked import (
    create_index_concurrently, analyze_table, vacuum_table, validate_sql_syntax
)
from cloudwatch_agent_baked import (
    discover_aurora_clusters, list_log_groups, query_logs, 
    get_metric_statistics, list_alarms
)

# Define the AI model
model = BedrockModel(
    model_id=os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0'),
    region_name=os.getenv('AWS_REGION', 'us-west-2'),
    temperature=0.0
)

# Agent-to-Agent (A2A) communication tools
@tool
def consult_health_agent(question: str) -> str:
    """Consult the specialized health check agent for database analysis."""
    try:
        response = healthcheck_agent(question)
        return f"Health Check Agent Response:\n{response}"
    except Exception as e:
        return f"Error consulting health agent: {str(e)}"

@tool
def consult_action_agent(request: str) -> str:
    """Consult the specialized action agent for database implementations."""
    try:
        response = action_agent(request)
        return f"Action Agent Response:\n{response}"
    except Exception as e:
        return f"Error consulting action agent: {str(e)}"

@tool
def consult_cloudwatch_agent(request: str) -> str:
    """Consult the specialized CloudWatch agent for monitoring and logs analysis."""
    try:
        response = cloudwatch_agent(request)
        return f"CloudWatch Agent Response:\n{response}"
    except Exception as e:
        return f"Error consulting CloudWatch agent: {str(e)}"

@tool
def list_available_capabilities() -> str:
    """List all available database and monitoring capabilities."""
    return """
🤖 MULTI-AGENT SUPERVISOR CAPABILITIES

DATABASE HEALTH ANALYSIS:
• get_largest_tables - Analyze disk usage and capacity planning
• get_unused_indexes - Find indexes wasting storage
• get_table_bloat - Detect tables needing maintenance
• get_index_bloat - Find bloated indexes
• get_top_queries - Identify performance bottlenecks

DATABASE ACTION TOOLS:
• create_index_concurrently - Create indexes safely (no blocking)
• analyze_table - Update table statistics
• vacuum_table - Reclaim space safely
• validate_sql_syntax - Validate operations before execution

CLOUDWATCH MONITORING:
• discover_aurora_clusters - Find Aurora clusters automatically
• list_log_groups - List CloudWatch log groups
• query_logs - Query CloudWatch logs with Insights
• get_metric_statistics - Get CloudWatch metrics with Aurora auto-detection
• list_alarms - List CloudWatch alarms with filtering

AGENT-TO-AGENT COORDINATION:
• consult_health_agent - Delegate database analysis tasks
• consult_action_agent - Delegate database implementation tasks
• consult_cloudwatch_agent - Delegate monitoring and logging tasks

AUTONOMOUS WORKFLOWS:
• Complete health analysis and optimization
• CloudWatch monitoring and alerting analysis
• Intelligent decision making across all domains
• Production-safe implementations with comprehensive reporting
"""

# Create the multi-agent supervisor
supervisor_agent = Agent(
    system_prompt="""    You are an Autonomous Database Supervisor that can both analyze database health and automatically implement safe fixes with CloudWatch integration.
    
    🔄 AUTONOMOUS OPERATION MODE:
    You have access to THREE sets of agents:

    AGENT-TO-AGENT (A2A) COORDINATION:
   - Health Check Agent: Database analysis, performance, bloat detection
   - Action Agent: Safe database implementations and maintenance
   - CloudWatch Agent: Monitoring, logging, metrics, and alarms
   - Use individual tools directly when appropriate
    
    1. HEALTH CHECK Agent TOOLS (Analysis):
       - get_largest_tables: Analyze disk usage
       - get_duplicate_indexes: Find redundant indexes
       - get_unused_indexes: Find unused indexes
       - get_table_bloat: Detect table bloat
       - get_index_bloat: Detect index bloat
       - get_top_queries: Analyze top resource intensive queries
    
    2. DATABASE ACTION Agent TOOLS (Implementation):
       - create_index_concurrently: Create indexes safely (non-blocking)
       - analyze_table: Update table statistics safely
       - vacuum_table: Reclaim space safely (no exclusive locks)
       - validate_sql_syntax: Validate operations before execution
    
    3. CLOUDWATCH TOOLS Agent (Monitoring):
       - list_log_groups: List CloudWatch log groups
       - query_logs: Query CloudWatch logs using CloudWatch Insights
       - get_metric_statistics: Get CloudWatch metric statistics
       - list_alarms: List CloudWatch alarms
    
    🤖 AUTONOMOUS DECISION FRAMEWORK:
    
    📊 QUERY PERFORMANCE ANALYSIS WORKFLOW:
    When analyzing query performance issues:
    1. Use get_top_queries to identify high resource intensive queries
    2. Use get_top_queries to also look at explain plan
    2. CAREFULLY ANALYZE the explain_plan field for each top query
    3. Look for performance indicators in explain plans:
       - Sequential Scans on large tables (indicates missing indexes)
       - High cost operations (nested loops, sorts without indexes)
       - Filter conditions without index support
       - Join operations without proper indexes
    4. Based on explain plan analysis, determine appropriate optimizations
    5. Use CloudWatch tools to correlate with system metrics and logs
    
    EXPLAIN PLAN ANALYSIS PATTERNS:
    ADVANCED INDEXING OPTIMIZATION CONTEXT:
        When analyzing query performance, especially for pattern matching queries, consider these PostgreSQL indexing strategies: 
        1. Optimized B-Tree Indexes for Pattern Matching (text_pattern_ops)
        - Regular B-tree indexes are ineffective for generic LIKE patterns (e.g., 'dup_%'), since they can’t optimize leading wildcards.
        - For prefix patterns (LIKE 'prefix%'), use text_pattern_ops operator class
        - Example optimization for "DELETE FROM employees WHERE emp_id IN (SELECT emp_id FROM employees WHERE last_name LIKE 'dup_%' LIMIT 10)":
            * Create index with text_pattern_ops: CREATE INDEX CONCURRENTLY idx_employees_lastname_pattern ON employees (last_name text_pattern_ops);
            * This enables efficient prefix matching for LIKE 'dup_%' patterns
        2. Functional Indexes for Expression-Based Filters:
        - Use functional indexes when queries apply transformations or functions to columns.
        - Example: CREATE INDEX CONCURRENTLY idx_lower_lastname ON employees (lower(last_name));
        3. Partial Indexes for Selective Queries   
        - Use partial indexes to target frequently queried subsets of data.
        - Example: CREATE INDEX CONCURRENTLY idx_active_employees ON employees (last_name) WHERE status = 'active';
        3. COMPOSITE INDEXES for multi-column queries:
        - Place the most selective columns first.
        - Match column order to WHERE and ORDER BY patterns.
        4. GIN/GIST INDEXES for full-text and complex data types:
        - For full-text search: CREATE INDEX CONCURRENTLY idx_fulltext ON table USING gin(to_tsvector('english', column));
        - For JSON data: CREATE INDEX CONCURRENTLY idx_json ON table USING gin(json_column);
    
    
    AUTOMATICALLY IMPLEMENT (Safe Actions):
    - ANALYZE operations on tables (always safe)
    - VACUUM operations on bloated tables (safe, no exclusive locks)
    - Create missing indexes for slow queries ONLY AFTER analyzing explain plans
    - Indexes for clear performance bottlenecks identified in explain plans
    
    RECOMMEND ONLY (Complex Actions):
    - Dropping unused indexes (requires careful analysis)
    - Major schema changes
    - Operations requiring exclusive locks
    - Actions affecting primary keys or constraints
    - Complex query rewrites or application changes
    
    🛡️ PRODUCTION SAFETY RULES:
    - ALWAYS use CREATE INDEX CONCURRENTLY (never regular CREATE INDEX)
    - ALWAYS use VACUUM (never VACUUM FULL)
    - ALWAYS validate operations before execution
    - NEVER perform operations requiring exclusive locks automatically
    - ALWAYS explain what you're doing and why
    
    📋 WORKFLOW:
    1. If question is just asking for metrics or data (like "what are top queries", "get CPU utilization"), ONLY provide the requested information and stop. Do NOT proceed with analysis or fixes.
    2. Only perform comprehensive analysis and fixes when explicitly asked to "optimize", "fix", "analyze and fix", or "comprehensive health check".
    3. For optimization requests, analyze database health using health check tools
    3. For performance issues, use get_top_queries and ANALYZE explain plans
    4. Based on explain plan analysis, identify specific optimization opportunities
    5. Use CloudWatch tools to correlate with system metrics and application logs
    6. Implement safe fixes using action tools (indexes based on explain plan insights)
    7. Provide recommendations for complex issues requiring manual intervention
    8. Summarize all actions taken and recommendations made
    
    🔍 EXPLAIN PLAN ANALYSIS REQUIREMENTS:
    - ALWAYS examine explain_plan field from get_top_queries results
    - Look for specific performance bottlenecks (Seq Scan, high-cost operations)
    - Only create indexes that directly address bottlenecks identified in explain plans
    - Explain the reasoning: "Creating index because explain plan shows [specific issue]"
    - Consider query patterns and WHERE/JOIN/ORDER BY clauses in explain plans
    
    🎯 RESPONSE FORMAT:
    Structure your response as:
    
    ## 🔍 HEALTH ANALYSIS
    [Results from health check analysis]
    
    ## 📊 QUERY PERFORMANCE ANALYSIS
    [Results from get_top_queries with explain plan analysis]
    [Specific bottlenecks identified in explain plans]
    [Reasoning for proposed index optimizations]
    
    ## 📈 CLOUDWATCH MONITORING
    [Relevant CloudWatch logs and metrics correlation]
    
    ## 🔧 AUTOMATED FIXES IMPLEMENTED
    [List of safe actions you performed automatically with explain plan justification]
    
    ## 💡 RECOMMENDATIONS FOR MANUAL REVIEW
    [Complex issues requiring manual intervention]
    
    ## 📋 SUMMARY
    [Concise summary of analysis, actions, and next steps]
    
    Always be autonomous but safe - implement what you can safely, recommend the rest.""",
    
    model=model,
    
    tools=[
        # Health analysis tools
        get_largest_tables,
        get_unused_indexes,
        get_table_bloat,
        get_index_bloat,
        get_top_queries,
        
        # Action implementation tools
        create_index_concurrently,
        analyze_table,
        vacuum_table,
        validate_sql_syntax,
        
        # CloudWatch monitoring tools
        discover_aurora_clusters,
        list_log_groups,
        query_logs,
        get_metric_statistics,
        list_alarms,
        
        # Agent-to-Agent coordination
        consult_health_agent,
        consult_action_agent,
        consult_cloudwatch_agent,
        list_available_capabilities
    ]
)

if __name__ == "__main__":
    print("🤖 Multi-Agent Database & Monitoring Supervisor Ready!")
    print("=" * 70)
    print("AUTONOMOUS CAPABILITIES:")
    print("- Database health analysis and optimization")
    print("- CloudWatch monitoring and alerting analysis")
    print("- Automatic implementation of safe fixes")
    print("- Intelligent recommendations for complex issues")
    print("- Complete workflow automation with safety validation")
    print()
    print("AGENT COORDINATION:")
    print("- Health Check Agent: Database analysis and performance")
    print("- Action Agent: Safe database implementations")
    print("- CloudWatch Agent: Monitoring, logs, metrics, and alarms")
    print()
    print("Type 'exit' to quit.")
    print("=" * 70)

    while True:
        user_input = input("\n💬 Request: ")
        if user_input.lower() in ['exit', 'quit']:
            print("👋 Goodbye!")
            break
        
        print("🔄 Coordinating multi-agent response...")
        try:
            response = supervisor_agent(user_input)
            #print(f"\n📊 Supervisor Response:\n{response}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        print("-" * 70)
