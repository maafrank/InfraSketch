#!/bin/bash
set -e

# Deploy social insights Lambda function with EventBridge daily schedule
# Posts branded chart videos with search performance insights to all platforms

FUNCTION_NAME="infrasketch-social-insights"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_social_insights.lambda_handler"
TIMEOUT=180  # 3 minutes for chart gen + video + upload + polling
MEMORY=512   # matplotlib needs memory

echo "=== Deploying InfraSketch Social Insights Lambda ==="

# Create deployment package
echo "Creating deployment package..."
cd "$(dirname "$0")"
rm -rf /tmp/social-insights-deploy /tmp/social-insights-deploy.zip
mkdir -p /tmp/social-insights-deploy

# Copy Lambda function, data, and assets
cp lambda_social_insights.py /tmp/social-insights-deploy/
cp search_console_data.py /tmp/social-insights-deploy/
cp logo.png /tmp/social-insights-deploy/

# Install dependencies for Lambda (Linux x86_64)
# Note: boto3/botocore are pre-installed on Lambda, skip to save ~25MB
# Note: av (PyAV) dropped to save ~114MB, using MJPEG AVI fallback instead
echo "Installing dependencies for Lambda..."

# Pure-Python packages FIRST (no platform constraint needed)
# Must run before binary packages so Linux .so files overwrite macOS ones
pip install anthropic requests certifi charset-normalizer idna urllib3 \
    google-auth \
    -t /tmp/social-insights-deploy/ \
    --quiet --upgrade

# Binary packages SECOND (overwrite any macOS .so files from pure-Python deps)
# cryptography is required by google-auth for service-account JWT signing (live GSC data).
pip install matplotlib Pillow "numpy<2" pydantic-core jiter cryptography \
    -t /tmp/social-insights-deploy/ \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --quiet --upgrade

# Strip unnecessary files to reduce package size
echo "Stripping unnecessary files..."
cd /tmp/social-insights-deploy
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
rm -rf matplotlib/tests matplotlib/testing matplotlib/mpl-data/sample_data 2>/dev/null || true
rm -rf numpy/tests numpy/testing numpy/f2py 2>/dev/null || true
rm -rf PIL/tests 2>/dev/null || true
# fontTools is 21MB, only needed for PDF font subsetting (we only make PNGs)
rm -rf fontTools 2>/dev/null || true
# Strip .so debug symbols
find . -name "*.so" -exec strip --strip-debug {} \; 2>/dev/null || true

# Create zip
echo "Creating zip file..."
zip -rq ../social-insights-deploy.zip .

ZIP_SIZE=$(du -h /tmp/social-insights-deploy.zip | cut -f1)
echo "Deployment package size: $ZIP_SIZE"

# Upload to S3 (required for packages > 50MB)
S3_BUCKET="infrasketch-lambda-deployments-059409992371"
S3_KEY="social-insights-deploy.zip"
echo "Uploading to S3..."
aws s3 cp /tmp/social-insights-deploy.zip "s3://$S3_BUCKET/$S3_KEY" --region $REGION

# Check if Lambda function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --s3-bucket $S3_BUCKET \
        --s3-key $S3_KEY \
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
        --code "S3Bucket=$S3_BUCKET,S3Key=$S3_KEY" \
        --environment "Variables={ANTHROPIC_API_KEY_SECRET=infrasketch/anthropic-api-key,UPLOAD_POST_API_KEY_SECRET=infrasketch/upload-post-api-key,GOOGLE_SEARCH_CONSOLE_SECRET=infrasketch/google-search-console,MPLCONFIGDIR=/tmp}" \
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
    --environment "Variables={ANTHROPIC_API_KEY_SECRET=infrasketch/anthropic-api-key,UPLOAD_POST_API_KEY_SECRET=infrasketch/upload-post-api-key,GOOGLE_SEARCH_CONSOLE_SECRET=infrasketch/google-search-console,MPLCONFIGDIR=/tmp}" \
    --region $REGION 2>/dev/null || true

aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION 2>/dev/null || true

# Create or update EventBridge rule for daily schedule (2 PM PST = 10 PM UTC)
RULE_NAME="infrasketch-social-insights-schedule"

echo "Setting up EventBridge schedule (daily at 2 PM PST)..."

# Create/update the rule
aws events put-rule \
    --name $RULE_NAME \
    --schedule-expression "cron(0 22 * * ? *)" \
    --state ENABLED \
    --description "Trigger InfraSketch social insights daily at 2 PM PST" \
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
echo "Schedule: Daily at 2 PM PST (10 PM UTC)"
echo ""
echo "To test manually:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME /tmp/output.json && cat /tmp/output.json"
echo ""
echo "To check CloudWatch logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
echo "IMPORTANT: Before first run, ensure:"
echo "  1. DynamoDB table 'infrasketch-social-insights' exists"
echo "  2. Secret 'infrasketch/upload-post-api-key' exists in Secrets Manager"
echo "  3. Secret 'infrasketch/anthropic-api-key' exists in Secrets Manager"
echo "  4. IAM policy 'DynamoDBSessionStorage' includes the new table ARN"
echo ""
echo "Create DynamoDB table:"
echo "  aws dynamodb create-table --table-name infrasketch-social-insights \\"
echo "    --attribute-definitions AttributeName=post_date,AttributeType=S \\"
echo "    --key-schema AttributeName=post_date,KeyType=HASH \\"
echo "    --billing-mode PAY_PER_REQUEST --region us-east-1"
echo ""
echo "Create Upload-Post secret:"
echo "  aws secretsmanager create-secret --name infrasketch/upload-post-api-key \\"
echo "    --secret-string '{\"UPLOAD_POST_API_KEY\":\"<your-key>\"}' --region us-east-1"
