#!/usr/bin/env python3
"""
CloudWatch MCP Server - Simplified for FastMCP
Provides real CloudWatch metrics and alarms - No Mock Data (Project Rule #1)
"""

from fastmcp import FastMCP
from typing import Dict, Any
import boto3
import logging
import sys
import os
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get AWS region from environment variable
AWS_REGION = os.environ.get('AWSREGION', 'us-west-2')

# Create CloudWatch MCP server instance
mcp = FastMCP("CloudWatch Monitoring Server")

# Add MCP prompts to guide LLM usage
@mcp.prompt()
def database_performance_analysis() -> str:
    """
    Comprehensive Aurora database performance analysis using CloudWatch metrics
    
    Use this prompt when you need to analyze Aurora PostgreSQL performance issues,
    monitor database health, or investigate performance bottlenecks.
    """
    return """
# Aurora Database Performance Analysis Guide

## When to Use CloudWatch Tools

### 🚨 **Immediate Issues (Use First)**
- `test_cloudwatch_connection()` - Verify AWS connectivity
- `get_aurora_alarms()` - Check for active alerts
- `get_alarms_last_hour()` - Recent alarm activity

### 📊 **Performance Monitoring**
- `get_cpu_utilization()` - CPU usage patterns and spikes
- `get_database_connections()` - Connection count and trends
- `get_aurora_db_load_metrics()` - Database load analysis
- `get_performance_metrics()` - I/O latency and IOPS

### 🔍 **Deep Analysis**
- `get_comprehensive_insights()` - Overall health scoring
- `get_aurora_cluster_metrics()` - Cluster-level metrics
- `get_aurora_instance_metrics()` - Instance-level details
- `get_performance_insights_data()` - Performance Insights integration

## Analysis Workflow

1. **Health Check**: Start with `test_cloudwatch_connection()` and `get_aurora_alarms()`
2. **Resource Analysis**: Check `get_cpu_utilization()` and `get_database_connections()`
3. **Performance Deep Dive**: Use `get_performance_metrics()` and `get_aurora_db_load_metrics()`
4. **Comprehensive Report**: Finish with `get_comprehensive_insights()`

## Key Metrics to Monitor

- **CPU Utilization**: Should be < 80% average
- **Database Connections**: Monitor for connection leaks
- **Database Load**: High load indicates resource contention
- **I/O Latency**: ReadLatency/WriteLatency should be < 20ms
- **Alarms**: Any ALARM state requires immediate attention

## Common Issues to Investigate

- High CPU → Check for inefficient queries
- High connections → Look for connection pool issues  
- High database load → Investigate wait events
- I/O latency spikes → Check for storage bottlenecks
"""

@mcp.prompt()
def alarm_investigation() -> str:
    """
    Aurora CloudWatch alarm investigation and troubleshooting
    
    Use this prompt when you need to investigate CloudWatch alarms,
    understand alarm patterns, or troubleshoot alert-related issues.
    """
    return """
# CloudWatch Alarm Investigation Guide

## Alarm Investigation Workflow

### Step 1: Get Current Alarm Status
```
Use: get_aurora_alarms()
Purpose: Get all Aurora-specific alarms and their current states
Look for: ALARM state, threshold breaches, state reasons
```

### Step 2: Check Recent Alarm Activity  
```
Use: get_alarms_last_hour()
Purpose: Get all alarms with recent state changes
Look for: Flapping alarms, new alarm states, patterns
```

### Step 3: Correlate with Metrics
```
Use: get_cpu_utilization() + get_database_connections()
Purpose: Understand what caused the alarm
Look for: Metric values near alarm thresholds
```

## Alarm Types and Actions

### **CPU Utilization Alarms**
- **Threshold**: Usually 80-90%
- **Investigation**: `get_cpu_utilization()` for trends
- **Next Steps**: Check for slow queries, inefficient indexes

### **Database Connection Alarms**
- **Threshold**: Usually 80% of max_connections
- **Investigation**: `get_database_connections()` for patterns
- **Next Steps**: Check connection pooling, connection leaks

### **Database Load Alarms**
- **Threshold**: Usually > number of vCPUs
- **Investigation**: `get_aurora_db_load_metrics()` for analysis
- **Next Steps**: Investigate wait events, query optimization

### **I/O Performance Alarms**
- **Threshold**: ReadLatency/WriteLatency > 20ms
- **Investigation**: `get_performance_metrics()` for I/O analysis
- **Next Steps**: Check storage performance, query patterns

## Alarm State Meanings

- **OK**: Metric is within normal range
- **ALARM**: Threshold breached, requires attention
- **INSUFFICIENT_DATA**: Not enough data points (check metric collection)
"""

