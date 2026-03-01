#!/usr/bin/env python3
"""
Autonomous Database Operations Dashboard
Real-time Streamlit frontend for database performance analysis and optimization
"""

import streamlit as st
import pandas as pd
import requests
import json
import sys
import os
from datetime import datetime, timedelta
import re
import time
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.database_agent import DatabaseAgent
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

# Configure Streamlit page
st.set_page_config(
    page_title="Autonomous Database Operations Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .alert-card {
        background-color: #fff2f2;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff4444;
    }
    .success-card {
        background-color: #f0fff4;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #00cc44;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

class DatabaseDashboard:
    """
    Main Dashboard Class for Autonomous Database Operations
    
    Integrates with MCP servers and DatabaseAgent to provide real-time
    database performance analysis and optimization recommendations.
    """
    
    def __init__(self):
        """Initialize dashboard with MCP client connections"""
        self.aurora_mcp_url = "http://localhost:8081/mcp"
        self.cloudwatch_mcp_url = "http://localhost:8080/mcp"
        
        # Initialize session state
        if 'mcp_status' not in st.session_state:
            st.session_state.mcp_status = {'aurora': False, 'cloudwatch': False}
        if 'last_health_check' not in st.session_state:
            st.session_state.last_health_check = None
        if 'cached_data' not in st.session_state:
            st.session_state.cached_data = {}
    
    def simple_port_check(self, port: int) -> bool:
        """
        Simple check if port is listening
        
        Args:
            port: Port number to check
            
        Returns:
            bool: True if port is listening
        """
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    def check_mcp_server_status(self, server_type: str) -> bool:
        """
        Check if MCP servers are running and accessible
        
        Args:
            server_type: 'aurora' or 'cloudwatch'
            
        Returns:
            bool: True if server is accessible
        """
        try:
            # Try to create MCP client and test connection
            client = self.get_mcp_client(server_type)
            if not client:
                return False
            
            # Test with actual MCP tool call
            with client:
                if server_type == 'aurora':
                    result = client.call_tool_sync(
                        tool_use_id="health_check",
                        name="test_connection",
                        arguments={}
                    )
                else:
                    result = client.call_tool_sync(
                        tool_use_id="health_check", 
                        name="test_cloudwatch_connection",
                        arguments={}
                    )
                return result.get('status') == 'success'
        except Exception as e:
            # Don't show error in UI during status check, just return False
            return False
    
    def get_mcp_client(self, server_type: str):
        """
        Get MCP client for specified server
        
        Args:
            server_type: 'aurora' or 'cloudwatch'
            
        Returns:
            MCPClient instance or None if connection fails
        """
        try:
            url = self.aurora_mcp_url if server_type == 'aurora' else self.cloudwatch_mcp_url
            return MCPClient(lambda: streamablehttp_client(url))
        except Exception as e:
            st.error(f"Failed to create {server_type} MCP client: {str(e)}")
            return None
    
    def call_mcp_tool(self, server_type: str, tool_name: str, arguments: Dict = None) -> Dict:
        """
        Call MCP tool and return results
        
        Args:
            server_type: 'aurora' or 'cloudwatch'
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments
            
        Returns:
            Dict: Tool execution results
        """
        try:
            client = self.get_mcp_client(server_type)
            if not client:
                return {"status": "error", "error": "MCP client not available"}
            
            with client:
                result = client.call_tool_sync(
                    tool_use_id=f"{tool_name}_{int(time.time())}",
                    name=tool_name,
                    arguments=arguments or {}
                )
                return result
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_system_health_data(self) -> Dict[str, Any]:
        """
        Get comprehensive system health data from MCP servers
        
        Returns:
            Dict: System health metrics
        """
        health_data = {
            'health_score': 0,
            'cpu_usage': 0,
            'active_sessions': 0,
            'active_alarms': 0,
            'database_connections': 0,
            'status': 'unknown'
        }
        
        try:
            # Get comprehensive insights from CloudWatch
            insights = self.call_mcp_tool('cloudwatch', 'get_comprehensive_insights')
            if insights.get('status') == 'success':
                data = insights.get('data', {})
                health_data['health_score'] = data.get('overall_health_score', 0)
                health_data['cpu_usage'] = data.get('cpu_utilization', 0)
                health_data['database_connections'] = data.get('active_connections', 0)
            
            # Get active sessions from Aurora
            sessions = self.call_mcp_tool('aurora', 'get_active_sessions')
            if sessions.get('status') == 'success':
                health_data['active_sessions'] = sessions.get('count', 0)
            
            # Get active alarms
            alarms = self.call_mcp_tool('cloudwatch', 'get_aurora_alarms')
            if alarms.get('status') == 'success':
                alarm_data = alarms.get('data', [])
                health_data['active_alarms'] = len([a for a in alarm_data if a.get('state') == 'ALARM'])
            
            health_data['status'] = 'success'
            
        except Exception as e:
            st.error(f"Failed to get system health data: {str(e)}")
            health_data['status'] = 'error'
        
        return health_data
    
    def get_active_alarms(self) -> List[Dict]:
        """
        Get active CloudWatch alarms with details
        
        Returns:
            List[Dict]: Active alarms data
        """
        try:
            alarms_result = self.call_mcp_tool('cloudwatch', 'get_aurora_alarms')
            if alarms_result.get('status') == 'success':
                return alarms_result.get('data', [])
            else:
                st.error(f"Failed to get alarms: {alarms_result.get('error', 'Unknown error')}")
                return []
        except Exception as e:
            st.error(f"Error fetching alarms: {str(e)}")
            return []
    
    def get_slow_queries(self, limit: int = 20) -> List[Dict]:
        """
        Get slow queries from Aurora database
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List[Dict]: Slow queries data
        """
        try:
            queries_result = self.call_mcp_tool('aurora', 'get_slow_queries')
            if queries_result.get('status') == 'success':
                queries = queries_result.get('data', [])
                return queries[:limit]
            else:
                st.error(f"Failed to get slow queries: {queries_result.get('error', 'Unknown error')}")
                return []
        except Exception as e:
            st.error(f"Error fetching slow queries: {str(e)}")
            return []
    
    def get_cpu_utilization_history(self) -> Dict:
        """
        Get CPU utilization history for charting
        
        Returns:
            Dict: CPU utilization data with timestamps
        """
        try:
            cpu_result = self.call_mcp_tool('cloudwatch', 'get_cpu_utilization')
            if cpu_result.get('status') == 'success':
                return cpu_result.get('metrics', [])
            return []
        except Exception as e:
            st.error(f"Error fetching CPU history: {str(e)}")
            return []
    
    def parse_analysis_report(self, markdown_report: str) -> Dict[str, str]:
        """
        Parse markdown analysis report into sections
        
        Args:
            markdown_report: Full markdown report from DatabaseAgent
            
        Returns:
            Dict: Parsed sections
        """
        sections = {}
        current_section = None
        current_content = []
        
        for line in markdown_report.split('\n'):
            if line.startswith('##'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = line.replace('#', '').strip().lower().replace(' ', '_').replace('&', 'and')
                current_content = []
            else:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def extract_sql_commands(self, text: str) -> List[str]:
        """
        Extract SQL commands from markdown text
        
        Args:
            text: Text containing SQL code blocks
            
        Returns:
            List[str]: Extracted SQL commands
        """
        sql_pattern = r'```sql\n(.*?)\n```'
        commands = re.findall(sql_pattern, text, re.DOTALL)
        return [cmd.strip() for cmd in commands if cmd.strip()]
    
    def render_sidebar(self):
        """Render sidebar with navigation and server status"""
        with st.sidebar:
            st.title("🤖 Database Operations")
            st.markdown("---")
            
            # Server Status Check
            st.subheader("🔧 Server Status")
            
            # Check MCP server status (simplified check)
            aurora_status = self.simple_port_check(8081)
            cloudwatch_status = self.simple_port_check(8080)
            
            st.session_state.mcp_status['aurora'] = aurora_status
            st.session_state.mcp_status['cloudwatch'] = cloudwatch_status
            
            col1, col2 = st.columns(2)
            with col1:
                status_icon = "🟢" if aurora_status else "🔴"
                st.write(f"{status_icon} Aurora MCP")
            with col2:
                status_icon = "🟢" if cloudwatch_status else "🔴"
                st.write(f"{status_icon} CloudWatch MCP")
            
            if not (aurora_status and cloudwatch_status):
                st.warning("⚠️ Some MCP servers are offline. Start servers with: `./mcp/start_mcp_servers.sh`")
            
            st.markdown("---")
            
            # Navigation
            st.subheader("📊 Navigation")
            page = st.selectbox(
                "Select Analysis Type:",
                [
                    "📊 System Health Overview",
                    "🚨 Alert Investigation", 
                    "🐌 Query Optimization",
                    "🔧 Index Optimization",
                    "📈 Performance Analysis",
                    "🎯 Custom Analysis"
                ]
            )
            
            st.markdown("---")
            
            # Quick Actions
            st.subheader("⚡ Quick Actions")
            if st.button("🔄 Refresh Data"):
                st.session_state.cached_data = {}
                st.rerun()
            
            if st.button("🧪 Test Connections"):
                self.test_all_connections()
            
            return page
    
    def test_all_connections(self):
        """Test all system connections"""
        with st.spinner("Testing connections..."):
            # Test Aurora connection
            aurora_test = self.call_mcp_tool('aurora', 'test_connection')
            
            # Test CloudWatch connection
            cloudwatch_test = self.call_mcp_tool('cloudwatch', 'test_cloudwatch_connection')
            
            if aurora_test.get('status') == 'success':
                st.success("✅ Aurora database connection successful")
            else:
                st.error(f"❌ Aurora connection failed: {aurora_test.get('error', 'Unknown error')}")
            
            if cloudwatch_test.get('status') == 'success':
                st.success("✅ CloudWatch connection successful")
            else:
                st.error(f"❌ CloudWatch connection failed: {cloudwatch_test.get('error', 'Unknown error')}")

    def render_health_overview(self):
        """Render system health overview page"""
        st.header("📊 System Health Overview")
        st.markdown("Real-time database performance metrics and health indicators")
        
        # Get health data
        with st.spinner("Loading system health data..."):
            health_data = self.get_system_health_data()
        
        if health_data['status'] != 'success':
            st.error("Failed to load health data. Please check MCP server connections.")
            return
        
        # Health Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            health_score = health_data['health_score']
            delta_color = "normal" if health_score >= 80 else "inverse"
            st.metric(
                "Health Score", 
                f"{health_score}/100",
                delta=f"{health_score-75}" if health_score > 75 else f"{health_score-75}",
                delta_color=delta_color
            )
        
        with col2:
            cpu_usage = health_data['cpu_usage']
            delta_color = "inverse" if cpu_usage > 80 else "normal"
            st.metric(
                "CPU Usage", 
                f"{cpu_usage:.1f}%",
                delta=f"{cpu_usage-70:.1f}%" if cpu_usage != 70 else None,
                delta_color=delta_color
            )
        
        with col3:
            active_sessions = health_data['active_sessions']
            st.metric(
                "Active Sessions", 
                active_sessions,
                delta=f"+{active_sessions-15}" if active_sessions > 15 else None
            )
        
        with col4:
            active_alarms = health_data['active_alarms']
            delta_color = "inverse" if active_alarms > 0 else "normal"
            st.metric(
                "Active Alarms", 
                active_alarms,
                delta=f"+{active_alarms}" if active_alarms > 0 else "0",
                delta_color=delta_color
            )
        
        # Charts Row
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("CPU Utilization Trend")
            cpu_history = self.get_cpu_utilization_history()
            
            if cpu_history:
                df = pd.DataFrame(cpu_history)
                if not df.empty and 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    fig = px.line(df, x='timestamp', y='average_cpu', 
                                title="CPU Usage (Last Hour)",
                                labels={'average_cpu': 'CPU %', 'timestamp': 'Time'})
                    fig.add_hline(y=80, line_dash="dash", line_color="red", 
                                annotation_text="High CPU Threshold")
                    st.plotly_chart(fig, use_container_width=True, key="cpu_trend_chart")
                else:
                    st.info("No CPU history data available")
            else:
                st.info("CPU history data not available")
        
        with col2:
            st.subheader("Database Connections")
            # Create a simple gauge chart for connections
            connections = health_data['database_connections']
            max_connections = 100  # Typical Aurora limit
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = connections,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Active Connections"},
                delta = {'reference': 50},
                gauge = {
                    'axis': {'range': [None, max_connections]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, max_connections], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 80
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True, key="connections_gauge_chart")
        
        # Recent Activity
        st.subheader("🔍 Recent Activity")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Recent Alarms**")
            alarms = self.get_active_alarms()
            if alarms:
                for alarm in alarms[:3]:  # Show top 3
                    state_icon = "🔴" if alarm.get('state') == 'ALARM' else "🟡"
                    st.write(f"{state_icon} {alarm.get('alarm_name', 'Unknown')}")
            else:
                st.success("✅ No active alarms")
        
        with col2:
            st.write("**System Status**")
            st.write(f"🟢 Database: Connected")
            st.write(f"🟢 Monitoring: Active")
            st.write(f"🟢 Analysis: Ready")
            
            if st.button("🧠 Run Quick Health Analysis"):
                self.run_quick_health_analysis()

    def run_quick_health_analysis(self):
        """Run a quick health analysis using DatabaseAgent"""
        with st.spinner("Running AI-powered health analysis..."):
            try:
                agent = DatabaseAgent("Perform quick database health check with current status and any immediate concerns")
                result = agent.run()
                
                st.success("✅ Health Analysis Complete!")
                
                # Display results in expandable sections
                sections = self.parse_analysis_report(result)
                
                if 'executive_summary' in sections:
                    with st.expander("📋 Executive Summary", expanded=True):
                        st.markdown(sections['executive_summary'])
                
                if 'actionable_recommendations' in sections:
                    with st.expander("🎯 Immediate Recommendations"):
                        st.markdown(sections['actionable_recommendations'])
                
                # Download option
                st.download_button(
                    "📥 Download Full Health Report",
                    data=result,
                    file_name=f"health_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
                
            except Exception as e:
                st.error(f"Health analysis failed: {str(e)}")

    def render_alert_investigation(self):
        """Render alert investigation page - Use Case #1"""
        st.header("🚨 Alert Investigation & Recommendations")
        st.markdown("Investigate CloudWatch alarms and get AI-powered recommendations")
        
        # Check if servers are available
        if not (st.session_state.mcp_status['aurora'] and st.session_state.mcp_status['cloudwatch']):
            st.error("⚠️ MCP servers are not available. Please start the servers first.")
            return
        
        # For now, show a placeholder
        st.info("🚧 Alert Investigation feature coming soon!")
        st.markdown("""
        This feature will:
        - Display active CloudWatch alarms
        - Allow selection of specific alarms
        - Provide AI-powered analysis and recommendations
        """)

    def render_query_optimization(self):
        """Render query optimization page - Use Case #2"""
        st.header("🐌 Slow Query Analysis & Optimization")
        st.markdown("Analyze slow-running queries and get AI-powered optimization recommendations")
        
        # Check if servers are available
        if not st.session_state.mcp_status['aurora']:
            st.error("⚠️ Aurora MCP server is not available. Please start the server first.")
            return
        
        # For now, show a placeholder
        st.info("🚧 Query Optimization feature coming soon!")
        st.markdown("""
        This feature will:
        - Fetch slow queries from pg_stat_statements
        - Allow selection of specific queries
        - Provide AI-powered optimization recommendations
        """)

    def render_index_optimization(self):
        """Render index optimization page"""
        st.header("🔧 Index Optimization")
        st.markdown("Analyze index usage patterns and identify optimization opportunities")
        
        if not st.session_state.mcp_status['aurora']:
            st.error("⚠️ Aurora MCP server is not available.")
            return
        
        st.info("🚧 Index Optimization feature coming soon!")

    def render_performance_analysis(self):
        """Render comprehensive performance analysis page"""
        st.header("📈 Performance Analysis")
        st.markdown("Comprehensive database performance analysis and monitoring")
        
        st.info("🚧 Performance Analysis feature coming soon!")

    def render_custom_analysis(self):
        """Render custom analysis page"""
        st.header("🎯 Custom Database Analysis")
        st.markdown("Create custom analysis requests using natural language")
        
        st.info("🚧 Custom Analysis feature coming soon!")

def main():
    """Main application entry point"""
    dashboard = DatabaseDashboard()
    
    # Render sidebar and get selected page
    selected_page = dashboard.render_sidebar()
    
    # Route to appropriate page
    if "System Health" in selected_page:
        dashboard.render_health_overview()
    elif "Alert Investigation" in selected_page:
        dashboard.render_alert_investigation()
    elif "Query Optimization" in selected_page:
        dashboard.render_query_optimization()
    elif "Index Optimization" in selected_page:
        dashboard.render_index_optimization()
    elif "Performance Analysis" in selected_page:
        dashboard.render_performance_analysis()
    else:
        dashboard.render_custom_analysis()
    
    # Route to appropriate page
    if "System Health" in selected_page:
        dashboard.render_health_overview()
    elif "Alert Investigation" in selected_page:
        dashboard.render_alert_investigation()
    elif "Query Optimization" in selected_page:
        dashboard.render_query_optimization()
    elif "Index Optimization" in selected_page:
        dashboard.render_index_optimization()
    elif "Performance Analysis" in selected_page:
        dashboard.render_performance_analysis()
    else:
        dashboard.render_custom_analysis()

if __name__ == "__main__":
    main()
