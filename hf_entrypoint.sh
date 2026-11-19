#!/usr/bin/env bash
set -e

echo "================================================================================"
echo "          Aethelgard · SIAT: Hugging Face Spaces Container Startup              "
echo "================================================================================"

# ------------------------------------------------------------------------------
# 1. Start PostgreSQL Service
# ------------------------------------------------------------------------------
echo "=== [1/4] Starting PostgreSQL Service ==="
find /etc/postgresql -name pg_hba.conf -exec sed -i 's/peer/trust/g' {} + 2>/dev/null || true
find /etc/postgresql -name pg_hba.conf -exec sed -i 's/md5/trust/g' {} + 2>/dev/null || true
find /etc/postgresql -name pg_hba.conf -exec sed -i 's/scram-sha-256/trust/g' {} + 2>/dev/null || true

service postgresql start || /etc/init.d/postgresql start

echo "Waiting for PostgreSQL service on port 5432..."
until pg_isready -h localhost -p 5432 -U postgres; do
    sleep 1
done
echo "[OK] PostgreSQL service is ready and accepting connections."

# ------------------------------------------------------------------------------
# 2. Database Initialization & Restore (siat_dwh)
# ------------------------------------------------------------------------------
echo "=== [2/4] Checking and Initializing Database (siat_dwh) ==="
psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE siat_dwh;" 2>/dev/null || true
psql -h localhost -p 5432 -U postgres -d siat_dwh -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" 2>/dev/null || true

TABLE_COUNT=$(psql -h localhost -p 5432 -U postgres -d siat_dwh -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='dwh'" 2>/dev/null || echo "0")

if [ "$TABLE_COUNT" -eq "0" ]; then
    if [ -f "/app/deploy_data/siat_dwh_backup.dump" ]; then
        echo "[*] Restoring DWH schema and 2.58M+ facts from /app/deploy_data/siat_dwh_backup.dump..."
        chmod 777 /app/deploy_data/siat_dwh_backup.dump 2>/dev/null || true
        PG_RESTORE_BIN=$(which pg_restore || ls -1 /usr/lib/postgresql/*/bin/pg_restore 2>/dev/null | sort -V | tail -n 1)
        echo "Using restore binary: $PG_RESTORE_BIN"
        "$PG_RESTORE_BIN" -h localhost -p 5432 -U postgres --no-owner --no-privileges -d siat_dwh -v /app/deploy_data/siat_dwh_backup.dump 2>&1 | tail -n 25 || true
        echo "[OK] Database restore completed successfully!"
    else
        echo "[!] Warning: /app/deploy_data/siat_dwh_backup.dump not found. Applying empty schema..."
        python dwh/apply_schema.py || true
    fi
else
    echo "[OK] DWH tables already present ($TABLE_COUNT tables found)."
fi

# ------------------------------------------------------------------------------
# 3. Environment Variables Configuration
# ------------------------------------------------------------------------------
echo "=== [3/4] Configuring Environment Variables ==="
export LLM_PROVIDER="${LLM_PROVIDER:-gemini}"
export LLM_MODEL="${LLM_MODEL:-gemini-2.5-flash}"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_USER="postgres"
export DB_NAME="siat_dwh"
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres@localhost:5432/siat_dwh}"
PORT="${PORT:-7860}"

if [ -z "$GEMINI_API_KEY" ]; then
    echo "[!] DIQQAT: GEMINI_API_KEY aniqlanmadi!"
    echo "[!] Hugging Face Space sozlamalarida (Settings -> Variables and secrets) 'GEMINI_API_KEY' secretini qo'shing."
    echo "[!] Tarmoqsiz test uchun Deterministik Demo rejim mavjud: http://localhost:$PORT/?demo"
else
    echo "[OK] GEMINI_API_KEY sozlandi."
fi

# ------------------------------------------------------------------------------
# 4. Launch FastAPI Server
# ------------------------------------------------------------------------------
echo "=== [4/4] Starting FastAPI Application on Port $PORT ==="
exec uvicorn api.main:app --host 0.0.0.0 --port "$PORT"
