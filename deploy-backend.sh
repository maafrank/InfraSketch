#!/bin/bash
set -e  # Exit on error

echo "🚀 Deploying InfraSketch Backend to AWS Lambda..."

# Configuration
LAMBDA_FUNCTION="infrasketch-backend"
S3_BUCKET="infrasketch-lambda-deployments-059409992371"
BACKEND_DIR="backend"

# Navigate to backend directory
cd "$BACKEND_DIR"

echo "📦 Cleaning previous build..."
rm -rf package lambda-deployment.zip

echo "📦 Creating package directory..."
mkdir package

echo "📥 Installing dependencies for Lambda (Linux x86_64)..."
pip install --platform manylinux2014_x86_64 \
    --target=package \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    -r requirements.txt mangum \
    --quiet

echo "📋 Copying application code..."
cp -r app package/
cp lambda_handler.py package/

echo "🗜️  Creating deployment package..."
cd package
zip -r ../lambda-deployment.zip . -q
cd ..

echo "📤 Uploading to S3..."
aws s3 cp lambda-deployment.zip s3://$S3_BUCKET/lambda-deployment.zip

echo "🔄 Updating Lambda function..."
aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION \
    --s3-bucket $S3_BUCKET \
    --s3-key lambda-deployment.zip \
    --no-cli-pager

echo "⏳ Waiting for Lambda update to complete..."
aws lambda wait function-updated --function-name $LAMBDA_FUNCTION

echo "✅ Backend deployment complete!"
echo "🔗 API URL: https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod"

echo "Deploying streak reminder Lambda..."
bash scripts/deploy-streak-reminder.sh

# Navigate back to root
cd ..