@mcp.prompt()
def cloudwatch_tool_selection() -> str:
    """
    Smart tool selection guide for CloudWatch MCP server
    
    Use this prompt to understand which CloudWatch tools to use for different
    database analysis scenarios and troubleshooting situations.
    """
    return """
# CloudWatch Tool Selection Guide

## 🎯 **Quick Tool Selection by Scenario**

### **"Database is slow"**
1. `get_cpu_utilization()` - Check for CPU bottlenecks
2. `get_aurora_db_load_metrics()` - Analyze database load
3. `get_performance_metrics()` - Check I/O latency and IOPS
4. `get_database_connections()` - Verify connection patterns

### **"Getting alerts"**
1. `get_aurora_alarms()` - Current Aurora-specific alarms
2. `get_alarms_last_hour()` - Recent alarm activity across all services
3. `get_comprehensive_insights()` - Overall health assessment

### **"Need health check"**
1. `test_cloudwatch_connection()` - Verify monitoring connectivity
2. `get_comprehensive_insights()` - Overall health score
3. `get_aurora_cluster_metrics()` - Cluster-level health
4. `get_aurora_instance_metrics()` - Instance-level details

### **"Planning capacity"**
1. `get_cpu_utilization()` - CPU trends and peaks
2. `get_database_connections()` - Connection usage patterns
3. `get_performance_metrics()` - I/O performance trends
4. `get_aurora_db_load_metrics()` - Load analysis over time

### **"Investigating performance"**
1. `get_performance_insights_data()` - Detailed performance analysis
2. `get_aurora_db_load_metrics()` - Database load breakdown
3. `get_performance_metrics()` - I/O and latency metrics
4. `get_cpu_utilization()` - CPU usage patterns

## 🔧 **Tool Categories**

### **Connection & Health**
- `test_cloudwatch_connection()` - Basic connectivity test
- `get_comprehensive_insights()` - Overall health scoring

### **Alerting & Monitoring**  
- `get_aurora_alarms()` - Aurora-specific alarms
- `get_alarms_last_hour()` - All recent alarm activity

### **Performance Analysis**
- `get_cpu_utilization()` - CPU metrics with historical data
- `get_database_connections()` - Connection count trends
- `get_aurora_db_load_metrics()` - Database load analysis
- `get_performance_metrics()` - I/O latency and IOPS
- `get_performance_insights_data()` - Advanced performance data

### **Infrastructure Monitoring**
- `get_aurora_cluster_metrics()` - Cluster-level metrics
- `get_aurora_instance_metrics()` - Instance-level information

## ⚡ **Best Practices**

1. **Always start with connectivity**: Use `test_cloudwatch_connection()` first
2. **Check alarms early**: Use `get_aurora_alarms()` to identify immediate issues
3. **Use time parameters**: Most tools accept `hours_back` parameter (default: 1 hour)
4. **Combine tools**: Use multiple tools for comprehensive analysis
5. **Follow the data**: Let metrics guide which tools to use next

## 📊 **Metric Interpretation**

### **CPU Utilization**
- < 50%: Normal operation
- 50-80%: Monitor closely
- > 80%: Investigation needed

### **Database Connections**
- Steady count: Normal
- Rapid growth: Potential leak
- Near max: Scaling needed

### **Database Load**
- < vCPU count: Good
- 1-2x vCPUs: Acceptable
- > 2x vCPUs: Optimization needed

### **I/O Latency**
- < 10ms: Excellent
- 10-20ms: Good
- > 20ms: Investigation needed
"""

