"""
This script creates an MCP server that provides CloudWatch tools for:
1. Listing CloudWatch log groups
2. Querying CloudWatch logs
3. Getting CloudWatch metrics
4. Managing CloudWatch alarms

Key features:
- AWS SDK integration with boto3
- Proper error handling and logging
- Read-only operations for safety
"""

import json
import boto3
import logging
import os
from datetime import datetime, timedelta
from fastmcp import FastMCP
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cloudwatch_mcp_server')

class CloudWatchManager:
    def __init__(self, region_name: str = None):
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-west-2')
        self._logs_client = None
        self._cloudwatch_client = None
        
    def get_logs_client(self):
        """Get CloudWatch Logs client"""
        if not self._logs_client:
            try:
                self._logs_client = boto3.client('logs', region_name=self.region_name)
                logger.info(f"Successfully created CloudWatch Logs client for region: {self.region_name}")
            except NoCredentialsError:
                logger.error("AWS credentials not found")
                raise Exception("AWS credentials not configured")
            except Exception as e:
                logger.error(f"Error creating CloudWatch Logs client: {str(e)}")
                raise Exception(f"Error creating CloudWatch Logs client: {str(e)}")
        return self._logs_client
    
    def get_cloudwatch_client(self):
        """Get CloudWatch client"""
        if not self._cloudwatch_client:
            try:
                self._cloudwatch_client = boto3.client('cloudwatch', region_name=self.region_name)
                logger.info(f"Successfully created CloudWatch client for region: {self.region_name}")
            except NoCredentialsError:
                logger.error("AWS credentials not found")
                raise Exception("AWS credentials not configured")
            except Exception as e:
                logger.error(f"Error creating CloudWatch client: {str(e)}")
                raise Exception(f"Error creating CloudWatch client: {str(e)}")
        return self._cloudwatch_client

def start_cloudwatch_server(region_name: str = None, port: int = 8082):
    """
    Initialize and start a CloudWatch MCP server.
    
    Args:
        region_name: AWS region name (defaults to AWS_REGION env var)
        port: Port number for the MCP server (default: 8082)
    """
    # Create an MCP server
    mcp = FastMCP("CloudWatch Server")
    
    # Initialize CloudWatch manager
    cw_manager = CloudWatchManager(region_name)
    
    @mcp.tool()
    def list_log_groups(limit: int = 50) -> List[Dict[str, Any]]:
        """List CloudWatch log groups
        
        Args:
            limit: Maximum number of log groups to return (default: 50, max: 100)
        """
        try:
            if limit > 100:
                limit = 100
            elif limit < 1:
                limit = 50
                
            client = cw_manager.get_logs_client()
            
            response = client.describe_log_groups(limit=limit)
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
            
            logger.info(f"Found {len(results)} log groups")
            return results
            
        except Exception as e:
            logger.error(f"Failed to list log groups: {str(e)}")
            return [{"error": f"Failed to list log groups: {str(e)}"}]
    
    @mcp.tool()
    def query_logs(log_group_name: str, query: str, hours_back: int = 1) -> List[Dict[str, Any]]:
        """Query CloudWatch logs using CloudWatch Insights
        
        Args:
            log_group_name: Name of the log group to query
            query: CloudWatch Insights query string
            hours_back: Number of hours back to search (default: 1, max: 24)
        """
        try:
            if hours_back > 24:
                hours_back = 24
            elif hours_back < 1:
                hours_back = 1
                
            client = cw_manager.get_logs_client()
            
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)
            
            # Start the query
            response = client.start_query(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query,
                limit=100
            )
            
            query_id = response['queryId']
            
            # Wait for query to complete (simplified - in production, add proper polling)
            import time
            time.sleep(2)
            
            # Get query results
            results_response = client.get_query_results(queryId=query_id)
            
            results = []
            for result in results_response.get('results', []):
                row = {}
                for field in result:
                    row[field['field']] = field['value']
                results.append(row)
            
            logger.info(f"Query returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to query logs: {str(e)}")
            return [{"error": f"Failed to query logs: {str(e)}"}]
    
    @mcp.tool()
    def get_metric_statistics(metric_name: str, namespace: str, statistic: str = 'Average', 
                            hours_back: int = 1, period: int = 300) -> List[Dict[str, Any]]:
        """Get CloudWatch metric statistics
        
        Args:
            metric_name: Name of the metric
            namespace: AWS namespace (e.g., 'AWS/EC2', 'AWS/RDS')
            statistic: Statistic type (Average, Sum, Maximum, Minimum, SampleCount)
            hours_back: Number of hours back to retrieve data (default: 1, max: 24)
            period: Period in seconds (default: 300, min: 60)
        """
        try:
            if hours_back > 24:
                hours_back = 24
            elif hours_back < 1:
                hours_back = 1
                
            if period < 60:
                period = 60
                
            client = cw_manager.get_cloudwatch_client()
            
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)
            
            response = client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[statistic]
            )
            
            datapoints = response.get('Datapoints', [])
            
            # Sort by timestamp
            datapoints.sort(key=lambda x: x['Timestamp'])
            
            results = []
            for dp in datapoints:
                results.append({
                    'timestamp': dp['Timestamp'].isoformat(),
                    'value': dp.get(statistic, 0),
                    'unit': dp.get('Unit', '')
                })
            
            logger.info(f"Retrieved {len(results)} metric datapoints")
            return results
            
        except Exception as e:
            logger.error(f"Failed to get metric statistics: {str(e)}")
            return [{"error": f"Failed to get metric statistics: {str(e)}"}]
    
    @mcp.tool()
    def list_alarms(state_value: Optional[str] = None, max_records: int = 50) -> List[Dict[str, Any]]:
        """List CloudWatch alarms
        
        Args:
            state_value: Filter by alarm state (OK, ALARM, INSUFFICIENT_DATA)
            max_records: Maximum number of alarms to return (default: 50, max: 100)
        """
        try:
            if max_records > 100:
                max_records = 100
            elif max_records < 1:
                max_records = 50
                
            client = cw_manager.get_cloudwatch_client()
            
            kwargs = {'MaxRecords': max_records}
            if state_value:
                kwargs['StateValue'] = state_value
            
            response = client.describe_alarms(**kwargs)
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
            
            logger.info(f"Found {len(results)} alarms")
            return results
            
        except Exception as e:
            logger.error(f"Failed to list alarms: {str(e)}")
            return [{"error": f"Failed to list alarms: {str(e)}"}]
    
    # Cleanup function
    def cleanup():
        logger.info("Cleaning up CloudWatch connections")
    
    # Register cleanup
    import atexit
    atexit.register(cleanup)
    
    print(f"Starting CloudWatch MCP Server on http://localhost:{port}")
    print(f"Using AWS region: {cw_manager.region_name}")
    logger.info(f"CloudWatch MCP Server starting up on port {port}")
    mcp.run(transport="streamable-http", port=port)


if __name__ == "__main__":
    # Configuration - update these values for your environment
    REGION_NAME = os.getenv('AWS_REGION')  # Get from environment variable
    PORT = 8082  # Default port for CloudWatch MCP server
    
    try:
        start_cloudwatch_server(REGION_NAME, PORT)
    except KeyboardInterrupt:
        print("Server shutting down...")
        logger.info("Server shutdown requested by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        logger.error(f"Error starting server: {e}")
