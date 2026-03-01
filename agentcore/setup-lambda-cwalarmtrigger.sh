#!/bin/bash

set -e

# === Configuration ===
ALARM_NAME="dat302-autodbops-labs-aurora-writer-cpu-alarm"
export AGENTCORE_RUNTIME_ARN=$(agentcore status | grep "Agent ARN:" | cut -d' ' -f4)
export AGENT_ENDPOINT=$(agentcore status | grep -i "endpoint" | awk '{print $2}')

# Use environment variables for AWS region and account ID
if [ -z "$AWS_REGION" ] || [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Error: AWS_REGION and AWS_ACCOUNT_ID environment variables must be set."
    exit 1
fi

if [ -z "$AGENTCORE_RUNTIME_ARN" ]; then
    echo "❌ Error: AGENTCORE_RUNTIME_ARN environment variable not set."
    exit 1
fi

echo "Using AgentCore Runtime ARN: $AGENTCORE_RUNTIME_ARN"

# === 1. Create Lambda function code ===
cat > database-operations-invoker.py << 'LAMBDA_EOF'
import json
import boto3
import os
import botocore

def lambda_handler(event, context):
    region = os.environ.get('AWS_REGION', 'us-west-2')
    agent_runtime_arn = os.environ.get('AGENTCORE_RUNTIME_ARN')

    print(f"Event received: {json.dumps(event)}")

    alarm_name = event.get('alarmData', {}).get('alarmName', 'UnknownAlarm')
    alarm_state = event.get('alarmData', {}).get('state', {}).get('value', 'UnknownState')

    prompt = (
        f"AUTONOMOUS ALERT: {alarm_name} is in {alarm_state} state. "
        "review top queries, look at execution plan, and provide recommendation to fix. Summarize only  top recommendations that will have minimal impact to production. Send SNS notification only once with summary."
    )

    client = boto3.client(
        'bedrock-agentcore',
        region_name=region,
        config=botocore.config.Config(connect_timeout=5, read_timeout=120)
    )

    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        payload=json.dumps({"prompt": prompt})
    )

    print(f"AgentCore response: {response}")
    return {"statusCode": 200, "body": json.dumps({"alarm": alarm_name, "state": alarm_state})}
LAMBDA_EOF

# === 2. Zip Lambda code ===
zip -q database-operations-invoker.zip database-operations-invoker.py

# === 3. Create IAM role for Lambda ===
aws iam create-role \
    --role-name DatabaseOperationsInvokerRole \
    --assume-role-policy-document file://<(echo '{
      "Version":"2012-10-17",
      "Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]
    }') \
    --no-cli-pager 1>/dev/null 2>&1|| echo "Role already exists"

aws iam put-role-policy \
    --role-name DatabaseOperationsInvokerRole \
    --policy-name DatabaseOperationsInvokerPolicy \
    --policy-document file://<(echo '{
      "Version":"2012-10-17",
      "Statement":[
        {"Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],"Resource":"arn:aws:logs:*:*:*"},
        {"Effect":"Allow","Action":["bedrock-agentcore:InvokeAgentRuntime"],"Resource":"*"}
      ]
    }') \
    --no-cli-pager 1>/dev/null 2>&1

# Wait for IAM propagation
echo "waiting for role propagation" 
sleep 10

# === 4. Deploy Lambda (or update if exists) ===
LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:database-operations-invoker"

aws lambda create-function \
    --function-name database-operations-invoker \
    --runtime python3.9 \
    --role "arn:aws:iam::${AWS_ACCOUNT_ID}:role/DatabaseOperationsInvokerRole" \
    --handler database-operations-invoker.lambda_handler \
    --zip-file fileb://database-operations-invoker.zip \
    --timeout 300 \
    --environment Variables="{AGENTCORE_RUNTIME_ARN=$AGENTCORE_RUNTIME_ARN,AWSREGION=${AWS_REGION}}" \
    --region ${AWS_REGION} \
    --no-cli-pager 1>/dev/null 2>&1 || {
        echo "Function exists, updating code..."
        aws lambda update-function-code --function-name database-operations-invoker --zip-file fileb://database-operations-invoker.zip --no-cli-pager
        aws lambda wait function-updated --function-name database-operations-invoker --no-cli-pager
        aws lambda update-function-configuration --function-name database-operations-invoker --timeout 300 --environment Variables="{AGENTCORE_RUNTIME_ARN=$AGENTCORE_RUNTIME_ARN,AWSREGION=${AWS_REGION}}" --no-cli-pager
    }

# === 5. Give CloudWatch permission to invoke Lambda ===
aws lambda add-permission \
  --function-name database-operations-invoker \
  --statement-id AlarmActionPermission \
  --action lambda:InvokeFunction \
  --principal lambda.alarms.cloudwatch.amazonaws.com \
  --source-account ${AWS_ACCOUNT_ID} \
  --source-arn "arn:aws:cloudwatch:${AWS_REGION}:${AWS_ACCOUNT_ID}:alarm:$ALARM_NAME" \
  --no-cli-pager 1>/dev/null 2>&1 || { echo "Permission already exists"; true; }

# === 6. Attach Lambda to existing alarm ===
# Get current alarm configuration
ALARM_JSON=$(aws cloudwatch describe-alarms --alarm-names "$ALARM_NAME" --region ${AWS_REGION} --output json)

# Extract alarm configuration details - access first element  of MetricAlarms array
METRIC_NAME=$(echo "$ALARM_JSON" | jq -r '.MetricAlarms[0].MetricName')
NAMESPACE=$(echo "$ALARM_JSON" | jq -r '.MetricAlarms[0].Namespace')
STATISTIC=$(echo "$ALARM_JSON" | jq -r '.MetricAlarms[0].Statistic')
PERIOD=$(echo "$ALARM_JSON" | jq -r '.MetricAlarms[0].Period')
EVAL_PERIODS=$(echo "$ALARM_JSON" | jq -r '.MetricAlarms[0].EvaluationPeriods')
THRESHOLD=$(echo "$ALARM_JSON" | jq -r '.MetricAlarms[0].Threshold')
COMPARISON=$(echo "$ALARM_JSON" | jq -r '.MetricAlarms[0].ComparisonOperator')
DIMENSIONS=$(echo "$ALARM_JSON" | jq -c '.MetricAlarms[0].Dimensions')


# Build dimensions parameter
DIMENSIONS_PARAM=""
if [ "$DIMENSIONS" != "null" ] && [ "$DIMENSIONS" != "[]" ]; then
    DIMENSIONS_PARAM="--dimensions $DIMENSIONS"
fi

# Update alarm with Lambda action
aws cloudwatch put-metric-alarm \
    --alarm-name "$ALARM_NAME" \
    --alarm-actions "$LAMBDA_ARN" \
    --metric-name "$METRIC_NAME" \
    --namespace "$NAMESPACE" \
    --statistic "$STATISTIC" \
    --period "$PERIOD" \
    --evaluation-periods "$EVAL_PERIODS" \
    --threshold "$THRESHOLD" \
    --comparison-operator "$COMPARISON" \
    $DIMENSIONS_PARAM \
    --region ${AWS_REGION} \
    --no-cli-pager 1>/dev/null 2>&1

echo "✅ Setup complete. Lambda will now trigger when the alarm transitions to ALARM state."

# Cleanup temporary files
rm -f database-operations-invoker.py database-operations-invoker.zip

