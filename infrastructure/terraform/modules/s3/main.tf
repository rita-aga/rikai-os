# S3 Module for RikaiOS
# Creates S3 bucket for document storage (replaces MinIO)

variable "environment" {
  type = string
}

variable "project_name" {
  type    = string
  default = "rikaios"
}

variable "bucket_suffix" {
  description = "Suffix to make bucket name unique (e.g., account ID)"
  type        = string
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}

# S3 Bucket
resource "aws_s3_bucket" "documents" {
  bucket = var.bucket_suffix != "" ? "${var.project_name}-${var.environment}-documents-${var.bucket_suffix}" : "${var.project_name}-${var.environment}-documents"

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-documents"
  })
}

# Enable versioning
resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rules for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    id     = "intelligent-tiering"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER_IR"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# CORS configuration (for web dashboard if needed)
resource "aws_s3_bucket_cors_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]  # Restrict in production
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# IAM Policy for ECS tasks to access bucket
resource "aws_iam_policy" "s3_access" {
  name        = "${var.project_name}-${var.environment}-s3-access"
  description = "Policy for ECS tasks to access RikaiOS documents bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })

  tags = var.tags
}

# Outputs
output "bucket_name" {
  value = aws_s3_bucket.documents.id
}

output "bucket_arn" {
  value = aws_s3_bucket.documents.arn
}

output "bucket_regional_domain_name" {
  value = aws_s3_bucket.documents.bucket_regional_domain_name
}

output "s3_access_policy_arn" {
  value = aws_iam_policy.s3_access.arn
}
