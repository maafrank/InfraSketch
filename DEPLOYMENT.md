# InfraSketch AWS Deployment Guide

This guide walks through deploying InfraSketch to AWS with secure API key management.

## Architecture Overview

```
┌─────────────────┐
│   CloudFront    │ ← HTTPS, CDN, Caching
└────────┬────────┘
         │
┌────────▼────────┐
│   S3 Bucket     │ ← Static React Frontend
└─────────────────┘

         │
┌────────▼────────┐
│  API Gateway    │ ← REST API, CORS, Rate Limiting
└────────┬────────┘
         │
┌────────▼────────┐
│ Lambda Function │ ← FastAPI Backend (via Mangum)
└────────┬────────┘
         │
┌────────▼────────┐
│ Secrets Manager │ ← ANTHROPIC_API_KEY
└─────────────────┘
```

## Prerequisites

- AWS Account with CLI configured
- Python 3.11+
- Node.js 18+
- Domain name (optional, for custom domain)

## Security: API Key Management

The backend supports **two methods** for API keys:

### Local Development (`.env`)
```bash
ANTHROPIC_API_KEY=sk-ant-api...
```

### Production (AWS Secrets Manager)
The application automatically tries:
1. **AWS Secrets Manager** (secret name: `infrasketch/anthropic-api-key`)
2. **Falls back to environment variable** if Secrets Manager fails

This means:
- ✅ Local dev works with `.env` file
- ✅ Production uses Secrets Manager
- ✅ Zero code changes between environments

---

## Deployment Option 1: Serverless (Recommended)

**Cost**: ~$5-10/month
**Scaling**: Automatic
**Maintenance**: Minimal

### Step 1: Create AWS Secrets Manager Secret

```bash
# Create the secret
aws secretsmanager create-secret \
    --name infrasketch/anthropic-api-key \
    --secret-string "sk-ant-api03-YOUR-KEY-HERE" \
    --description "Anthropic API key for InfraSketch" \
    --region us-east-1
```

**Cost**: $0.40/month + $0.05 per 10,000 API calls

### Step 2: Prepare Backend for Lambda

Install dependencies:
```bash
cd backend
pip install -r requirements.txt
pip install mangum  # FastAPI adapter for Lambda
```

Create `lambda_handler.py`:
```python
from mangum import Mangum
from app.main import app

handler = Mangum(app)
```

### Step 3: Package Lambda Function

```bash
# Create deployment package
cd backend
mkdir package
pip install -r requirements.txt -t package/
cp -r app package/
cp lambda_handler.py package/

# Create zip
cd package
zip -r ../lambda-deployment.zip .
cd ..
```

### Step 4: Create Lambda Function

```bash
aws lambda create-function \
    --function-name infrasketch-backend \
    --runtime python3.11 \
    --role arn:aws:iam::YOUR-ACCOUNT-ID:role/lambda-execution-role \
    --handler lambda_handler.handler \
    --zip-file fileb://lambda-deployment.zip \
    --timeout 30 \
    --memory-size 512 \
    --environment Variables={AWS_REGION=us-east-1} \
    --region us-east-1
```

**Important**: Create IAM role with:
- AWSLambdaBasicExecutionRole (for CloudWatch logs)
- SecretsManagerReadWrite (for reading API key)

### Step 5: Create API Gateway

1. Go to AWS Console → API Gateway
2. Create REST API
3. Create resource: `/api`
4. Create method: `ANY` → Integration type: Lambda
5. Enable CORS
6. Deploy to stage: `prod`

**CORS Configuration**:
```json
{
  "Access-Control-Allow-Origin": "*",  // Change to your domain in production
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type"
}
```

### Step 6: Deploy Frontend to S3

Build React app:
```bash
cd frontend

# Update API endpoint in .env.production
echo "VITE_API_URL=https://YOUR-API-GATEWAY-URL.execute-api.us-east-1.amazonaws.com/prod" > .env.production

npm run build
```

Create S3 bucket:
```bash
aws s3 mb s3://infrasketch-frontend
aws s3 website s3://infrasketch-frontend --index-document index.html --error-document index.html
```

Upload build:
```bash
cd dist
aws s3 sync . s3://infrasketch-frontend --acl public-read
```

### Step 7: Create CloudFront Distribution

1. Go to CloudFront → Create Distribution
2. Origin: Your S3 bucket
3. Viewer Protocol Policy: Redirect HTTP to HTTPS
4. Default Root Object: `index.html`
5. Error Pages: 404 → /index.html (for React routing)

**Result**: `https://d123456.cloudfront.net`

---

## Deployment Option 2: EC2 (Traditional)

**Cost**: ~$15-25/month
**Scaling**: Manual
**Maintenance**: Higher

### Step 1: Launch EC2 Instance

- Instance type: `t3.small` (2GB RAM, 2 vCPU)
- AMI: Ubuntu 22.04 LTS
- Security Group: Allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)

