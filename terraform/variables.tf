variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
  default     = "staging"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "treasury-home"
}

variable "enable_custom_domain" {
  description = "Enable custom domain with ACM certificate (disabled - Akamai handles domains)"
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Custom domain name for the site (only used if enable_custom_domain = true)"
  type        = string
  default     = ""
}

variable "route53_zone_name" {
  description = "Name of the Route53 hosted zone (only used if enable_custom_domain = true)"
  type        = string
  default     = ""
}