@mcp.prompt()
def capacity_planning() -> str:
    """
    Aurora capacity planning and resource optimization using CloudWatch data
    
    Use this prompt when you need to plan for capacity, optimize resources,
    or understand usage patterns for scaling decisions.
    """
    return """
# Aurora Capacity Planning Guide

## Capacity Analysis Workflow

### Step 1: Baseline Resource Usage
```
Tools: get_cpu_utilization(), get_database_connections(), get_aurora_db_load_metrics()
Purpose: Establish current resource consumption patterns
Timeline: Analyze 24-hour and 7-day trends
```

### Step 2: Performance Trend Analysis
```
Tools: get_performance_metrics(), get_aurora_cluster_metrics()
Purpose: Identify performance trends and bottlenecks
Look for: Increasing latency, I/O saturation, connection growth
```

### Step 3: Health and Efficiency Assessment
```
Tools: get_comprehensive_insights(), get_aurora_instance_metrics()
Purpose: Overall system health and resource efficiency
Metrics: Health scores, resource utilization ratios
```

## Capacity Planning Metrics

### **CPU Capacity**
- **Current**: Average and peak CPU utilization
- **Trend**: Week-over-week growth patterns
- **Threshold**: Plan scaling at 70% sustained usage
- **Action**: Consider instance class upgrade or read replicas

### **Connection Capacity**
- **Current**: Peak concurrent connections
- **Trend**: Connection growth rate
- **Threshold**: Plan scaling at 80% of max_connections
- **Action**: Optimize connection pooling or increase limits

### **I/O Capacity**
- **Current**: IOPS and throughput utilization
- **Trend**: I/O growth patterns
- **Threshold**: Latency > 10ms sustained
- **Action**: Consider storage optimization or scaling

### **Memory Capacity**
- **Current**: Database load relative to vCPUs
- **Trend**: Memory pressure indicators
- **Threshold**: Database load > 2x vCPUs
- **Action**: Instance memory upgrade consideration

## Scaling Recommendations

### **Scale Up Scenarios**
- CPU utilization > 70% sustained
- Database load > 1.5x vCPUs consistently
- I/O latency > 15ms average

### **Scale Out Scenarios**  
- Read-heavy workload with high connection count
- Geographic distribution requirements
- High availability requirements

### **Optimization Opportunities**
- Connection count spikes → Connection pooling
- CPU spikes → Query optimization needed
- I/O latency → Index optimization potential
"""

def get_resource_id_for_instance(db_instance_identifier: str) -> str:
    """
    Get Performance Insights resource ID for a DB instance
    """
    try:
        rds_client = boto3.client('rds', region_name=AWS_REGION)
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier=db_instance_identifier
        )
        
        db_instance = response['DBInstances'][0]
        resource_id = db_instance.get('DbiResourceId')
        
        if not resource_id:
            raise Exception(f"No DbiResourceId found for instance: {db_instance_identifier}")
            
        return resource_id
        
    except Exception as e:
        logger.error(f"Error getting resource ID: {str(e)}")
        raise Exception(f"Resource ID retrieval failed: {e}")

def get_aurora_cluster_id() -> str:
    """
    Get Aurora cluster identifier from Secrets Manager (Project Rule #2)
    
    WHAT IT IS:
    This function retrieves the Aurora cluster identifier directly from the
    dbClusterIdentifier field in AWS Secrets Manager. No URL parsing needed.
    
    WHERE WE USE IT:
    - CloudWatch alarm queries: Need cluster ID for alarm filtering
    - Metric queries: Required for cluster-level CloudWatch metrics
    - Alarm history: Filter alarms specific to our Aurora cluster
    
    Returns:
        str: Aurora cluster identifier from Secrets Manager
        
    Raises:
        Exception: If Secrets Manager access fails or no cluster ID found
    """
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config.secrets import SecretsManager
        
        secrets_manager = SecretsManager()
        config = secrets_manager.get_aurora_config()
        
        # Get cluster identifier directly from dbClusterIdentifier field
        cluster_id = config.get('dbClusterIdentifier')
        if not cluster_id:
            raise Exception("No dbClusterIdentifier found in Secrets Manager configuration")
        
        # Debug: Log the actual cluster ID value
        logger.info(f"DEBUG: Raw cluster ID from secrets: '{cluster_id}'")
        logger.info(f"DEBUG: Cluster ID type: {type(cluster_id)}")
        logger.info(f"Aurora cluster ID retrieved from Secrets Manager: {cluster_id}")
        return cluster_id
        
    except Exception as e:
        logger.error(f"Failed to get Aurora cluster ID from Secrets Manager: {e}")
        raise Exception(f"Secrets Manager error: {e}")

