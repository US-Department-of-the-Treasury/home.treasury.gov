output "s3_bucket_name" {
  description = "Name of the S3 bucket for static content"
  value       = aws_s3_bucket.site.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.site.arn
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.site.id
}

output "cloudfront_domain" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.site.domain_name
}

output "custom_domain" {
  description = "Custom domain name for the site (if enabled)"
  value       = var.enable_custom_domain ? var.domain_name : null
}

output "certificate_arn" {
  description = "ARN of the ACM certificate (if custom domain enabled)"
  value       = var.enable_custom_domain ? aws_acm_certificate.main[0].arn : null
}

output "site_url" {
  description = "URL to access the site"
  value       = var.enable_custom_domain ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.site.domain_name}"
}
