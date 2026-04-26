#!/bin/bash
# Deploy the infrasketch-visitor-count-refresh Lambda. Refreshes the
# DynamoDB cache row that GET /api/badges/monthly-visitors.svg reads from.
# The serving endpoint is cache-only because parsing 30 days of CloudFront
# logs in the request path exceeds API Gateway's 30s timeout.

set -e
cd "$(dirname "$0")"
source lib/deploy-lambda.sh

FUNCTION_NAME="infrasketch-visitor-count-refresh"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_visitor_count_refresh.lambda_handler"
TIMEOUT=900
MEMORY=1024
ZIP_FILE="/tmp/visitor-count-refresh-deploy.zip"

echo "=== Deploying InfraSketch Visitor Count Refresh Lambda ==="

rm -rf /tmp/visitor-count-refresh-deploy
mkdir -p /tmp/visitor-count-refresh-deploy

# Bundle handler + reused parsing/caching module from the backend
cp lambda_visitor_count_refresh.py /tmp/visitor-count-refresh-deploy/
cp ../backend/app/utils/badge_generator.py /tmp/visitor-count-refresh-deploy/

(cd /tmp/visitor-count-refresh-deploy && zip -rq "$ZIP_FILE" .)

update_or_create_function

setup_eventbridge_schedule \
    "infrasketch-visitor-count-refresh-schedule" \
    "cron(0 8 * * ? *)" \
    "Refresh InfraSketch monthly-visitors badge cache daily at 1 AM PST"

echo ""
echo "=== Deployment Complete ==="
echo "Function: $FUNCTION_NAME"
echo "Schedule: Daily at 1 AM PST (8 AM UTC)"
echo ""
echo "Manual refresh (recommended right after first deploy):"
echo "  aws lambda invoke --function-name $FUNCTION_NAME /tmp/output.json && cat /tmp/output.json"
echo ""
echo "Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --since 5m --follow"
echo ""
echo "Verify cache row:"
echo "  aws dynamodb get-item --table-name infrasketch-sessions --key '{\"session_id\":{\"S\":\"CACHE#monthly-visitors\"}}'"
