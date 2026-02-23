#!/bin/sh
set -e

DATABASE_URL=${DATABASE_URL:-postgresql://reliscore:reliscore@postgres:5432/reliscore}
MODEL_SERVICE_URL=${MODEL_SERVICE_URL:-http://model:8000}

export DATABASE_URL
export MODEL_SERVICE_URL

echo "Waiting for Postgres..."
until nc -z postgres 5432 >/dev/null 2>&1; do
  sleep 1
done

echo "Waiting for model service..."
until curl -sf "$MODEL_SERVICE_URL/health" >/dev/null 2>&1; do
  sleep 2
done

echo "Applying Prisma schema..."
pnpm prisma db push

echo "Running demo seed..."
pnpm prisma:seed

echo "Starting API service..."
node dist/main.js
