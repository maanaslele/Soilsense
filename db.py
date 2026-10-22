"""Database helper (PostgreSQL via psycopg2). Used by app.py and setup_db.py."""
import os
import psycopg2, psycopg2.extras
from dotenv import load_dotenv
load_dotenv()

def conn():
    if os.getenv("DATABASE_URL"):                     # hosted database
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    return psycopg2.connect(host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
                            user=os.getenv("DB_USER", "postgres"), password=os.getenv("DB_PASSWORD"),
                            dbname=os.getenv("DB_NAME", "soilsense"))

def run(sql, args=None, one=False):
    """Run one SQL statement; returns rows as dicts (or None for INSERT/UPDATE/DELETE)."""
    c = conn()
    try:
        with c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:   # 'with c' = commit
            cur.execute(sql, args)
            if cur.description is None:
                return None
            return cur.fetchone() if one else cur.fetchall()
    finally:
        c.close()
