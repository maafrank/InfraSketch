#!/bin/bash
set -e
export AWS_PAGER=""

# Deploy streak reminder Lambda function

FUNCTION_NAME="infrasketch-streak-reminder"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_streak_reminder.lambda_handler"
TIMEOUT=120
MEMORY=256

echo "=== Deploying InfraSketch Streak Reminder Lambda ==="

# Create deployment package
echo "Creating deployment package..."
cd "$(dirname "$0")"
rm -rf /tmp/streak-reminder-deploy
mkdir -p /tmp/streak-reminder-deploy

# Copy Lambda function
cp lambda_streak_reminder.py /tmp/streak-reminder-deploy/

# Create zip
cd /tmp/streak-reminder-deploy
zip -r ../streak-reminder-deploy.zip .

# Check if Lambda function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb:///tmp/streak-reminder-deploy.zip \
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
        --zip-file fileb:///tmp/streak-reminder-deploy.zip \
        --environment "Variables={RESEND_API_KEY_SECRET=infrasketch/resend-api-key}" \
        --region $REGION
fi

# Wait for function to be ready
echo "Waiting for function to be ready..."
aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || true

# Create or update EventBridge rule for daily schedule (noon EST = 6 PM UTC)
RULE_NAME="infrasketch-streak-reminder-schedule"

echo "Setting up EventBridge schedule (daily at 12 PM EST / 6 PM UTC)..."

# Check if rule exists
if aws events describe-rule --name $RULE_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing schedule rule..."
else
    echo "Creating new schedule rule..."
fi

# Create/update the rule - daily at 6 PM UTC (12 PM EST)
aws events put-rule \
    --name $RULE_NAME \
    --schedule-expression "cron(0 18 * * ? *)" \
    --state ENABLED \
    --description "Trigger InfraSketch streak reminder at 12 PM EST" \
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
echo "Schedule: Daily at 12 PM EST (6 PM UTC)"
echo ""
echo "To test manually:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME /tmp/output.json && cat /tmp/output.json"
echo ""
echo "To check CloudWatch logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
echo "IMPORTANT: Make sure this secret exists in AWS Secrets Manager:"
echo "  - infrasketch/resend-api-key"
