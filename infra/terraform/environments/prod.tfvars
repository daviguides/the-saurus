environment             = "prod"
aws_region              = "us-east-1"
project_name            = "the-saurus"
domain                  = "the-saurus.example.com"
vpc_cidr                = "10.2.0.0/16"

# EKS — production
eks_node_instance_types = ["t3.xlarge"]
eks_node_min_size       = 3
eks_node_max_size       = 10
eks_node_desired_size   = 3

# Aurora — production
aurora_min_capacity = 2
aurora_max_capacity = 32

# Redis — production
redis_node_type = "cache.r7g.large"

# NOTE: Sensitive values (aurora_master_password, redis_auth_token)
# are NOT stored here. Provide them via environment variables:
#   TF_VAR_aurora_master_password
#   TF_VAR_redis_auth_token
# or a secrets manager integration.
