#!/bin/bash
# Deploy the infrasketch-blog-publisher Lambda. Generates and publishes blog posts daily.

set -e
cd "$(dirname "$0")"
source lib/deploy-lambda.sh

FUNCTION_NAME="infrasketch-blog-publisher"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_blog_publisher.lambda_handler"
TIMEOUT=300  # 5 minutes for article generation
MEMORY=512   # More memory for Claude API calls
ZIP_FILE="/tmp/blog-publisher-deploy.zip"
ENVIRONMENT_VARS="Variables={ANTHROPIC_API_KEY_SECRET=infrasketch/anthropic-api-key,DEVTO_API_KEY_SECRET=infrasketch/devto-api-key}"

echo "=== Deploying InfraSketch Blog Publisher Lambda ==="

rm -rf /tmp/blog-publisher-deploy
mkdir -p /tmp/blog-publisher-deploy
cp lambda_blog_publisher.py /tmp/blog-publisher-deploy/
cp blog_ideas_data.py /tmp/blog-publisher-deploy/

echo "Installing dependencies for Lambda (Linux x86_64)..."
pip install anthropic requests boto3 \
    -t /tmp/blog-publisher-deploy/ \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --quiet --upgrade

(cd /tmp/blog-publisher-deploy && zip -rq "$ZIP_FILE" .)
echo "Deployment package size: $(du -h "$ZIP_FILE" | cut -f1)"

update_or_create_function

setup_eventbridge_schedule \
    "infrasketch-blog-publisher-schedule" \
    "cron(0 18 * * ? *)" \
    "Trigger InfraSketch blog publisher daily at 10 AM PST"

echo ""
echo "=== Deployment Complete ==="
echo "Function: $FUNCTION_NAME"
echo "Memory: ${MEMORY}MB"
echo "Timeout: ${TIMEOUT}s"
echo "Schedule: Daily at 10 AM PST (6 PM UTC)"
echo ""
echo "Manual test: aws lambda invoke --function-name $FUNCTION_NAME /tmp/output.json && cat /tmp/output.json"
echo "Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
echo "Required secrets in AWS Secrets Manager:"
echo "  - infrasketch/anthropic-api-key"
echo "  - infrasketch/devto-api-key"
echo "  - infrasketch/unsplash-api-key (optional)"
echo ""
echo "Seed blog ideas table: python scripts/seed_blog_ideas.py --seed"
