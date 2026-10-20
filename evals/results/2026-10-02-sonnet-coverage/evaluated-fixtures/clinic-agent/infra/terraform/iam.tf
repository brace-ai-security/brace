# Runtime identity for the agent pods (IRSA). This role belongs to the agent, not to any user:
# patients and staff never receive AWS credentials, and revoking this role does not touch theirs.
resource "aws_iam_role" "runtime" {
  name                 = "clinic-agent-runtime"
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = module.eks.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${module.eks.oidc_provider}:sub" = [
            "system:serviceaccount:clinic-agent:clinic-agent",
            "system:serviceaccount:clinic-agent:clinic-agent-reminders",
          ]
          "${module.eks.oidc_provider}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "runtime" {
  name = "clinic-agent-runtime"
  role = aws_iam_role.runtime.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadClinicSecrets"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:clinic-agent/*"
      },
      {
        Sid    = "AgentState"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:BatchGetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
        ]
        Resource = "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/clinic-agent-*"
      },
      {
        Sid      = "Audit"
        Effect   = "Allow"
        Action   = ["firehose:PutRecord", "firehose:PutRecordBatch"]
        Resource = aws_kinesis_firehose_delivery_stream.audit.arn
      },
    ]
  })
}

# Operators who may stop the agent. Assumable only through SSO by the on-call group.
resource "aws_iam_role" "ops_killswitch" {
  name = "clinic-agent-ops"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringLike = { "aws:PrincipalArn" = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aws-reserved/sso.amazonaws.com/*/AWSReservedSSO_AgentPlatformOnCall_*" }
      }
    }]
  })
}

resource "aws_iam_role_policy" "ops_killswitch" {
  name = "clinic-agent-ops"
  role = aws_iam_role.ops_killswitch.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:GetItem"]
      Resource = aws_dynamodb_table.control.arn
    }]
  })
}

resource "aws_iam_role" "firehose" {
  name = "clinic-agent-audit-firehose"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "firehose.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "firehose" {
  name = "write-audit-bucket"
  role = aws_iam_role.firehose.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:AbortMultipartUpload", "s3:GetBucketLocation"]
      Resource = [aws_s3_bucket.audit.arn, "${aws_s3_bucket.audit.arn}/*"]
    }]
  })
}
