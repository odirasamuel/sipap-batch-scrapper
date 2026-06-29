# SIPAP Batch Scraper Deployment Guide

**Version:** 1.0
**Date:** 2026-06-28
**Status:** Ready for Deployment

---

## Overview

This guide documents the deployment of 3 scheduled jobs to AWS:

1. **Daily Harvest** - Fargate task (runs daily at 12 AM UTC)
2. **Odds Updater** - Lambda function (runs daily at 11 PM UTC)
3. **Fixture Updater** - Lambda function (runs hourly)

**Total Infrastructure Cost:** $0.21/month
**Total API Cost:** $0/month (all free tier)

---

## Architecture Overview

```
EventBridge (Scheduler)
├─── Daily Harvest (12:00 AM UTC)
│    └─ Fargate Task: sipap-batch-scraper
│       ├─ Duration: 2-3 minutes
│       ├─ Cost: $0.05/month
│       └─ Coverage: 9 leagues (FD + TDB)
│
├─── Odds Updater (9:00 AM UTC)
│    └─ Lambda: sipap-odds-updater
│       ├─ Duration: 2 minutes
│       ├─ Cost: $0.01/month
│       └─ Coverage: 9 leagues (The Odds API)
│
└─── Fixture Updater (Every hour)
     └─ Lambda: sipap-fixture-updater
        ├─ Duration: 2 minutes
        ├─ Cost: $0.15/month
        └─ Coverage: 13 competitions (FD + TDB)

Storage Layer
├─ Aurora PostgreSQL (persistent storage)
└─ ElastiCache Redis (multi-tier cache)
```

---

## Secrets Manager Setup (REQUIRED)

All API keys and database credentials are stored securely in AWS Secrets Manager. This section must be completed **before** deploying any jobs.

### Step 1: Create API Keys Secret

```bash
# Create secret for API keys
aws secretsmanager create-secret \
  --name sipap/dev/api-keys \
  --description "SIPAP API keys for batch scraper jobs" \
  --secret-string '{
    "FOOTBALL_DATA_KEY": "your_football_data_api_key_here",
    "ODDS_API_KEY": "your_odds_api_key_here",
    "THESPORTSDB_KEY": "123"
  }' \
  --region us-east-1
```

**How to get API keys:**

1. **Football-Data.org API Key (FREE tier)**
   - Register at: https://www.football-data.org/client/register
   - Free tier: 10 requests/minute, FREE forever
   - Coverage: 13 competitions

2. **The Odds API Key (FREE tier)**
   - Register at: https://the-odds-api.com/
   - Free tier: 500 credits/month
   - Coverage: 9 soccer leagues

3. **TheSportsDB API Key (FREE tier)**
   - Use `"123"` for free tier (public test key)
   - Or get premium key at: https://www.thesportsdb.com/api.php

### Step 2: Create Aurora Credentials Secret

```bash
# Retrieve Aurora password from existing secret
AURORA_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id sipap/dev/aurora-password \
  --query SecretString \
  --output text \
  --region us-east-1)

# Get Aurora endpoint from Terraform outputs
AURORA_HOST=$(cd ../../sipap-terraform && terraform output -raw aurora_cluster_endpoint)

# Create Aurora credentials secret
aws secretsmanager create-secret \
  --name sipap/dev/aurora-credentials \
  --description "Aurora PostgreSQL credentials for SIPAP" \
  --secret-string "{
    \"username\": \"sipap_admin\",
    \"password\": \"${AURORA_PASSWORD}\",
    \"host\": \"${AURORA_HOST}\",
    \"port\": \"5432\",
    \"database\": \"sipap_dev\"
  }" \
  --region us-east-1
```

### Step 3: Verify Secrets Created

