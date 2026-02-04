#!/bin/sh
set -e

echo "Waiting for database..."
until python -c "
import asyncio, asyncpg, os

async def check():
    url = os.environ['DATABASE_URL']
    # asyncpg expects a plain postgresql:// URL, strip the +asyncpg driver
    dsn = url.replace('+asyncpg', '', 1)
    conn = await asyncpg.connect(dsn, timeout=3)
    await conn.close()

asyncio.run(check())
" 2>/dev/null; do
  echo "  database not ready — retrying in 1s"
  sleep 1
done
echo "Database is ready"

echo "Running migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 "$@"
