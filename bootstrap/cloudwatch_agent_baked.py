from strands import Agent, tool
from strands.models import BedrockModel
import boto3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError

# CloudWatch connection helper
def get_cloudwatch_clients():
    """Get CloudWatch clients"""
    region_name = os.getenv('AWS_REGION', 'us-west-2')
    try:
        logs_client = boto3.client('logs', region_name=region_name)
        cloudwatch_client = boto3.client('cloudwatch', region_name=region_name)
        return logs_client, cloudwatch_client
    except Exception as e:
        raise Exception(f"Error connecting to CloudWatch: {str(e)}")

# Define the AI model
model = BedrockModel(
    model_id=os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0'),
    region_name=os.getenv('AWS_REGION', 'us-west-2'),
    temperature=0.3
)

@tool
def list_log_groups(limit: int = 50) -> str:
    """List CloudWatch log groups"""
    try:
        if limit > 100:
            limit = 100
        elif limit < 1:
            limit = 50
            
        logs_client, _ = get_cloudwatch_clients()
        response = logs_client.describe_log_groups(limit=limit)
        log_groups = response.get('logGroups', [])
        
        results = []
        for lg in log_groups:
            results.append({
                'logGroupName': lg.get('logGroupName'),
                'creationTime': lg.get('creationTime'),
                'retentionInDays': lg.get('retentionInDays'),
                'storedBytes': lg.get('storedBytes', 0),
                'metricFilterCount': lg.get('metricFilterCount', 0)
            })
        
        return results
    except Exception as e:
        return f"Error listing log groups: {str(e)}"

