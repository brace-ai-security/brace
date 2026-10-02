terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.70" }
  }
}

provider "aws" { region = var.region }

variable "region" { default = "us-east-1" }
variable "image_tag" { default = "latest" }
variable "ecr_repo" { default = "412093557310.dkr.ecr.us-east-1.amazonaws.com/shopper-agent" }

resource "aws_ecs_cluster" "agents" { name = "shopper-agents" }

resource "aws_ecs_task_definition" "agent" {
  family                   = "shopper-agent"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 2048
  memory                   = 4096
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.agent.arn

  volume { name = "tmp" }
  volume { name = "vault" }

  container_definitions = jsonencode([
    {
      name                   = "agent"
      image                  = "${var.ecr_repo}:${var.image_tag}"
      essential              = true
      user                   = "1001"
      readonlyRootFilesystem = true
      linuxParameters        = { capabilities = { drop = ["ALL"] }, initProcessEnabled = true }
      portMappings           = [{ containerPort = 8080 }]
      mountPoints = [
        { sourceVolume = "tmp", containerPath = "/tmp" },
        { sourceVolume = "vault", containerPath = "/run/vault", readOnly = true },
      ]
      environment = [
        { name = "CONTROL_TABLE", value = aws_dynamodb_table.control.name },
        { name = "MEMORY_TABLE", value = aws_dynamodb_table.memory.name },
        { name = "APPROVALS_TABLE", value = aws_dynamodb_table.approvals.name },
        { name = "IDP_ISSUER", value = "https://login.shopper.app/" },
        { name = "OPERATIONAL_OWNER", value = "agent-platform-oncall" },
      ]
      secrets = [
        { name = "ANTHROPIC_API_KEY", valueFrom = aws_secretsmanager_secret.anthropic.arn },
        { name = "APPROVAL_HMAC_KEY", valueFrom = aws_secretsmanager_secret.approval_hmac.arn },
      ]
    },
    {
      name      = "vault-token"
      image     = "412093557310.dkr.ecr.us-east-1.amazonaws.com/vaultline-token-sidecar@sha256:9a1f0c6e2b7d4e8f3a5c1b0d9e6f2a7c4b8d3e1f0a9c6b2d7e4f8a3c5b1d0e9f"
      essential = true
      user      = "1001"
      mountPoints = [{ sourceVolume = "vault", containerPath = "/run/vault" }]
      environment = [{ name = "VAULTLINE_CLIENT_ID", value = "shopper-agent-prod" }, { name = "TOKEN_TTL", value = "300" }]
    },
  ])
}

resource "aws_ecs_service" "agent" {
  name            = "shopper-agent"
  cluster         = aws_ecs_cluster.agents.id
  task_definition = aws_ecs_task_definition.agent.arn
  desired_count   = 6
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.agent.id]
    assign_public_ip = false
  }
}

resource "aws_dynamodb_table" "memory" {
  name         = "shopper-memory"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"
  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  attribute {
    name = "sourceUrl"
    type = "S"
  }
  attribute {
    name = "writtenRunId"
    type = "S"
  }
  global_secondary_index {
    name            = "by-source"
    hash_key        = "sourceUrl"
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "by-run"
    hash_key        = "writtenRunId"
    projection_type = "ALL"
  }
  point_in_time_recovery { enabled = true }
}

resource "aws_dynamodb_table" "approvals" {
  name         = "shopper-approvals"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  attribute {
    name = "id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "control" {
  name         = "shopper-control"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  attribute {
    name = "pk"
    type = "S"
  }
}

resource "aws_secretsmanager_secret" "anthropic" { name = "shopper/anthropic-api-key" }
resource "aws_secretsmanager_secret" "approval_hmac" { name = "shopper/approval-hmac" }

resource "aws_vpc" "main" {
  cidr_block                       = "10.40.0.0/16"
  assign_generated_ipv6_cidr_block = true
}

resource "aws_subnet" "private" {
  count           = 3
  vpc_id          = aws_vpc.main.id
  cidr_block      = cidrsubnet(aws_vpc.main.cidr_block, 4, count.index)
  ipv6_cidr_block = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, count.index)
}

resource "aws_security_group" "alb" {
  name   = "shopper-alb"
  vpc_id = aws_vpc.main.id
}
