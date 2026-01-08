# Amplify Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "repository_url" {
  description = "GitHub repository URL (e.g., https://github.com/username/repo)"
  type        = string
}

variable "branch_name" {
  description = "Git branch to deploy"
  type        = string
  default     = "main"
}

variable "api_url" {
  description = "Backend API URL for the dashboard to connect to"
  type        = string
  default     = ""
}

variable "github_access_token" {
  description = "GitHub personal access token for repository access"
  type        = string
  sensitive   = true
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
