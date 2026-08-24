import os
import urllib.parse
import psycopg2

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("No DATABASE_URL found. Skipping connection cleanup.")
    exit(0)

try:
    print("Attempting to clean up idle PostgreSQL connections...")
    url = urllib.parse.urlparse(db_url)
    conn = psycopg2.connect(
        dbname=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        connect_timeout=10
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE usename = current_user
              AND pid <> pg_backend_pid();
        """)
        print("Successfully terminated old idle connections.")
except Exception as e:
    print(f"Connection cleanup skipped or failed: {e}")
