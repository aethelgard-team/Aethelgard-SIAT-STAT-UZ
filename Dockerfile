# ==============================================================================
# Multi-stage Dockerfile for Aethelgard · SIAT (Hugging Face Spaces)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Frontend (Node.js 20)
# ------------------------------------------------------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Python 3.11-slim + PostgreSQL 16 Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies & PostgreSQL 16 + pg_restore client
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    build-essential \
    libpq-dev \
    procps \
 && install -d /etc/apt/keyrings \
 && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg \
 && echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update && apt-get install -y --no-install-recommends \
    postgresql-16 \
    postgresql-contrib-16 \
    postgresql-client-17 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy application source code
COPY agent/ ./agent/
COPY api/ ./api/
COPY mcp_server/ ./mcp_server/
COPY ml/ ./ml/
COPY dwh/ ./dwh/
COPY etl/ ./etl/
COPY docs/ ./docs/
COPY tests/ ./tests/
COPY check_db.py ./
COPY .env.example ./

# Copy database dump for initialization
COPY deploy_data/ ./deploy_data/

# Copy boot entrypoint script
COPY hf_entrypoint.sh ./
RUN sed -i 's/\r$//' hf_entrypoint.sh && chmod +x hf_entrypoint.sh

# Expose standard Hugging Face Spaces port
EXPOSE 7860

# Default environment variables
ENV PORT=7860
ENV LLM_PROVIDER=gemini
ENV LLM_MODEL=gemini-2.5-flash
ENV DB_HOST=localhost
ENV DB_PORT=5432
ENV DB_USER=postgres
ENV DB_NAME=siat_dwh
ENV DATABASE_URL=postgresql://postgres@localhost:5432/siat_dwh

CMD ["/bin/bash", "/app/hf_entrypoint.sh"]
