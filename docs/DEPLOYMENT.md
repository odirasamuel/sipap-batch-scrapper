# Batch Scraper Automated Deployment

**No manual builds required** - All builds are automated via GitHub Actions.

## Overview

The batch scraper uses **automated CI/CD** with GitHub Actions:
- Lambda packages built automatically and uploaded to S3
- Docker images built automatically and pushed to ECR
- ECS task definitions updated automatically

## Prerequisites

### 1. Configure GitHub Secrets

Add the following secret to the sipap-batch-scraper repository:

- **Name**: `SIPAP_DEV_AWS_ROLE_ARN`
- **Value**: Get from cicd_infra terraform output

```bash
cd /Users/charlesotuya/AI-Odi/sentinel/sipap/repos/sipap-terraform/cicd_infra
terraform output github_actions_role_arn
```

### 2. Deploy CI/CD Infrastructure (One-Time)

```bash
cd /Users/charlesotuya/AI-Odi/sentinel/sipap/repos/sipap-terraform/cicd_infra

# Initialize and deploy S3 bucket for Lambda packages
terraform init
terraform apply
```

This creates:
- S3 bucket: `sipap-lambda-packages-dev`
- IAM role for GitHub Actions (OIDC-based, no AWS credentials needed)
- Bucket versioning + encryption + lifecycle policies

## Automated Workflows

### Workflow 1: Lambda Package Builder

**File**: `.github/workflows/build-lambda-packages.yml`

**Triggers**:
- Push to `main` branch (when `src/`, `requirements.txt`, or scripts change)
- Manual workflow dispatch

**What it does**:
1. Builds both Lambda packages (odds_updater, fixture_updater) for ARM64
2. Uploads to S3: `s3://sipap-lambda-packages-dev/batch-scraper/*.zip`
3. If Lambda functions exist, updates them automatically with new code

**How to trigger manually**:
- Go to GitHub → Actions → "Build & Upload Lambda Packages" → Run workflow

### Workflow 2: Docker Image Builder

**File**: `.github/workflows/build-batch-scraper-image.yml`

**Triggers**:
- Push to `main` branch (when `src/`, `requirements.txt`, or `Dockerfile` changes)
- Manual workflow dispatch

**What it does**:
1. Builds Docker image for daily harvest job (linux/amd64)
2. Pushes to ECR: `sipap-dev-batch-scraper:latest`
3. If ECS task definition exists, creates new revision automatically

**How to trigger manually**:
- Go to GitHub → Actions → "Build & Push Batch Scraper Image" → Run workflow

## Deployment Process

### Initial Deployment

**Step 1**: Deploy CI/CD infrastructure (cicd_infra/)
```bash
cd sipap-terraform/cicd_infra
terraform apply
```

**Step 2**: Push code to trigger builds
```bash
cd sipap-batch-scraper
git add .
git commit -m "Trigger builds"
git push origin main
```

Wait for GitHub Actions to complete (~5 minutes):
- Lambda packages uploaded to S3
- Docker image pushed to ECR

**Step 3**: Deploy events infrastructure
```bash
cd sipap-terraform/events
terraform init
terraform apply
```

Terraform will:
- Pull Lambda packages from S3
- Pull Docker image from ECR
- Create Lambda functions + ECS task definition
- Set up EventBridge schedules

### Updating Code

**Zero manual steps required!**

1. Make changes to code
2. Commit and push to main branch
3. GitHub Actions automatically:
   - Build new Lambda packages → upload to S3 → update Lambda functions
   - Build new Docker image → push to ECR → update ECS task definition

```bash
cd sipap-batch-scraper

# Make your changes
vim src/sipap_batch_scraper/jobs/odds_updater.py

# Commit and push
git add .
git commit -m "Update odds updater logic"
git push origin main

# GitHub Actions handles everything automatically!
```

### Monitoring Deployments

**GitHub Actions**:
- Check workflow runs: https://github.com/odirasamuel/sipap-batch-scraper/actions

**AWS**:
```bash
# Check S3 Lambda packages
aws s3 ls s3://sipap-lambda-packages-dev/batch-scraper/ --profile odiraaws

# Check Lambda function versions
aws lambda list-versions-by-function --function-name sipap-dev-odds-updater --profile odiraaws --region us-east-1

# Check ECR images
aws ecr describe-images --repository-name sipap-dev-batch-scraper --profile odiraaws --region us-east-1

# Check ECS task definition revisions
aws ecs list-task-definitions --family-prefix sipap-dev-daily-harvest --profile odiraaws --region us-east-1
```

## Cost

**Infrastructure**: $0.21/month
- Fargate daily harvest: $0.05/month
- Lambda odds updater: $0.01/month
- Lambda fixture updater: $0.15/month

**S3 Storage**: <$0.01/month
- ~24 MB total (2 Lambda packages)
- Versioning enabled (old versions deleted after 90 days)

**Total**: ~$0.22/month

## Troubleshooting

### GitHub Actions Failing

**Check permissions**:
```bash
# Verify IAM role ARN in GitHub secrets matches terraform output
cd sipap-terraform/cicd_infra
terraform output github_actions_role_arn
```

**Check GitHub Actions logs**:
- Go to repository → Actions → Click failed workflow → View logs

### Lambda Update Not Working

**Symptom**: Code changes not reflected in Lambda execution

**Solution**:
```bash
# Manually trigger function update from S3
aws lambda update-function-code \
  --function-name sipap-dev-odds-updater \
  --s3-bucket sipap-lambda-packages-dev \
  --s3-key batch-scraper/odds_updater.zip \
  --publish \
  --profile odiraaws \
  --region us-east-1
```

### Docker Image Update Not Working

**Symptom**: ECS task still using old image

**Solution**:
```bash
# Force new task definition revision
cd sipap-terraform/events
terraform apply -replace=aws_ecs_task_definition.daily_harvest
```

## Manual Builds (Emergency Only)

If GitHub Actions are down, you can build manually:

### Lambda Packages
```bash
cd sipap-batch-scraper
./scripts/build_lambda_packages.sh

# Upload manually
aws s3 cp ../sipap-terraform/lambda_packages/odds_updater.zip \
  s3://sipap-lambda-packages-dev/batch-scraper/ \
  --profile odiraaws
```

### Docker Image
```bash
cd sipap-batch-scraper

ECR_REPO=$(cd ../sipap-terraform && terraform output -json ecr_repository_urls | jq -r '.["batch-scraper"]')

docker build -t sipap-batch-scraper:latest .
docker tag sipap-batch-scraper:latest $ECR_REPO:latest
aws ecr get-login-password --region us-east-1 --profile odiraaws | \
  docker login --username AWS --password-stdin $ECR_REPO
docker push $ECR_REPO:latest
```

---

**Key Point**: Once initial setup is complete, **just push code to main** and everything deploys automatically. No manual builds ever needed.
