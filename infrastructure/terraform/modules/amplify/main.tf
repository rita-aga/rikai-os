# AWS Amplify for Next.js Dashboard
# Deploys the RikaiOS dashboard to AWS Amplify

resource "aws_amplify_app" "dashboard" {
  name       = "${var.project_name}-dashboard-${var.environment}"
  repository = var.repository_url

  # Build settings for Next.js
  build_spec = <<-EOT
    version: 1
    frontend:
      phases:
        preBuild:
          commands:
            - cd dashboard
            - npm ci
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: dashboard/.next
        files:
          - '**/*'
      cache:
        paths:
          - dashboard/node_modules/**/*
          - dashboard/.next/cache/**/*
  EOT

  # Environment variables
  environment_variables = {
    NEXT_PUBLIC_API_URL = var.api_url
    NODE_ENV            = "production"
  }

  # Enable auto branch creation for feature branches
  enable_auto_branch_creation = false
  enable_branch_auto_build    = true
  enable_branch_auto_deletion = false

  # Platform - Next.js SSR support
  platform = "WEB_COMPUTE"

  # Custom rules for SPA routing
  custom_rule {
    source = "/<*>"
    status = "404-200"
    target = "/index.html"
  }

  tags = var.tags
}

# Main branch deployment
resource "aws_amplify_branch" "main" {
  app_id      = aws_amplify_app.dashboard.id
  branch_name = var.branch_name

  framework = "Next.js - SSR"
  stage     = var.environment == "prod" ? "PRODUCTION" : "DEVELOPMENT"

  environment_variables = {
    NEXT_PUBLIC_API_URL = var.api_url
  }

  enable_auto_build = true

  tags = var.tags
}

# Webhook for GitHub (if using manual triggers)
resource "aws_amplify_webhook" "main" {
  app_id      = aws_amplify_app.dashboard.id
  branch_name = aws_amplify_branch.main.branch_name
  description = "Trigger deployment from GitHub"
}
