#!/bin/sh
set -e

echo "==> SynapseLM Release Step: Running database migrations..."
alembic upgrade head
echo "==> Migrations applied successfully to head."
