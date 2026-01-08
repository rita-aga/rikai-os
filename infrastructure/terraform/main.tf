# RikaiOS AWS Infrastructure
# Main Terraform configuration

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Uncomment for remote state (recommended for team use)
  # backend "s3" {
  #   bucket         = "rikaios-terraform-state"
  #   key            = "rikaios/terraform.tfstate"
  #   region         = "us-west-2"
  #   encrypt        = true
  #   dynamodb_table = "rikaios-terraform-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Local variables
locals {
  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
  })
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  environment        = var.environment
  project_name       = var.project_name
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  tags               = local.common_tags
}

# Aurora PostgreSQL Module
module "aurora" {
  source = "./modules/aurora"

  environment        = var.environment
  project_name       = var.project_name
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  db_name            = var.db_name
  db_username        = var.db_username
  min_capacity       = var.aurora_min_capacity
  max_capacity       = var.aurora_max_capacity
  tags               = local.common_tags

  # Security group allows all VPC traffic (10.0.0.0/8) so ECS can connect
  allowed_security_groups = []

  depends_on = [module.vpc]
}

# S3 Module
module "s3" {
  source = "./modules/s3"

  environment   = var.environment
  project_name  = var.project_name
  bucket_suffix = data.aws_caller_identity.current.account_id
  tags          = local.common_tags
}

# ECR Module
module "ecr" {
  source = "./modules/ecr"

  environment           = var.environment
  project_name          = var.project_name
  image_retention_count = var.ecr_image_retention_count
}

# Store database connection string in SSM
resource "aws_ssm_parameter" "db_url" {
  name        = "/${var.project_name}/${var.environment}/db/url"
  description = "RikaiOS database connection URL"
  type        = "SecureString"
  value       = module.aurora.connection_string

  tags = local.common_tags
}

# ECS Module
module "ecs" {
  source = "./modules/ecs"

  environment        = var.environment
  project_name       = var.project_name
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids
  aws_region         = var.aws_region

  # Container configurations
  rikaios_api_image = var.rikaios_api_image
  letta_image       = var.letta_image
  api_cpu           = var.api_cpu
  api_memory        = var.api_memory
  api_desired_count = var.api_desired_count
  letta_cpu         = var.letta_cpu
  letta_memory      = var.letta_memory

  # Database
  database_url_ssm_arn       = aws_ssm_parameter.db_url.arn
  database_security_group_id = module.aurora.security_group_id

  # S3
  s3_bucket_name       = module.s3.bucket_name
  s3_access_policy_arn = module.s3.s3_access_policy_arn

  # API Keys (optional - create SSM parameters manually)
  voyage_api_key_arn    = var.voyage_api_key_arn
  anthropic_api_key_arn = var.anthropic_api_key_arn

  tags = local.common_tags

  depends_on = [module.vpc, module.aurora, module.s3]
}

# Amplify Module (Dashboard) - Disabled, set up via AWS Console
# module "amplify" {
#   source = "./modules/amplify"
#
#   environment    = var.environment
#   project_name   = var.project_name
#   repository_url = var.github_repository_url
#   branch_name    = var.github_branch
#   api_url        = "http://${module.ecs.alb_dns_name}"
#   tags           = local.common_tags
#
#   depends_on = [module.ecs]
# }
