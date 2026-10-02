CREATE TABLE audit_events (
    seq                bigserial PRIMARY KEY,
    created_at         timestamptz NOT NULL,
    run_id             text NOT NULL,
    call_id            text NOT NULL,
    agent_type_id      text NOT NULL,
    agent_instance_id  text NOT NULL,
    parent_instance_id text NOT NULL,
    accountable_party  text NOT NULL,
    operational_owner  text NOT NULL,
    subject            text NOT NULL,
    tenant             text NOT NULL,
    trace_id           text NOT NULL,
    span_id            text NOT NULL,
    tool               text NOT NULL,
    args               jsonb NOT NULL,
    decision           text NOT NULL CHECK (decision IN ('allow', 'approved', 'deny')),
    policy_version     text NOT NULL,
    approval_id        text NOT NULL,
    approver           text NOT NULL,
    result             text NOT NULL,
    error              text NOT NULL,
    context_tokens     integer,
    context_method     text NOT NULL CHECK (context_method IN ('provider_usage', 'unavailable')),
    prev_hash          text NOT NULL,
    hash               text NOT NULL UNIQUE
);
CREATE INDEX audit_events_run ON audit_events (run_id);
CREATE INDEX audit_events_trace ON audit_events (trace_id);

CREATE TABLE approvals (
    id                text PRIMARY KEY,
    fingerprint       text NOT NULL,
    run_id            text NOT NULL,
    agent_instance_id text NOT NULL,
    tenant            text NOT NULL,
    tool              text NOT NULL,
    target            text NOT NULL,
    args              jsonb NOT NULL,
    approver          text,
    approved_at       timestamptz,
    expires_at        timestamptz NOT NULL,
    uses              integer NOT NULL DEFAULT 0,
    last_used_at      timestamptz
);
CREATE INDEX approvals_fp ON approvals (fingerprint, expires_at);

CREATE TABLE subagent_launches (
    id                 bigserial PRIMARY KEY,
    created_at         timestamptz NOT NULL DEFAULT now(),
    parent_instance_id text NOT NULL,
    child_instance_id  text NOT NULL UNIQUE,
    child_type_id      text NOT NULL,
    trace_id           text NOT NULL,
    prompt_redacted    text NOT NULL
);

-- The agent connects as cloudops_agent; incident reviewers connect as cloudops_review.
GRANT SELECT, INSERT, UPDATE, DELETE ON audit_events TO cloudops_agent;
GRANT SELECT, INSERT, UPDATE ON approvals TO cloudops_agent;
GRANT INSERT ON subagent_launches TO cloudops_agent;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO cloudops_agent;
GRANT SELECT ON audit_events, approvals, subagent_launches TO cloudops_review;
