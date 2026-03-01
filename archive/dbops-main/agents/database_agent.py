#!/usr/bin/env python3
"""
DatabaseAgent - Autonomous Database Operations Agent
Uses MCP servers for Aurora PostgreSQL and CloudWatch monitoring with AI analysis
"""

from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseAgent:
    """
    Autonomous Database Operations Agent
    
    WHAT IT IS:
    AI-powered database performance analysis agent that uses MCP tools to monitor
    Aurora PostgreSQL and CloudWatch metrics, providing intelligent recommendations.
    
    WHERE WE USE IT:
    - Database performance troubleshooting and optimization
    - Proactive monitoring and alerting analysis
    - Automated database health assessments
    - Performance bottleneck identification and resolution
    """
    
    def __init__(self, user_input, specific_tools=None):
        """
        Initialize DatabaseAgent with MCP connections and AI model
        
        Args:
            user_input (str): User's database analysis request
            specific_tools (list, optional): List of specific tool names to use. If None, uses all tools.
        """
        # MCP server endpoints (our working servers)
        self.pg_mcp_url = "http://localhost:8081/mcp"  # Aurora PostgreSQL server (13 tools)
        self.cw_mcp_url = "http://localhost:8082/mcp"  # CloudWatch monitoring server (11 tools)
        self.user_prompts = user_input
        self.specific_tools = specific_tools
        
        # Initialize Bedrock model for AI analysis
        self.bedrock_model = BedrockModel(
            model_id=os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0'),
            region_name=os.getenv('AWS_REGION', 'us-west-2'),
            temperature=0.3,
        )
        
        # Initialize MCP clients for our servers
        try:
            self.pg_mcp_client = MCPClient(lambda: streamablehttp_client(self.pg_mcp_url))
            logger.info("Aurora PostgreSQL MCP client initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Aurora MCP server: {e}")
            raise
            
        try:
            self.cw_mcp_client = MCPClient(lambda: streamablehttp_client(self.cw_mcp_url))
            logger.info("CloudWatch MCP client initialized")
        except Exception as e:
            logger.error(f"Failed to connect to CloudWatch MCP server: {e}")
            raise

    def get_latest_alerts(self):
        """
        Get latest CloudWatch alerts for immediate attention (example method)
        
        Returns:
            Dict: Recent alarm data from CloudWatch
        """
        try:
            with self.cw_mcp_client:
                alerts = self.cw_mcp_client.call_tool_sync(
                    tool_use_id="get_alarms_last_hour",
                    name="get_alarms_last_hour",
                    arguments={}
                )
                logger.info(f"Retrieved {alerts.get('count', 0)} recent alerts")
                return alerts
        except Exception as e:
            logger.error(f"Failed to get latest alerts: {e}")
            return {"status": "error", "error": str(e)}

    def run(self):
        """
        Run the DatabaseAgent analysis with AI-powered recommendations
        
        Returns:
            str: AI-generated database analysis report in markdown format
        """
        # Create dynamic system prompt based on whether specific tools are provided
        if self.specific_tools:
            system_prompt = f"""
            You are a database admin agent focused on specific database analysis tasks. 
            Your task is to help developers with PostgreSQL performance issues using 
            ONLY the specific tools provided to you.
            
            IMPORTANT: You have access to ONLY these specific MCP tools:
            {', '.join(self.specific_tools)}
            
            DO NOT attempt to use any other tools. Focus your analysis exclusively 
            on what these specific tools can provide.
            
            The output needs to be a focused report in markdown format that describes 
            and explains the findings with actionable recommendations based only on 
            the data from the provided tools.
            """
        else:
            system_prompt = """
            You are a database admin agent. Your task is to help developers 
            with PostgreSQL performance issues. You have MCP tools to connect 
            to the database for performance and schema information.
            
            IMPORTANT: You have access to MCP PROMPTS that provide guidance on tool usage:
            
            AURORA POSTGRESQL PROMPTS:
            - Use 'aurora_tool_selection' prompt for guidance on which Aurora database tools to use
            - Use 'query_performance_analysis' prompt for comprehensive query optimization workflows
            - Use 'database_troubleshooting' prompt when investigating database problems and issues
            - Use 'index_optimization' prompt for index analysis and optimization strategies
            
            CLOUDWATCH MONITORING PROMPTS:
            - Use 'cloudwatch_tool_selection' prompt for guidance on which CloudWatch tools to use
            - Use 'database_performance_analysis' prompt for comprehensive performance analysis workflows
            - Use 'alarm_investigation' prompt when investigating CloudWatch alarms
            - Use 'capacity_planning' prompt for resource planning and optimization
            
            You are provided by 2 MCP servers with ALL available tools:
            
            1. Aurora PostgreSQL Server (13 tools):
               - test_connection: Test database connectivity
               - get_active_sessions: Monitor real-time database sessions
               - get_table_names: List all tables in database
               - get_slow_queries: Analyze slow queries from pg_stat_statements
               - get_table_stats: Get table usage statistics and scan ratios
               - get_schemas: Discover database schemas
               - get_index_usage: Analyze index efficiency and usage patterns
               - get_blocking_queries: Detect blocking queries and deadlocks
               - suggest_indexes: AI-powered index recommendations
               - get_buffer_cache_stats: Memory cache analysis
               - get_wait_events: Wait event monitoring for bottlenecks
               - get_connection_pool_stats: Connection management analysis
               - identify_unused_indexes: Find unused indexes for cleanup
               
            2. CloudWatch Monitoring Server (11 tools):
               - test_cloudwatch_connection: Test AWS service connectivity
               - get_aurora_alarms: Get real CloudWatch alarms
               - get_database_connections: Monitor connection metrics
               - get_cpu_utilization: CPU performance analysis
               - get_alarms_last_hour: Recent alarm activity
               - get_aurora_db_load_metrics: Database load analysis
               - get_performance_metrics: Performance metrics (latency, IOPS)
               - get_performance_insights_data: Performance Insights integration
               - get_aurora_cluster_metrics: Cluster-level monitoring
               - get_aurora_instance_metrics: Instance-level monitoring
               - get_comprehensive_insights: Combined health scoring
            
            USE ALL AVAILABLE TOOLS to provide comprehensive analysis. The AI agent 
            has access to all 24 tools and should use them intelligently based on 
            the analysis requirements.
            
            The output needs to be a report in markdown format that describes 
            and explains the findings with actionable recommendations.
            """
        
        try:
            with self.pg_mcp_client, self.cw_mcp_client:
                # Get all available tools from both servers
                pg_tools = self.pg_mcp_client.list_tools_sync()
                cw_tools = self.cw_mcp_client.list_tools_sync()
                all_tools = pg_tools + cw_tools
                
                # Filter tools if specific tools are requested
                if self.specific_tools:
                    try:
                        # Filter tools based on tool_name attribute
                        filtered_tools = []
                        for tool in all_tools:
                            # Get tool name (MCP tools use 'tool_name' attribute)
                            tool_name = getattr(tool, 'tool_name', None)
                            if tool_name and tool_name in self.specific_tools:
                                filtered_tools.append(tool)
                        
                        # Use filtered tools if successful, otherwise fallback to all tools
                        tools = filtered_tools if filtered_tools else all_tools
                        logger.info(f"Using {len(tools)} tools for focused analysis")
                    
                    except Exception as e:
                        # Fallback to all tools if there's any error in filtering
                        tools = all_tools
                        logger.error(f"Tool filtering failed: {e}, using all tools")
                else:
                    tools = all_tools
                    logger.info(f"Using all {len(tools)} available tools for comprehensive analysis")
                
                # Create the agent with selected MCP tools
                agent = Agent(
                    system_prompt=system_prompt,
                    model=self.bedrock_model,
                    tools=tools
                )
                
                # Create dynamic message based on whether specific tools are provided
                if self.specific_tools and len(tools) < len(all_tools):
                    message = f"""
                    {self.user_prompts}
                    
                    IMPORTANT INSTRUCTIONS:
                    - Use ONLY the specific tools provided to you: {', '.join(self.specific_tools)}
                    - DO NOT attempt to use any other tools
                    - Focus your analysis exclusively on what these tools can provide
                    - Provide specific findings with actual data from these tools only
                    - Generate a focused report based only on the available tool data
                    """
                    logger.info(f"Starting focused analysis with {len(tools)} tools")
                else:
                    message = f"""
                    Please perform a comprehensive database performance analysis using ALL available MCP tools:
                    
                    REQUIRED ANALYSIS:
                    1. **Database Connectivity & Health**
                       - Test database and CloudWatch connections
                       - Get overall database health score
                    
                    2. **Performance Analysis**
                       - Find top 20 queries by CPU and execution time
                       - Analyze I/O latency and performance metrics
                       - Check for blocking queries and deadlocks
                       - Monitor active sessions and wait events
                    
                    3. **Schema & Index Optimization**
                       - Analyze table statistics and scan ratios
                       - Review index usage efficiency
                       - Identify unused indexes for cleanup
                       - Generate AI-powered index recommendations
                    
                    4. **AWS Monitoring Integration**
                       - Review CloudWatch alarms and recent alerts
                       - Analyze CPU utilization and database load
                       - Check connection metrics and pool statistics
                       - Get Performance Insights data
                    
                    5. **Resource Analysis**
                       - Buffer cache hit ratios and memory usage
                       - Connection pool efficiency
                       - Database and cluster-level metrics
                    
                    ADDITIONAL USER REQUEST: {self.user_prompts}
                    
                    INSTRUCTIONS:
                    - Use ALL relevant MCP tools to gather comprehensive data
                    - Provide specific findings with actual data from the tools
                    - Include actionable recommendations with priority levels
                    - Generate a professional markdown report with clear sections
                    
                    REPORT STRUCTURE:
                    # Database Performance Analysis Report
                    
                    ## Executive Summary
                    - Overall health score and critical issues
                    
                    ## Database Connectivity & Status
                    - Connection test results
                    - Schema and table overview
                    
                    ## Performance Analysis
                    - Slow query analysis with specific examples
                    - I/O and latency metrics
                    - Active sessions and blocking queries
                    
                    ## Index & Schema Optimization
                    - Index usage analysis
                    - Unused index recommendations
                    - Table scan ratio analysis
                    
                    ## AWS CloudWatch Insights
                    - Alarm status and recent alerts
                    - CPU and performance metrics
                    - Connection and load analysis
                    
                    ## Actionable Recommendations
                    - High priority actions (immediate)
                    - Medium priority improvements (short-term)
                    - Low priority optimizations (long-term)
                    
                    ## Priority Action Plan
                    - Specific SQL commands or configuration changes
                    - Expected impact and benefits
                    """
                    logger.info("Starting comprehensive analysis with all available tools")
                
                return agent(message)
                
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return f"# Database Analysis Error\n\nFailed to complete analysis: {str(e)}"

def main():
    """
    Main function to run DatabaseAgent
    """
    print("🤖 Autonomous Database Operations Agent")
    print("======================================")
    print("Powered by Aurora PostgreSQL + CloudWatch MCP servers")
    print("AI Analysis: Claude 3.7 Sonnet via Amazon Bedrock")
    print()
    
    # Get user input
    user_input = input("Enter your database analysis request: ").strip()
    if not user_input:
        user_input = "Perform comprehensive database performance analysis"
    
    try:
        # Create and run DatabaseAgent
        agent = DatabaseAgent(user_input)
        
        print("\n🔍 Starting database analysis...")
        print("📊 Connecting to MCP servers...")
        print("🧠 Initializing AI analysis...")
        print()
        
        # Run analysis
        result = agent.run()
        
        print("📋 Database Analysis Report:")
        print("=" * 50)
        print(result)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"DatabaseAgent failed: {e}")

if __name__ == "__main__":
    main()
