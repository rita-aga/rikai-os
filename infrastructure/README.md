# RikaiOS AWS Infrastructure

Terraform configurations for deploying RikaiOS to AWS.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           AWS Region                                 │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                         VPC                                  │    │
│  │  ┌─────────────────┐    ┌─────────────────┐                 │    │
│  │  │  Public Subnet  │    │  Public Subnet  │                 │    │
│  │  │  (us-west-2a)   │    │  (us-west-2b)   │                 │    │
│  │  │    ┌─────┐      │    │                 │                 │    │
│  │  │    │ ALB │      │    │                 │                 │    │
│  │  │    └──┬──┘      │    │                 │                 │    │
│  │  └───────┼─────────┘    └─────────────────┘                 │    │
│  │          │                                                   │    │
│  │  ┌───────┼─────────┐    ┌─────────────────┐                 │    │
│  │  │  Private Subnet │    │  Private Subnet │                 │    │
│  │  │  ┌──────────────┴────┴──────────────┐  │                 │    │
│  │  │  │           ECS Fargate            │  │                 │    │
│  │  │  │  ┌──────────┐  ┌──────────┐     │  │                 │    │
│  │  │  │  │RikaiOS   │  │  Letta   │     │  │                 │    │
│  │  │  │  │  API     │  │  Server  │     │  │                 │    │
│  │  │  │  └────┬─────┘  └────┬─────┘     │  │                 │    │
│  │  │  └───────┼─────────────┼───────────┘  │                 │    │
│  │  │          │             │              │                 │    │
│  │  │  ┌───────┴─────────────┴───────┐     │                 │    │
│  │  │  │   Aurora PostgreSQL         │     │                 │    │
│  │  │  │   (Serverless v2 + pgvector)│     │                 │    │
│  │  │  └─────────────────────────────┘     │                 │    │
│  │  └──────────────────────────────────────┘                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────┐                                                   │
│  │     S3       │  Documents storage                                │
│  └──────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform >= 1.5.0
3. Docker for building container images

## Quick Start

```bash
# 1. Initialize Terraform
cd infrastructure/terraform
terraform init

# 2. Create terraform.tfvars from example
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# 3. Create API keys in SSM Parameter Store
aws ssm put-parameter \
  --name "/rikaios/dev/voyage-api-key" \
  --type "SecureString" \
  --value "your-voyage-api-key"

aws ssm put-parameter \
  --name "/rikaios/dev/anthropic-api-key" \
  --type "SecureString" \
  --value "your-anthropic-api-key"

# 4. Build and push Docker image
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com
docker build -t rikaios .
docker tag rikaios:latest <account>.dkr.ecr.us-west-2.amazonaws.com/rikaios:latest
docker push <account>.dkr.ecr.us-west-2.amazonaws.com/rikaios:latest

# 5. Update terraform.tfvars with image URI
# rikaios_api_image = "<account>.dkr.ecr.us-west-2.amazonaws.com/rikaios:latest"

# 6. Deploy
terraform plan
terraform apply
```

## Modules

| Module | Description |
|--------|-------------|
| `vpc` | VPC, subnets, NAT gateway, route tables |
| `aurora` | Aurora PostgreSQL Serverless v2 with pgvector |
| `s3` | S3 bucket for document storage |
| `ecs` | ECS Fargate cluster, services, ALB |

## Configuration

### Environment Variables (set in ECS task)

| Variable | Description |
|----------|-------------|
| `RIKAI_POSTGRES_URL` | Database connection string (from SSM) |
| `RIKAI_VECTOR_BACKEND` | `pgvector` (default) |
| `RIKAI_S3_BUCKET` | S3 bucket name |
| `RIKAI_S3_USE_IAM_ROLE` | `true` (uses ECS task role) |
| `RIKAI_VOYAGE_API_KEY` | Voyage AI API key (from SSM) |
| `ANTHROPIC_API_KEY` | Anthropic API key (from SSM) |

### Scaling

Aurora Serverless v2 automatically scales between `min_capacity` and `max_capacity` ACUs.

For ECS, modify `api_desired_count` or set up auto-scaling based on CPU/memory metrics.

## Costs

Estimated monthly costs (dev environment):
- Aurora Serverless v2 (0.5 ACU min): ~$45/month
- NAT Gateway: ~$32/month
- ALB: ~$16/month
- ECS Fargate (2 tasks): ~$30/month
- S3: Pay per use

**Total: ~$125/month** (can be lower with reserved capacity)

## Cleanup

```bash
terraform destroy
```

Note: If deletion protection is enabled (prod), disable it first in the AWS console.
