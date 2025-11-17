#!/bin/bash

# Fix API Gateway CORS for error responses
# This ensures 4XX/5XX responses include CORS headers

API_ID="b31htlojb0"
REGION="us-east-1"

echo "Adding CORS headers to API Gateway error responses..."

# Get list of response types
aws apigateway get-gateway-responses \
  --rest-api-id $API_ID \
  --region $REGION \
  --query 'items[*].responseType' \
  --output text

# Update DEFAULT_4XX
echo "Updating DEFAULT_4XX..."
aws apigateway put-gateway-response \
  --rest-api-id $API_ID \
  --response-type DEFAULT_4XX \
  --region $REGION \
  --response-parameters '{
    "gatewayresponse.header.Access-Control-Allow-Origin": "'"'"'https://infrasketch.net'"'"'",
    "gatewayresponse.header.Access-Control-Allow-Headers": "'"'"'*'"'"'",
    "gatewayresponse.header.Access-Control-Allow-Methods": "'"'"'*'"'"'",
    "gatewayresponse.header.Access-Control-Allow-Credentials": "'"'"'true'"'"'"
  }'

# Update DEFAULT_5XX
echo "Updating DEFAULT_5XX..."
aws apigateway put-gateway-response \
  --rest-api-id $API_ID \
  --response-type DEFAULT_5XX \
  --region $REGION \
  --response-parameters '{
    "gatewayresponse.header.Access-Control-Allow-Origin": "'"'"'https://infrasketch.net'"'"'",
    "gatewayresponse.header.Access-Control-Allow-Headers": "'"'"'*'"'"'",
    "gatewayresponse.header.Access-Control-Allow-Methods": "'"'"'*'"'"'",
    "gatewayresponse.header.Access-Control-Allow-Credentials": "'"'"'true'"'"'"
  }'

# Create deployment
echo "Creating deployment..."
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION \
  --description "Add CORS headers to error responses"

echo "✓ Done! CORS headers added to error responses."
echo "Test by trying to generate a diagram with Sonnet 4.5"
