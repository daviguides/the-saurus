locals {
  is_production = var.environment == "prod"
}

resource "aws_kms_key" "aurora" {
  description             = "KMS key for Aurora encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.cluster_name}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = { Name = "${var.cluster_name}-subnet-group" }
}

resource "aws_rds_cluster" "this" {
  cluster_identifier     = var.cluster_name
  engine                 = "aurora-postgresql"
  engine_mode            = "provisioned"
  engine_version         = var.engine_version
  master_username        = var.master_username
  master_password        = var.master_password
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = var.security_group_ids
  kms_key_id             = aws_kms_key.aurora.arn
  storage_encrypted      = true
  deletion_protection    = local.is_production
  skip_final_snapshot    = !local.is_production
  final_snapshot_identifier = local.is_production ? "${var.cluster_name}-final" : null

  serverlessv2_scaling_configuration {
    min_capacity = var.min_capacity
    max_capacity = var.max_capacity
  }
}

resource "aws_rds_cluster_instance" "this" {
  count              = local.is_production ? 2 : 1
  identifier         = "${var.cluster_name}-${count.index}"
  cluster_identifier = aws_rds_cluster.this.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.this.engine
  engine_version     = aws_rds_cluster.this.engine_version
}
