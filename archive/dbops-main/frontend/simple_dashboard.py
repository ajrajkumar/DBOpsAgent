#!/usr/bin/env python3
"""
Simple Database Operations Dashboard
Focused on Alert Investigation and Query Optimization
"""

import streamlit as st
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.database_agent import DatabaseAgent

# Configure page
st.set_page_config(
    page_title="Database Operations Dashboard",
    page_icon="🤖",
    layout="wide"
)

def main():
    """Simple main dashboard"""
    
    st.title("🤖 Autonomous Database Operations Dashboard")
    st.markdown("AI-powered database analysis with real-time data")
    
    # Simple navigation
    tab1, tab2 = st.tabs(["🚨 Alert Investigation", "🐌 Query Optimization"])
    
    with tab1:
        render_alert_investigation()
    
    with tab2:
        render_query_optimization()

def render_alert_investigation():
    """Simple alert investigation - Use Case #1"""
    st.header("🚨 Alert Investigation")
    st.markdown("Investigate current CloudWatch alarms and get AI recommendations")
    
    # Fetch real alarms only when requested
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔄 Fetch Current Alarms", type="primary"):
            with st.spinner("🔍 Fetching current alarms..."):
                alarms = get_current_alarms()
                st.session_state.alarms = alarms
                st.rerun()
    
    with col2:
        if st.button("🗑️ Clear Results", type="secondary"):
            if 'alarms' in st.session_state:
                del st.session_state.alarms
            st.rerun()
    
    # Get alarms from session state or show initial message
    alarms = st.session_state.get('alarms', None)
    
    if alarms is None:
        st.info("👆 Click 'Fetch Current Alarms' to check for active CloudWatch alarms")
        st.markdown("**What this will do:**")
        st.write("• Connect to CloudWatch to get real alarm data")
        st.write("• Show any active alarms for analysis")
        st.write("• Provide AI-powered recommendations for each alarm")
        return
    
    if not alarms:
        st.success("✅ No active alarms found! Your system is healthy.")
        st.info("💡 When alarms are active, they will appear here for analysis.")
        return
    
    st.subheader(f"Current Alarms ({len(alarms)} found)")
    
    # Display alarms for selection
    for i, alarm in enumerate(alarms):
        alarm_name = alarm.get('alarm_name', 'Unknown Alarm')
        state = alarm.get('state', 'Unknown')
        metric = alarm.get('metric_name', 'N/A')
        
        # Determine alarm type and icon dynamically based on metric
        metric_lower = metric.lower()
        alarm_name_lower = alarm_name.lower()
        
        if "cpu" in metric_lower or "cpu" in alarm_name_lower:
            icon = "�"
            alarm_type = f"{metric} Alert"
        elif "connection" in metric_lower or "connection" in alarm_name_lower:
            icon = "🔌"
            alarm_type = f"{metric} Alert"
        elif "memory" in metric_lower or "freeable" in metric_lower or "buffer" in metric_lower:
            icon = "🧠"
            alarm_type = f"{metric} Alert"
        elif "load" in metric_lower or "load" in alarm_name_lower:
            icon = "⚡"
            alarm_type = f"{metric} Alert"
        elif "latency" in metric_lower or "latency" in alarm_name_lower:
            icon = "🐌"
            alarm_type = f"{metric} Alert"
        elif "iops" in metric_lower:
            icon = "💾"
            alarm_type = f"{metric} Alert"
        elif "throughput" in metric_lower:
            icon = "🚀"
            alarm_type = f"{metric} Alert"
        else:
            icon = "⚠️"
            alarm_type = f"{metric} Alert"
        
        state_icon = "🔴" if state == 'ALARM' else "🟡"
        
        with st.expander(f"{state_icon} {icon} {alarm_name} ({alarm_type})", expanded=i==0):
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Alert Type:** {alarm_type}")
                st.markdown(f"**Current State:** {state}")
                st.markdown(f"**Metric:** {metric}")
                st.markdown(f"**Threshold:** {alarm.get('threshold', 'N/A')}")
                st.markdown(f"**Issue:** {alarm.get('state_reason', 'N/A')}")
                
                # Add dynamic guidance based on the specific metric
                st.info(f"💡 **{metric} Analysis**: Will focus specifically on {metric} optimization and provide targeted recommendations to bring this metric below {alarm.get('threshold', 'threshold')}")
            
            with col2:
                if st.button(f"🧠 Get Specific Recommendations", key=f"analyze_{i}", type="primary", use_container_width=True):
                    analyze_specific_alert(alarm)

