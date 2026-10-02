data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "shopper-agent-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.anthropic.arn, aws_secretsmanager_secret.approval_hmac.arn]
    }]
  })
}

# Runtime identity of the agent itself. Not shared with the web app or any human role.
resource "aws_iam_role" "agent" {
  name               = "shopper-agent-runtime"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "agent_data" {
  role = aws_iam_role.agent.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AgentTables"
        Effect   = "Allow"
        Action   = ["dynamodb:*"]
        Resource = ["arn:aws:dynamodb:${var.region}:412093557310:table/shopper-*"]
      },
      {
        Sid      = "AgentTableIndexes"
        Effect   = "Allow"
        Action   = ["dynamodb:Query"]
        Resource = ["arn:aws:dynamodb:${var.region}:412093557310:table/shopper-*/index/*"]
      },
    ]
  })
}

resource "aws_security_group" "agent" {
  name   = "shopper-agent"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}