```bash
# List all SIPAP secrets
aws secretsmanager list-secrets \
  --filters Key=name,Values=sipap/ \
  --region us-east-1

# Verify API keys secret
aws secretsmanager get-secret-value \
  --secret-id sipap/dev/api-keys \
  --query SecretString \
  --output text \
  --region us-east-1 | jq

# Verify Aurora credentials secret
aws secretsmanager get-secret-value \
  --secret-id sipap/dev/aurora-credentials \
  --query SecretString \
  --output text \
  --region us-east-1 | jq
```

### Step 4: Update IAM Roles for Secrets Access

**Lambda Execution Role:**

```bash
# Create inline policy for Secrets Manager access
cat > lambda-secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:<account-id>:secret:sipap/dev/api-keys-*",
        "arn:aws:secretsmanager:us-east-1:<account-id>:secret:sipap/dev/aurora-credentials-*"
      ]
    }
  ]
}
EOF

# Attach policy to Lambda execution role
aws iam put-role-policy \
  --role-name sipap-dev-lambda-execution-role \
  --policy-name SecretsManagerAccess \
  --policy-document file://lambda-secrets-policy.json
```

**ECS Task Role:**

```bash
# Attach same policy to ECS task role (for Fargate daily harvest)
aws iam put-role-policy \
  --role-name sipap-dev-ecs-task-role \
  --policy-name SecretsManagerAccess \
  --policy-document file://lambda-secrets-policy.json
```

### Step 5: Test Secrets Retrieval (Optional)

Create a test Python script to verify Secrets Manager access:

```python
# test_secrets.py
import boto3
import json

def test_api_keys():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='sipap/dev/api-keys')
    secrets = json.loads(response['SecretString'])
    print("API Keys:", list(secrets.keys()))
    return secrets

def test_db_credentials():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='sipap/dev/aurora-credentials')
    creds = json.loads(response['SecretString'])
    print("DB Credentials:", list(creds.keys()))
    return creds

if __name__ == '__main__':
    api_keys = test_api_keys()
    db_creds = test_db_credentials()
    print("✅ All secrets retrieved successfully!")
```

Run the test:

```bash
python test_secrets.py
```

---

## Prerequisites

### 1. AWS Resources (Already Deployed)

✅ **From sipap-terraform:**
- VPC with public/private subnets
- Security groups
- Aurora PostgreSQL cluster (sipap-dev-cluster)
- ElastiCache Redis cluster
- ECS cluster (sipap-dev-cluster)
- IAM roles (ECS task role, Lambda execution role)
- CloudWatch log groups

### 2. Environment Variables

**Required environment variables for Lambda/Fargate:**

```bash
# Environment identifier (dev, staging, prod)
ENVIRONMENT=dev

# ElastiCache Redis URL (from Terraform outputs)
REDIS_URL=redis://sipap-dev-redis.xxxxx.0001.use1.cache.amazonaws.com:6379
```

**Note:** API keys and database credentials are fetched from AWS Secrets Manager at runtime for security. See "Secrets Manager Setup" section above.

### 3. Docker Image

Build and push the batch scraper Docker image:

```bash
cd repos/sipap-batch-scraper

# Build image
docker build -t sipap-batch-scraper:latest .

# Tag for ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker tag sipap-batch-scraper:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/sipap-batch-scraper:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/sipap-batch-scraper:latest
```

---

## Deployment 1: Daily Harvest (Fargate)

### Step 1: Create ECS Task Definition

**File:** `fargate-task-definition-daily-harvest.json`

**Note:** API keys and database credentials are fetched from Secrets Manager at runtime for security.

```json
{
  "family": "sipap-daily-harvest",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/sipap-dev-ecs-execution-role",
  "taskRoleArn": "arn:aws:iam::<account-id>:role/sipap-dev-ecs-task-role",
  "containerDefinitions": [
    {
      "name": "daily-harvest",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/sipap-batch-scraper:latest",
      "command": ["python", "-m", "sipap_batch_scraper.jobs.daily_harvest"],
      "essential": true,
      "environment": [
        {"name": "ENVIRONMENT", "value": "dev"},
        {"name": "REDIS_URL", "value": "${REDIS_URL}"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/sipap-daily-harvest",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

**Register task definition:**

```bash
aws ecs register-task-definition --cli-input-json file://fargate-task-definition-daily-harvest.json
```

### Step 2: Create EventBridge Rule

**Schedule:** Daily at 12:00 AM UTC

```bash
aws events put-rule \
  --name sipap-daily-harvest-schedule \
  --schedule-expression "cron(0 0 * * ? *)" \
  --description "Daily harvest job - runs at 12 AM UTC" \
  --state ENABLED