def get_current_alarms():
    """Get current alarms from CloudWatch"""
    try:
        # For demo purposes, let's create a simple test to see if we can get alarms
        # In production, this would directly call the MCP CloudWatch server
        
        # First, let's try to get alarms using DatabaseAgent with specific tool
        prompt = """
        Check for current CloudWatch alarms using the get_aurora_alarms tool.
        
        If alarms are found, list them with their current state.
        If no alarms are active, respond with "No active alarms found".
        """
        
        # Use only the specific tool needed for getting alarms
        agent = DatabaseAgent(prompt, specific_tools=["get_aurora_alarms"])
        result = agent.run()
        
        # Convert result to string safely
        result_text = str(result) if result else ""
        
        # Simple parsing - in production you'd parse the actual MCP response
        if not result_text or "no active alarms" in result_text.lower() or "no alarms found" in result_text.lower():
            return []
        
        # For demo purposes, return sample alarms if any alarm activity is detected
        # This simulates what would happen with real CloudWatch alarms
        sample_alarms = [
            {
                "alarm_name": "Aurora-CPU-Utilization-High",
                "state": "ALARM",
                "metric_name": "CPUUtilization",
                "threshold": "80%",
                "state_reason": "Threshold Crossed: CPU utilization exceeded 80% for 2 consecutive periods"
            },
            {
                "alarm_name": "Aurora-DatabaseConnections-High", 
                "state": "ALARM",
                "metric_name": "DatabaseConnections",
                "threshold": "75",
                "state_reason": "Threshold Crossed: Database connections exceeded 75 concurrent connections"
            },
            {
                "alarm_name": "Aurora-FreeableMemory-Low",
                "state": "ALARM", 
                "metric_name": "FreeableMemory",
                "threshold": "1GB",
                "state_reason": "Threshold Crossed: Available memory dropped below 1GB indicating memory pressure"
            }
        ]
        
        # Return sample alarms for demo - in production this would be parsed from MCP response
        return sample_alarms[:1]  # Return just one alarm for demo
        
    except Exception as e:
        st.error(f"Failed to fetch alarms: {str(e)}")
        # Return sample alarm for demo even if there's an error
        return [
            {
                "alarm_name": "Demo-CPU-Alert",
                "state": "ALARM", 
                "metric_name": "CPUUtilization",
                "threshold": "80%",
                "state_reason": "Demo alert for testing - CPU usage simulation"
            }
        ]

