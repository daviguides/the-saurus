locals {
  is_production = var.environment == "prod"
  cluster_name  = "${var.project_name}-${var.environment}"
}

# ---------- VPC ----------

module "vpc" {
  source = "./modules/vpc"

  cidr_block   = var.vpc_cidr
  environment  = var.environment
  project_name = var.project_name
}

# ---------- EKS ----------

module "eks" {
  source = "./modules/eks"

  cluster_name        = "${local.cluster_name}-eks"
  k8s_version         = var.eks_k8s_version
  node_instance_types = var.eks_node_instance_types
  node_min_size       = var.eks_node_min_size
  node_max_size       = var.eks_node_max_size
  node_desired_size   = var.eks_node_desired_size
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  environment         = var.environment
  project_name        = var.project_name
}

# ---------- Aurora ----------

resource "aws_security_group" "aurora" {
  name_prefix = "${local.cluster_name}-aurora-"
  description = "Allow PostgreSQL access from EKS nodes"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.cluster_name}-aurora-sg" }
}

module "aurora" {
  source = "./modules/aurora"

  cluster_name       = "${local.cluster_name}-aurora"
  engine_version     = var.aurora_engine_version
  master_username    = var.aurora_master_username
  master_password    = var.aurora_master_password
  min_capacity       = var.aurora_min_capacity
  max_capacity       = var.aurora_max_capacity
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [aws_security_group.aurora.id]
  environment        = var.environment
  project_name       = var.project_name
}

# ---------- ElastiCache ----------

resource "aws_security_group" "redis" {
  name_prefix = "${local.cluster_name}-redis-"
  description = "Allow Redis access from EKS nodes"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.cluster_name}-redis-sg" }
}

module "elasticache" {
  source = "./modules/elasticache"

  cluster_name       = "${local.cluster_name}-redis"
  node_type          = var.redis_node_type
  auth_token         = var.redis_auth_token
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [aws_security_group.redis.id]
  environment        = var.environment
  project_name       = var.project_name
}

# ---------- S3 ----------

module "s3" {
  source = "./modules/s3"

  environment  = var.environment
  project_name = var.project_name
}
