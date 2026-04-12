output "langfuse_bucket_name" {
  description = "Name of the Langfuse storage bucket"
  value       = aws_s3_bucket.this["langfuse"].bucket
}

output "artifacts_bucket_name" {
  description = "Name of the pipeline artifacts bucket"
  value       = aws_s3_bucket.this["artifacts"].bucket
}

output "langfuse_bucket_arn" {
  description = "ARN of the Langfuse storage bucket"
  value       = aws_s3_bucket.this["langfuse"].arn
}

output "artifacts_bucket_arn" {
  description = "ARN of the pipeline artifacts bucket"
  value       = aws_s3_bucket.this["artifacts"].arn
}
