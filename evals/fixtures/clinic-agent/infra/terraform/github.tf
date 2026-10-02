# Who can change production: only the deploy workflow running in the "production" or
# "production-emergency" GitHub environment can assume the deploy role, and both environments
# require a named reviewer from agent-platform-leads. Nobody else has write access to the
# clinic-agent namespace (see access_entries in main.tf), and the cluster API is private.

provider "github" {
  owner = "northbay-clinics"
}

data "github_team" "leads" {
  slug = "agent-platform-leads"
}

resource "github_branch_protection" "main" {
  repository_id = "clinic-agent"
  pattern       = "main"

  enforce_admins                  = true
  allows_force_pushes             = false
  allows_deletions                = false
  required_linear_history         = true
  require_signed_commits          = true
  require_conversation_resolution = true

  required_pull_request_reviews {
    required_approving_review_count = 2
    require_code_owner_reviews      = true
    dismiss_stale_reviews           = true
    require_last_push_approval      = true
  }

  required_status_checks {
    strict   = true
    contexts = ["ci / test", "ci / manifest-check"]
  }
}

resource "github_repository_environment" "production" {
  repository  = "clinic-agent"
  environment = "production"
  reviewers {
    teams = [data.github_team.leads.id]
  }
  prevent_self_review = true
  deployment_branch_policy {
    protected_branches     = true
    custom_branch_policies = false
  }
}

resource "github_repository_environment" "production_emergency" {
  repository  = "clinic-agent"
  environment = "production-emergency"
  reviewers {
    teams = [data.github_team.leads.id]
  }
  prevent_self_review = true
  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "emergency_branches" {
  repository     = "clinic-agent"
  environment    = github_repository_environment.production_emergency.environment
  branch_pattern = "hotfix/*"
}

resource "aws_iam_role" "deploy" {
  name = "clinic-agent-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com" }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = [
            "repo:northbay-clinics/clinic-agent:environment:production",
            "repo:northbay-clinics/clinic-agent:environment:production-emergency",
          ]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "deploy" {
  name = "clinic-agent-deploy"
  role = aws_iam_role.deploy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:PutImage", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:BatchGetImage"]
        Resource = aws_ecr_repository.agent.arn
      },
      {
        Effect   = "Allow"
        Action   = ["eks:DescribeCluster"]
        Resource = module.eks.cluster_arn
      },
    ]
  })
}
