terraform {
  required_providers {
    aws    = { source = "hashicorp/aws", version = "5.68.0" }
    github = { source = "integrations/github", version = "6.3.0" }
    helm   = { source = "hashicorp/helm", version = "2.15.0" }
  }
}

locals {
  oidc_provider = "oidc.eks.us-east-1.amazonaws.com/id/7C1E0B5A9F4D2E8B3A6C1F0D9E8B7A6C"
  account_id    = "418273650912"
}

data "aws_iam_policy_document" "worker_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${local.account_id}:oidc-provider/${local.oidc_provider}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider}:sub"
      values   = ["system:serviceaccount:agents:issuesmith-worker"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "worker" {
  name                 = "issuesmith-worker"
  assume_role_policy   = data.aws_iam_policy_document.worker_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "worker" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = ["arn:aws:secretsmanager:us-east-1:${local.account_id}:secret:issuesmith/github-app-key-*"]
  }
  statement {
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["arn:aws:s3:::acme-issuesmith-memory/conventions/*"]
  }
  statement {
    actions   = ["s3:PutObject"]
    resources = ["arn:aws:s3:::acme-issuesmith-prompts/parent-prompts/*"]
  }
  statement {
    actions   = ["kms:GenerateDataKey"]
    resources = ["arn:aws:kms:us-east-1:${local.account_id}:alias/issuesmith-prompts"]
  }
  statement {
    actions   = ["rds-db:connect"]
    resources = ["arn:aws:rds-db:us-east-1:${local.account_id}:dbuser:cluster-C8X2K1/issuesmith_worker"]
  }
}

resource "aws_iam_role_policy" "worker" {
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker.json
}

data "aws_iam_policy_document" "deployer_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${local.account_id}:oidc-provider/token.actions.githubusercontent.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:acme-corp/issuesmith:environment:production"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "deployer" {
  name                 = "issuesmith-deployer"
  assume_role_policy   = data.aws_iam_policy_document.deployer_trust.json
  max_session_duration = 3600
}

resource "aws_eks_access_entry" "deployer" {
  cluster_name  = "platform-prod"
  principal_arn = aws_iam_role.deployer.arn
  kubernetes_groups = ["issuesmith-deployers"]
}

# --- source repository protections ---------------------------------------

resource "github_branch_protection" "main" {
  repository_id                   = "issuesmith"
  pattern                         = "main"
  enforce_admins                  = true
  allows_force_pushes             = false
  allows_deletions                = false
  require_signed_commits          = true
  required_linear_history         = true
  require_conversation_resolution = true

  required_pull_request_reviews {
    required_approving_review_count = 2
    require_code_owner_reviews      = true
    dismiss_stale_reviews           = true
    require_last_push_approval      = true
  }

  required_status_checks {
    strict   = true
    contexts = ["build", "test", "agent-evals"]
  }
}

resource "github_repository_environment" "production" {
  repository  = "issuesmith"
  environment = "production"
  reviewers {
    teams = [data.github_team.devprod_leads.id, data.github_team.appsec.id]
  }
  prevent_self_review = true
  deployment_branch_policy {
    protected_branches     = true
    custom_branch_policies = false
  }
}

data "github_team" "devprod_leads" { slug = "devprod-leads" }
data "github_team" "appsec" { slug = "appsec" }

# --- admission control ---------------------------------------------------

resource "helm_release" "kyverno" {
  name             = "kyverno"
  repository       = "https://kyverno.github.io/kyverno"
  chart            = "kyverno"
  version          = "3.5.2"
  namespace        = "kyverno"
  create_namespace = true
  set {
    name  = "features.policyExceptions.enabled"
    value = "false"
  }
}
