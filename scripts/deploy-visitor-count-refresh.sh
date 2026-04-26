#!/bin/bash
set -e

# Deploy the visitor-count-refresh Lambda. This refreshes the DynamoDB cache
# row that GET /api/badges/monthly-visitors.svg reads from. The serving
# endpoint is cache-only because parsing 30 days of CloudFront logs in the
# request path exceeds API Gateway's 30s timeout.

FUNCTION_NAME="infrasketch-visitor-count-refresh"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_visitor_count_refresh.lambda_handler"
TIMEOUT=900
MEMORY=1024

echo "=== Deploying InfraSketch Visitor Count Refresh Lambda ==="

cd "$(dirname "$0")"
rm -rf /tmp/visitor-count-refresh-deploy
mkdir -p /tmp/visitor-count-refresh-deploy

# Bundle handler + reused parsing/caching module from the backend
cp lambda_visitor_count_refresh.py /tmp/visitor-count-refresh-deploy/
cp ../backend/app/utils/badge_generator.py /tmp/visitor-count-refresh-deploy/

cd /tmp/visitor-count-refresh-deploy
zip -r ../visitor-count-refresh-deploy.zip .

if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb:///tmp/visitor-count-refresh-deploy.zip \
        --region $REGION

    aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || true

    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --region $REGION
else
    echo "Creating new Lambda function..."

    # Reuse the shared backend execution role (already has S3 + DynamoDB access)
    ROLE_ARN=$(aws lambda get-function --function-name infrasketch-backend --query 'Configuration.Role' --output text --region $REGION)

    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --handler $HANDLER \
        --role $ROLE_ARN \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --zip-file fileb:///tmp/visitor-count-refresh-deploy.zip \
        --region $REGION
fi

aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || true

# EventBridge rule: daily at 1 AM PST (8 AM UTC), off-peak
RULE_NAME="infrasketch-visitor-count-refresh-schedule"

echo "Setting up EventBridge schedule (daily at 1 AM PST)..."

aws events put-rule \
    --name $RULE_NAME \
    --schedule-expression "cron(0 8 * * ? *)" \
    --state ENABLED \
    --description "Refresh InfraSketch monthly-visitors badge cache daily at 1 AM PST" \
    --region $REGION

aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id "EventBridgeInvoke-$RULE_NAME" \
    --action "lambda:InvokeFunction" \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$REGION:$(aws sts get-caller-identity --query Account --output text):rule/$RULE_NAME" \
    --region $REGION 2>/dev/null || true

LAMBDA_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $REGION)

aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id"="1","Arn"="$LAMBDA_ARN" \
    --region $REGION

echo ""
echo "=== Deployment Complete ==="
echo "Function: $FUNCTION_NAME"
echo "Schedule: Daily at 1 AM PST (8 AM UTC)"
echo ""
echo "To run a refresh manually (recommended right after first deploy):"
echo "  aws lambda invoke --function-name $FUNCTION_NAME /tmp/output.json && cat /tmp/output.json"
echo ""
echo "To check CloudWatch logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --since 5m --follow"
echo ""
echo "To verify the cache row was written:"
echo "  aws dynamodb get-item --table-name infrasketch-sessions --key '{\"session_id\":{\"S\":\"CACHE#monthly-visitors\"}}'"
