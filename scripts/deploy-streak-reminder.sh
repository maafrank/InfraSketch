#!/bin/bash
# Deploy the infrasketch-streak-reminder Lambda. Sends streak emails at 12 PM EST.

set -e
cd "$(dirname "$0")"
source lib/deploy-lambda.sh

FUNCTION_NAME="infrasketch-streak-reminder"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_streak_reminder.lambda_handler"
TIMEOUT=120
MEMORY=256
ZIP_FILE="/tmp/streak-reminder-deploy.zip"
ENVIRONMENT_VARS="Variables={RESEND_API_KEY_SECRET=infrasketch/resend-api-key}"

echo "=== Deploying InfraSketch Streak Reminder Lambda ==="

rm -rf /tmp/streak-reminder-deploy
mkdir -p /tmp/streak-reminder-deploy
cp lambda_streak_reminder.py /tmp/streak-reminder-deploy/

(cd /tmp/streak-reminder-deploy && zip -rq "$ZIP_FILE" .)

update_or_create_function

setup_eventbridge_schedule \
    "infrasketch-streak-reminder-schedule" \
    "cron(0 18 * * ? *)" \
    "Trigger InfraSketch streak reminder at 12 PM EST"

echo ""
echo "=== Deployment Complete ==="
echo "Function: $FUNCTION_NAME"
echo "Schedule: Daily at 12 PM EST (6 PM UTC)"
echo ""
echo "Manual test: aws lambda invoke --function-name $FUNCTION_NAME /tmp/output.json && cat /tmp/output.json"
echo "Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
echo "Required secret: infrasketch/resend-api-key"