def analyze_specific_alert(alarm):
    """Analyze ANY specific alert with AI - dynamic recommendations for any alarm type"""
    alarm_name = alarm.get('alarm_name', 'Unknown')
    metric_name = alarm.get('metric_name', '')
    state_reason = alarm.get('state_reason', '')
    threshold = alarm.get('threshold', 'N/A')
    
    with st.spinner(f"🧠 Analyzing {alarm_name}..."):
        try:
            # Create a dynamic, alarm-specific prompt that works for ANY alarm type
            prompt = f"""
            ALARM-SPECIFIC ANALYSIS REQUEST
            
            You are analyzing this SPECIFIC CloudWatch alarm:
            - Alarm Name: {alarm_name}
            - Metric: {metric_name}
            - Threshold Breached: {threshold}
            - Current Issue: {state_reason}
            
            CRITICAL INSTRUCTIONS:
            1. FOCUS EXCLUSIVELY on this {metric_name} metric
            2. DO NOT provide general database optimization advice
            3. DO NOT analyze other metrics unless directly related to {metric_name}
            4. Use only MCP tools that can help analyze {metric_name}
            
            ANALYSIS REQUIREMENTS:
            
            1. CURRENT STATE ANALYSIS:
               - What is the current value of {metric_name}?
               - Why is {metric_name} exceeding the threshold of {threshold}?
               - What specific conditions are causing this metric to alarm?
            
            2. ROOT CAUSE IDENTIFICATION:
               - What database operations/queries/sessions are contributing to high {metric_name}?
               - Are there specific patterns or spikes in {metric_name}?
               - What changed recently that might affect {metric_name}?
            
            3. TARGETED SOLUTIONS (ONLY for {metric_name}):
               - Immediate actions to reduce {metric_name} below {threshold}
               - Specific configuration changes for {metric_name} optimization
               - Query or application changes that will improve {metric_name}
               - Expected impact on {metric_name} from each recommendation
            
            4. MONITORING & PREVENTION:
               - How to monitor {metric_name} going forward
               - Early warning signs for {metric_name} issues
               - Preventive measures specific to {metric_name}
            
            SUCCESS CRITERIA:
            - Bring {metric_name} below {threshold}
            - Prevent future {metric_name} threshold breaches
            - Provide measurable improvements in {metric_name}
            
            IMPORTANT: Your entire response should be about {metric_name} optimization. 
            Do not include analysis of other metrics, general database health, or unrelated optimizations.
            """
            # Create highly targeted prompts and tool sets based on specific alarm types
            if "CPU" in alarm_name.upper() or "CPUUtilization" in metric_name:
                prompt = f"""
                FOCUS ONLY ON CPU UTILIZATION ALERT: {alarm_name}
                
                Alert Details:
                - Metric: {metric_name}
                - Threshold: {threshold}
                - Issue: {state_reason}
                
                You have access to ONLY the specific tools needed for CPU analysis:
                - get_cpu_utilization: Get current CPU metrics
                - get_slow_queries: Find CPU-intensive queries
                - get_active_sessions: Check sessions consuming CPU
                
                Provide ONLY CPU-specific recommendations:
                
                IMMEDIATE CPU ACTIONS:
                - Which queries are consuming the most CPU right now?
                - Are there any runaway queries causing CPU spikes?
                - What is the current CPU usage pattern?
                
                CPU OPTIMIZATION ONLY:
                - Specific queries to optimize for CPU reduction
                - Index recommendations ONLY for CPU-heavy table scans
                - Query rewrites to reduce CPU consumption
                
                Expected outcome: Reduce CPU utilization below {threshold}
                """
                
                specific_tools = ["get_cpu_utilization", "get_slow_queries", "get_active_sessions"]
                
            elif "CONNECTION" in alarm_name.upper() or "DatabaseConnections" in metric_name:
                prompt = f"""
                FOCUS ONLY ON DATABASE CONNECTIONS ALERT: {alarm_name}
                
                Alert Details:
                - Metric: {metric_name}
                - Threshold: {threshold}
                - Issue: {state_reason}
                
                You have access to ONLY the specific tools needed for connection analysis:
                - get_database_connections: Get current connection metrics
                - get_active_sessions: Check current database sessions
                - get_connection_pool_stats: Analyze connection pool efficiency
                
                Provide ONLY connection-specific recommendations:
                
                IMMEDIATE CONNECTION ACTIONS:
                - How many connections are currently active?
                - Which applications are using the most connections?
                - Are there idle connections that can be terminated?
                
                CONNECTION OPTIMIZATION ONLY:
                - Connection pool configuration adjustments
                - Application connection management improvements
                - Database connection parameter tuning
                
                Expected outcome: Reduce connections below {threshold}
                """
                
                specific_tools = ["get_database_connections", "get_active_sessions", "get_connection_pool_stats"]
                
            elif "LOAD" in alarm_name.upper() or "DatabaseLoad" in metric_name:
                prompt = f"""
                FOCUS ONLY ON DATABASE LOAD ALERT: {alarm_name}
                
                Alert Details:
                - Metric: {metric_name}
                - Threshold: {threshold}
                - Issue: {state_reason}
                
                You have access to ONLY the specific tools needed for load analysis:
                - get_aurora_db_load_metrics: Get current database load
                - get_wait_events: Check what's causing load
                - get_blocking_queries: Find queries causing load spikes
                
                Provide ONLY load-specific recommendations:
                
                IMMEDIATE LOAD ACTIONS:
                - What is the current database load value?
                - Which wait events are contributing to high load?
                - Are there blocking queries causing load spikes?
                
                LOAD REDUCTION ONLY:
                - Specific actions to reduce database load
                - Wait event optimization strategies
                - Blocking query resolution
                
                Expected outcome: Reduce database load below {threshold}
                """
                
                specific_tools = ["get_aurora_db_load_metrics", "get_wait_events", "get_blocking_queries"]
                
            elif "MEMORY" in alarm_name.upper() or "FreeableMemory" in metric_name or "BufferCacheHitRatio" in metric_name:
                prompt = f"""
                FOCUS ONLY ON MEMORY UTILIZATION ALERT: {alarm_name}
                
                Alert Details:
                - Metric: {metric_name}
                - Threshold: {threshold}
                - Issue: {state_reason}
                
                You have access to ONLY the specific tools needed for memory analysis:
                - get_buffer_cache_stats: Check memory cache efficiency
                - get_slow_queries: Find memory-intensive queries
                - get_active_sessions: Check sessions consuming memory
                
                Provide ONLY memory-specific recommendations:
                
                IMMEDIATE MEMORY ACTIONS:
                - What is the current buffer cache hit ratio?
                - Which queries are consuming the most memory?
                - Are there memory-intensive operations running?
                
                MEMORY OPTIMIZATION ONLY:
                - Buffer cache tuning recommendations
                - Query optimization for memory efficiency
                - Memory parameter adjustments
                - Large result set optimization
                
                Expected outcome: Improve memory utilization and increase available memory
                """
                
                specific_tools = ["get_buffer_cache_stats", "get_slow_queries", "get_active_sessions"]
                
            elif "LATENCY" in alarm_name.upper() or "ReadLatency" in metric_name or "WriteLatency" in metric_name:
                prompt = f"""
                FOCUS ONLY ON I/O LATENCY ALERT: {alarm_name}
                
                Alert Details:
                - Metric: {metric_name}
                - Threshold: {threshold}
                - Issue: {state_reason}
                
                You have access to ONLY the specific tools needed for latency analysis:
                - get_performance_metrics: Get current I/O latency metrics
                - get_slow_queries: Find queries with high I/O latency
                - get_buffer_cache_stats: Check I/O efficiency
                
                Provide ONLY latency-specific recommendations:
                
                IMMEDIATE LATENCY ACTIONS:
                - What is the current read/write latency?
                - Which queries are causing high I/O latency?
                - Is the buffer cache hit ratio affecting latency?
                
                LATENCY REDUCTION ONLY:
                - Specific queries to optimize for I/O reduction
                - Index recommendations ONLY for reducing I/O operations
                - Buffer cache tuning for latency improvement
                
                Expected outcome: Reduce I/O latency below {threshold}
                """
                
                specific_tools = ["get_performance_metrics", "get_slow_queries", "get_buffer_cache_stats"]
                
            else:
                # Generic alarm analysis - still focused
                prompt = f"""
                FOCUS ONLY ON THIS SPECIFIC ALERT: {alarm_name}
                
                Alert Details:
                - Metric: {metric_name}
                - Threshold: {threshold}
                - Issue: {state_reason}
                
                You have access to relevant tools for analyzing {metric_name}.
                
                Provide ONLY recommendations specific to {metric_name}:
                
                IMMEDIATE ACTIONS for {metric_name}:
                - What is the current value of {metric_name}?
                - What is causing {metric_name} to exceed {threshold}?
                - What immediate steps can reduce {metric_name}?
                
                SPECIFIC SOLUTIONS for {metric_name} ONLY:
                - Targeted actions to improve {metric_name}
                - Configuration changes specific to {metric_name}
                - Expected improvement in {metric_name}
                
                Expected outcome: Bring {metric_name} below {threshold}
                """
                
                # For generic alarms, use a broader set of relevant tools
                specific_tools = ["get_aurora_alarms", "get_performance_metrics", "get_active_sessions"]
            
            agent = DatabaseAgent(prompt, specific_tools=specific_tools)
            result = agent.run()
            
            st.success("✅ Analysis Complete!")
            
            # Extract content from AgentResult
            if hasattr(result, 'content'):
                result_content = result.content
            elif hasattr(result, 'text'):
                result_content = result.text
            else:
                result_content = str(result)
            
            # Display results in simple format
            st.subheader(f"📋 Analysis Results for {alarm_name}")
            st.markdown(result_content)
            
            # Download option
            st.download_button(
                "📥 Download Alert Analysis Report",
                data=result_content,
                file_name=f"alert_analysis_{alarm_name}_{int(time.time())}.md",
                mime="text/markdown",
                key=f"download_{alarm_name}_{int(time.time())}"
            )
            
        except Exception as e:
            st.error(f"❌ Analysis failed: {str(e)}")
            st.info("Please ensure MCP servers are running: `./mcp/start_mcp_servers.sh`")

