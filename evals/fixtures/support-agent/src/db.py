import os

import psycopg

_conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)


def query(sql: str, params: tuple) -> list[tuple]:
    with _conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall() if cur.description else []


def tenant_for_subdomain(subdomain: str) -> str | None:
    rows = query("SELECT tenant_id FROM tenants WHERE zendesk_subdomain = %s", (subdomain,))
    return rows[0][0] if rows else None
