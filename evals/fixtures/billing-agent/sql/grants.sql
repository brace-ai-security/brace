CREATE TABLE IF NOT EXISTS policy_chunks (
    id           bigserial PRIMARY KEY,
    tenant_id    text        NOT NULL,
    source_uri   text        NOT NULL,
    added_by     text        NOT NULL,
    added_at     timestamptz NOT NULL DEFAULT now(),
    trust_level  text        NOT NULL CHECK (trust_level IN ('reviewed', 'imported')),
    status       text        NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'quarantined', 'revoked')),
    expires_at   timestamptz,
    content      text        NOT NULL,
    embedding    vector(1024) NOT NULL
);

CREATE ROLE billing_agent_ro LOGIN;
CREATE ROLE policy_ingest LOGIN;

REVOKE ALL ON policy_chunks FROM PUBLIC;
GRANT SELECT ON policy_chunks TO billing_agent_ro;
GRANT SELECT, INSERT, UPDATE ON policy_chunks TO policy_ingest;
GRANT USAGE ON SEQUENCE policy_chunks_id_seq TO policy_ingest;

ALTER TABLE policy_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE policy_chunks FORCE ROW LEVEL SECURITY;

CREATE POLICY agent_read ON policy_chunks FOR SELECT TO billing_agent_ro
    USING (
        tenant_id = current_setting('app.tenant_id', false)
        AND status = 'active'
        AND (expires_at IS NULL OR expires_at > now())
    );

CREATE POLICY ingest_all ON policy_chunks TO policy_ingest USING (true) WITH CHECK (true);

-- invoices replica
CREATE ROLE billing_agent_invoices LOGIN;
GRANT SELECT ON invoices, payments, customers TO billing_agent_invoices;
