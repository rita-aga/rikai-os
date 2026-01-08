# RikaiOS AWS Deployment Plan

## Status: Phases 1-4 Complete

---

## Phase 1: pgvector Migration ✅

**Commits:** `2d330da`, `b50dd3c`

Replaced Qdrant with pgvector for simpler infrastructure (single database).

### Changes Made
| File | Change |
|------|--------|
| `rikaios/umi/storage/base.py` | NEW - Abstract VectorStorageAdapter base class |
| `rikaios/umi/storage/pgvector.py` | NEW - PgVectorAdapter implementation |
| `rikaios/umi/storage/vectors.py` | Kept EmbeddingProvider classes, VectorAdapter for legacy |
| `rikaios/umi/client.py` | Uses PgVectorAdapter by default based on config |
| `rikaios/core/config.py` | Added `vector_backend` setting (pgvector/qdrant) |
| `rikaios/core/models.py` | Added `vector_backend` to UmiConfig |
| `docker/docker-compose.yml` | Removed Qdrant service |
| `docker/init/postgres/01-init.sql` | Added embeddings table with vector column |
| `pyproject.toml` | Replaced qdrant-client with pgvector |

### Configuration
```bash
RIKAI_VECTOR_BACKEND=pgvector  # default
RIKAI_VECTOR_BACKEND=qdrant    # legacy support
```

---

## Phase 2: AWS Infrastructure (Terraform) ✅

**Commit:** `dbb46b9`

Created Terraform modules for AWS deployment.

### Architecture
```
┌─────────────────────────────────────────────────────────────────────┐
│                           AWS Region                                 │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                         VPC                                  │    │
│  │  ┌─────────────────┐    ┌─────────────────┐                 │    │
│  │  │  Public Subnet  │    │  Public Subnet  │                 │    │
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
│  ┌──────────────┐  ┌──────────────┐                                 │
│  │     S3       │  │     ECR      │                                 │
│  └──────────────┘  └──────────────┘                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Terraform Modules
| Module | Path | Description |
|--------|------|-------------|
| VPC | `infrastructure/terraform/modules/vpc/` | VPC, subnets, NAT gateway |
| Aurora | `infrastructure/terraform/modules/aurora/` | Aurora PostgreSQL Serverless v2 |
| S3 | `infrastructure/terraform/modules/s3/` | Document storage bucket |
| ECR | `infrastructure/terraform/modules/ecr/` | Container registry |
| ECS | `infrastructure/terraform/modules/ecs/` | Fargate cluster, services, ALB |

### Deployment
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

---

## Phase 3: CI/CD and S3 IAM Role Support ✅

**Commit:** `f3d28b8`

Added GitHub Actions workflows and S3 IAM role support for ECS.

### Changes Made
| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | NEW - Lint, test, build on PR/push |
| `.github/workflows/deploy.yml` | NEW - ECR push, ECS deploy |
| `infrastructure/terraform/modules/ecr/` | NEW - ECR Terraform module |
| `rikaios/umi/storage/objects.py` | Added IAM role support |
| `rikaios/umi/client.py` | S3/MinIO conditional logic |
| `rikaios/core/config.py` | Added S3 settings |
| `rikaios/core/models.py` | Added S3 settings to UmiConfig |

### S3 Configuration
```bash
# AWS S3 with IAM role (ECS/EC2)
RIKAI_S3_BUCKET=my-bucket
RIKAI_S3_REGION=us-west-2
RIKAI_S3_USE_IAM_ROLE=true

# MinIO (local development) - used if S3_BUCKET is empty
RIKAI_MINIO_ENDPOINT=localhost:9000
RIKAI_MINIO_ACCESS_KEY=rikai
RIKAI_MINIO_SECRET_KEY=password
RIKAI_MINIO_BUCKET=rikai-documents
```

### CI/CD Workflows
- **ci.yml**: Runs on PR/push to main
  - Lint with ruff
  - Type check with mypy
  - Test with pytest (uses PostgreSQL + MinIO services)

- **deploy.yml**: Runs on push to main or manual trigger
  - Build Docker image
  - Push to ECR
  - Deploy to ECS

---

## Phase 4: rikai-code Submodule ✅

**Commit:** `2d330da`

Added rikai-code as a git submodule (Letta Code fork for CLI).

### Submodule Configuration
```
[submodule "rikai-code"]
    path = rikai-code
    url = https://github.com/rita-aga/rikai-code.git
```

### Usage
```bash
# Initialize submodule after clone
git submodule update --init --recursive

# Run rikai CLI
cd rikai-code && bun run rikai.js
```

---

## Phase 5: Future Enhancements (Deferred)

### 5.1 OpenSearch Adapter
When pgvector hits scale limits (>1M vectors), implement OpenSearch adapter.

**File:** `rikaios/umi/storage/opensearch.py`
- Implement `OpenSearchAdapter` using same `VectorStorageAdapter` interface
- Configure via `RIKAI_VECTOR_BACKEND=opensearch`

### 5.2 Web Dashboard
React/Next.js frontend for browser-based access.

**Structure:**
```
web/
  src/
    app/
      page.tsx          # Home/chat
      entities/page.tsx # Entity browser
      settings/page.tsx # Configuration
    components/
      ChatInterface.tsx
      EntityManager.tsx
```

---

## Estimated AWS Costs (dev environment)

| Resource | Monthly Cost |
|----------|-------------|
| Aurora Serverless v2 (0.5 ACU min) | ~$45 |
| NAT Gateway | ~$32 |
| ALB | ~$16 |
| ECS Fargate (2 tasks) | ~$30 |
| S3 | Pay per use |
| **Total** | **~$125/month** |

---

## Quick Reference

### Local Development
```bash
# Start infrastructure
docker-compose -f docker/docker-compose.yml up -d

# Run tests
pytest

# Check status
rikai status
```

### AWS Deployment
```bash
# 1. Create SSM parameters for API keys
aws ssm put-parameter --name "/rikaios/dev/voyage-api-key" --type "SecureString" --value "your-key"
aws ssm put-parameter --name "/rikaios/dev/anthropic-api-key" --type "SecureString" --value "your-key"

# 2. Deploy infrastructure
cd infrastructure/terraform
terraform apply

# 3. Push Docker image (or use CI/CD)
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com
docker build -t rikaios .
docker push <account>.dkr.ecr.us-west-2.amazonaws.com/rikaios:latest
```
