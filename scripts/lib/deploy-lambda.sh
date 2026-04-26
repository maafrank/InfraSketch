#!/bin/bash
# Shared helpers for deploying scheduled Lambda functions.
#
# Usage from a deploy-*.sh script:
#
#   source "$(dirname "$0")/lib/deploy-lambda.sh"
#
#   FUNCTION_NAME="infrasketch-foo"
#   REGION="us-east-1"
#   RUNTIME="python3.11"
#   HANDLER="lambda_foo.lambda_handler"
#   TIMEOUT=120
#   MEMORY=256
#   ZIP_FILE="/tmp/foo-deploy.zip"
#   ENVIRONMENT_VARS=""  # optional, e.g. "Variables={KEY=val}"
#
#   # ... build $ZIP_FILE however the function needs (cp files, pip install, zip) ...
#
#   update_or_create_function
#   setup_eventbridge_schedule "infrasketch-foo-schedule" "cron(0 17 * * ? *)" "Daily at 9 AM PST"

set -e
export AWS_PAGER=""

# Updates an existing Lambda or creates a new one. Reuses the infrasketch-backend
# IAM role for new functions so all internal Lambdas share one execution role.
#
# Required vars: FUNCTION_NAME, REGION, RUNTIME, HANDLER, TIMEOUT, MEMORY, ZIP_FILE
# Optional vars: ENVIRONMENT_VARS (e.g. "Variables={KEY=val}")
update_or_create_function() {
    if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null >/dev/null; then
        echo "Updating existing Lambda function: $FUNCTION_NAME"
        aws lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file "fileb://$ZIP_FILE" \
            --region "$REGION"

        aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || true

        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY" \
            --region "$REGION" 2>/dev/null || true
    else
        echo "Creating new Lambda function: $FUNCTION_NAME"
        local role_arn
        role_arn=$(aws lambda get-function --function-name infrasketch-backend --query 'Configuration.Role' --output text --region "$REGION")

        local create_args=(
            --function-name "$FUNCTION_NAME"
            --runtime "$RUNTIME"
            --handler "$HANDLER"
            --role "$role_arn"
            --timeout "$TIMEOUT"
            --memory-size "$MEMORY"
            --zip-file "fileb://$ZIP_FILE"
            --region "$REGION"
        )
        if [ -n "${ENVIRONMENT_VARS:-}" ]; then
            create_args+=(--environment "$ENVIRONMENT_VARS")
        fi

        aws lambda create-function "${create_args[@]}"
    fi

    aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || true
}

# Wires an EventBridge cron schedule to the Lambda named by $FUNCTION_NAME.
# Idempotent: re-running updates the rule and skips already-granted invoke permission.
#
# Args:
#   $1: rule_name             (e.g. "infrasketch-foo-schedule")
#   $2: schedule_expression   (e.g. "cron(0 17 * * ? *)")
#   $3: description
setup_eventbridge_schedule() {
    local rule_name="$1"
    local schedule_expression="$2"
    local description="$3"

    echo "Configuring EventBridge schedule: $rule_name ($schedule_expression)"

    aws events put-rule \
        --name "$rule_name" \
        --schedule-expression "$schedule_expression" \
        --state ENABLED \
        --description "$description" \
        --region "$REGION"

    aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id "EventBridgeInvoke-$rule_name" \
        --action "lambda:InvokeFunction" \
        --principal events.amazonaws.com \
        --source-arn "arn:aws:events:$REGION:$(aws sts get-caller-identity --query Account --output text):rule/$rule_name" \
        --region "$REGION" 2>/dev/null || true

    local lambda_arn
    lambda_arn=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.FunctionArn' --output text --region "$REGION")

    aws events put-targets \
        --rule "$rule_name" \
        --targets "Id=1,Arn=$lambda_arn" \
        --region "$REGION"
}
