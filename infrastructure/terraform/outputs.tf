# RikaiOS AWS Infrastructure Outputs

# VPC
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

# Aurora
output "aurora_endpoint" {
  description = "Aurora cluster endpoint"
  value       = module.aurora.cluster_endpoint
}

output "aurora_reader_endpoint" {
  description = "Aurora cluster reader endpoint"
  value       = module.aurora.cluster_reader_endpoint
}

output "aurora_database_name" {
  description = "Aurora database name"
  value       = module.aurora.database_name
}

output "aurora_password_ssm_arn" {
  description = "ARN of SSM parameter containing database password"
  value       = module.aurora.password_ssm_arn
}

# S3
output "s3_bucket_name" {
  description = "S3 bucket name for documents"
  value       = module.s3.bucket_name
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = module.s3.bucket_arn
}

# ECS
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "api_service_name" {
  description = "ECS API service name"
  value       = module.ecs.api_service_name
}

output "letta_service_name" {
  description = "ECS Letta service name"
  value       = module.ecs.letta_service_name
}

output "alb_dns_name" {
  description = "ALB DNS name for API access"
  value       = module.ecs.alb_dns_name
}

output "letta_internal_endpoint" {
  description = "Internal endpoint for Letta service"
  value       = "http://${module.ecs.letta_service_discovery_name}:8283"
}

# Deployment Info
output "api_url" {
  description = "URL to access the RikaiOS API"
  value       = "http://${module.ecs.alb_dns_name}"
}

output "database_url_ssm_arn" {
  description = "ARN of SSM parameter containing full database URL"
  value       = aws_ssm_parameter.db_url.arn
}
