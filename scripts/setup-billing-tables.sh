#!/bin/bash

# Setup DynamoDB tables for InfraSketch Billing
# Run this script with AWS credentials configured

set -e

echo "Creating DynamoDB tables for billing..."

# Create user credits table
echo "Creating infrasketch-user-credits table..."
aws dynamodb create-table \
  --table-name infrasketch-user-credits \
  --attribute-definitions AttributeName=user_id,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --tags Key=Application,Value=InfraSketch Key=Environment,Value=production \
  --region us-east-1 \
  2>/dev/null || echo "Table infrasketch-user-credits may already exist"

# Create credit transactions table with GSI
echo "Creating infrasketch-credit-transactions table..."
aws dynamodb create-table \
  --table-name infrasketch-credit-transactions \
  --attribute-definitions \
    AttributeName=transaction_id,AttributeType=S \
    AttributeName=user_id,AttributeType=S \
  --key-schema AttributeName=transaction_id,KeyType=HASH \
  --global-secondary-indexes \
    '[{"IndexName":"user_id-index","KeySchema":[{"AttributeName":"user_id","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}}]' \
  --billing-mode PAY_PER_REQUEST \
  --tags Key=Application,Value=InfraSketch Key=Environment,Value=production \
  --region us-east-1 \
  2>/dev/null || echo "Table infrasketch-credit-transactions may already exist"

echo "Waiting for tables to be active..."
aws dynamodb wait table-exists --table-name infrasketch-user-credits --region us-east-1
aws dynamodb wait table-exists --table-name infrasketch-credit-transactions --region us-east-1

echo "DynamoDB tables created successfully!"
echo ""
echo "Next steps:"
echo "1. Update Lambda IAM role to include these tables"
echo "2. Deploy backend with new billing code"
echo "3. Configure Clerk Billing in dashboard"
