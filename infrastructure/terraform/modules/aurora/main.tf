# Aurora PostgreSQL Module for RikaiOS
# Creates Aurora Serverless v2 cluster with pgvector support

variable "environment" {
  type = string
}

variable "project_name" {
  type    = string
  default = "rikaios"
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "db_name" {
  type    = string
  default = "rikai"
}

variable "db_username" {
  type    = string
  default = "rikai"
}

variable "min_capacity" {
  type    = number
  default = 0.5
}

variable "max_capacity" {
  type    = number
  default = 4
}

variable "allowed_security_groups" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}

# Random password for database
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store password in SSM Parameter Store
resource "aws_ssm_parameter" "db_password" {
  name        = "/${var.project_name}/${var.environment}/db/password"
  description = "RikaiOS database password"
  type        = "SecureString"
  value       = random_password.db_password.result

  tags = var.tags
}

# Security Group for Aurora
resource "aws_security_group" "aurora" {
  name_prefix = "${var.project_name}-${var.environment}-aurora-"
  description = "Security group for Aurora PostgreSQL"
  vpc_id      = var.vpc_id

  # Allow PostgreSQL from VPC
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "PostgreSQL from VPC"
  }

  # Allow from specified security groups
  dynamic "ingress" {
    for_each = var.allowed_security_groups
    content {
      from_port       = 5432
      to_port         = 5432
      protocol        = "tcp"
      security_groups = [ingress.value]
      description     = "PostgreSQL from allowed security groups"
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-aurora-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "aurora" {
  name        = "${var.project_name}-${var.environment}-aurora"
  description = "Subnet group for Aurora PostgreSQL"
  subnet_ids  = var.private_subnet_ids

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-aurora-subnet-group"
  })
}

# Parameter Group with pgvector support
resource "aws_rds_cluster_parameter_group" "aurora" {
  name        = "${var.project_name}-${var.environment}-aurora-params"
  family      = "aurora-postgresql16"
  description = "RikaiOS Aurora PostgreSQL parameter group"

  # Performance tuning (pgvector is enabled via CREATE EXTENSION after cluster creation)
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  tags = var.tags
}

# Aurora Cluster
resource "aws_rds_cluster" "aurora" {
  cluster_identifier = "${var.project_name}-${var.environment}"
  engine             = "aurora-postgresql"
  engine_mode        = "provisioned"
  engine_version     = "16.4"
  database_name      = var.db_name
  master_username    = var.db_username
  master_password    = random_password.db_password.result

  vpc_security_group_ids          = [aws_security_group.aurora.id]
  db_subnet_group_name            = aws_db_subnet_group.aurora.name
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.aurora.name

  # Serverless v2 scaling
  serverlessv2_scaling_configuration {
    min_capacity = var.min_capacity
    max_capacity = var.max_capacity
  }

  # Backup configuration
  backup_retention_period = var.environment == "prod" ? 7 : 1
  preferred_backup_window = "03:00-04:00"

  # Deletion protection (enable in prod)
  deletion_protection = var.environment == "prod"
  skip_final_snapshot = var.environment != "prod"

  # Enable enhanced monitoring
  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-aurora"
  })
}

# Aurora Instance (Serverless v2)
resource "aws_rds_cluster_instance" "aurora" {
  identifier         = "${var.project_name}-${var.environment}-1"
  cluster_identifier = aws_rds_cluster.aurora.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora.engine
  engine_version     = aws_rds_cluster.aurora.engine_version

  # Performance insights (free for 7 days retention)
  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-aurora-instance"
  })
}

# Outputs
output "cluster_endpoint" {
  value = aws_rds_cluster.aurora.endpoint
}

output "cluster_reader_endpoint" {
  value = aws_rds_cluster.aurora.reader_endpoint
}

output "cluster_port" {
  value = aws_rds_cluster.aurora.port
}

output "database_name" {
  value = aws_rds_cluster.aurora.database_name
}

output "master_username" {
  value = aws_rds_cluster.aurora.master_username
}

output "password_ssm_arn" {
  value = aws_ssm_parameter.db_password.arn
}

output "security_group_id" {
  value = aws_security_group.aurora.id
}

output "connection_string" {
  value     = "postgresql://${aws_rds_cluster.aurora.master_username}:${urlencode(random_password.db_password.result)}@${aws_rds_cluster.aurora.endpoint}:${aws_rds_cluster.aurora.port}/${aws_rds_cluster.aurora.database_name}"
  sensitive = true
}

output "connection_string_ssm" {
  description = "Connection string with SSM parameter reference for password"
  value       = "postgresql://${aws_rds_cluster.aurora.master_username}:$${DB_PASSWORD}@${aws_rds_cluster.aurora.endpoint}:${aws_rds_cluster.aurora.port}/${aws_rds_cluster.aurora.database_name}"
}
