#!/bin/sh
set -e

# Render/Postgres can return postgres:// or postgresql:// URLs. Normalize both
# into the async URL SQLAlchemy expects, and derive the sync URL Alembic needs.
if [ -n "$DATABASE_URL" ]; then
  DATABASE_URL=$(printf '%s' "$DATABASE_URL" | sed -E 's#^postgres(ql)?(\+asyncpg)?://#postgresql+asyncpg://#')
  export DATABASE_URL
  # Alembic uses a sync driver. SQLAlchemy 2.x maps bare postgresql:// to
  # psycopg3, but this image ships psycopg2, so select it explicitly.
  SYNC_DATABASE_URL=$(printf '%s' "$DATABASE_URL" | sed -E 's#\+asyncpg#+psycopg2#')
  export SYNC_DATABASE_URL
fi

if [ -z "$PORT" ]; then
  PORT=8000
  export PORT
fi

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
