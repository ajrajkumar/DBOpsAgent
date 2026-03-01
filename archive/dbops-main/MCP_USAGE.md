# MCP Servers Usage Guide

## 🚀 Starting Both MCP Servers

### Quick Start
```bash
cd /Users/karumajj/autonomous-dbops-v2

# Set AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret  
export AWS_SESSION_TOKEN=your_token
export DB_NAME=demodb

source .venv/bin/activate

# Start both servers
./mcp/start_mcp_servers.sh
```

### Alternative Usage
```bash
# From mcp directory
cd mcp
./start_mcp_servers.sh

# Individual servers
python aurora_server.py
python cloudwatch_server.py
```

## 📊 Server Details

### Aurora MCP Server (13 Tools + 4 Prompts)
- **Name**: Aurora PostgreSQL Server
- **Transport**: Streamable HTTP (Port 8081)
- **Database Tools** (13 total):
  - `test_connection` - Test Aurora database connection
  - `get_active_sessions` - Monitor real-time database sessions
  - `get_table_names` - List all tables in database
  - `get_slow_queries` - Analyze slow queries from pg_stat_statements
  - `get_table_stats` - Get table usage statistics and scan ratios
  - `get_schemas` - Discover database schemas
  - `get_index_usage` - Analyze index efficiency and usage patterns
  - `get_blocking_queries` - Detect blocking queries and deadlocks
  - `suggest_indexes` - AI-powered index recommendations
  - `get_buffer_cache_stats` - Memory cache analysis
  - `get_wait_events` - Wait event monitoring for bottlenecks
  - `get_connection_pool_stats` - Connection management analysis
  - `identify_unused_indexes` - Find unused indexes for cleanup

- **Smart Prompts** (4 total):
  - `aurora_tool_selection` - Smart tool selection guide for different scenarios
  - `query_performance_analysis` - Comprehensive query optimization workflows
  - `database_troubleshooting` - Problem resolution and emergency workflows
  - `index_optimization` - Index analysis and optimization strategies

### CloudWatch MCP Server (11 Tools + 4 Prompts)
- **Name**: CloudWatch Monitoring Server
- **Transport**: Streamable HTTP (Port 8080)
- **Monitoring Tools** (11 total):
  - `test_cloudwatch_connection` - Test AWS CloudWatch service
  - `get_aurora_alarms` - Get real CloudWatch alarms for Aurora
  - `get_database_connections` - Monitor connection metrics
  - `get_cpu_utilization` - CPU performance analysis with historical data
  - `get_alarms_last_hour` - Recent alarm activity across all services
  - `get_aurora_db_load_metrics` - Database load analysis
  - `get_performance_metrics` - Performance metrics (latency, IOPS)
  - `get_performance_insights_data` - Performance Insights integration
  - `get_aurora_cluster_metrics` - Cluster-level monitoring
  - `get_aurora_instance_metrics` - Instance-level monitoring
  - `get_comprehensive_insights` - Combined health scoring

- **Smart Prompts** (4 total):
  - `cloudwatch_tool_selection` - Smart tool selection for monitoring scenarios
  - `database_performance_analysis` - Comprehensive performance analysis workflows
  - `alarm_investigation` - CloudWatch alarm troubleshooting workflows
  - `capacity_planning` - Resource optimization and scaling guidance

## 🎯 How MCP Works

MCP (Model Context Protocol) servers provide **AI agents with structured access** to tools and knowledge:
- **Tools**: Executable functions that return real data
- **Prompts**: Contextual guidance for intelligent tool usage
- **Transport**: HTTP-based communication for this implementation
- **Integration**: Used by DatabaseAgent for comprehensive analysis

## 🧠 Smart Prompt System

### Aurora Prompts Guide LLM For:
- **Scenario-based tool selection**: "Database is slow" → specific tool sequence
- **Performance analysis workflows**: Structured 5-step query optimization
- **Troubleshooting decision trees**: Emergency response procedures
- **Index optimization strategies**: Cleanup, creation, and optimization workflows

### CloudWatch Prompts Guide LLM For:
- **Monitoring tool selection**: Which metrics to check for different issues
- **Alarm investigation**: Systematic approach to alert troubleshooting
- **Performance analysis**: CPU, memory, I/O, and connection monitoring
- **Capacity planning**: Resource optimization and scaling decisions

## 🔧 Server Status

### Aurora Server Success Output:
```
🚀 Starting Aurora MCP Server...
📊 Available tools: 13 total (test_connection, get_active_sessions, get_table_names, ...)
🧠 Available prompts: 4 total (aurora_tool_selection, query_performance_analysis, ...)
🌐 Starting on http://localhost:8081/mcp
```