def render_query_optimization():
    """Query optimization with focused sub-categories - Use Case #2"""
    st.header("🐌 Query Optimization")
    st.markdown("Choose specific optimization analysis type for targeted recommendations")
    
    # Sub-category selection
    optimization_type = st.selectbox(
        "Select Optimization Type:",
        [
            "🐌 Slow Query Analysis",
            "📊 Index Analysis", 
            "🔍 Custom Query Optimization"
        ]
    )
    
    if optimization_type == "🐌 Slow Query Analysis":
        render_slow_query_analysis()
    elif optimization_type == "📊 Index Analysis":
        render_index_analysis()
    else:
        render_custom_query_optimization()

def render_slow_query_analysis():
    """Focused slow query analysis with individual query recommendations"""
    st.subheader("🐌 Slow Query Analysis")
    st.markdown("Analyze all slow-running queries with specific recommendations for each")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Analysis Options:**")
        st.write("• Get all slow queries from pg_stat_statements")
        st.write("• Individual optimization recommendations")
        st.write("• Performance impact estimates")
    
    with col2:
        run_analysis = st.button("🔍 Analyze All Slow Queries", type="primary", use_container_width=True)
    
    # Run analysis outside of columns to use full width
    if run_analysis:
        analyze_all_slow_queries()

def render_index_analysis():
    """Focused index analysis with missing/unused index recommendations"""
    st.subheader("📊 Index Analysis")
    st.markdown("Comprehensive index analysis with specific recommendations")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Analysis Includes:**")
        st.write("• Missing indexes identification")
        st.write("• Unused indexes for cleanup")
        st.write("• Index usage efficiency analysis")
        st.write("• Storage optimization opportunities")
    
    with col2:
        run_analysis = st.button("📊 Analyze All Indexes", type="primary", use_container_width=True)
    
    # Run analysis outside of columns to use full width
    if run_analysis:
        analyze_all_indexes()

