environment             = "staging"
aws_region              = "us-east-1"
project_name            = "the-saurus"
domain                  = "staging.the-saurus.example.com"
vpc_cidr                = "10.1.0.0/16"

# EKS — medium
eks_node_instance_types = ["t3.large"]
eks_node_min_size       = 2
eks_node_max_size       = 4
eks_node_desired_size   = 2

# Aurora — moderate
aurora_min_capacity = 1
aurora_max_capacity = 16

# Redis — small
redis_node_type = "cache.t3.small"
