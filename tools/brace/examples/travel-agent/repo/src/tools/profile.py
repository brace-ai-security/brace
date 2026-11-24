"""Traveler profiles: names, passport numbers, contact details."""
import psycopg


def get_traveler_profile(ctx, traveler_id):
    with psycopg.connect(ctx.profiles_dsn) as conn:
        row = conn.execute("select * from travelers where id = %s", (traveler_id,)).fetchone()
    return dict(row)
