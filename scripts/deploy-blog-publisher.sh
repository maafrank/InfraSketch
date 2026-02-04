#!/bin/bash
set -e

# Deploy blog publisher Lambda function with EventBridge daily schedule

FUNCTION_NAME="infrasketch-blog-publisher"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_blog_publisher.lambda_handler"
TIMEOUT=300  # 5 minutes for article generation
MEMORY=512   # More memory for Claude API calls

echo "=== Deploying InfraSketch Blog Publisher Lambda ==="

# Create deployment package
echo "Creating deployment package..."
cd "$(dirname "$0")"
rm -rf /tmp/blog-publisher-deploy
mkdir -p /tmp/blog-publisher-deploy

# Copy Lambda function and data
cp lambda_blog_publisher.py /tmp/blog-publisher-deploy/
cp blog_ideas_data.py /tmp/blog-publisher-deploy/

# Install dependencies
echo "Installing dependencies..."
pip install anthropic requests boto3 -t /tmp/blog-publisher-deploy/ --quiet --upgrade

# Create zip
echo "Creating zip file..."
cd /tmp/blog-publisher-deploy
zip -rq ../blog-publisher-deploy.zip .

ZIP_SIZE=$(du -h /tmp/blog-publisher-deploy.zip | cut -f1)
echo "Deployment package size: $ZIP_SIZE"

# Check if Lambda function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb:///tmp/blog-publisher-deploy.zip \
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
        --zip-file fileb:///tmp/blog-publisher-deploy.zip \
        --environment "Variables={ANTHROPIC_API_KEY_SECRET=infrasketch/anthropic-api-key,DEVTO_API_KEY_SECRET=infrasketch/devto-api-key}" \
        --region $REGION
fi

# Wait for function to be ready
echo "Waiting for function to be ready..."
aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || true

# Update function configuration (in case it already existed)
echo "Updating function configuration..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --timeout $TIMEOUT \
    --memory-size $MEMORY \
    --region $REGION 2>/dev/null || true

aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || true

# Create or update EventBridge rule for daily schedule (10 AM PST = 6 PM UTC)
RULE_NAME="infrasketch-blog-publisher-schedule"

echo "Setting up EventBridge schedule (daily at 10 AM PST)..."

# Check if rule exists
if aws events describe-rule --name $RULE_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing schedule rule..."
else
    echo "Creating new schedule rule..."
fi

# Create/update the rule - daily at 6 PM UTC (10 AM PST)
aws events put-rule \
    --name $RULE_NAME \
    --schedule-expression "cron(0 18 * * ? *)" \
    --state ENABLED \
    --description "Trigger InfraSketch blog publisher daily at 10 AM PST" \
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
echo "Memory: ${MEMORY}MB"
echo "Timeout: ${TIMEOUT}s"
echo "Schedule: Daily at 10 AM PST (6 PM UTC)"
echo ""
echo "To test manually:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME /tmp/output.json && cat /tmp/output.json"
echo ""
echo "To check CloudWatch logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
echo "IMPORTANT: Make sure these secrets exist in AWS Secrets Manager:"
echo "  - infrasketch/anthropic-api-key"
echo "  - infrasketch/devto-api-key"
echo "  - infrasketch/unsplash-api-key (optional)"
echo ""
echo "To seed the blog ideas table:"
echo "  python scripts/seed_blog_ideas.py --seed"
