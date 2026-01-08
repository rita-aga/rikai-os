# RikaiOS AWS Infrastructure Variables

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "rikaios"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]
}

# Aurora Configuration
variable "aurora_instance_class" {
  description = "Aurora instance class (use db.serverless for Serverless v2)"
  type        = string
  default     = "db.serverless"
}

variable "aurora_min_capacity" {
  description = "Minimum ACU for Aurora Serverless v2"
  type        = number
  default     = 0.5
}

variable "aurora_max_capacity" {
  description = "Maximum ACU for Aurora Serverless v2"
  type        = number
  default     = 4
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "rikai"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "rikai"
}

# ECS Configuration
variable "api_cpu" {
  description = "CPU units for API container (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Memory for API container in MB"
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Desired number of API containers"
  type        = number
  default     = 1
}

variable "letta_cpu" {
  description = "CPU units for Letta container"
  type        = number
  default     = 1024
}

variable "letta_memory" {
  description = "Memory for Letta container in MB"
  type        = number
  default     = 2048
}

# Container Images
variable "rikaios_api_image" {
  description = "Docker image for RikaiOS API"
  type        = string
  default     = ""  # Set via terraform.tfvars or CI/CD
}

variable "letta_image" {
  description = "Docker image for Letta server"
  type        = string
  default     = "letta/letta:latest"
}

# API Keys (sensitive - pass via environment or secrets manager)
variable "voyage_api_key_arn" {
  description = "ARN of SSM parameter containing Voyage API key"
  type        = string
  default     = ""
}

variable "anthropic_api_key_arn" {
  description = "ARN of SSM parameter containing Anthropic API key"
  type        = string
  default     = ""
}

# Tags
variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
