#!/bin/bash
set -e

# Deploy daily report Lambda function

FUNCTION_NAME="infrasketch-daily-report"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_daily_report.lambda_handler"
TIMEOUT=120
MEMORY=256

echo "=== Deploying InfraSketch Daily Report Lambda ==="

# Create deployment package
echo "Creating deployment package..."
cd "$(dirname "$0")"
rm -rf /tmp/daily-report-deploy
mkdir -p /tmp/daily-report-deploy

# Copy Lambda function
cp lambda_daily_report.py /tmp/daily-report-deploy/

# Create zip
cd /tmp/daily-report-deploy
zip -r ../daily-report-deploy.zip .

# Check if Lambda function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb:///tmp/daily-report-deploy.zip \
        --region $REGION
else
    echo "Creating new Lambda function..."

    # Get the IAM role ARN (use same role as main backend)
    ROLE_ARN=$(aws lambda get-function --function-name infrasketch-backend --query 'Configuration.Role' --output text --region $REGION)

    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --handler $HANDLER \
        --role $ROLE_ARN \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --zip-file fileb:///tmp/daily-report-deploy.zip \
        --region $REGION
fi

# Wait for function to be ready
echo "Waiting for function to be ready..."
aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || true

# Create or update EventBridge rule for daily schedule (9 AM PST = 5 PM UTC)
RULE_NAME="infrasketch-daily-report-schedule"

echo "Setting up EventBridge schedule (daily at 9 AM PST)..."

# Check if rule exists
if aws events describe-rule --name $RULE_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing schedule rule..."
else
    echo "Creating new schedule rule..."
fi

# Create/update the rule - daily at 5 PM UTC (9 AM PST)
aws events put-rule \
    --name $RULE_NAME \
    --schedule-expression "cron(0 17 * * ? *)" \
    --state ENABLED \
    --description "Trigger InfraSketch daily report at 9 AM PST" \
    --region $REGION

# Add Lambda permission for EventBridge to invoke the function
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id "EventBridgeInvoke-$RULE_NAME" \
    --action "lambda:InvokeFunction" \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$REGION:$(aws sts get-caller-identity --query Account --output text):rule/$RULE_NAME" \
    --region $REGION 2>/dev/null || true

# Get Lambda ARN
LAMBDA_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text --region $REGION)

# Add the Lambda as target for the rule
aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id"="1","Arn"="$LAMBDA_ARN" \
    --region $REGION

echo ""
echo "=== Deployment Complete ==="
echo "Function: $FUNCTION_NAME"
echo "Schedule: Daily at 9 AM PST (5 PM UTC)"
echo ""
echo "To test manually:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME /tmp/output.json && cat /tmp/output.json"
echo ""
echo "To check CloudWatch logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
