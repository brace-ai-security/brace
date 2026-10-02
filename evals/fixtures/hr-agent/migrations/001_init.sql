-- Roles (created by the platform team): hr_agent, hr_gateway, hr_agent_operator,
-- hr_audit_reader, hr_audit_maint, hr_docs_ingest.
CREATE SCHEMA audit; CREATE SCHEMA control; CREATE SCHEMA approvals; CREATE SCHEMA quota; CREATE SCHEMA retrieval;

CREATE TABLE audit.events (
    event_id uuid NOT NULL, ts timestamptz NOT NULL, event_type text NOT NULL,
    run_id uuid NOT NULL, step_id uuid, parent_step_id uuid,
    accountable_party text NOT NULL, operational_owner text NOT NULL, tenant text NOT NULL,
    agent_type_id text NOT NULL, agent_instance_id text NOT NULL,
    trace_id char(32) NOT NULL, span_id char(16) NOT NULL, traceparent text NOT NULL,
    delegated_subject text NOT NULL, agent_principal text NOT NULL,
    tool text, operation_target text, decision text, reason text, policy_version text NOT NULL, approval_id uuid,
    args_redacted jsonb, result_redacted jsonb,
    context_tokens integer, context_tokens_method text, model_requested text, model_served text,
    PRIMARY KEY (event_id, ts)
) PARTITION BY RANGE (ts);
CREATE INDEX ON audit.events (trace_id);
CREATE INDEX ON audit.events (run_id, ts);

CREATE TABLE audit.gateway_decisions (
    ts timestamptz NOT NULL, traceparent text NOT NULL, tenant text NOT NULL,
    accountable_party text NOT NULL, operational_owner text NOT NULL,
    agent_type_id_hint text NOT NULL, agent_instance_hint text NOT NULL,   -- caller-supplied; join key only
    subject text, actor text, tool text, decision text NOT NULL, reason text, policy_version text NOT NULL
) PARTITION BY RANGE (ts);

-- Creates `ahead` partitions into the future and drops partitions older than the newest `keep`.
CREATE FUNCTION audit.maintain_partitions(parent regclass, period interval, ahead int, keep int)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = audit, pg_temp AS $$
DECLARE
    start_ts timestamptz := date_trunc('week', now());
    part record;
BEGIN
    FOR i IN 0..ahead LOOP
        EXECUTE format('CREATE TABLE IF NOT EXISTS %s_%s PARTITION OF %s FOR VALUES FROM (%L) TO (%L)',
                       parent, to_char(start_ts + i * period, 'IYYY"w"IW'), parent,
                       start_ts + i * period, start_ts + (i + 1) * period);
    END LOOP;
    FOR part IN
        SELECT c.oid::regclass AS rel FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
         WHERE i.inhparent = parent ORDER BY c.relname DESC OFFSET keep + ahead + 1
    LOOP
        EXECUTE format('DROP TABLE %s', part.rel);
    END LOOP;
END $$;

CREATE TABLE control.stop_flags (
    flag_id bigserial PRIMARY KEY,
    scope text NOT NULL CHECK (scope IN ('fleet', 'agent_type', 'agent_instance', 'subject', 'agent_principal')),
    value text, active boolean NOT NULL DEFAULT true, reason text NOT NULL,
    set_by text NOT NULL DEFAULT current_user, set_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE approvals.grants (
    approval_id uuid PRIMARY KEY, run_id uuid NOT NULL, agent_instance_id text NOT NULL, subject text NOT NULL,
    operation text NOT NULL, target text NOT NULL, args_sha256 char(64) NOT NULL, args jsonb NOT NULL,
    tool_use_id text NOT NULL, description text NOT NULL,
    requested_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
    approved_by text, approved_at timestamptz, used_at timestamptz
);

CREATE TABLE quota.usage (
    scope text NOT NULL, key text NOT NULL, window_start timestamptz NOT NULL,
    runs integer NOT NULL DEFAULT 0, tokens bigint NOT NULL DEFAULT 0, cost_usd numeric(12, 4) NOT NULL DEFAULT 0,
    PRIMARY KEY (scope, key, window_start)
);

CREATE TABLE retrieval.index_state (id int PRIMARY KEY CHECK (id = 1), version text NOT NULL);
CREATE TABLE retrieval.chunks (
    chunk_id text PRIMARY KEY, doc_id text NOT NULL, source text NOT NULL,
    added_at timestamptz NOT NULL DEFAULT now(), added_by text NOT NULL DEFAULT current_user,
    trust text NOT NULL CHECK (trust IN ('reviewed', 'hr_authored')),
    audience text NOT NULL CHECK (audience IN ('all', 'employee')),
    allowed_employees text[] NOT NULL DEFAULT '{}',
    expires_at timestamptz, quarantined boolean NOT NULL DEFAULT false, text text NOT NULL,
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED
);
CREATE INDEX ON retrieval.chunks USING gin (tsv);

GRANT USAGE ON SCHEMA audit, control, approvals, quota, retrieval TO hr_agent;
GRANT INSERT ON audit.events TO hr_agent;
GRANT SELECT ON control.stop_flags TO hr_agent;
GRANT SELECT, INSERT ON approvals.grants TO hr_agent;
GRANT UPDATE (approved_by, approved_at, used_at) ON approvals.grants TO hr_agent;
GRANT SELECT, INSERT, UPDATE ON quota.usage TO hr_agent;
GRANT SELECT ON retrieval.chunks, retrieval.index_state TO hr_agent;

GRANT USAGE ON SCHEMA audit, control TO hr_gateway;
GRANT INSERT ON audit.gateway_decisions TO hr_gateway;
GRANT SELECT ON control.stop_flags TO hr_gateway;

GRANT USAGE ON SCHEMA control TO hr_agent_operator;
GRANT SELECT, INSERT, UPDATE ON control.stop_flags TO hr_agent_operator;
GRANT USAGE ON SEQUENCE control.stop_flags_flag_id_seq TO hr_agent_operator;

GRANT USAGE ON SCHEMA audit TO hr_audit_reader, hr_audit_maint;
GRANT SELECT ON ALL TABLES IN SCHEMA audit TO hr_audit_reader;
REVOKE EXECUTE ON FUNCTION audit.maintain_partitions(regclass, interval, int, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION audit.maintain_partitions(regclass, interval, int, int) TO hr_audit_maint;

GRANT USAGE ON SCHEMA retrieval TO hr_docs_ingest;
GRANT SELECT, INSERT, UPDATE ON retrieval.chunks, retrieval.index_state TO hr_docs_ingest;