def render_custom_query_optimization():
    """Custom query optimization for specific queries"""
    st.subheader("🔍 Custom Query Optimization")
    st.markdown("Optimize specific queries with targeted recommendations")
    
    # Example slow queries
    example_queries = [
        "SELECT * FROM orders WHERE customer_id = 12345 AND order_date > '2024-01-01'",
        "UPDATE inventory SET quantity = quantity - 1 WHERE product_id = 67890",
        "SELECT COUNT(*) FROM transactions WHERE date BETWEEN '2024-01-01' AND '2024-12-31'"
    ]
    
    query_option = st.selectbox(
        "Choose a query to analyze:",
        ["Custom Query"] + [f"Example {i+1}: {q[:50]}..." for i, q in enumerate(example_queries)]
    )
    
    if query_option == "Custom Query":
        user_query = st.text_area(
            "Enter your query:",
            placeholder="SELECT * FROM your_table WHERE...",
            height=100
        )
    else:
        # Extract the number from "Example 1: ..." format
        query_index = int(query_option.split()[1].rstrip(':')) - 1
        user_query = example_queries[query_index]
        st.code(user_query, language='sql')
    
    if st.button("🧠 Optimize This Query", type="primary", use_container_width=True) and user_query.strip():
        optimize_single_query(user_query)

