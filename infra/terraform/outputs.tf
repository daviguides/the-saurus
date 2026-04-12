output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = module.eks.cluster_endpoint
}

output "aurora_endpoint" {
  description = "Aurora writer endpoint"
  value       = module.aurora.cluster_endpoint
}

output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = module.elasticache.primary_endpoint
}

output "langfuse_bucket_name" {
  description = "Langfuse S3 bucket name"
  value       = module.s3.langfuse_bucket_name
}

output "artifacts_bucket_name" {
  description = "Pipeline artifacts S3 bucket name"
  value       = module.s3.artifacts_bucket_name
}

output "oidc_provider_arn" {
  description = "EKS OIDC provider ARN for IRSA"
  value       = module.eks.oidc_provider_arn
}
