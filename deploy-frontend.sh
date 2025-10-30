#!/bin/bash
set -e  # Exit on error

echo "🚀 Deploying InfraSketch Frontend to S3/CloudFront..."

# Configuration
S3_BUCKET="infrasketch-frontend-059409992371"
CLOUDFRONT_DIST_ID="E2YM028NUBX2QN"
FRONTEND_DIR="frontend"

# Navigate to frontend directory
cd "$FRONTEND_DIR"

echo "🔨 Building frontend..."
npm run build

echo "📤 Uploading to S3..."
cd dist
aws s3 sync . s3://$S3_BUCKET --delete

echo "🔄 Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
    --distribution-id $CLOUDFRONT_DIST_ID \
    --paths "/*" \
    --no-cli-pager

echo "✅ Frontend deployment complete!"
echo "🔗 CloudFront URL: https://dr6smezctn6x0.cloudfront.net"
echo "⏳ Cache invalidation in progress (1-2 minutes)..."

# Navigate back to root
cd ../..
