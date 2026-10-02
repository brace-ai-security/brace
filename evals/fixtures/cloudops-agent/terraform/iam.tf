terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "= 5.82.2" }
  }
}

variable "control_cluster_oidc_provider_arn" { type = string }
variable "control_cluster_oidc_issuer" { type = string }
variable "workload_cluster_arns" { type = list(string) }

# Agent workload identity: only the cloudops-agent service account in the cloudops namespace
# of the control cluster can assume it.
resource "aws_iam_role" "agent" {
  name                 = "cloudops-agent"
  max_session_duration = 3600
  tags                 = { owner = "platform-engineering", agent = "cloudops-oncall" }
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = var.control_cluster_oidc_provider_arn }
      Condition = { StringEquals = {
        "${var.control_cluster_oidc_issuer}:sub" = "system:serviceaccount:cloudops:cloudops-agent"
        "${var.control_cluster_oidc_issuer}:aud" = "sts.amazonaws.com"
      } }
    }]
  })
}

resource "aws_iam_role_policy" "agent" {
  role = aws_iam_role.agent.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["eks:DescribeCluster"], Resource = var.workload_cluster_arns }]
  })
}

# Cloud MCP server credentials.
resource "aws_iam_user" "mcp" {
  name = "cloudops-mcp"
  tags = { owner = "platform-engineering", agent = "cloudops-oncall" }
}

resource "aws_iam_access_key" "mcp" {
  user = aws_iam_user.mcp.name
}

resource "aws_iam_user_policy" "mcp" {
  user = aws_iam_user.mcp.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "NodeGroups"
        Effect   = "Allow"
        Action   = ["eks:DescribeNodegroup", "eks:ListNodegroups", "eks:UpdateNodegroupConfig"]
        Resource = [for arn in var.workload_cluster_arns : "${replace(arn, ":cluster/", ":nodegroup/")}/*/*"]
      },
      {
        Sid       = "ReplaceNodes"
        Effect    = "Allow"
        Action    = ["ec2:TerminateInstances", "ec2:DescribeInstances"]
        Resource  = "*"
        Condition = { StringLike = { "aws:ResourceTag/eks:cluster-name" = "prod-*" } }
      },
    ]
  })
}

output "mcp_secret_access_key" {
  value     = aws_iam_access_key.mcp.secret
  sensitive = true
}
