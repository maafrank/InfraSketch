#!/bin/bash
set -e  # Exit on error
export AWS_PAGER=""

echo "🚀 Deploying InfraSketch (Backend + Frontend)..."
echo ""

# Deploy backend
echo "============================================"
echo "📱 BACKEND DEPLOYMENT"
echo "============================================"
./deploy-backend.sh

echo ""
echo "============================================"
echo "🌐 FRONTEND DEPLOYMENT"
echo "============================================"
./deploy-frontend.sh

echo ""
echo "============================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "============================================"
echo "🔗 Application URL: https://infrasketch.net"
echo "🔗 API URL: https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod"
echo ""
echo "⏳ Wait 1-2 minutes for CloudFront cache to clear, then test!"
