#!/bin/bash

# Autonomous DBOps Setup Script
# Configures event-driven database operations with customizable alerts

set -e

# Configuration with defaults
CPU_THRESHOLD=${CPU_THRESHOLD:-50}
EVALUATION_PERIODS=${EVALUATION_PERIODS:-1}
ALARM_PERIOD=${ALARM_PERIOD:-60}

echo "🚀 Setting up Autonomous Database Operations..."
echo "Configuration:"
echo "  CPU Threshold: ${CPU_THRESHOLD}%"
echo "  Evaluation Periods: $EVALUATION_PERIODS"
echo "  Alarm Period: ${ALARM_PERIOD}s"

# Get required values from environment and AWS
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$AGENTCORE_RUNTIME_ARN" ]; then
    echo "❌ Error: AGENTCORE_RUNTIME_ARN environment variable not set. Make sure you ran the previous deployment step."
    exit 1
fi

echo "Using AgentCore Runtime ARN: $AGENTCORE_RUNTIME_ARN"

# 1. Create Lambda function code
echo "📝 Creating Lambda proxy function..."
cat > database-operations-invoker.py << 'LAMBDA_EOF'
import json
import boto3
import os

def lambda_handler(event, context):
    """Lambda function to invoke AgentCore runtime from EventBridge events"""
    
    client = boto3.client('bedrock-agentcore', region_name=os.environ.get('AWSREGION', 'us-west-2'))
    
    # Extract alarm information from EventBridge event
    alarm_name = event['detail']['alarmName']
    alarm_state = event['detail']['state']['value']
    
    # Create prompt for AgentCore
    prompt = f"AUTONOMOUS ALERT: {alarm_name} is in {alarm_state} state. Perform emergency database analysis and provide immediate recommendations for resolution."
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=os.environ['AGENTCORE_RUNTIME_ARN'],
            payload=json.dumps({"prompt": prompt})
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'AgentCore invoked successfully',
                'alarm': alarm_name,
                'state': alarm_state
            })
        }
        
    except Exception as e:
        print(f"Error invoking AgentCore: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'alarm': alarm_name,
                'state': alarm_state
            })
        }
LAMBDA_EOF

# Create deployment package
zip -q database-operations-invoker.zip database-operations-invoker.py

# 2. Create IAM role for Lambda
echo "🔐 Creating IAM role for Lambda..."
cat > lambda-trust-policy.json << 'TRUST_EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
TRUST_EOF

cat > lambda-permissions-policy.json << PERM_EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:InvokeAgentRuntime"
            ],
            "Resource": [
                "${AGENTCORE_RUNTIME_ARN}",
                "${AGENTCORE_RUNTIME_ARN}/runtime-endpoint/DEFAULT"
            ]
        }
    ]
}
PERM_EOF

# Create IAM role
aws iam create-role \
    --role-name DatabaseOperationsInvokerRole \
    --assume-role-policy-document file://lambda-trust-policy.json \
    --no-cli-pager 2>/dev/null || echo "Role already exists"

aws iam put-role-policy \
    --role-name DatabaseOperationsInvokerRole \
    --policy-name DatabaseOperationsInvokerPolicy \
    --policy-document file://lambda-permissions-policy.json \
    --no-cli-pager

# Wait for IAM propagation
echo "⏳ Waiting for IAM role propagation..."
sleep 15

# 3. Deploy Lambda function
echo "🚀 Deploying Lambda function..."
aws lambda create-function \
    --function-name database-operations-invoker \
    --runtime python3.9 \
    --role "arn:aws:iam::$ACCOUNT_ID:role/DatabaseOperationsInvokerRole" \
    --handler database-operations-invoker.lambda_handler \
    --zip-file fileb://database-operations-invoker.zip \
    --timeout 60 \
    --environment Variables="{AGENTCORE_RUNTIME_ARN=$AGENTCORE_RUNTIME_ARN,AWSREGION=$AWSREGION}" \
    --region $AWSREGION \
    --no-cli-pager 2>/dev/null

if [ $? -ne 0 ]; then
    echo "Function might already exist, updating code..."
    aws lambda update-function-code \
        --function-name database-operations-invoker \
        --zip-file fileb://database-operations-invoker.zip \
        --no-cli-pager
fi

# 4. Configure EventBridge rule
echo "📡 Setting up EventBridge automation..."
aws events put-rule \
    --name database-autonomous-response \
    --description "Triggers autonomous database operations on performance issues" \
    --event-pattern '{
        "source": ["aws.cloudwatch"],
        "detail-type": ["CloudWatch Alarm State Change"],
        "detail": {
            "state": {
                "value": ["ALARM"]
            },
            "alarmName": ["dat302-autodbops-labs-aurora-writer-cpu-alarm"]
        }
    }' \
    --no-cli-pager

aws events put-targets \
    --rule database-autonomous-response \
    --targets '[{
        "Id": "1",
        "Arn": "arn:aws:lambda:'$AWSREGION':'$ACCOUNT_ID':function:database-operations-invoker"
    }]' \
    --no-cli-pager

aws lambda add-permission \
    --function-name database-operations-invoker \
    --statement-id allow-eventbridge \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$AWSREGION:$ACCOUNT_ID:rule/database-autonomous-response" \
    --no-cli-pager 2>/dev/null || echo "Permission already exists"

# Reset alarm state to ensure clean testing state
echo "🔄 Resetting alarm state for clean testing..."
aws cloudwatch set-alarm-state \
    --alarm-name "dat302-autodbops-labs-aurora-writer-cpu-alarm" \
    --state-value OK \
    --state-reason "Reset to OK state after EventBridge setup" \
    --no-cli-pager

# 5. Create performance alerts
echo "⚠️  Creating performance alerts..."
aws cloudwatch put-metric-alarm \
    --alarm-name "dat302-autodbops-labs-aurora-writer-cpu-alarm" \
    --alarm-description "Aurora database CPU utilization too high" \
    --metric-name CPUUtilization \
    --namespace AWS/RDS \
    --statistic Average \
    --period $ALARM_PERIOD \
    --threshold $CPU_THRESHOLD \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods $EVALUATION_PERIODS \
    --dimensions Name=DBInstanceIdentifier,Value=dat302-autodbops-labs-node-01 \
    --alarm-actions "arn:aws:sns:$AWSREGION:$ACCOUNT_ID:agentcore-database-alerts" \
    --no-cli-pager

echo "✅ Autonomous Database Operations setup complete!"
echo ""
echo "🎯 What was configured:"
echo "   • Lambda proxy function for AgentCore integration"
echo "   • EventBridge rule for automatic alarm response"
echo "   • CloudWatch alarm with threshold:"
echo "     - Aurora CPU: ${CPU_THRESHOLD}%"
echo "🧪 Test the system:"
echo "   aws cloudwatch set-alarm-state --alarm-name dat302-autodbops-labs-aurora-writer-cpu-alarm --state-value ALARM --state-reason 'Testing autonomous response'"

# Cleanup temporary files
rm -f database-operations-invoker.py database-operations-invoker.zip
rm -f lambda-trust-policy.json lambda-permissions-policy.json