@mcp.tool()
def test_cloudwatch_connection() -> Dict[str, Any]:
    """Test CloudWatch service connection"""
    try:
        client = boto3.client('cloudwatch', region_name=AWS_REGION)
        
        # Simple test - list metric namespaces
        response = client.list_metrics(Namespace='AWS/RDS', MaxRecords=1)
        
        return {
            "status": "success",
            "message": "CloudWatch connection successful",
            "region": AWS_REGION
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_aurora_alarms() -> Dict[str, Any]:
    """Get real CloudWatch alarms for Aurora cluster"""
    try:
        client = boto3.client('cloudwatch', region_name=AWS_REGION)
        cluster_id = get_aurora_cluster_id()
        
        # Get alarms with Aurora cluster prefix
        response = client.describe_alarms(AlarmNamePrefix=cluster_id, MaxRecords=20)
        
        alarms = []
        for alarm in response.get('MetricAlarms', []):
            alarms.append({
                'alarm_name': alarm['AlarmName'],
                'state': alarm['StateValue'],
                'metric_name': alarm['MetricName'],
                'threshold': alarm.get('Threshold', 0),
                'comparison': alarm.get('ComparisonOperator', ''),
                'state_reason': alarm['StateReason']
            })
        
        return {"status": "success", "data": alarms, "count": len(alarms), "cluster_id": cluster_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_database_connections() -> Dict[str, Any]:
    """Get real database connection count from CloudWatch"""
    try:
        client = boto3.client('cloudwatch', region_name=AWS_REGION)
        cluster_id = get_aurora_cluster_id()
        
        # Get recent connection metrics
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        response = client.get_metric_statistics(
            Namespace='AWS/RDS', MetricName='DatabaseConnections',
            Dimensions=[{'Name': 'DBClusterIdentifier', 'Value': cluster_id}],
            StartTime=start_time, EndTime=end_time, Period=300, Statistics=['Average']
        )
        
        datapoints = response.get('Datapoints', [])
        current_connections = datapoints[-1]['Average'] if datapoints else 0
        
        return {
            "status": "success",
            "current_connections": int(current_connections),
            "cluster_id": cluster_id,
            "datapoints_count": len(datapoints)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_cpu_utilization() -> Dict[str, Any]:
    """Get CPU utilization metrics from CloudWatch using instance identifier"""
    try:
        client = boto3.client('cloudwatch', region_name=AWS_REGION)
        
        # Get instance identifier directly from Secrets Manager
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config.secrets import SecretsManager
        
        secrets_manager = SecretsManager()
        config = secrets_manager.get_aurora_config()
        
        instance_id = config.get('dbInstanceIdentifier')
        if not instance_id:
            return {"status": "error", "error": "No dbInstanceIdentifier found in Secrets Manager"}
        
        logger.info(f"Using instance identifier: {instance_id}")
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        response = client.get_metric_statistics(
            Namespace='AWS/RDS', MetricName='CPUUtilization',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': instance_id}],
            StartTime=start_time, EndTime=end_time, Period=300, Statistics=['Average', 'Maximum']
        )
        
        datapoints = response.get('Datapoints', [])
        
        metrics = []
        for point in sorted(datapoints, key=lambda x: x['Timestamp']):
            metrics.append({
                'timestamp': point['Timestamp'].isoformat(),
                'average_cpu': round(point['Average'], 2),
                'maximum_cpu': round(point['Maximum'], 2)
            })
        
        current_cpu = metrics[-1]['average_cpu'] if metrics else 0
        
        return {
            "status": "success",
            "current_cpu_percent": current_cpu,
            "instance_id": instance_id,
            "metrics": metrics,
            "count": len(metrics)
        }
    except Exception as e:
        logger.error(f"CPU utilization error: {str(e)}")
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_alarms_last_hour() -> Dict[str, Any]:
    """
    Get all CloudWatch alarms with their current states
    
    Returns:
        Dict[str, Any]: All alarms with current states and details
    """
    try:
        client = boto3.client('cloudwatch', region_name=AWS_REGION)
        cluster_id = get_aurora_cluster_id()
        
        # Get all alarms using pagination
        paginator = client.get_paginator('describe_alarms')
        all_alarms = []
        
        for page in paginator.paginate():
            all_alarms.extend(page['MetricAlarms'])
        
        # Process all alarms
        processed_alarms = []
        aurora_alarms = []
        
        for alarm in all_alarms:
            # Create alarm data structure
            alarm_data = {
                'alarm_name': alarm['AlarmName'],
                'state': alarm['StateValue'],
                'state_reason': alarm['StateReason'],
                'state_updated': alarm['StateUpdatedTimestamp'].isoformat(),
                'metric_name': alarm.get('MetricName', ''),
                'namespace': alarm.get('Namespace', ''),
                'threshold': alarm.get('Threshold', ''),
                'comparison_operator': alarm.get('ComparisonOperator', ''),
                'dimensions': alarm.get('Dimensions', [])
            }
            
            processed_alarms.append(alarm_data)
            
            # Track Aurora-specific alarms
            if cluster_id in alarm['AlarmName'] or 'aurora' in alarm['AlarmName'].lower():
                aurora_alarms.append(alarm_data)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "cluster_id": cluster_id,
            "total_alarms": len(all_alarms),
            "aurora_specific_alarms": len(aurora_alarms),
            "all_alarms": processed_alarms,
            "aurora_alarms": aurora_alarms
        }
        
    except Exception as e:
        logger.error(f"Error in get_alarms_last_hour: {str(e)}")
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_aurora_db_load_metrics(hours_back: int = 1) -> Dict[str, Any]:
    """
    Get comprehensive Aurora DB load analysis metrics from CloudWatch
    
    WHAT IT IS:
    Retrieves multiple related Aurora performance metrics including database load,
    CPU breakdown, connections, and memory usage for comprehensive analysis.
    
    WHERE WE USE IT:
    - Database performance analysis and bottleneck identification
    - Load pattern analysis and capacity planning
    - Performance troubleshooting with detailed metric breakdown
    
    Args:
        hours_back (int): Hours of historical data to retrieve (default: 1)
        
    Returns:
        Dict[str, Any]: Comprehensive metrics with timestamps and values
    """
    try:
        client = boto3.client('cloudwatch', region_name=AWS_REGION)
        cluster_id = get_aurora_cluster_id()
        
        # Get instance identifier dynamically
        rds_client = boto3.client('rds', region_name=AWS_REGION)
        clusters = rds_client.describe_db_clusters(DBClusterIdentifier=cluster_id)
        
        if not clusters['DBClusters'] or not clusters['DBClusters'][0]['DBClusterMembers']:
            return {"status": "error", "error": "No instances found in cluster"}
        
        # Get the first available instance
        instance_id = clusters['DBClusters'][0]['DBClusterMembers'][0]['DBInstanceIdentifier']
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)
        
        # Comprehensive metrics for DB load analysis
        metrics_to_fetch = [
            'DatabaseConnections',
            'DatabaseLoad', 
            'DatabaseLoadCPU',
            'DatabaseLoadNonCPU',
            'CPUUtilization',
            'FreeableMemory'
        ]
        
        # Build metric queries for batch retrieval
        metric_queries = []
        for i, metric_name in enumerate(metrics_to_fetch):
            metric_queries.append({
                'Id': f'metric_{i}',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': metric_name,
                        'Dimensions': [
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': instance_id
                            }
                        ]
                    },
                    'Period': 300,  # 5 minutes
                    'Stat': 'Average'
                },
                'ReturnData': True
            })
        
        # Get all metrics in single API call
        response = client.get_metric_data(
            MetricDataQueries=metric_queries,
            StartTime=start_time,
            EndTime=end_time
        )
        
        # Process response into structured format
        metrics_data = {}
        for result in response['MetricDataResults']:
            metric_id = result['Id']
            metric_name = metrics_to_fetch[int(metric_id.split('_')[1])]
            metrics_data[metric_name] = {
                'current_value': result['Values'][-1] if result['Values'] else 0,
                'timestamps': [ts.isoformat() for ts in result['Timestamps']],
                'values': result['Values'],
                'status': result['StatusCode']
            }
        
        return {
            "status": "success",
            "instance_id": instance_id,
            "cluster_id": cluster_id,
            "metrics": metrics_data,
            "datapoints_count": len(response['MetricDataResults']),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Aurora DB load metrics error: {str(e)}")
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_performance_metrics(hours_back: int = 1) -> Dict[str, Any]:
    """
    Retrieve Database Performance Analysis metrics
    """
    try:
        # Get instance identifier directly from Secrets Manager
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config.secrets import SecretsManager
        
        secrets_manager = SecretsManager()
        config = secrets_manager.get_aurora_config()
        
        db_instance_identifier = config.get('dbInstanceIdentifier')
        if not db_instance_identifier:
            return {"status": "error", "error": "No dbInstanceIdentifier found in Secrets Manager"}
        
        client = boto3.client('cloudwatch', region_name=AWS_REGION)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)
        
        performance_metrics = [
            'ReadLatency',
            'WriteLatency',
            'ReadThroughput',
            'WriteThroughput',
            'ReadIOPS',
            'WriteIOPS',
            'NetworkReceiveThroughput',
            'NetworkTransmitThroughput',
            'CommitLatency',
            'SelectLatency',
            'InsertLatency',
            'UpdateLatency',
            'DeleteLatency'
        ]
        
        metric_queries = []
        for i, metric_name in enumerate(performance_metrics):
            metric_queries.append({
                'Id': f'perf_{i}',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': metric_name,
                        'Dimensions': [
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': db_instance_identifier
                            }
                        ]
                    },
                    'Period': 300,
                    'Stat': 'Average'
                },
                'ReturnData': True
            })
        
        response = client.get_metric_data(
            MetricDataQueries=metric_queries,
            StartTime=start_time,
            EndTime=end_time
        )
        
        performance_data = {}
        for result in response['MetricDataResults']:
            metric_id = result['Id']
            metric_name = performance_metrics[int(metric_id.split('_')[1])]
            performance_data[metric_name] = {
                'timestamps': [ts.isoformat() for ts in result['Timestamps']],
                'values': result['Values'],
                'status': result['StatusCode']
            }
        
        return {
            "status": "success",
            "instance_id": db_instance_identifier,
            "metrics": performance_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}")
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_performance_insights_data(hours_back: int = 1) -> Dict[str, Any]:
    """
    Retrieve Performance Insights metrics for detailed analysis
    """
    try:
        # Get instance identifier from Secrets Manager
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config.secrets import SecretsManager
        
        secrets_manager = SecretsManager()
        config = secrets_manager.get_aurora_config()
        
        db_instance_identifier = config.get('dbInstanceIdentifier')
        if not db_instance_identifier:
            return {"status": "error", "error": "No dbInstanceIdentifier found in Secrets Manager"}
        
        # Get Performance Insights resource ID
        resource_id = get_resource_id_for_instance(db_instance_identifier)
        
        pi_client = boto3.client('pi', region_name=AWS_REGION)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)
        
        # Get DB Load with wait events breakdown
        db_load_response = pi_client.get_resource_metrics(
            ServiceType='RDS',
            Identifier=resource_id,
            MetricQueries=[
                {
                    'Metric': 'db.load.avg',
                    'GroupBy': {
                        'Group': 'db.wait_event'
                    }
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            PeriodInSeconds=300
        )
        
        # Get top SQL statements
        top_sql_response = pi_client.get_dimension_key_details(
            ServiceType='RDS',
            Identifier=resource_id,
            Group='db.sql_tokenized.statement',
            GroupIdentifier='top-sql',
            RequestedDimensions=['db.sql_tokenized.statement']
        )
        
        # Get top wait events
        wait_events_response = pi_client.describe_dimension_keys(
            ServiceType='RDS',
            Identifier=resource_id,
            Metric='db.load.avg',
            GroupBy={'Group': 'db.wait_event'},
            StartTime=start_time,
            EndTime=end_time,
            MaxResults=10
        )
        
        return {
            "status": "success",
            "resource_id": resource_id,
            "instance_id": db_instance_identifier,
            "db_load_metrics": db_load_response,
            "top_sql": top_sql_response,
            "wait_events": wait_events_response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching Performance Insights data: {str(e)}")
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_aurora_cluster_metrics(hours_back: int = 1) -> Dict[str, Any]:
    """
    Get comprehensive Aurora cluster-level metrics from CloudWatch
    
    WHAT IT IS:
    Retrieves Aurora cluster-specific metrics including storage, I/O operations,
    capacity, and backup storage for cluster-level performance analysis.
    
    WHERE WE USE IT:
    - Cluster storage and capacity planning
    - I/O performance analysis at cluster level
    - Backup storage cost monitoring
    - Serverless capacity tracking
    
    Args:
        hours_back (int): Hours of historical data to retrieve (default: 1)
        
    Returns:
        Dict[str, Any]: Cluster metrics with timestamps and values
    """
    try:
        client = boto3.client('cloudwatch', region_name=AWS_REGION)
        cluster_id = get_aurora_cluster_id()
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)
        
        # Aurora cluster-specific metrics
        cluster_metrics = [
            'VolumeReadIOPs',
            'VolumeWriteIOPs', 
            'VolumeBytesUsed',
            'SnapshotStorageUsed',
            'TotalBackupStorageBilled',
            'DatabaseConnections',
            'DatabaseLoad'
        ]
        
        # Build metric queries for batch retrieval
        metric_queries = []
        for i, metric_name in enumerate(cluster_metrics):
            metric_queries.append({
                'Id': f'cluster_{i}',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': metric_name,
                        'Dimensions': [
                            {
                                'Name': 'DBClusterIdentifier',
                                'Value': cluster_id
                            }
                        ]
                    },
                    'Period': 300,
                    'Stat': 'Average'
                },
                'ReturnData': True
            })
        
        # Get all cluster metrics in single API call
        response = client.get_metric_data(
            MetricDataQueries=metric_queries,
            StartTime=start_time,
            EndTime=end_time
        )
        
        # Process response into structured format
        cluster_data = {}
        for result in response['MetricDataResults']:
            metric_id = result['Id']
            metric_name = cluster_metrics[int(metric_id.split('_')[1])]
            cluster_data[metric_name] = {
                'current_value': result['Values'][-1] if result['Values'] else 0,
                'timestamps': [ts.isoformat() for ts in result['Timestamps']],
                'values': result['Values'],
                'status': result['StatusCode']
            }
        
        return {
            "status": "success",
            "cluster_id": cluster_id,
            "metrics": cluster_data,
            "datapoints_count": len(response['MetricDataResults']),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Aurora cluster metrics error: {str(e)}")
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_aurora_instance_metrics(hours_back: int = 1) -> Dict[str, Any]:
    """Get Aurora instance-level metrics"""
    try:
        client = boto3.client('cloudwatch', region_name=AWS_REGION)
        cluster_id = get_aurora_cluster_id()
        
        rds_client = boto3.client('rds', region_name=AWS_REGION)
        cluster_response = rds_client.describe_db_clusters(DBClusterIdentifier=cluster_id)
        
        if not cluster_response['DBClusters']:
            return {"status": "error", "error": "Cluster not found"}
        
        instance_count = len(cluster_response['DBClusters'][0]['DBClusterMembers'])
        return {"status": "success", "cluster_id": cluster_id, "instance_count": instance_count}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_comprehensive_insights(hours_back: int = 1) -> Dict[str, Any]:
    """Get comprehensive Aurora insights"""
    try:
        cpu_metrics = get_cpu_utilization()
        connection_metrics = get_database_connections()
        alarms = get_aurora_alarms()
        
        health_score = 100
        if cpu_metrics.get('status') == 'success':
            cpu = cpu_metrics.get('current_cpu_percent', 0)
            if cpu > 80: health_score -= 20
        
        insights = {
            "overall_health_score": max(0, health_score),
            "cpu_utilization": cpu_metrics.get('current_cpu_percent', 0),
            "active_connections": connection_metrics.get('current_connections', 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {"status": "success", "data": insights, "cluster_id": get_aurora_cluster_id()}
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    print("🚀 Starting CloudWatch MCP Server (Simplified)...")
    print("📊 Available tools: test_cloudwatch_connection, get_aurora_alarms, get_database_connections, get_cpu_utilization, get_alarms_last_hour")
    print("🌐 Starting on http://localhost:8082/mcp")
    
    try:
        mcp.run(transport="streamable-http", port=8082)
    except KeyboardInterrupt:
        print("\n👋 CloudWatch MCP Server stopped")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        import traceback
        traceback.print_exc()

