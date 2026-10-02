CREATE TABLE approvers (
  login      text NOT NULL,
  tenant     text NOT NULL,
  operation  text NOT NULL,
  PRIMARY KEY (login, tenant, operation)
);

CREATE TABLE approvals (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_instance_id  text NOT NULL,
  tenant             text NOT NULL,
  operation          text NOT NULL,
  target             text NOT NULL,
  args_sha256        text NOT NULL,
  args_json          jsonb NOT NULL,
  summary            text NOT NULL,
  requested_by       text NOT NULL,
  requested_at       timestamptz NOT NULL DEFAULT now(),
  status             text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  approver           text,
  approved_at        timestamptz,
  expires_at         timestamptz,
  consumed_at        timestamptz,
  consumed_by        text
);

-- worker: may file requests and mark them used; cannot approve or edit approvers
CREATE ROLE issuesmith_worker LOGIN;
GRANT rds_iam TO issuesmith_worker;
GRANT INSERT (agent_instance_id, tenant, operation, target, args_sha256, args_json, summary, requested_by)
  ON approvals TO issuesmith_worker;
GRANT SELECT ON approvals, approvers TO issuesmith_worker;
GRANT UPDATE (consumed_at, consumed_by) ON approvals TO issuesmith_worker;

-- approvals console: records decisions, sets a 30 minute expiry, never consumes
CREATE ROLE approvals_console LOGIN;
GRANT rds_iam TO approvals_console;
GRANT SELECT ON approvals, approvers TO approvals_console;
GRANT UPDATE (status, approver, approved_at, expires_at) ON approvals TO approvals_console;

-- approvers rows are written only by the platform_admin role from each repository's maintainer team