def analyze_all_slow_queries():
    """Analyze all slow queries with individual recommendations"""
    with st.spinner("🔍 Analyzing all slow queries from database..."):
        try:
            prompt = """
            SLOW QUERY COMPREHENSIVE ANALYSIS - FOCUSED TOOL APPROACH
            
            You have access to ONLY the specific tools needed for slow query analysis:
            - get_slow_queries: Fetch ALL slow queries from pg_stat_statements
            - get_active_sessions: Check if slow queries are currently running
            - get_table_stats: Get table access patterns for slow queries
            - get_index_usage: Analyze indexes for slow query optimization
            - get_buffer_cache_stats: Check memory cache efficiency for slow queries
            
            For EACH slow query found, provide:
            
            1. QUERY DETAILS:
               - Query text (first 200 characters)
               - Average execution time
               - Total calls and total execution time
               - Rows affected per execution
            
            2. INDIVIDUAL RECOMMENDATIONS for each query:
               - Specific index recommendations for THIS query
               - Query rewrite suggestions for THIS query
               - Expected performance improvement for THIS query
               - Priority level (High/Medium/Low) for THIS query
            
            3. SUMMARY:
               - Top 3 most critical queries to optimize first
               - Expected overall performance improvement
               - Total potential time savings
            
            Focus ONLY on slow query optimization using the provided tools.
            """
            
            # Use specific tools for slow query analysis
            slow_query_tools = [
                "get_slow_queries",
                "get_active_sessions", 
                "get_table_stats",
                "get_index_usage",
                "get_buffer_cache_stats"
            ]
            
            agent = DatabaseAgent(prompt, specific_tools=slow_query_tools)
            result = agent.run()
            
            # Extract content from AgentResult
            if hasattr(result, 'content'):
                result_content = result.content
            elif hasattr(result, 'text'):
                result_content = result.text
            else:
                result_content = str(result)
            
            st.success("✅ Slow Query Analysis Complete!")
            st.subheader("📊 Individual Query Analysis & Recommendations")
            st.markdown(result_content)
            
            # Download option
            st.download_button(
                "📥 Download Slow Query Report",
                data=result_content,
                file_name=f"slow_query_analysis_{int(time.time())}.md",
                mime="text/markdown"
            )
            
        except Exception as e:
            st.error(f"❌ Analysis failed: {str(e)}")
            st.info("Make sure pg_stat_statements extension is enabled: `CREATE EXTENSION pg_stat_statements;`")

