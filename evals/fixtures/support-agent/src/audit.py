"""Append-only audit log in Postgres."""
import json
import os
from datetime import datetime, timezone

import psycopg

_conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)


def record(identity: dict, event: str, details: dict) -> None:
    _conn.execute(
        """
        INSERT INTO agent_audit (ts, event, accountable_party, operational_owner, tenant,
                                 agent_type_id, agent_instance_id, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            datetime.now(timezone.utc),
            event,
            identity["accountable_party"],
            identity["operational_owner"],
            identity["tenant"],
            identity["agent_type_id"],
            identity["agent_instance_id"],
            json.dumps(details),
        ),
    )
