# InfraSketch Deployment Guide

## Quick Deploy

### Deploy Everything
```bash
./deploy-all.sh
```

### Deploy Backend Only
```bash
./deploy-backend.sh
```

### Deploy Frontend Only
```bash
./deploy-frontend.sh
```

---

## What Gets Committed to Git

### ✅ Commit These Files

**Backend:**
- `backend/app/` - All application code
- `backend/requirements.txt` - Python dependencies
- `backend/lambda_handler.py` - Lambda entry point

**Frontend:**
- `frontend/src/` - All React source code
- `frontend/package.json` - NPM dependencies
- `frontend/.env.production` - Production API URL
- `frontend/index.html` - HTML template
- `frontend/vite.config.js` - Vite configuration

**Root:**
- `.gitignore` - Ignore rules
- `deploy-*.sh` - Deployment scripts
- `README.md` - Project documentation
- `DEPLOYMENT.md` - AWS deployment guide
- `DEPLOYMENT_GUIDE.md` - This file

### ❌ Don't Commit (Already in .gitignore)

**Secrets:**
- `.env` - Local environment variables
- `.env.local` - Local overrides
- Any files with API keys!

**Build Artifacts:**
- `backend/package/` - Lambda dependencies folder
- `backend/lambda-deployment.zip` - Lambda package
- `frontend/dist/` - Built frontend files
- `frontend/node_modules/` - NPM packages

---

## URLs

**Production:**
- Frontend: https://infrasketch.net
- API: https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod

**Local Development:**
- Frontend: http://localhost:5173
- API: http://localhost:8000

---

## Prerequisites for Deployment

1. **AWS CLI configured** with your credentials
   ```bash
   aws configure
   ```

2. **Node.js & NPM** installed (for frontend build)

3. **Python 3.11** and pip (for backend packaging)

---

## Deployment Process

### Manual Steps (First Time Only)

These were already done during initial setup:

1. ✅ Created AWS Secrets Manager secret
2. ✅ Created IAM role for Lambda
3. ✅ Created Lambda function
4. ✅ Created API Gateway
5. ✅ Created S3 bucket
6. ✅ Created CloudFront distribution

### Automated Steps (Every Deploy)

The deploy scripts handle:

**Backend (`deploy-backend.sh`):**
1. Clean old build artifacts
2. Install Python dependencies for Linux
3. Package code + dependencies
4. Upload to S3
5. Update Lambda function
6. Wait for update to complete

**Frontend (`deploy-frontend.sh`):**
1. Build React app with production settings
2. Upload to S3
3. Invalidate CloudFront cache
4. New version live in 1-2 minutes

---

## Typical Workflow

### Making Changes

1. **Make your code changes**
   ```bash
   # Edit files in backend/app/ or frontend/src/
   ```

2. **Test locally**
   ```bash
   # Terminal 1: Backend
   cd backend
   python3 -m uvicorn app.main:app --reload --port 8000

   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

3. **Commit changes**
   ```bash
   git add .
   git commit -m "Your change description"
   git push
   ```

4. **Deploy to production**
   ```bash
   # Deploy both frontend and backend
   ./deploy-all.sh

   # Or deploy individually
   ./deploy-backend.sh    # Backend changes only
   ./deploy-frontend.sh   # Frontend changes only
   ```

5. **Wait and test**
   - Backend: Ready immediately
   - Frontend: Wait 1-2 minutes for CloudFront cache

---

## Troubleshooting Deployments

### Backend deployment fails

**Check:**
- AWS credentials: `aws sts get-caller-identity`
- Lambda exists: `aws lambda get-function --function-name infrasketch-backend`
- S3 bucket exists: `aws s3 ls s3://infrasketch-lambda-deployments-059409992371`

**Common issues:**
- Pip install fails → Check internet connection
- S3 upload fails → Check AWS credentials
- Lambda update fails → Check IAM permissions

### Frontend deployment fails

**Check:**
- Build succeeds: `cd frontend && npm run build`
- S3 bucket exists: `aws s3 ls s3://infrasketch-frontend-059409992371`
- CloudFront ID correct: Check `deploy-frontend.sh`

**Common issues:**
- Build fails → Check `package.json` dependencies
- S3 sync fails → Check bucket permissions
- Changes not appearing → Wait for CloudFront cache (or hard refresh: Cmd+Shift+R)

### Site works but API calls fail

**Check:**
1. CORS settings in `backend/app/main.py`
2. API Gateway deployed: Go to AWS Console → API Gateway → Deploy API
3. Lambda function updated: Check "Last modified" time
4. `.env.production` has correct API URL

---

## Cost Monitoring

**Check your AWS bill:**
1. Go to AWS Console → Billing
2. Monitor these services:
   - Lambda: Invocations + duration
   - API Gateway: Requests
   - S3: Storage + requests
   - CloudFront: Data transfer
   - Secrets Manager: $0.40/month

**Expected costs:**
- Low traffic: $5-10/month
- Medium traffic: $15-25/month

---

## Rollback

If deployment breaks something:

### Backend Rollback
1. Go to Lambda Console
2. Click "Versions" tab
3. Find previous version
4. Click "Actions" → "Publish new version"
5. Update alias to point to old version

### Frontend Rollback
```bash
# Revert git changes
git revert HEAD

# Redeploy
./deploy-frontend.sh
```

---

## Adding New Environment Variables

### Backend
1. Add to AWS Secrets Manager OR Lambda environment variables
2. Update `backend/app/utils/secrets.py` if needed
3. Redeploy: `./deploy-backend.sh`

### Frontend
1. Add to `frontend/.env.production` (with `VITE_` prefix)
2. Redeploy: `./deploy-frontend.sh`

---

## Security Checklist

Before deploying:

- [ ] No API keys in code
- [ ] `.env` files in `.gitignore`
- [ ] CORS configured (not `*` in production ideally)
- [ ] API Gateway rate limiting enabled
- [ ] Monitor CloudWatch logs for errors
- [ ] S3 bucket not accidentally fully public (only CloudFront should access)

---

## Getting Help

- Check CloudWatch Logs: AWS Console → CloudWatch → Log groups → `/aws/lambda/infrasketch-backend`
- Check browser console for frontend errors
- Review [DEPLOYMENT.md](DEPLOYMENT.md) for detailed AWS setup
- Check [README.md](README.md) for local development