### CloudWatch Server Success Output:
```
🚀 Starting CloudWatch MCP Server...
📊 Available tools: 11 total (test_cloudwatch_connection, get_aurora_alarms, ...)
🧠 Available prompts: 4 total (cloudwatch_tool_selection, database_performance_analysis, ...)
🌐 Starting on http://localhost:8080/mcp
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. **Cluster ID Error** (Fixed)
```
ERROR: DBCluster localhost not found
```
**Solution**: Fixed in CloudWatch server - now uses `dbClusterIdentifier` from Secrets Manager

#### 2. **Connection Issues**
- Check AWS credentials are set
- Verify virtual environment is activated
- Ensure Secrets Manager access permissions
- Confirm Aurora cluster is accessible via SSH tunnel

#### 3. **Extension Missing**
```
ERROR: pg_stat_statements extension not available
```
**Solution**: Enable extension in Aurora: `CREATE EXTENSION pg_stat_statements;`

#### 4. **Port Conflicts**
- Aurora server: Port 8081
- CloudWatch server: Port 8080
- Check ports are available: `lsof -i :8080` and `lsof -i :8081`

### Testing Tools

#### Aurora Tools Test:
```python
# Test database connectivity
test_connection()

# Check current activity
get_active_sessions()

# Analyze performance
get_slow_queries()
get_table_stats()
```

#### CloudWatch Tools Test:
```python
# Test AWS connectivity
test_cloudwatch_connection()

# Check alarms
get_aurora_alarms()

# Monitor performance
get_cpu_utilization()
get_database_connections()
```

## 🎉 Success Indicators

### ✅ **Servers Working When You See**:
- FastMCP banner displays with correct tool/prompt counts
- "Starting on http://localhost:PORT/mcp" message
- No error messages in startup output
- Process stays running and responsive to requests

### ❌ **Issues If You See**:
- Python import errors → Check virtual environment
- AWS credential errors → Verify AWS configuration
- Database connection failures → Check SSH tunnel and credentials
- Process exits with error code → Review error logs

## � NAdvanced Usage

### Using Prompts in DatabaseAgent
The DatabaseAgent automatically uses prompts to guide tool selection:

```python
# Example: LLM uses aurora_tool_selection prompt
# Scenario: "Database is slow"
# Prompt guides: get_slow_queries() → get_table_stats() → get_index_usage()

agent = DatabaseAgent("Analyze slow database performance")
result = agent.run()  # Uses smart prompts for optimal tool selection
```

### Manual Prompt Access
```python
# Access prompts directly for guidance
aurora_guidance = aurora_client.get_prompt("aurora_tool_selection")
cloudwatch_guidance = cw_client.get_prompt("cloudwatch_tool_selection")
```

### Tool Combinations Guided by Prompts
- **Performance Issues**: `get_slow_queries()` + `get_table_stats()` + `get_index_usage()`
- **Blocking Problems**: `get_blocking_queries()` + `get_wait_events()` + `get_active_sessions()`
- **Index Optimization**: `get_index_usage()` + `identify_unused_indexes()` + `suggest_indexes()`
- **Health Monitoring**: `test_connection()` + `get_comprehensive_insights()` + `get_aurora_alarms()`

## 🔗 Integration with DatabaseAgent

### Complete Workflow:
1. **Start MCP Servers**: Both Aurora and CloudWatch servers
2. **Run DatabaseAgent**: Connects to both servers automatically
3. **Smart Analysis**: Uses prompts to guide tool selection
4. **Comprehensive Report**: Combines data from all 24 tools

### Example Analysis Request:
```bash
python agents/database_agent.py
# Input: "Find performance bottlenecks and optimization opportunities"
# Result: Uses prompts to intelligently select and sequence tools
```

## 📈 Performance & Monitoring

### Server Performance:
- **Response Time**: < 2 seconds for most tools
- **Concurrent Requests**: Supports multiple simultaneous analyses
- **Resource Usage**: Minimal overhead on Aurora cluster
- **Connection Pooling**: Efficient database connection management

### Monitoring Server Health:
```bash
# Check server status
curl -X POST http://localhost:8081/mcp  # Aurora server
curl -X POST http://localhost:8080/mcp  # CloudWatch server

# Monitor server logs
tail -f logs/aurora_server.log
tail -f logs/cloudwatch_server.log
```

## 🎯 Best Practices

### 1. **Server Management**
- Always start both servers before running DatabaseAgent
- Monitor server logs for errors and performance
- Restart servers after configuration changes
- Use process managers (systemd/pm2) for production

### 2. **Tool Usage**
- Let prompts guide tool selection for optimal results
- Start with connectivity tests before deep analysis
- Combine Aurora and CloudWatch tools for comprehensive insights
- Use time parameters (hours_back) for historical analysis

### 3. **Troubleshooting**
- Check server logs first for error diagnosis
- Verify AWS credentials and permissions
- Ensure SSH tunnel is active for Aurora access
- Test individual tools before running full analysis

### 4. **Performance Optimization**
- Use connection pooling for database tools
- Cache expensive query results when appropriate
- Monitor server resource usage
- Scale servers horizontally if needed