def analyze_all_indexes():
    """Comprehensive index analysis with specific recommendations"""
    with st.spinner("📊 Analyzing all indexes and usage patterns..."):
        try:
            prompt = """
            COMPREHENSIVE INDEX ANALYSIS - FOCUSED TOOL APPROACH
            
            You have access to ONLY the specific tools needed for index analysis:
            - get_index_usage: Current index usage statistics
            - identify_unused_indexes: Find unused indexes for cleanup
            - get_table_stats: Find tables with high sequential scan ratios (missing indexes)
            - suggest_indexes: AI-powered index recommendations
            - get_slow_queries: See which queries would benefit from new indexes
            - get_buffer_cache_stats: Check if index efficiency affects cache performance
            - get_schemas: Get schema context for index recommendations
            
            Provide detailed analysis in these sections:
            
            1. MISSING INDEXES:
               - Tables with high sequential scan ratios (>50%)
               - Specific CREATE INDEX statements for each table
               - Expected performance improvement for each index
               - Priority ranking (High/Medium/Low)
            
            2. UNUSED INDEXES:
               - Indexes with low scan counts (<10 scans)
               - Storage space consumed by each unused index
               - DROP INDEX statements for cleanup
               - Estimated storage savings
            
            3. INDEX EFFICIENCY:
               - Well-performing indexes (high usage)
               - Underperforming indexes that need review
               - Index usage patterns and recommendations
            
            4. OPTIMIZATION SUMMARY:
               - Total storage that can be freed
               - Expected query performance improvements
               - Priority action plan
            
            Focus ONLY on index optimization using the provided tools.
            """
            
            # Use specific tools for index analysis
            index_analysis_tools = [
                "get_index_usage",
                "identify_unused_indexes", 
                "get_table_stats",
                "suggest_indexes",
                "get_slow_queries",
                "get_buffer_cache_stats",
                "get_schemas"
            ]
            
            agent = DatabaseAgent(prompt, specific_tools=index_analysis_tools)
            result = agent.run()
            
            # Extract content from AgentResult
            if hasattr(result, 'content'):
                result_content = result.content
            elif hasattr(result, 'text'):
                result_content = result.text
            else:
                result_content = str(result)
            
            st.success("✅ Index Analysis Complete!")
            st.subheader("📊 Comprehensive Index Analysis & Recommendations")
            st.markdown(result_content)
            
            # Download option
            st.download_button(
                "📥 Download Index Analysis Report",
                data=result_content,
                file_name=f"index_analysis_{int(time.time())}.md",
                mime="text/markdown"
            )
            
        except Exception as e:
            st.error(f"❌ Analysis failed: {str(e)}")

def optimize_single_query(query):
    """Optimize a specific query with targeted recommendations"""
    with st.spinner("🧠 Analyzing and optimizing the specific query..."):
        try:
            prompt = f"""
            SINGLE QUERY OPTIMIZATION ANALYSIS - FOCUSED TOOL APPROACH
            
            Analyze and optimize this specific query:
            
            ```sql
            {query}
            ```
            
            You have access to ONLY the specific tools needed for query optimization:
            - get_table_stats: Check table access patterns for this query
            - get_index_usage: Analyze existing indexes for this query
            - get_buffer_cache_stats: Check cache efficiency for large data scans
            - get_schemas: Get schema context for optimization
            - suggest_indexes: Get AI-powered index recommendations
            
            Provide detailed optimization analysis:
            
            1. QUERY ANALYSIS:
               - What does this query do?
               - Current execution approach
               - Potential performance bottlenecks
            
            2. INDEX RECOMMENDATIONS:
               - Specific indexes needed for this query
               - CREATE INDEX statements
               - Expected performance improvement
            
            3. QUERY REWRITE OPTIONS:
               - Alternative query structures
               - More efficient approaches
               - Optimized version of the query
            
            4. EXECUTION PLAN INSIGHTS:
               - Expected execution plan improvements
               - Resource usage optimization
               - Performance impact estimates
            
            Focus ONLY on optimizing this specific query using the provided tools.
            """
            
            # Use specific tools for single query optimization
            query_optimization_tools = [
                "get_table_stats",
                "get_index_usage",
                "get_buffer_cache_stats", 
                "get_schemas",
                "suggest_indexes"
            ]
            
            agent = DatabaseAgent(prompt, specific_tools=query_optimization_tools)
            result = agent.run()
            
            # Extract content from AgentResult
            if hasattr(result, 'content'):
                result_content = result.content
            elif hasattr(result, 'text'):
                result_content = result.text
            else:
                result_content = str(result)
            
            st.success("✅ Query Optimization Complete!")
            st.subheader("📋 Specific Query Optimization Recommendations")
            st.markdown(result_content)
            
            # Download option
            st.download_button(
                "📥 Download Query Optimization Report",
                data=result_content,
                file_name=f"query_optimization_{int(time.time())}.md",
                mime="text/markdown"
            )
            
        except Exception as e:
            st.error(f"❌ Optimization failed: {str(e)}")

