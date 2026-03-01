from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import boto3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

app = BedrockAgentCoreApp()

@tool
def get_aurora_alarms() -> List[Dict[str, Any]]:
    """Get current CloudWatch alarms for Aurora cluster"""
    try:
        client = boto3.client('cloudwatch', region_name='us-west-2')
        response = client.describe_alarms(AlarmNamePrefix='aurora', MaxRecords=50)
        alarms = response.get('MetricAlarms', [])
        
        results = []
        for alarm in alarms:
            results.append({
                'alarmName': alarm.get('AlarmName'),
                'stateValue': alarm.get('StateValue'),
                'stateReason': alarm.get('StateReason', ''),
                'metricName': alarm.get('MetricName'),
                'threshold': alarm.get('Threshold'),
                'comparisonOperator': alarm.get('ComparisonOperator')
            })
        return results
    except Exception as e:
        return [{"error": f"Failed to get Aurora alarms: {str(e)}"}]

@tool
def get_cpu_utilization() -> Dict[str, Any]:
    """Get CPU utilization for Aurora cluster over the last hour"""
    try:
        client = boto3.client('cloudwatch', region_name='us-west-2')
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        response = client.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='CPUUtilization',
            Dimensions=[
                {'Name': 'DBClusterIdentifier', 'Value': 'apgpg-dat302'}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=['Average', 'Maximum']
        )
        
        datapoints = response.get('Datapoints', [])
        if datapoints:
            latest = max(datapoints, key=lambda x: x['Timestamp'])
            avg_cpu = sum(d['Average'] for d in datapoints) / len(datapoints)
            return {
                "status": "success",
                "latest_cpu": latest['Average'],
                "max_cpu": latest['Maximum'],
                "average_cpu": avg_cpu,
                "datapoints": len(datapoints)
            }
        else:
            return {"status": "no_data", "message": "No CPU data available"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@tool
def test_connection() -> Dict[str, Any]:
    """Test database connection"""
    try:
        import psycopg2
        secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
        secret = secrets_client.get_secret_value(SecretId='apgpg-dat302-secret')
        creds = json.loads(secret['SecretString'])
        
        conn = psycopg2.connect(
            host=creds['host'],
            port=creds['port'],
            database=creds['dbname'],
            user=creds['username'],
            password=creds['password'],
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        conn.close()
        
        return {"status": "success", "version": version}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}

@tool
def send_notification(subject: str, message: str, severity: str = "INFO") -> Dict[str, Any]:
    """Send email notification via SNS"""
    try:
        sns_client = boto3.client('sns', region_name='us-west-2')
        
        # Use account ID from environment
        account_id = os.getenv('AWS_ACCOUNT_ID')
        topic_arn = f'arn:aws:sns:us-west-2:{account_id}:agentcore-database-alerts'
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        formatted_message = f"""
DATABASE OPERATIONS ALERT
========================
Timestamp: {timestamp}
Severity: {severity}
Subject: {subject}

{message}

---
Sent by AgentCore Database Operations Agent
"""
        
        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject=f"[{severity}] Database Alert: {subject}",
            Message=formatted_message
        )
        
        return {
            "status": "success", 
            "messageId": response.get('MessageId'),
            "subject": subject,
            "severity": severity
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@tool
def get_largest_tables() -> str:
    """Find the top 20 largest tables by disk usage for capacity planning"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
        secret = secrets_client.get_secret_value(SecretId='apgpg-dat302-secret')
        creds = json.loads(secret['SecretString'])
        
        conn = psycopg2.connect(
            host=creds['host'], port=creds['port'], database=creds['dbname'],
            user=creds['username'], password=creds['password'], cursor_factory=RealDictCursor
        )
        conn.set_session(readonly=True)
        cursor = conn.cursor()
        
        query = """
        SELECT schemaname AS schema_name, tablename AS table_name,
               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size
        FROM pg_tables WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 20
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not results:
            return "No tables found in the database."
        
        output = "TOP 20 LARGEST TABLES BY DISK USAGE:\n" + "=" * 60 + "\n"
        for row in results:
            output += f"Table: {row['schema_name']}.{row['table_name']}\n"
            output += f"  Total Size: {row['total_size']}\n" + "-" * 40 + "\n"
        return output
        
    except Exception as e:
        return f"Error retrieving largest tables: {str(e)}"

@tool
def get_duplicate_indexes() -> str:
    """Find duplicate indexes that waste storage and slow down writes"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
        secret = secrets_client.get_secret_value(SecretId='apgpg-dat302-secret')
        creds = json.loads(secret['SecretString'])
        
        conn = psycopg2.connect(
            host=creds['host'], port=creds['port'], database=creds['dbname'],
            user=creds['username'], password=creds['password'], cursor_factory=RealDictCursor
        )
        conn.set_session(readonly=True)
        cursor = conn.cursor()
        
        query = """
        SELECT indrelid::regclass AS table_name, array_agg(indexrelid::regclass) AS duplicate_indexes
        FROM pg_index GROUP BY indrelid, indkey HAVING COUNT(*) > 1
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not results:
            return "No duplicate indexes found. Your database is well-optimized!"
        
        output = "DUPLICATE INDEXES FOUND:\n" + "=" * 40 + "\n"
        for row in results:
            output += f"Table: {row['table_name']}\n"
            output += f"Duplicate Indexes: {', '.join(str(idx) for idx in row['duplicate_indexes'])}\n"
            output += "Recommendation: Consider dropping redundant indexes.\n" + "-" * 40 + "\n"
        return output
        
    except Exception as e:
        return f"Error finding duplicate indexes: {str(e)}"

@tool
def get_unused_indexes() -> str:
    """Find indexes that are never used by queries"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
        secret = secrets_client.get_secret_value(SecretId='apgpg-dat302-secret')
        creds = json.loads(secret['SecretString'])
        
        conn = psycopg2.connect(
            host=creds['host'], port=creds['port'], database=creds['dbname'],
            user=creds['username'], password=creds['password'], cursor_factory=RealDictCursor
        )
        conn.set_session(readonly=True)
        cursor = conn.cursor()
        
        query = """
        SELECT schemaname, relname AS table_name, indexrelname AS index_name,
               pg_size_pretty(pg_relation_size(i.indexrelid)) AS index_size, idx_scan AS index_scans
        FROM pg_stat_user_indexes ui JOIN pg_index i ON ui.indexrelid = i.indexrelid
        WHERE idx_scan < 1 AND pg_relation_size(i.indexrelid) > 10240
        ORDER BY pg_relation_size(i.indexrelid) DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not results:
            return "No unused indexes found. All indexes are being utilized!"
        
        output = "UNUSED INDEXES FOUND:\n" + "=" * 40 + "\n"
        for row in results:
            output += f"Schema: {row['schemaname']}\n"
            output += f"Table: {row['table_name']}\n"
            output += f"Index: {row['index_name']}\n"
            output += f"Size: {row['index_size']}\n"
            output += f"Scans: {row['index_scans']}\n"
            output += "Recommendation: Consider dropping this unused index.\n" + "-" * 40 + "\n"
        return output
        
    except Exception as e:
        return f"Error finding unused indexes: {str(e)}"

@tool
def get_table_bloat() -> str:
    """Identify tables with excessive dead space (bloat)"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
        secret = secrets_client.get_secret_value(SecretId='apgpg-dat302-secret')
        creds = json.loads(secret['SecretString'])
        
        conn = psycopg2.connect(
            host=creds['host'], port=creds['port'], database=creds['dbname'],
            user=creds['username'], password=creds['password'], cursor_factory=RealDictCursor
        )
        conn.set_session(readonly=True)
        cursor = conn.cursor()
        
        query = """
        SELECT schemaname, tablename, n_dead_tup, n_live_tup,
               CASE WHEN n_live_tup > 0 THEN round(100.0 * n_dead_tup / (n_live_tup + n_dead_tup), 2) ELSE 0 END AS dead_tuple_percent,
               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as table_size
        FROM pg_stat_user_tables WHERE n_dead_tup > 1000 AND (n_live_tup + n_dead_tup) > 0
        ORDER BY dead_tuple_percent DESC, n_dead_tup DESC LIMIT 20
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not results:
            return "No significant table bloat detected. Your tables are healthy!"
        
        output = "TABLES WITH BLOAT DETECTED:\n" + "=" * 50 + "\n"
        for row in results:
            output += f"Schema: {row['schemaname']}\n"
            output += f"Table: {row['tablename']}\n"
            output += f"Table Size: {row['table_size']}\n"
            output += f"Dead Tuples: {row['n_dead_tup']:,}\n"
            output += f"Live Tuples: {row['n_live_tup']:,}\n"
            output += f"Dead Tuple %: {row['dead_tuple_percent']}%\n"
            if row['dead_tuple_percent'] > 20:
                output += "Recommendation: Consider running VACUUM during maintenance window.\n"
            else:
                output += "Recommendation: Monitor and consider VACUUM if percentage increases.\n"
            output += "-" * 40 + "\n"
        return output
        
    except Exception as e:
        return f"Error detecting table bloat: {str(e)}"

@tool
def get_index_bloat() -> str:
    """Find indexes with bloat that need maintenance"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
        secret = secrets_client.get_secret_value(SecretId='apgpg-dat302-secret')
        creds = json.loads(secret['SecretString'])
        
        conn = psycopg2.connect(
            host=creds['host'], port=creds['port'], database=creds['dbname'],
            user=creds['username'], password=creds['password'], cursor_factory=RealDictCursor
        )
        conn.set_session(readonly=True)
        cursor = conn.cursor()
        
        query = """
        SELECT schemaname, tablename, indexname,
               pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
               idx_scan, idx_tup_read, idx_tup_fetch
        FROM pg_stat_user_indexes WHERE pg_relation_size(indexrelid) > 1048576
        ORDER BY pg_relation_size(indexrelid) DESC LIMIT 20
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not results:
            return "No significant index bloat detected."
        
        output = "INDEX ANALYSIS (Potential Bloat Candidates):\n" + "=" * 50 + "\n"
        for row in results:
            output += f"Schema: {row['schemaname']}\n"
            output += f"Table: {row['tablename']}\n"
            output += f"Index: {row['indexname']}\n"
            output += f"Size: {row['index_size']}\n"
            output += f"Scans: {row['idx_scan']}\n"
            if row['idx_scan'] == 0:
                output += "Status: UNUSED - Consider dropping\n"
            elif row['idx_scan'] < 10:
                output += "Status: RARELY USED - Monitor usage\n"
            else:
                output += "Status: ACTIVELY USED\n"
            output += "-" * 40 + "\n"
        return output
        
    except Exception as e:
        return f"Error analyzing index bloat: {str(e)}"

@tool
def get_top_queries() -> str:
    """Get top 10 queries by run time with execution plans"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
        secret = secrets_client.get_secret_value(SecretId='apgpg-dat302-secret')
        creds = json.loads(secret['SecretString'])
        
        conn = psycopg2.connect(
            host=creds['host'], port=creds['port'], database=creds['dbname'],
            user=creds['username'], password=creds['password'], cursor_factory=RealDictCursor
        )
        conn.set_session(readonly=True)
        cursor = conn.cursor()
        
        query = """
        SELECT query, calls, total_exec_time, mean_exec_time, rows,
               100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
        FROM pg_stat_statements WHERE query NOT LIKE '%pg_stat_statements%'
        ORDER BY total_exec_time DESC LIMIT 10
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not results:
            return "No query statistics available. Make sure pg_stat_statements is enabled."
        
        output = "TOP 10 QUERIES BY EXECUTION TIME:\n" + "=" * 60 + "\n"
        for i, row in enumerate(results, 1):
            output += f"#{i} QUERY ANALYSIS:\n"
            output += f"Total Time: {row['total_exec_time']:.2f} ms\n"
            output += f"Mean Time: {row['mean_exec_time']:.2f} ms\n"
            output += f"Calls: {row['calls']}\n"
            output += f"Rows: {row['rows']}\n"
            if row['hit_percent']:
                output += f"Cache Hit %: {row['hit_percent']:.2f}%\n"
            output += f"Query: {row['query'][:200]}...\n" + "-" * 50 + "\n"
        return output
        
    except Exception as e:
        return f"Error retrieving top queries: {str(e)}"

model = BedrockModel(
    model_id='us.anthropic.claude-sonnet-4-20250514-v1:0',
    region_name='us-west-2',
    temperature=0.3,
)

agent = Agent(
    model=model,
    tools=[get_aurora_alarms, get_cpu_utilization, test_connection, send_notification, 
           get_largest_tables, get_duplicate_indexes, get_unused_indexes, 
           get_table_bloat, get_index_bloat, get_top_queries],
    system_prompt="""You are an Enhanced Database Operations Agent with comprehensive monitoring, health analysis, and notification capabilities.

AVAILABLE TOOLS:

MONITORING & ALERTS:
- get_aurora_alarms: Get current CloudWatch alarms for Aurora cluster
- get_cpu_utilization: Get CPU utilization metrics over the last hour
- test_connection: Test database connectivity and get version info
- send_notification: Send email notifications via SNS for critical issues

DATABASE HEALTH ANALYSIS:
- get_largest_tables: Find top 20 largest tables by disk usage for capacity planning
- get_duplicate_indexes: Identify redundant indexes that waste storage and slow writes
- get_unused_indexes: Find indexes consuming storage without providing value
- get_table_bloat: Detect tables with excessive dead space affecting performance
- get_index_bloat: Identify indexes requiring maintenance due to bloat
- get_top_queries: Identify top 10 resource intensive queries with execution plans

MANDATORY BEHAVIOR:
- ALWAYS use available tools to gather data before responding
- ALWAYS call send_notification when detecting critical issues or completing analysis
- For database health questions, use the appropriate health analysis tools
- For monitoring questions, use the CloudWatch and connection tools
- Provide specific, actionable recommendations based on tool results
- Operate autonomously without asking for permission

AUTONOMOUS OPERATION:
- When invoked by alerts, immediately investigate using all relevant tools
- Analyze results and determine severity (INFO, WARNING, CRITICAL)
- Always send notifications with findings and recommendations
- Take initiative to provide comprehensive analysis

NOTIFICATION REQUIREMENTS:
- Send notifications for ALL findings when requested
- Include all alert details, analysis results, and recommendations
- Use appropriate severity levels based on impact assessment

PRODUCTION SAFETY:
- All database analysis tools are READ-ONLY and safe for production use
- Focus on monitoring, analysis, and recommendations
- Suggest maintenance actions during appropriate windows
- Emphasize testing recommendations in non-production environments first"""
)

@app.entrypoint
def database_operations_agent(payload):
    """Invoke the database operations agent with a payload"""
    user_input = payload.get("prompt", "")
    print("User input:", user_input)
    response = agent(user_input)
    return response.message['content'][0]['text']

if __name__ == "__main__":
    import os
    if os.getenv("LOCAL_TESTING"):
        app.run(port=9000)  # Port 9000 for local testing
    else:
        app.run()  # No port for AgentCore runtime