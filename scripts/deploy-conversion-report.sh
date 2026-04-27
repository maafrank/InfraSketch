#!/bin/bash
# Deploy the infrasketch-conversion-report Lambda. Sends a weekly conversion-customer
# analysis email at 9 AM PST on Mondays.

set -e
cd "$(dirname "$0")"
source lib/deploy-lambda.sh

FUNCTION_NAME="infrasketch-conversion-report"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_conversion_report.lambda_handler"
TIMEOUT=600
MEMORY=512
ZIP_FILE="/tmp/conversion-report-deploy.zip"

echo "=== Deploying InfraSketch Conversion Report Lambda ==="

rm -rf /tmp/conversion-report-deploy
mkdir -p /tmp/conversion-report-deploy
cp lambda_conversion_report.py /tmp/conversion-report-deploy/
cp analyze_conversions.py /tmp/conversion-report-deploy/

(cd /tmp/conversion-report-deploy && zip -rq "$ZIP_FILE" .)

update_or_create_function

# Mondays at 9 AM PST = 17:00 UTC. Cron: minute hour day-of-month month day-of-week year.
# AWS cron uses "?" for one of day-of-month/day-of-week. Day-of-week 2 = Monday in AWS.
setup_eventbridge_schedule \
    "infrasketch-conversion-report-schedule" \
    "cron(0 17 ? * MON *)" \
    "Trigger InfraSketch conversion report weekly Mondays at 9 AM PST"

echo ""
echo "=== Deployment Complete ==="
echo "Function: $FUNCTION_NAME"
echo "Schedule: Mondays at 9 AM PST (17:00 UTC)"
echo ""
echo "Manual test: aws lambda invoke --function-name $FUNCTION_NAME /tmp/output.json && cat /tmp/output.json"
echo "Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
echo "Note: this Lambda reads from infrasketch-user-credits, infrasketch-credit-transactions,"
echo "infrasketch-sessions, infrasketch-user-gamification, and infrasketch-user-preferences."
echo "It uses the shared infrasketch-lambda-role, which already has access to those tables."