@tool
def query_logs(log_group_name: str, query: str, hours_back: int = 1) -> str:
    """Query CloudWatch logs using CloudWatch Insights"""
    try:
        if hours_back > 24:
            hours_back = 24
        elif hours_back < 1:
            hours_back = 1
            
        logs_client, _ = get_cloudwatch_clients()
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        response = logs_client.start_query(
            logGroupName=log_group_name,
            startTime=int(start_time.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query,
            limit=100
        )
        
        query_id = response['queryId']
        
        import time
        time.sleep(2)
        
        results_response = logs_client.get_query_results(queryId=query_id)
        
        results = []
        for result in results_response.get('results', []):
            row = {}
            for field in result:
                row[field['field']] = field['value']
            results.append(row)
        
        return results
    except Exception as e:
        return f"Error querying logs: {str(e)}"

@tool
def discover_aurora_clusters() -> str:
    """Discover Aurora clusters in the region"""
    try:
        rds = boto3.client("rds", region_name=os.getenv('AWS_REGION', 'us-west-2'))
        response = rds.describe_db_clusters()
        clusters = []
        for cluster in response.get('DBClusters', []):
            if cluster.get('Engine', '').startswith('aurora'):
                clusters.append({
                    'clusterIdentifier': cluster.get('DBClusterIdentifier'),
                    'engine': cluster.get('Engine'),
                    'status': cluster.get('Status'),
                    'writerInstance': next(
                        (m["DBInstanceIdentifier"] for m in cluster.get("DBClusterMembers", []) if m.get("IsClusterWriter")),
                        None
                    )
                })
        return clusters
    except Exception as e:
        return f"Error discovering Aurora clusters: {str(e)}"

@tool
def get_metric_statistics(metric_name: str, namespace: str, statistic: str = 'Average', 
                         hours_back: int = 1, period: int = 300, 
                         cluster_identifier: Optional[str] = None) -> str:
    """Get CloudWatch metric statistics"""
    try:
        hours_back = max(1, min(hours_back, 24))
        period = max(60, period)
        _, cloudwatch_client = get_cloudwatch_clients()

        dimensions = None
        if namespace == "AWS/RDS" and not cluster_identifier:
            # Auto-discover first Aurora cluster
            try:
                rds = boto3.client("rds", region_name=os.getenv('AWS_REGION', 'us-west-2'))
                clusters = rds.describe_db_clusters()["DBClusters"]
                aurora_cluster = next((c for c in clusters if c.get('Engine', '').startswith('aurora')), None)
                if aurora_cluster:
                    cluster_identifier = aurora_cluster['DBClusterIdentifier']
            except Exception:
                pass
        
        if namespace == "AWS/RDS" and cluster_identifier:
            try:
                rds = boto3.client("rds", region_name=os.getenv('AWS_REGION', 'us-west-2'))
                cluster = rds.describe_db_clusters()["DBClusters"][0]
                writer = next(
                    (m["DBInstanceIdentifier"] for m in cluster["DBClusterMembers"] if m["IsClusterWriter"]),
                    None
                )
                if writer:
                    dimensions = [{"Name": "DBInstanceIdentifier", "Value": writer}]
                else:
                    dimensions = [{"Name": "DBClusterIdentifier", "Value": cluster_identifier}]
            except Exception:
                dimensions = [{"Name": "DBClusterIdentifier", "Value": cluster_identifier}]

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        request_params = {
            "Namespace": namespace,
            "MetricName": metric_name,
            "StartTime": start_time,
            "EndTime": end_time,
            "Period": period,
            "Statistics": [statistic]
        }

        if dimensions:
            request_params["Dimensions"] = dimensions

        response = cloudwatch_client.get_metric_statistics(**request_params)
        datapoints = sorted(response.get("Datapoints", []), key=lambda x: x["Timestamp"])

        results = [
            {
                "timestamp": dp["Timestamp"].isoformat(),
                "value": dp.get(statistic, 0),
                "unit": dp.get("Unit", "")
            }
            for dp in datapoints
        ]

        return results
    except Exception as e:
        return f"Error getting metric statistics: {str(e)}"

@tool
def list_alarms(state_value: Optional[str] = None, max_records: int = 50) -> str:
    """List CloudWatch alarms"""
    try:
        if max_records > 100:
            max_records = 100
        elif max_records < 1:
            max_records = 50
            
        _, cloudwatch_client = get_cloudwatch_clients()
        
        kwargs = {'MaxRecords': max_records}
        if state_value:
            kwargs['StateValue'] = state_value
        
        response = cloudwatch_client.describe_alarms(**kwargs)
        alarms = response.get('MetricAlarms', [])
        
        results = []
        for alarm in alarms:
            results.append({
                'alarmName': alarm.get('AlarmName'),
                'alarmDescription': alarm.get('AlarmDescription', ''),
                'stateValue': alarm.get('StateValue'),
                'stateReason': alarm.get('StateReason', ''),
                'metricName': alarm.get('MetricName'),
                'namespace': alarm.get('Namespace'),
                'statistic': alarm.get('Statistic'),
                'threshold': alarm.get('Threshold'),
                'comparisonOperator': alarm.get('ComparisonOperator'),
                'alarmArn': alarm.get('AlarmArn')
            })
        
        return results
    except Exception as e:
        return f"Error listing alarms: {str(e)}"

# Create the system prompt
system_prompt = """You are a CloudWatch monitoring assistant that specializes in AWS CloudWatch analysis.

You have these CloudWatch monitoring tools:
- discover_aurora_clusters: Automatically discover Aurora clusters in the region
- list_log_groups: List CloudWatch log groups with metadata
- query_logs: Query CloudWatch logs using CloudWatch Insights
- get_metric_statistics: Get CloudWatch metric statistics with auto-detection for Aurora
- list_alarms: List CloudWatch alarms with filtering options

Always provide actionable insights and recommendations based on the CloudWatch data you retrieve.
Keep responses clear and focused on practical monitoring and troubleshooting."""

# Create the agent
agent = Agent(
    system_prompt=system_prompt, 
    model=model, 
    tools=[
        discover_aurora_clusters,
        list_log_groups,
        query_logs,
        get_metric_statistics,
        list_alarms
    ]
)

if __name__ == "__main__":
    print("📊 CloudWatch Monitoring Agent Ready!")
    print("Ask questions about your CloudWatch logs, metrics, and alarms. Type 'exit' to quit.")
    print("\nExample questions:")
    print("- Discover my Aurora clusters")
    print("- List my CloudWatch log groups")
    print("- Query logs for errors in the last 2 hours")
    print("- Show CPU utilization for my Aurora cluster")
    print("- List all active alarms")

    while True:
        user_input = input("\n💬 Your question: ")
        if user_input.lower() in ['exit', 'quit']:
            print("👋 Goodbye!")
            break
        
        print("🔄 Analyzing...")
        try:
            response = agent(user_input)
            print(f"\n📊 Analysis: {response}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        print("-" * 50)
