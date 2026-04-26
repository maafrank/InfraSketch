#!/bin/bash
# Deploy the infrasketch-daily-report Lambda. Sends a daily ops report at 9 AM PST.

set -e
cd "$(dirname "$0")"
source lib/deploy-lambda.sh

FUNCTION_NAME="infrasketch-daily-report"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_daily_report.lambda_handler"
TIMEOUT=120
MEMORY=256
ZIP_FILE="/tmp/daily-report-deploy.zip"

echo "=== Deploying InfraSketch Daily Report Lambda ==="

rm -rf /tmp/daily-report-deploy
mkdir -p /tmp/daily-report-deploy
cp lambda_daily_report.py /tmp/daily-report-deploy/

(cd /tmp/daily-report-deploy && zip -rq "$ZIP_FILE" .)

update_or_create_function

setup_eventbridge_schedule \
    "infrasketch-daily-report-schedule" \
    "cron(0 17 * * ? *)" \
    "Trigger InfraSketch daily report at 9 AM PST"

echo ""
echo "=== Deployment Complete ==="
echo "Function: $FUNCTION_NAME"
echo "Schedule: Daily at 9 AM PST (5 PM UTC)"
echo ""
echo "Manual test: aws lambda invoke --function-name $FUNCTION_NAME /tmp/output.json && cat /tmp/output.json"
echo "Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