```

### Step 3: Create EventBridge Target

```json
{
  "Rule": "sipap-daily-harvest-schedule",
  "Targets": [
    {
      "Id": "1",
      "Arn": "arn:aws:ecs:us-east-1:<account-id>:cluster/sipap-dev-cluster",
      "RoleArn": "arn:aws:iam::<account-id>:role/sipap-dev-eventbridge-ecs-role",
      "EcsParameters": {
        "TaskDefinitionArn": "arn:aws:ecs:us-east-1:<account-id>:task-definition/sipap-daily-harvest:1",
        "TaskCount": 1,
        "LaunchType": "FARGATE",
        "NetworkConfiguration": {
          "awsvpcConfiguration": {
            "Subnets": ["subnet-xxxxx", "subnet-yyyyy"],
            "SecurityGroups": ["sg-xxxxx"],
            "AssignPublicIp": "ENABLED"
          }
        },
        "PlatformVersion": "LATEST"
      }
    }
  ]
}
```

**Add target:**

```bash
aws events put-targets --cli-input-json file://daily-harvest-target.json
```

---

## Deployment 2: Odds Updater (Lambda)

### Step 1: Package Lambda Function

```bash
cd repos/sipap-batch-scraper

# Create deployment package
mkdir -p lambda-package
pip install --target lambda-package -r requirements.txt
cp -r src/sipap_batch_scraper lambda-package/

cd lambda-package
zip -r ../odds-updater.zip .
cd ..
```

### Step 2: Create Lambda Function

**Note:** API keys and database credentials are fetched from Secrets Manager at runtime.

```bash
aws lambda create-function \
  --function-name sipap-odds-updater \
  --runtime python3.12 \
  --role arn:aws:iam::<account-id>:role/sipap-dev-lambda-execution-role \
  --handler sipap_batch_scraper.jobs.odds_updater.lambda_handler \
  --zip-file fileb://odds-updater.zip \
  --timeout 180 \
  --memory-size 1024 \
  --architectures arm64 \
  --environment Variables="{
    ENVIRONMENT=dev,
    REDIS_URL=${REDIS_URL}
  }" \
  --description "Daily odds updater - runs at 9 AM UTC" \
  --vpc-config SubnetIds=subnet-xxxxx,subnet-yyyyy,SecurityGroupIds=sg-xxxxx
```

### Step 3: Create EventBridge Rule

**Schedule:** Daily at 9:00 AM UTC

```bash
aws events put-rule \
  --name sipap-odds-updater-schedule \
  --schedule-expression "cron(0 9 * * ? *)" \
  --description "Odds updater - runs daily at 9 AM UTC" \
  --state ENABLED
```

### Step 4: Add EventBridge Permission to Lambda

```bash
aws lambda add-permission \
  --function-name sipap-odds-updater \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:<account-id>:rule/sipap-odds-updater-schedule
```

### Step 5: Create EventBridge Target

```bash
aws events put-targets \
  --rule sipap-odds-updater-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:<account-id>:function:sipap-odds-updater"
```

---

## Deployment 3: Fixture Updater (Lambda)

### Step 1: Package Lambda Function

```bash
cd repos/sipap-batch-scraper

