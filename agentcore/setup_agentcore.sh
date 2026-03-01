#!/bin/bash
set -euo pipefail

echo "Installing Strands + dependencies..."
pip install "fastmcp>=0.4.0" "boto3>=1.28.0" "asyncpg>=0.28.0" \
            "pydantic>=2.0.0" psycopg2-binary strands-agents strands-agents-tools

# ---------------------------------------------------------
# Move to AgentCore workspace
# ---------------------------------------------------------
cd /workshop/agentcore || { echo "❌ /workshop/agentcore not found"; exit 1; }

# ---------------------------------------------------------
# Install AgentCore CLI
# ---------------------------------------------------------
echo "📦 Installing AgentCore CLI..."
pip install "bedrock-agentcore-starter-toolkit>=0.1.21"

echo "🔍 Verifying AgentCore..."
if agentcore --help >/dev/null 2>&1; then
  echo "✅ AgentCore installed."
else
  echo "❌ AgentCore failed to install."
  exit 1
fi

# ---------------------------------------------------------
# Create requirements.txt
# ---------------------------------------------------------
cat > requirements.txt << 'EOF'
bedrock-agentcore>=1.0.0
strands-agents>=1.0.0
strands-agents-tools>=0.2.0
boto3>=1.34.0
psycopg2-binary>=2.9.0
python-dotenv>=1.0.0
EOF

# ---------------------------------------------------------
# Resolve environment details (VPC, Subnets, SG)
# ---------------------------------------------------------
SECURITY_GROUP_ID=$(aws rds describe-db-clusters \
  --db-cluster-identifier apgpg-dat302 \
  --region "$AWSREGION" \
  --query 'DBClusters[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
  --output text)

export SECURITY_GROUP_ID
export AGENTCORE_ROLE_ARN="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/AgentCoreDBOpsRole"
export SNS_TOPIC_ARN=$(aws sns create-topic --name agentcore-database-alerts --query 'TopicArn' --output text)

echo -e "\n=== Environment Variables ==="
echo "AWS_REGION:        $AWSREGION"
echo "AWS_ACCOUNT_ID:    $AWS_ACCOUNT_ID"
echo "VPC_ID:            $VPC_ID"
echo "SUBNET1:           $SUBNET1"
echo "SUBNET2:           $SUBNET2"
echo "SECURITY_GROUP_ID: $SECURITY_GROUP_ID"
echo "AURORA_CLUSTER_ID: apgpg-dat302"
echo "AURORA_SECRET_ID:  apgpg-dat302-secret"
echo "BEDROCK_MODEL_ID:  $BEDROCK_MODEL_ID"
echo "AGENTCORE_ROLE_ARN:$AGENTCORE_ROLE_ARN"
echo "SNS_TOPIC_ARN:     $SNS_TOPIC_ARN"
echo "==============================================="

# ---------------------------------------------------------
# Configure AgentCore
# ---------------------------------------------------------
echo "⚙️ Configuring AgentCore..."
agentcore configure \
  --entrypoint healthcheck_agentcore.py \
  --name baked_healthcheck_agentcore \
  --execution-role "$AGENTCORE_ROLE_ARN" \
  --requirements-file requirements.txt \
  --vpc \
  --subnets "$SUBNET1,$SUBNET2" \
  --security-groups "$SECURITY_GROUP_ID" \
  --non-interactive

echo "✅ AgentCore configured."

# ---------------------------------------------------------
# Launch AgentCore Runtime (background)
# ---------------------------------------------------------
echo "🚀 Launching agent in background..."

agentcore launch \
  --env AWS_REGION="$AWSREGION" \
  --env AWS_ACCOUNT_ID="$AWS_ACCOUNT_ID" \
  --env AURORA_CLUSTER_ID=apgpg-dat302 \
  --env AURORA_SECRET_ID=apgpg-dat302-secret \
  --env BEDROCK_MODEL_ID="$BEDROCK_MODEL_ID" \
  --env SNS_TOPIC_ARN="$SNS_TOPIC_ARN" \
  1>/dev/null 2>&1 &

echo "✅ Deployment started (running in background)."
echo "Environment initial setup completed date: `date`"
echo "Proceed with next steps in session"
