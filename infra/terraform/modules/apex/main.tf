# APEX Infrastructure Module
# Main Terraform module for APEX deployment

terraform {
  required_version = ">= 1.5"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# VPC and Networking
module "vpc" {
  source = "../vpc"
  
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
  availability_zones = var.availability_zones
}

# Database
module "database" {
  source = "../rds"
  
  environment = var.environment
  vpc_id      = module.vpc.vpc_id
  subnet_ids  = module.vpc.private_subnet_ids
  
  instance_class       = var.database_instance
  allocated_storage    = var.database_storage
  max_allocated_storage = var.database_storage_max
  multi_az            = var.database_multi_az
  backup_retention_days = var.backup_retention_days
  
  kms_key_id = module.kms.kms_key_id
}

# Redis (ElastiCache)
module "redis" {
  source = "../elasticache"
  
  environment = var.environment
  vpc_id      = module.vpc.vpc_id
  subnet_ids  = module.vpc.private_subnet_ids
  
  node_type     = var.redis_node_type
  num_nodes      = var.redis_num_nodes
  multi_az      = var.environment == "prod"
  transit_encryption = var.environment == "prod"
}

# S3 Buckets
module "storage" {
  source = "../s3"
  
  environment = var.environment
  kms_key_id  = module.kms.kms_key_id
}

# EKS Cluster
module "eks" {
  source = "../eks"
  
  environment = var.environment
  vpc_id      = module.vpc.vpc_id
  subnet_ids  = module.vpc.private_subnet_ids
  
  cluster_version = "1.28"
  instance_type   = var.instance_type
  min_instances   = var.min_instances
  max_instances   = var.max_instances
  
  kms_key_id = module.kms.kms_key_id
}

# KMS for Encryption
module "kms" {
  source = "../kms"
  
  environment = var.environment
}

# Outputs
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "database_endpoint" {
  value = module.database.endpoint
}

output "redis_endpoint" {
  value = module.redis.endpoint
}

output "s3_bucket" {
  value = module.storage.bucket_name
}

output "eks_cluster_id" {
  value = module.eks.cluster_id
}