# Reuse lambda-package from odds updater
cd lambda-package
zip -r ../fixture-updater.zip .
cd ..
```

### Step 2: Create Lambda Function

**Note:** API keys and database credentials are fetched from Secrets Manager at runtime.

```bash
aws lambda create-function \
  --function-name sipap-fixture-updater \
  --runtime python3.12 \
  --role arn:aws:iam::<account-id>:role/sipap-dev-lambda-execution-role \
  --handler sipap_batch_scraper.jobs.fixture_updater.lambda_handler \
  --zip-file fileb://fixture-updater.zip \
  --timeout 180 \
  --memory-size 1024 \
  --architectures arm64 \
  --environment Variables="{
    ENVIRONMENT=dev,
    REDIS_URL=${REDIS_URL}
  }" \
  --description "Hourly fixture updater - refreshes fixtures and standings" \
  --vpc-config SubnetIds=subnet-xxxxx,subnet-yyyyy,SecurityGroupIds=sg-xxxxx
```

### Step 3: Create EventBridge Rule

**Schedule:** Every hour

```bash
aws events put-rule \
  --name sipap-fixture-updater-schedule \
  --schedule-expression "rate(1 hour)" \
  --description "Fixture updater - runs hourly" \
  --state ENABLED
```

### Step 4: Add EventBridge Permission

```bash
aws lambda add-permission \
  --function-name sipap-fixture-updater \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:<account-id>:rule/sipap-fixture-updater-schedule
```

### Step 5: Create EventBridge Target

```bash
aws events put-targets \
  --rule sipap-fixture-updater-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:<account-id>:function:sipap-fixture-updater"
```

---

## Verification & Monitoring

### 1. Test Manual Invocations

**Daily Harvest (Fargate):**
```bash
aws ecs run-task \
  --cluster sipap-dev-cluster \
  --task-definition sipap-daily-harvest:1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}"
```

**Odds Updater (Lambda):**
```bash
aws lambda invoke \
  --function-name sipap-odds-updater \
  --payload '{}' \
  response.json

cat response.json
```

**Fixture Updater (Lambda):**
```bash
aws lambda invoke \
  --function-name sipap-fixture-updater \
  --payload '{}' \
  response.json

cat response.json
```

### 2. Monitor CloudWatch Logs

```bash
# Daily Harvest
aws logs tail /ecs/sipap-daily-harvest --follow

# Odds Updater
aws logs tail /aws/lambda/sipap-odds-updater --follow

# Fixture Updater
aws logs tail /aws/lambda/sipap-fixture-updater --follow
```

### 3. Verify EventBridge Rules

```bash
# List all SIPAP rules
aws events list-rules --name-prefix sipap-

# Check rule targets
aws events list-targets-by-rule --rule sipap-daily-harvest-schedule
aws events list-targets-by-rule --rule sipap-odds-updater-schedule
aws events list-targets-by-rule --rule sipap-fixture-updater-schedule
```

### 4. Check API Usage

**The Odds API:**
```bash
# Check remaining credits
curl -X GET "https://api.the-odds-api.com/v4/sports?apiKey=${ODDS_API_KEY}"
# Response headers include: x-requests-remaining, x-requests-used
```

**Football-Data.org:**
```bash
# Check rate limits
curl -X GET "https://api.football-data.org/v4/competitions" \
  -H "X-Auth-Token: ${FOOTBALL_DATA_KEY}"
# Response headers include: X-Requests-Available-Minute
```

### 5. Monitor Database

```bash
# Connect to Aurora
psql -h ${AURORA_HOST} -U sipap_admin -d sipap_dev

# Check fixture counts
SELECT COUNT(*) FROM matches;
SELECT COUNT(*) FROM odds;
SELECT COUNT(*) FROM standings;

