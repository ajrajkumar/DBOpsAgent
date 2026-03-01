"""
Secrets Manager Integration
Always use AWS Secrets Manager for credentials - Project Rule #2

This module handles all credential management through AWS Secrets Manager
to ensure secure access to Aurora PostgreSQL and other AWS services.
"""

import boto3
import json
import logging
import os
from typing import Dict, Any

# Configure logging for this module
logger = logging.getLogger(__name__)

class SecretsManager:
    """
    Manages all credential retrieval from AWS Secrets Manager
    
    This class centralizes credential management to follow Project Rule #2:
    "Always use Secrets Manager" - no hardcoded credentials anywhere
    """
    
    def __init__(self, region: str = None):
        """
        Initialize Secrets Manager client
        
        Args:
            region: AWS region where secrets are stored (default: from AWS_REGION env var or us-west-2)
        """
        # Initialize AWS Secrets Manager client for secure credential access
        region = region or os.getenv('AWS_REGION', 'us-west-2')
        self.client = boto3.client('secretsmanager', region_name=region)
        logger.info(f"SecretsManager initialized for region: {region}")
    
    def get_aurora_config(self) -> Dict[str, Any]:
        """
        Get Aurora PostgreSQL configuration from Secrets Manager
        
        Returns:
            Dict containing Aurora connection parameters:
            - host: localhost (for SSH tunnel) or Aurora cluster endpoint from Secrets Manager
            - port: Database port from Secrets Manager
            - database: Database name from Secrets Manager (dbname or database field)
            - user: Database username from Secrets Manager
            - password: Database password from Secrets Manager
            - dbClusterIdentifier: Aurora cluster identifier from Secrets Manager
            - dbInstanceIdentifier: Aurora instance identifier from Secrets Manager
            
        Raises:
            Exception: If secret retrieval fails or secret format is invalid
        """
        try:
            # Retrieve the hackathon/demo secret containing Aurora credentials
            logger.info("Retrieving Aurora credentials from Secrets Manager")
            secret_id = os.getenv('AURORA_SECRET_ID', 'apgpg-dat302-secret')
            response = self.client.get_secret_value(SecretId=secret_id)
            
            # Parse the JSON secret string to extract credentials
            secret = json.loads(response['SecretString'])
            logger.info(f"Secret keys found: {list(secret.keys())}")
            
            # Build Aurora configuration using workshop environment variables with Secrets Manager fallback
            # All other parameters come from Secrets Manager (Project Rule #2)
            config = {
                'host': os.getenv('PGHOST', os.getenv('DBENDP', secret.get('host', 'localhost'))),  # Workshop vars or secret
                'port': int(os.getenv('PGPORT', secret.get('port', 5432))),  # Port from env var or secret
                'database': os.getenv('PGDATABASE', os.getenv('DB_NAME', secret.get('database') or secret.get('dbname') or 'postgres')),  # Workshop vars or secret
                'user': os.getenv('PGUSER', os.getenv('DBUSER', secret.get('username') or secret.get('user'))),        # Workshop vars or secret
                'password': os.getenv('PGPASSWORD', os.getenv('DBPASS', secret.get('password'))),                          # Workshop vars or secret
                'dbClusterIdentifier': secret.get('dbClusterIdentifier'),    # Cluster ID from Secrets Manager
                'dbInstanceIdentifier': secret.get('dbInstanceIdentifier')   # Instance ID from Secrets Manager
            }
            
            # Validate all required parameters are present
            required_params = ['host', 'user', 'password']  # database can be defaulted
            missing_params = [param for param in required_params if not config.get(param)]
            
            if missing_params:
                logger.error(f"Missing required parameters in Secrets Manager: {missing_params}")
                logger.error(f"Available secret keys: {list(secret.keys())}")
                raise ValueError(f"Missing required parameters in Secrets Manager: {missing_params}")
            
            # If no database specified, try common defaults
            if not config['database']:
                config['database'] = 'postgres'  # Default PostgreSQL database
                logger.warning("No database name found in secret, using default 'postgres'")
            
            logger.info(f"Aurora config retrieved successfully - Host: {config['host']} (SSH tunnel), Database: {config['database']}, User: {config['user']}")
            return config
            
        except Exception as e:
            # Log the error and re-raise for proper error handling upstream
            logger.error(f"Failed to get Aurora config from Secrets Manager: {e}")
            raise
    
    def get_bedrock_config(self) -> Dict[str, Any]:
        """
        Get Bedrock AI model configuration
        
        Returns:
            Dict containing Bedrock configuration:
            - region: AWS region for Bedrock service
            - model_id: Claude 3.7 Sonnet model identifier
        """
        # Bedrock configuration for AI agent interactions
        config = {
            'region': os.getenv('AWS_REGION', 'us-west-2'),  # Bedrock service region
            'model_id': os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0')  # Claude model
        }
        
        logger.info(f"Bedrock config prepared for model: {config['model_id']}")
        return config
