# APEX Module Variables

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "database_instance" {
  description = "RDS instance type"
  type        = string
  default     = "db.t3.medium"
}

variable "database_storage" {
  description = "Initial database storage (GB)"
  type        = number
  default     = 100
}

variable "database_storage_max" {
  description = "Maximum database storage (GB)"
  type        = number
  default     = 500
}

variable "database_multi_az" {
  description = "Enable multi-AZ for database"
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Database backup retention (days)"
  type        = number
  default     = 7
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.medium"
}

variable "redis_num_nodes" {
  description = "Number of Redis nodes"
  type        = number
  default     = 1
}

variable "instance_type" {
  description = "EC2 instance type for EKS nodes"
  type        = string
  default     = "t3.medium"
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

