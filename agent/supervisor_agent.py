from strands import Agent, tool
from strands.models import BedrockModel
import os

# Import the specialized agents
from healthcheck_agent import agent as healthcheck_agent
from action_agent import agent as action_agent

# Import individual tools from both agents
from healthcheck_agent import (
    get_largest_tables, get_unused_indexes, get_table_bloat, 
    get_index_bloat, get_top_queries
)
from action_agent import (
    create_index_concurrently, analyze_table, vacuum_table
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
    """
    Consult the specialized health check agent for database analysis.
    Use this for questions about database health, performance, bloat, etc.
    """
    try:
        response = healthcheck_agent(question)
        return f"Health Check Agent Response:\n{response}"
    except Exception as e:
        return f"Error consulting health agent: {str(e)}"

@tool
def consult_action_agent(request: str) -> str:
    """
    Consult the specialized action agent for database implementations.
    Use this for implementing fixes, creating indexes, maintenance, etc.
    """
    try:
        response = action_agent(request)
        return f"Action Agent Response:\n{response}"
    except Exception as e:
        return f"Error consulting action agent: {str(e)}"

@tool
def list_available_capabilities() -> str:
    """
    List all available database management capabilities.
    """
    return """
🤖 AUTONOMOUS DATABASE SUPERVISOR CAPABILITIES

HEALTH ANALYSIS TOOLS:
• get_largest_tables - Analyze disk usage and capacity planning
• get_unused_indexes - Find indexes wasting storage
• get_table_bloat - Detect tables needing maintenance
• get_index_bloat - Find bloated indexes
• get_top_queries - Identify performance bottlenecks

ACTION IMPLEMENTATION TOOLS:
• create_index_concurrently - Create indexes safely (no blocking)
• analyze_table - Update table statistics
• vacuum_table - Reclaim space safely


AGENT-TO-AGENT COORDINATION:
• consult_health_agent - Delegate analysis tasks
• consult_action_agent - Delegate implementation tasks

AUTONOMOUS WORKFLOWS:
• Complete health analysis and optimization
• Intelligent decision making between analysis and action
• Production-safe implementations with comprehensive reporting

"""

# Create the autonomous supervisor agent
supervisor_agent = Agent(
    system_prompt="""You are an Autonomous Database Supervisor that coordinates between specialized database agents.

🎯 YOUR ROLE: Intelligent coordinator for database analysis and optimization

AGENT-TO-AGENT (A2A) COORDINATION:
- You have access to specialized Health Check and Action agents
- Use consult_health_agent() for analysis questions
- Use consult_action_agent() for implementation requests
- You can also use individual tools directly when appropriate

DECISION MAKING LOGIC:
- For "analyze", "check", "show", "find" → Use health analysis tools
- For "fix", "create", "optimize", "implement" → Use action tools
- For complex workflows → Coordinate between both agents

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

AUTONOMOUS WORKFLOW EXAMPLE:
1. User asks: "Analyze database and fix issues"
2. You consult health agent for comprehensive analysis
3. You evaluate results and identify safe optimizations
4. You consult action agent to implement safe fixes
5. You provide comprehensive report of analysis and actions

PRODUCTION SAFETY:
- Always prioritize production safety
- Only implement non-blocking operations automatically
- Provide clear explanations of all actions taken
- Escalate complex issues for human review

COMMUNICATION STYLE:
- Be clear and comprehensive in reporting
- Explain your decision-making process
- Provide actionable insights and recommendations
- Maintain professional DBA expertise level""",
    
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
        
        # Agent-to-Agent coordination
        consult_health_agent,
        consult_action_agent,
        list_available_capabilities
    ]
)

if __name__ == "__main__":
    print("🤖 Autonomous Database Supervisor Ready!")
    print("=" * 60)
    print("AUTONOMOUS CAPABILITIES:")
    print("- Comprehensive database health analysis")
    print("- Automatic implementation of safe fixes")
    print("- Intelligent recommendations for complex issues")
    print("- Complete workflow automation with safety validation")
    print()
    print("SAFETY FEATURES:")
    print("- Only implements production-safe operations automatically")
    print("- Provides recommendations for complex changes")
    print("- Complete transparency of all actions taken")
    print("- Comprehensive summary reporting")
    print()
    print("Type 'exit' to quit.")
    print("=" * 60)

    while True:
        user_input = input("\n💬 Database Request: ")
        if user_input.lower() in ['exit', 'quit']:
            print("👋 Goodbye!")
            break
        
        print("🔄 Coordinating database management...")
        try:
            response = supervisor_agent(user_input)
            #print(f"\n📊 Supervisor Response:\n{response}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        print("-" * 60)