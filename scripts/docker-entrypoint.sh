#!/bin/bash
set -e

# Run Alembic migrations if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "Running database migrations..."
    python3 -m alembic upgrade head
    echo "Database migrations complete."
fi

# Start the application
exec python3 -m modules.webapi --host 0.0.0.0 --port 8000 "$@"
