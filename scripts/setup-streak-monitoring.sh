#!/bin/bash
set -e

# Set up CloudWatch alarms + SNS email notifications for streak reminder Lambda.
# Run once to create the infrastructure. Safe to re-run (idempotent).

REGION="us-east-1"
LAMBDA_FUNCTION="infrasketch-streak-reminder"
SNS_TOPIC_NAME="infrasketch-lambda-alerts"
ALERT_EMAIL="mattafrank2439@gmail.com"
LOG_GROUP="/aws/lambda/$LAMBDA_FUNCTION"

echo "=== Setting up monitoring for $LAMBDA_FUNCTION ==="

# 1. Create SNS topic (idempotent - returns existing ARN if already exists)
echo "Creating SNS topic..."
SNS_TOPIC_ARN=$(aws sns create-topic \
    --name $SNS_TOPIC_NAME \
    --region $REGION \
    --query 'TopicArn' \
    --output text)
echo "  Topic ARN: $SNS_TOPIC_ARN"

# 2. Subscribe email (AWS deduplicates, won't send duplicate confirmation)
echo "Subscribing $ALERT_EMAIL..."
aws sns subscribe \
    --topic-arn "$SNS_TOPIC_ARN" \
    --protocol email \
    --notification-endpoint "$ALERT_EMAIL" \
    --region $REGION \
    --output text > /dev/null
echo "  Check your email for a confirmation link (if not already confirmed)"

# 3. CloudWatch Alarm: Lambda invocation errors (catches raised exceptions)
echo "Creating alarm: Lambda invocation errors..."
aws cloudwatch put-metric-alarm \
    --alarm-name "infrasketch-streak-reminder-errors" \
    --alarm-description "Streak reminder Lambda failed (raised exception). Check CloudWatch logs." \
    --namespace "AWS/Lambda" \
    --metric-name "Errors" \
    --dimensions "Name=FunctionName,Value=$LAMBDA_FUNCTION" \
    --statistic "Sum" \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator "GreaterThanOrEqualToThreshold" \
    --alarm-actions "$SNS_TOPIC_ARN" \
    --treat-missing-data "notBreaching" \
    --region $REGION
echo "  Alarm created: infrasketch-streak-reminder-errors"

# 4. CloudWatch Metric Filter: catch partial failures logged in summary
echo "Creating metric filter for partial email failures..."
aws logs put-metric-filter \
    --log-group-name "$LOG_GROUP" \
    --filter-name "streak-reminder-email-failures" \
    --filter-pattern "STREAK_REMINDER_ERROR" \
    --metric-transformations '[{"metricName":"StreakReminderEmailFailures","metricNamespace":"InfraSketch","metricValue":"1","defaultValue":0}]' \
    --region $REGION
echo "  Metric filter created: streak-reminder-email-failures"

# 5. CloudWatch Alarm on the metric filter (catches partial failures)
echo "Creating alarm: partial email failures..."
aws cloudwatch put-metric-alarm \
    --alarm-name "infrasketch-streak-reminder-email-failures" \
    --alarm-description "Streak reminder had email send failures (partial or total). Check CloudWatch logs." \
    --namespace "InfraSketch" \
    --metric-name "StreakReminderEmailFailures" \
    --statistic "Sum" \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator "GreaterThanOrEqualToThreshold" \
    --alarm-actions "$SNS_TOPIC_ARN" \
    --treat-missing-data "notBreaching" \
    --region $REGION
echo "  Alarm created: infrasketch-streak-reminder-email-failures"

echo ""
echo "=== Monitoring setup complete ==="
echo ""
echo "Alarms created:"
echo "  1. infrasketch-streak-reminder-errors        - Lambda crashes/exceptions"
echo "  2. infrasketch-streak-reminder-email-failures - Any email send failures"
echo ""
echo "Both alarms notify: $ALERT_EMAIL via SNS topic $SNS_TOPIC_NAME"
echo ""
echo "IMPORTANT: Confirm the SNS subscription in your email if this is the first time."
echo ""
echo "To test alarms manually:"
echo "  aws cloudwatch set-alarm-state --alarm-name infrasketch-streak-reminder-errors --state-value ALARM --state-reason 'Manual test' --region $REGION"