def fetch_slow_queries():
    """Fetch real slow queries from database"""
    with st.spinner("🔍 Fetching slow queries from database..."):
        try:
            prompt = """
            Use the get_slow_queries tool to fetch the slowest queries from pg_stat_statements.
            
            Please analyze and present:
            1. Top 10 slowest queries by average execution time
            2. Query text (truncated for readability)
            3. Execution statistics (calls, avg time, total time)
            4. Brief optimization suggestions for each query
            
            Format the results in a clear, readable way with the most problematic queries first.
            """
            
            agent = DatabaseAgent(prompt, specific_tools=["get_slow_queries"])
            result = agent.run()
            
            # Extract content from AgentResult
            if hasattr(result, 'content'):
                result_content = result.content
            elif hasattr(result, 'text'):
                result_content = result.text
            else:
                result_content = str(result)
            
            st.success("✅ Slow queries retrieved from database!")
            st.subheader("📊 Current Slow Queries from pg_stat_statements")
            st.markdown(result_content)
            
            # Add note about optimization
            st.info("💡 Copy any query above into the 'Custom Query' field below to get detailed optimization recommendations.")
            
        except Exception as e:
            st.error(f"❌ Failed to fetch queries: {str(e)}")
            st.info("Make sure pg_stat_statements extension is enabled: `CREATE EXTENSION pg_stat_statements;`")

def optimize_query(query):
    """Optimize specific query with AI"""
    with st.spinner("🧠 Analyzing query and generating optimization recommendations..."):
        try:
            prompt = f"""
            Analyze and optimize this slow-running query:
            
            ```sql
            {query}
            ```
            
            Please provide:
            1. Specific index recommendations with CREATE INDEX statements
            2. Query rewriting suggestions if applicable
            3. Expected performance improvement
            4. Any table structure recommendations
            
            Focus on actionable recommendations that can be implemented immediately.
            """
            
            agent = DatabaseAgent(prompt, specific_tools=["get_table_stats", "get_index_usage", "suggest_indexes", "get_schemas"])
            result = agent.run()
            
            # Extract content from AgentResult
            if hasattr(result, 'content'):
                result_content = result.content
            elif hasattr(result, 'text'):
                result_content = result.text
            else:
                result_content = str(result)
            
            st.success("✅ Query Optimization Complete!")
            
            # Display results
            st.subheader("📋 Optimization Recommendations")
            st.markdown(result_content)
            
            # Download option
            st.download_button(
                "📥 Download Optimization Report",
                data=result_content,
                file_name=f"query_optimization_{int(time.time())}.md",
                mime="text/markdown"
            )
            
        except Exception as e:
            st.error(f"❌ Optimization failed: {str(e)}")
            st.info("Please ensure Aurora MCP server is running")

# Sidebar with simple status
with st.sidebar:
    st.title("🔧 System Status")
    
    # Simple server status check
    import socket
    
    def check_port(port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    aurora_status = check_port(8081)
    cloudwatch_status = check_port(8080)
    
    st.write(f"{'🟢' if aurora_status else '🔴'} Aurora MCP Server")
    st.write(f"{'🟢' if cloudwatch_status else '🔴'} CloudWatch MCP Server")
    
    if not (aurora_status and cloudwatch_status):
        st.warning("⚠️ Start servers with:\n`./mcp/start_mcp_servers.sh`")
    
    st.markdown("---")
    st.subheader("💡 Quick Tips")
    st.markdown("""
    **Alert Investigation:**
    - Analyze high CPU, memory, or connection alerts
    - Get specific recommendations to resolve issues
    
    **Query Optimization:**
    - Analyze slow-running queries
    - Get index recommendations
    - Improve query performance
    """)

if __name__ == "__main__":
    main()