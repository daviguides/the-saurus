variable "cluster_name" {
  description = "Name of the ElastiCache replication group"
  type        = string
}

variable "node_type" {
  description = "ElastiCache node instance type"
  type        = string
  default     = "cache.t3.micro"
}

variable "auth_token" {
  description = "Auth token for Redis authentication"
  type        = string
  sensitive   = true
}

variable "vpc_id" {
  description = "VPC ID for the cache cluster"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for the cache subnet group"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs to attach"
  type        = list(string)
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}
