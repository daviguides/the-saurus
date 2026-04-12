environment             = "dev"
aws_region              = "us-east-1"
project_name            = "the-saurus"
domain                  = "dev.the-saurus.example.com"
vpc_cidr                = "10.0.0.0/16"

# EKS — small
eks_node_instance_types = ["t3.medium"]
eks_node_min_size       = 1
eks_node_max_size       = 3
eks_node_desired_size   = 1

# Aurora — minimal
aurora_min_capacity = 0.5
aurora_max_capacity = 8

# Redis — micro
redis_node_type = "cache.t3.micro"
