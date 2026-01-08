# Amplify Module Outputs

output "app_id" {
  description = "Amplify App ID"
  value       = aws_amplify_app.dashboard.id
}

output "app_arn" {
  description = "Amplify App ARN"
  value       = aws_amplify_app.dashboard.arn
}

output "default_domain" {
  description = "Default Amplify domain (e.g., main.xxxxx.amplifyapp.com)"
  value       = "${aws_amplify_branch.main.branch_name}.${aws_amplify_app.dashboard.default_domain}"
}

output "dashboard_url" {
  description = "Full dashboard URL"
  value       = "https://${aws_amplify_branch.main.branch_name}.${aws_amplify_app.dashboard.default_domain}"
}

output "webhook_url" {
  description = "Webhook URL for manual deployments"
  value       = aws_amplify_webhook.main.url
}
