"""
Autonomous Database Supervisor Agent with CloudWatch Integration

This script creates a simplified autonomous database supervisor that combines
health check analysis with safe database actions and CloudWatch monitoring.
It automatically implements safe fixes and provides recommendations for complex issues.

Make sure all MCP servers are running before starting this supervisor:
- Database Health Check Server on port 8083
- Database Action Server on port 8084
- CloudWatch Logs Server on port 8082
"""

import time
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from strands.models import BedrockModel
import os
import logging

logger = logging.getLogger(__name__)

def main():
    """Main function to run Autonomous Database Supervisor with CloudWatch"""
    print("🤖 Autonomous Database Supervisor with CloudWatch")
    print("Ready! Type 'exit' to quit.")
    print()
    
    # Initialize Bedrock model
    bedrock_model = BedrockModel(
        model_id=os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0'),
        region_name=os.getenv('AWS_REGION', 'us-west-2'),
        temperature=0.3,
    )
    
    # Create MCP client connections
    def create_healthcheck_transport():
        return streamablehttp_client("http://localhost:8083/mcp/")
    
    def create_action_transport():
        return streamablehttp_client("http://localhost:8084/mcp/")
    
    def create_cloudwatch_transport():
        return streamablehttp_client("http://localhost:8082/mcp/")
    
    healthcheck_mcp_client = MCPClient(create_healthcheck_transport)
    action_mcp_client = MCPClient(create_action_transport)
    cloudwatch_mcp_client = MCPClient(create_cloudwatch_transport)
    
    # Create comprehensive system prompt for autonomous operation
    system_prompt = """
    You are an Autonomous Database Supervisor that can both analyze database health and automatically implement safe fixes with CloudWatch integration.
    
    🔄 AUTONOMOUS OPERATION MODE:
    You have access to THREE sets of tools:
    
    1. HEALTH CHECK TOOLS (Analysis):
       - get_largest_tables: Analyze disk usage
       - get_duplicate_indexes: Find redundant indexes
       - get_unused_indexes: Find unused indexes
       - get_table_bloat: Detect table bloat
       - get_index_bloat: Detect index bloat
       - get_top_queries: Analyze top resource intensive queries
    
    2. DATABASE ACTION TOOLS (Implementation):
       - create_index_concurrently: Create indexes safely (non-blocking)
       - analyze_table: Update table statistics safely
       - vacuum_table: Reclaim space safely (no exclusive locks)
       - validate_sql_syntax: Validate operations before execution
    
    3. CLOUDWATCH TOOLS (Monitoring):
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
            * Create functional index: CREATE INDEX CONCURRENTLY idx_employees_lastname_pattern ON employees (last_name text_pattern_ops);
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
    
    Always be autonomous but safe - implement what you can safely, recommend the rest.
    """
    
    try:
        print("Connecting to MCP servers...")
        
        # Use all MCP clients in context managers
        with healthcheck_mcp_client, action_mcp_client, cloudwatch_mcp_client:
            # Get tools from all servers
            health_tools = healthcheck_mcp_client.list_tools_sync()
            action_tools = action_mcp_client.list_tools_sync()
            cloudwatch_tools = cloudwatch_mcp_client.list_tools_sync()
            
            # Combine all tools
            all_tools = health_tools + action_tools + cloudwatch_tools
            
            print(f"Connected. {len(all_tools)} tools available.")
            
            # Create autonomous supervisor agent with all tools
            supervisor = Agent(
                system_prompt=system_prompt,
                model=bedrock_model,
                tools=all_tools
            )
            
            # Interactive loop
            print(f"\nAutonomous Database Supervisor Ready!")
            
            while True:
                # Get user input
                user_input = input("\nAutonomous Request: ")

                # Check if the user wants to exit
                if user_input.lower() in ["exit", "quit"]:
                    break

                # Process the user's request
                response = supervisor(user_input)


                # Print the supervisor's response
                print("\n" + str(response))
                print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Autonomous Database Supervisor failed: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
