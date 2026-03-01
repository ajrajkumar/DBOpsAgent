# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import boto3
from fastmcp import FastMCP
from typing import Annotated, List, Dict, Any, Optional
from pydantic import Field
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RDSServer")

mcp = FastMCP("RDS Server")


@mcp.tool()
def list_aurora_clusters(
    region: Annotated[str, Field(description="AWS region (optional)")] = ""
) -> Dict[str, List[Dict[str, Any]]]:
    """List Aurora DB clusters in the specified region"""
    client = boto3.client('rds', region_name=region)
    
    try:
        response = client.describe_db_clusters()
        
        clusters = []
        for cluster in response['DBClusters']:
            clusters.append({
                "identifier": cluster['DBClusterIdentifier'],
                "engine": cluster['Engine'],
                "engine_version": cluster['EngineVersion'],
                "status": cluster['Status'],
                "endpoint": cluster.get('Endpoint', 'N/A'),
                "reader_endpoint": cluster.get('ReaderEndpoint', 'N/A'),
                "port": cluster.get('Port', 'N/A'),
                "database_name": cluster.get('DatabaseName', 'N/A'),
                "master_username": cluster.get('MasterUsername', 'N/A'),
                "multi_az": cluster.get('MultiAZ', False),
                "storage_encrypted": cluster.get('StorageEncrypted', False),
                "backup_retention_period": cluster.get('BackupRetentionPeriod', 'N/A'),
                "cluster_members": len(cluster.get('DBClusterMembers', [])),
            })
        
        logger.info(f"Listed {len(clusters)} Aurora clusters")
        return {"clusters": clusters}
    
    except Exception as e:
        logger.error(f"Error listing Aurora clusters: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def describe_aurora_cluster(
    cluster_id: Annotated[str, Field(description="Aurora cluster identifier")],
    region: Annotated[str, Field(description="AWS region (optional)")] = ""
) -> Dict[str, Any]:
    """Get detailed information about an Aurora cluster"""
    client = boto3.client('rds', region_name=region)
    
    try:
        response = client.describe_db_clusters(DBClusterIdentifier=cluster_id)
        
        if not response['DBClusters']:
            return {"error": f"No cluster found with ID {cluster_id}"}
        
        cluster = response['DBClusters'][0]
        
        # Extract cluster members information
        cluster_members = []
        for member in cluster.get('DBClusterMembers', []):
            cluster_members.append({
                "instance_identifier": member['DBInstanceIdentifier'],
                "is_cluster_writer": member['IsClusterWriter'],
                "promotion_tier": member.get('PromotionTier', 'N/A'),
            })
        
        # Extract detailed cluster information
        result = {
            "identifier": cluster['DBClusterIdentifier'],
            "engine": cluster['Engine'],
            "engine_version": cluster['EngineVersion'],
            "status": cluster['Status'],
            "endpoint": cluster.get('Endpoint', 'N/A'),
            "reader_endpoint": cluster.get('ReaderEndpoint', 'N/A'),
            "port": cluster.get('Port', 'N/A'),
            "database_name": cluster.get('DatabaseName', 'N/A'),
            "master_username": cluster.get('MasterUsername', 'N/A'),
            "multi_az": cluster.get('MultiAZ', False),
            "storage_encrypted": cluster.get('StorageEncrypted', False),
            "kms_key_id": cluster.get('KmsKeyId', 'N/A'),
            "backup_retention_period": cluster.get('BackupRetentionPeriod', 'N/A'),
            "preferred_backup_window": cluster.get('PreferredBackupWindow', 'N/A'),
            "preferred_maintenance_window": cluster.get('PreferredMaintenanceWindow', 'N/A'),
            "vpc_security_groups": [sg['VpcSecurityGroupId'] for sg in cluster.get('VpcSecurityGroups', [])],
            "db_subnet_group": cluster.get('DBSubnetGroup', 'N/A'),
            "cluster_parameter_group": cluster.get('DBClusterParameterGroup', 'N/A'),
            "cluster_members": cluster_members,
            "serverless_v2_scaling": cluster.get('ServerlessV2ScalingConfiguration', {}),
            "performance_insights_enabled": cluster.get('PerformanceInsightsEnabled', False),
            "deletion_protection": cluster.get('DeletionProtection', False),
            "http_endpoint_enabled": cluster.get('HttpEndpointEnabled', False),
        }
        
        logger.info(f"Retrieved details for Aurora cluster {cluster_id}")
        return {"cluster": result}
    
    except client.exceptions.DBClusterNotFoundFault:
        logger.error(f"Aurora cluster {cluster_id} not found")
        return {"error": f"Cluster {cluster_id} not found"}
    except Exception as e:
        logger.error(f"Error describing Aurora cluster {cluster_id}: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def list_cluster_instances(
    cluster_id: Annotated[str, Field(description="Aurora cluster identifier")],
    region: Annotated[str, Field(description="AWS region (optional)")] = ""
) -> Dict[str, List[Dict[str, Any]]]:
    """List all instances in an Aurora cluster with their details"""
    client = rds_operator.get_client(region)
    
    try:
        # First get the cluster to find its members
        cluster_response = client.describe_db_clusters(DBClusterIdentifier=cluster_id)
        
        if not cluster_response['DBClusters']:
            return {"error": f"No cluster found with ID {cluster_id}"}
        
        cluster = cluster_response['DBClusters'][0]
        cluster_members = cluster.get('DBClusterMembers', [])
        
        if not cluster_members:
            return {"instances": []}
        
        # Get detailed information for each instance
        instance_ids = [member['DBInstanceIdentifier'] for member in cluster_members]
        instances_response = client.describe_db_instances()
        
        instances = []
        for instance in instances_response['DBInstances']:
            if instance['DBInstanceIdentifier'] in instance_ids:
                # Find the corresponding cluster member info
                member_info = next(
                    (m for m in cluster_members if m['DBInstanceIdentifier'] == instance['DBInstanceIdentifier']),
                    {}
                )
                
                instances.append({
                    "identifier": instance['DBInstanceIdentifier'],
                    "instance_class": instance['DBInstanceClass'],
                    "engine": instance['Engine'],
                    "engine_version": instance['EngineVersion'],
                    "status": instance['DBInstanceStatus'],
                    "availability_zone": instance.get('AvailabilityZone', 'N/A'),
                    "is_cluster_writer": member_info.get('IsClusterWriter', False),
                    "promotion_tier": member_info.get('PromotionTier', 'N/A'),
                    "endpoint": instance.get('Endpoint', {}).get('Address', 'N/A'),
                    "port": instance.get('Endpoint', {}).get('Port', 'N/A'),
                    "performance_insights_enabled": instance.get('PerformanceInsightsEnabled', False),
                    "monitoring_interval": instance.get('MonitoringInterval', 0),
                })
        
        logger.info(f"Listed {len(instances)} instances for Aurora cluster {cluster_id}")
        return {"instances": instances}
    
    except client.exceptions.DBClusterNotFoundFault:
        logger.error(f"Aurora cluster {cluster_id} not found")
        return {"error": f"Cluster {cluster_id} not found"}
    except Exception as e:
        logger.error(f"Error listing instances for Aurora cluster {cluster_id}: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def list_db_engine_versions(
    engine: Annotated[str, Field(description="Database engine (e.g., mysql, postgres, aurora-mysql, aurora-postgresql)")],
    region: Annotated[str, Field(description="AWS region (optional)")] = ""
) -> Dict[str, List[Dict[str, Any]]]:
    """List available engine versions for a specific database engine"""
    client = rds_operator.get_client(region)
    
    try:
        response = client.describe_db_engine_versions(Engine=engine)
        
        versions = []
        for version in response['DBEngineVersions']:
            versions.append({
                "engine": version['Engine'],
                "version": version['EngineVersion'],
                "description": version.get('DBEngineVersionDescription', 'N/A'),
                "default_parameter_family": version.get('DBParameterGroupFamily', 'N/A'),
                "supports_log_exports": version.get('SupportedLogTypes', []),
                "supports_read_replica": version.get('SupportsReadReplica', False),
            })
        
        logger.info(f"Listed {len(versions)} engine versions for {engine}")
        return {"versions": versions}
    
    except Exception as e:
        logger.error(f"Error listing engine versions for {engine}: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
