# ECS Fargate Module for RikaiOS
# Creates ECS cluster, services, and task definitions

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

variable "public_subnet_ids" {
  type = list(string)
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

# Container configurations
variable "rikaios_api_image" {
  type = string
}

variable "letta_image" {
  type    = string
  default = "letta/letta:latest"
}

variable "api_cpu" {
  type    = number
  default = 512
}

variable "api_memory" {
  type    = number
  default = 1024
}

variable "api_desired_count" {
  type    = number
  default = 1
}

variable "letta_cpu" {
  type    = number
  default = 1024
}

variable "letta_memory" {
  type    = number
  default = 2048
}

# Database configuration
variable "database_url_ssm_arn" {
  description = "ARN of SSM parameter containing database URL"
  type        = string
}

variable "database_security_group_id" {
  type = string
}

# S3 configuration
variable "s3_bucket_name" {
  type = string
}

variable "s3_access_policy_arn" {
  type = string
}

# API Keys
variable "voyage_api_key_arn" {
  type    = string
  default = ""
}

variable "anthropic_api_key_arn" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-cluster"
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.project_name}-${var.environment}/api"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "letta" {
  name              = "/ecs/${var.project_name}-${var.environment}/letta"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = var.tags
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.project_name}-${var.environment}-ecs-"
  description = "Security group for ECS tasks"
  vpc_id      = var.vpc_id

  # Allow inbound from ALB (API)
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "API from ALB"
  }

  # Allow Letta port from within VPC
  ingress {
    from_port   = 8283
    to_port     = 8283
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "Letta from VPC"
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-ecs-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Security Group for ALB
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-${var.environment}-alb-"
  description = "Security group for Application Load Balancer"
  vpc_id      = var.vpc_id

  # Allow HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }

  # Allow HTTP (redirect to HTTPS)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-alb-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-${var.environment}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for SSM parameter access
resource "aws_iam_role_policy" "ecs_execution_ssm" {
  name = "ssm-parameters"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter"
        ]
        Resource = compact([
          var.database_url_ssm_arn,
          var.voyage_api_key_arn,
          var.anthropic_api_key_arn
        ])
      },
      {
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = "*"
      }
    ]
  })
}

# IAM Role for ECS Task
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-${var.environment}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

# Attach S3 policy to task role
resource "aws_iam_role_policy_attachment" "ecs_task_s3" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = var.s3_access_policy_arn
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "prod"

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-alb"
  })
}

# Target Group for API
resource "aws_lb_target_group" "api" {
  name        = "${var.project_name}-${var.environment}-api"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = var.tags
}

# ALB Listener (HTTP - redirect to HTTPS in prod)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# RikaiOS API Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-${var.environment}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "rikaios-api"
      image = var.rikaios_api_image
      essential = true

      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]

      environment = [
        { name = "RIKAI_VECTOR_BACKEND", value = "pgvector" },
        { name = "RIKAI_S3_BUCKET", value = var.s3_bucket_name },
        { name = "RIKAI_S3_USE_IAM_ROLE", value = "true" },
        { name = "AWS_REGION", value = var.aws_region },
      ]

      secrets = [
        {
          name      = "RIKAI_POSTGRES_URL"
          valueFrom = var.database_url_ssm_arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = var.tags
}

# RikaiOS API Service
resource "aws_ecs_service" "api" {
  name            = "rikaios-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "rikaios-api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]

  tags = var.tags
}

# Letta Task Definition
resource "aws_ecs_task_definition" "letta" {
  family                   = "${var.project_name}-${var.environment}-letta"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.letta_cpu
  memory                   = var.letta_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "letta"
      image     = var.letta_image
      essential = true

      portMappings = [{
        containerPort = 8283
        protocol      = "tcp"
      }]

      environment = []

      secrets = [
        {
          name      = "LETTA_PG_URI"
          valueFrom = var.database_url_ssm_arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.letta.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8283/v1/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = var.tags
}

# Letta Service
resource "aws_ecs_service" "letta" {
  name            = "letta"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.letta.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  # Service discovery for internal access
  service_registries {
    registry_arn = aws_service_discovery_service.letta.arn
  }

  tags = var.tags
}

# Service Discovery for Letta
resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "${var.project_name}.local"
  description = "Private DNS namespace for RikaiOS services"
  vpc         = var.vpc_id

  tags = var.tags
}

resource "aws_service_discovery_service" "letta" {
  name = "letta"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# Outputs
output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "cluster_arn" {
  value = aws_ecs_cluster.main.arn
}

output "api_service_name" {
  value = aws_ecs_service.api.name
}

output "letta_service_name" {
  value = aws_ecs_service.letta.name
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "alb_zone_id" {
  value = aws_lb.main.zone_id
}

output "ecs_security_group_id" {
  value = aws_security_group.ecs_tasks.id
}

output "letta_service_discovery_name" {
  value = "letta.${var.project_name}.local"
}
