terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 6.14" }
    github = { source = "integrations/github", version = "~> 6.6" }
  }
  backend "s3" {
    bucket         = "northbay-tfstate-418295730611"
    key            = "clinic-agent/prod.tfstate"
    region         = "us-west-2"
    dynamodb_table = "northbay-tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { app = "clinic-agent", owner = "agent-platform", data = "phi" }
  }
}

variable "region" {
  type    = string
  default = "us-west-2"
}

variable "clinic_ids" {
  type    = list(string)
  default = ["nb-castro", "nb-fremont", "nb-oakland", "nb-sanmateo", "nb-walnutcreek"]
}

data "aws_caller_identity" "current" {}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.3.1"

  name               = "clinic-agent-prod"
  kubernetes_version = "1.33"
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets

  endpoint_public_access = false
  enable_irsa            = true

  authentication_mode = "API"
  access_entries = {
    deploy = {
      principal_arn = aws_iam_role.deploy.arn
      policy_associations = {
        ns = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"
          access_scope = { type = "namespace", namespaces = ["clinic-agent"] }
        }
      }
    }
  }

  eks_managed_node_groups = {
    agents = {
      instance_types = ["m7g.large"]
      ami_type       = "BOTTLEROCKET_ARM_64"
      min_size       = 2
      max_size       = 6
      desired_size   = 3
      metadata_options = {
        http_tokens                 = "required"
        http_put_response_hop_limit = 1
      }
    }
  }
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.4.0"

  name            = "clinic-agent-prod"
  cidr            = "10.42.0.0/16"
  azs             = ["us-west-2a", "us-west-2b", "us-west-2c"]
  private_subnets = ["10.42.1.0/24", "10.42.2.0/24", "10.42.3.0/24"]
  public_subnets  = ["10.42.101.0/24", "10.42.102.0/24", "10.42.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = false
}

resource "aws_ecr_repository" "agent" {
  name                 = "clinic-agent"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

# State tables. Approvals are written by the staff console; budgets by the agent; the control
# table holds the stop flags operators set.
resource "aws_dynamodb_table" "approvals" {
  name         = "clinic-agent-approvals"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  attribute {
    name = "id"
    type = "S"
  }
  point_in_time_recovery { enabled = true }
}

resource "aws_dynamodb_table" "budgets" {
  name         = "clinic-agent-budgets"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  attribute {
    name = "pk"
    type = "S"
  }
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "control" {
  name         = "clinic-agent-control"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  attribute {
    name = "pk"
    type = "S"
  }
  point_in_time_recovery { enabled = true }
}

# Audit: Firehose to an S3 bucket with object lock in compliance mode (7 years, HIPAA retention).
resource "aws_s3_bucket" "audit" {
  bucket              = "clinic-agent-audit-${data.aws_caller_identity.current.account_id}"
  object_lock_enabled = true
}

resource "aws_s3_bucket_object_lock_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    default_retention {
      mode  = "COMPLIANCE"
      years = 7
    }
  }
}

resource "aws_kinesis_firehose_delivery_stream" "audit" {
  name        = "clinic-agent-audit"
  destination = "extended_s3"
  extended_s3_configuration {
    role_arn            = aws_iam_role.firehose.arn
    bucket_arn          = aws_s3_bucket.audit.arn
    prefix              = "audit/dt=!{timestamp:yyyy-MM-dd}/"
    error_output_prefix = "audit-errors/!{firehose:error-output-type}/"
    buffering_interval  = 60
  }
}

resource "aws_secretsmanager_secret" "ehr" {
  for_each = toset(concat(var.clinic_ids, ["_catalog"]))
  name     = "clinic-agent/ehr/${each.key}"
}

resource "aws_secretsmanager_secret" "payments" {
  for_each = toset(var.clinic_ids)
  name     = "clinic-agent/payments/${each.key}"
}

resource "aws_secretsmanager_secret" "sms" {
  for_each = toset(var.clinic_ids)
  name     = "clinic-agent/sms/${each.key}"
}

resource "aws_secretsmanager_secret" "sms_signing" {
  name = "clinic-agent/sms-signing"
}