# Check latest updates
SELECT MAX(updated_at) FROM matches;
SELECT MAX(updated_at) FROM odds;
```

---

## Cost Monitoring

### Expected Monthly Costs

| Component | Configuration | Monthly Cost |
|-----------|---------------|--------------|
| **Fargate Daily Harvest** | 0.25 vCPU, 0.5 GB, 3 min/day | $0.05 |
| **Lambda Odds Updater** | 1024 MB, 2 min/day, ARM64 | $0.01 |
| **Lambda Fixture Updater** | 1024 MB, 2 min/hour, ARM64 | $0.15 |
| **TOTAL** | | **$0.21/month** |

### Set Up Cost Alerts

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name sipap-batch-scraper-cost-alert \
  --alarm-description "Alert if batch scraper costs exceed $1/month" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 1.0 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ServiceName,Value=AmazonECS Name=ServiceName,Value=AWSLambda
```

---

## Troubleshooting

### Issue: Lambda Timeout

**Symptom:** Lambda function times out after 3 minutes

**Solution:**
```bash
aws lambda update-function-configuration \
  --function-name sipap-odds-updater \
  --timeout 300  # Increase to 5 minutes
```

### Issue: VPC Connectivity

**Symptom:** Lambda cannot connect to Aurora or Redis

**Solution:**
1. Verify security groups allow inbound traffic from Lambda security group
2. Check VPC route tables have route to NAT gateway
3. Verify Lambda is in private subnets with NAT gateway access

### Issue: High API Usage

**Symptom:** Approaching free tier limits

**Solution:**
1. Check CloudWatch logs for unexpected API calls
2. Verify EventBridge rules are not triggering too frequently
3. Review API error responses (429 rate limit errors)

### Issue: Fargate Task Fails to Start

**Symptom:** ECS task fails with "CannotPullContainerError"

**Solution:**
1. Verify ECR image exists and is accessible
2. Check ECS execution role has permissions to pull from ECR
3. Verify VPC has route to ECR service endpoint

---

## Rollback Procedure

### Disable All Jobs

```bash
# Disable EventBridge rules
aws events disable-rule --name sipap-daily-harvest-schedule
aws events disable-rule --name sipap-odds-updater-schedule
aws events disable-rule --name sipap-fixture-updater-schedule
```

### Delete Resources

```bash
# Delete EventBridge rules
aws events remove-targets --rule sipap-daily-harvest-schedule --ids 1
aws events delete-rule --name sipap-daily-harvest-schedule

aws events remove-targets --rule sipap-odds-updater-schedule --ids 1
aws events delete-rule --name sipap-odds-updater-schedule

aws events remove-targets --rule sipap-fixture-updater-schedule --ids 1
aws events delete-rule --name sipap-fixture-updater-schedule

# Delete Lambda functions
aws lambda delete-function --function-name sipap-odds-updater
aws lambda delete-function --function-name sipap-fixture-updater

# Deregister ECS task definition (optional)
aws ecs deregister-task-definition --task-definition sipap-daily-harvest:1
```

---

## Next Steps After Deployment

1. ✅ Monitor first 24 hours of execution
2. ✅ Verify data is populating Aurora tables
3. ✅ Check Redis cache hit rates
4. ✅ Monitor API usage (should stay within free tier)
5. ✅ Set up CloudWatch alarms for failures
6. ✅ Create operational runbook
7. ✅ Document incident response procedures

---

**Deployment Checklist:**
- [ ] API keys obtained and stored in AWS Secrets Manager (sipap/dev/api-keys)
- [ ] Aurora credentials stored in AWS Secrets Manager (sipap/dev/aurora-credentials)
- [ ] IAM roles updated with Secrets Manager permissions
- [ ] Docker image built and pushed to ECR
- [ ] Fargate task definition created and registered
- [ ] Lambda functions packaged and deployed
- [ ] EventBridge rules created and enabled
- [ ] Permissions configured (IAM roles, Lambda invoke permissions)
- [ ] VPC configuration verified (subnets, security groups)
- [ ] CloudWatch log groups created
- [ ] Manual test invocations successful
- [ ] Monitoring and alerting configured
- [ ] Cost tracking enabled
- [ ] Documentation complete

**Deployment Status:** ⏳ READY - Awaiting manual deployment

**Estimated Deployment Time:** 2-3 hours

**Post-Deployment Monitoring:** 24-48 hours
