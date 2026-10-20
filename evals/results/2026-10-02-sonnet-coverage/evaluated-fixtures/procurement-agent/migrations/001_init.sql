-- Procurement agent schema. Applied by the migration job with the
-- procurement_owner role; the running agent connects as procurement_agent.

CREATE TABLE audit_events (
    node_id             text PRIMARY KEY,
    parent_node_id      text REFERENCES audit_events (node_id),
    run_id              text NOT NULL,
    ts                  timestamptz NOT NULL,
    kind                text NOT NULL,
    accountable_party   text NOT NULL CHECK (accountable_party <> ''),
    operational_owner   text NOT NULL CHECK (operational_owner <> ''),
    tenant              text NOT NULL CHECK (tenant <> ''),
    agent_type_id       text NOT NULL CHECK (agent_type_id <> ''),
    agent_instance_id   text NOT NULL CHECK (agent_instance_id <> ''),
    trace_id            text NOT NULL CHECK (trace_id <> ''),
    span_id             text,
    delegated_subject   text NOT NULL,
    agent_principal     text NOT NULL,
    parent_instance_id  text,
    policy_version      text,
    approval_id         text,
    operation_id        text,
    context_tokens      integer CHECK (context_tokens IS NULL OR context_tokens > 0),
    context_method      text NOT NULL,
    context_compacted   boolean NOT NULL,
    payload             jsonb NOT NULL
);
CREATE INDEX audit_events_run ON audit_events (run_id, ts);
CREATE INDEX audit_events_instance ON audit_events (agent_instance_id, ts);
CREATE INDEX audit_events_trace ON audit_events (trace_id);

CREATE TABLE approvals (
    id                     text PRIMARY KEY,
    tool                   text NOT NULL,
    target                 text NOT NULL,
    args_sha256            text NOT NULL,
    args_summary           jsonb NOT NULL,
    tenant                 text NOT NULL,
    requested_by_instance  text NOT NULL,
    requested_by_run       text NOT NULL,
    delegated_subject      text NOT NULL,
    status                 text NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
    requested_at           timestamptz NOT NULL,
    expires_at             timestamptz NOT NULL,
    approver               text,
    approver_role          text,
    decided_at             timestamptz
);
CREATE INDEX approvals_lookup ON approvals (tool, target, tenant, status);

CREATE TABLE approvers (
    slack_user_id  text PRIMARY KEY,
    email          text NOT NULL,
    role           text NOT NULL,
    business_unit  text NOT NULL,
    active         boolean NOT NULL DEFAULT true
);

CREATE TABLE documents (
    doc_id         text PRIMARY KEY,
    business_unit  text NOT NULL,
    source         text NOT NULL,
    media_type     text NOT NULL,
    sha256         text NOT NULL,
    status         text NOT NULL CHECK (status IN ('accepted', 'quarantined')),
    reject_reason  text,
    text           text,
    received_at    timestamptz NOT NULL
);
CREATE INDEX documents_bu ON documents (business_unit, doc_id);

CREATE TABLE dept_notes (
    note_id            text PRIMARY KEY,
    business_unit      text NOT NULL,
    department         text NOT NULL,
    kind               text NOT NULL,
    body               text NOT NULL,
    verified           boolean NOT NULL DEFAULT false,
    verified_by        text,
    quarantined        boolean NOT NULL DEFAULT false,
    expires_at         timestamptz,
    writer_instance    text NOT NULL,
    writer_type_id     text NOT NULL,
    run_id             text NOT NULL,
    source_doc_id      text,
    delegated_subject  text NOT NULL,
    context_tokens     integer,
    context_method     text NOT NULL,
    created_at         timestamptz NOT NULL
);
CREATE INDEX dept_notes_lookup ON dept_notes (business_unit, department, created_at DESC);
CREATE INDEX dept_notes_source ON dept_notes (source_doc_id);
CREATE INDEX dept_notes_writer ON dept_notes (writer_instance);

CREATE TABLE control_flags (
    scope    text PRIMARY KEY,           -- 'fleet' or 'tenant:<business_unit>'
    halted   boolean NOT NULL,
    reason   text NOT NULL,
    set_by   text NOT NULL,
    set_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE spend_quota (
    scope      text NOT NULL,
    key        text NOT NULL,
    day        date NOT NULL,
    spent_usd  numeric(12, 4) NOT NULL,
    PRIMARY KEY (scope, key, day)
);

CREATE TABLE run_start_window (
    scope   text NOT NULL,
    key     text NOT NULL,
    minute  timestamptz NOT NULL,
    starts  integer NOT NULL,
    PRIMARY KEY (scope, key, minute)
);

-- Runtime role: append-only audit, no access to control flags beyond reading.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM procurement_agent;
GRANT SELECT, INSERT ON audit_events TO procurement_agent;
GRANT SELECT, INSERT, UPDATE ON approvals TO procurement_agent;
GRANT SELECT ON approvers TO procurement_agent;
GRANT SELECT, INSERT ON documents TO procurement_agent;
GRANT SELECT, INSERT ON dept_notes TO procurement_agent;
GRANT SELECT ON control_flags TO procurement_agent;
GRANT SELECT, INSERT, UPDATE ON spend_quota TO procurement_agent;
GRANT SELECT, INSERT, UPDATE ON run_start_window TO procurement_agent;

-- Operators: halt and resume.
GRANT SELECT, INSERT, UPDATE ON control_flags TO procurement_ops;
GRANT SELECT ON audit_events TO procurement_ops;
GRANT SELECT, UPDATE (verified, verified_by, quarantined) ON dept_notes TO procurement_ops;