### Step 2: Setup EC2

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install dependencies
sudo apt update
sudo apt install python3.11 python3-pip nginx nodejs npm -y

# Install PM2 for process management
sudo npm install -g pm2
```

### Step 3: Deploy Backend

```bash
# Clone repo (or upload via SCP)
git clone https://github.com/yourusername/infrasketch.git
cd infrasketch/backend

# Install dependencies
pip3 install -r requirements.txt

# Create .env or use Secrets Manager
# If using Secrets Manager, ensure EC2 has IAM role with SecretsManager permissions

# Start with PM2
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name infrasketch-backend
pm2 save
pm2 startup
```

### Step 4: Deploy Frontend

```bash
cd ../frontend
npm install
npm run build

# Copy build to nginx
sudo cp -r dist/* /var/www/html/
```

### Step 5: Configure Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /var/www/html;
        try_files $uri /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo systemctl restart nginx
```

### Step 6: SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

## Environment Variables

### Backend

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key (fallback) | Yes* | - |
| `AWS_REGION` | AWS region for Secrets Manager | No | `us-east-1` |
| `LANGSMITH_TRACING` | Enable LangSmith tracing | No | `False` |

*Required if not using AWS Secrets Manager

### Frontend

| Variable | Description | Required |
|----------|-------------|----------|
| `VITE_API_URL` | Backend API URL | Yes |

Example `.env.production`:
```
VITE_API_URL=https://api.infrasketch.com
```

---

## Cost Estimates

### Serverless (Lambda + S3 + CloudFront)
- **Light usage** (1k requests/month): $5-8/month
- **Moderate usage** (100k requests/month): $15-25/month
- **Heavy usage** (1M requests/month): $50-100/month

Breakdown:
- S3: $0.50/month
- CloudFront: $1-10/month (data transfer)
- API Gateway: $3.50 per million requests
- Lambda: $0.20 per 100k requests (3s avg, 512MB)
- Secrets Manager: $0.40/month

### EC2 (t3.small)
- **Fixed cost**: $15-20/month (instance)
- Data transfer: $1-5/month
- **Total**: ~$20-25/month

---

## Security Checklist

Before going live:

- [ ] API key stored in AWS Secrets Manager (not in code)
- [ ] `.env` file in `.gitignore` (never committed)
- [ ] CORS restricted to your domain only
- [ ] HTTPS enabled everywhere
- [ ] API Gateway rate limiting enabled (e.g., 100 req/min)
- [ ] Lambda function has minimal IAM permissions
- [ ] CloudFront prevents direct S3 access (Origin Access Identity)
- [ ] Security headers configured (CSP, X-Frame-Options)

---

## Testing Deployment

### Test Backend
```bash
curl https://your-api-gateway-url/api/health
# Expected: {"status": "healthy"}
```

### Test Secrets Manager Integration
```bash
# SSH into Lambda or EC2
python3 -c "from app.utils.secrets import get_anthropic_api_key; print('✓ API key loaded')"
```

### Test Frontend
1. Visit CloudFront URL
2. Open browser console (should show no errors)
3. Generate a diagram
4. Check backend logs

---

## Troubleshooting

### "Could not retrieve secret"
- Check AWS credentials: `aws sts get-caller-identity`
- Verify secret exists: `aws secretsmanager list-secrets`
- Check IAM permissions for Lambda/EC2

### CORS errors
- Update API Gateway CORS settings
- Check backend CORS configuration in `main.py`

### Lambda timeout
- Increase timeout (max 15 minutes)
- Increase memory (improves CPU)

### Cold starts
- Use provisioned concurrency (costs more)
- Or accept 1-2 second cold start

---

## Monitoring

### CloudWatch Logs
```bash
# View Lambda logs
aws logs tail /aws/lambda/infrasketch-backend --follow
```

### Metrics to Monitor
- Lambda invocations
- API Gateway 4xx/5xx errors
- Lambda duration (watch for timeouts)
- CloudFront cache hit ratio

---

## Updating Deployment

### Backend Updates
```bash
# Lambda
cd backend
./deploy-lambda.sh  # Create this script

# EC2
ssh into-instance
cd infrasketch/backend
git pull
pm2 restart infrasketch-backend
```

### Frontend Updates
```bash
npm run build
aws s3 sync dist/ s3://infrasketch-frontend
aws cloudfront create-invalidation --distribution-id YOUR-ID --paths "/*"
```

---

## Next Steps

1. **Custom Domain**: Route 53 + ACM certificate
2. **CI/CD**: GitHub Actions for automatic deployments
3. **Database**: Add DynamoDB for persistent sessions
4. **Monitoring**: Set up CloudWatch alarms
5. **Analytics**: Add Google Analytics or Plausible

---

## Support

For issues with deployment, check:
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
