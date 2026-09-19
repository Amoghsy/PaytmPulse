#!/bin/bash
set -e

echo "======================================================================"
echo "          PAYTM PULSE - REAL-TIME AI BUSINESS PARTNER                 "
echo "          Starting Full Stack Services...                             "
echo "======================================================================"

if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker is not running! Please start Docker first."
    exit 1
fi

echo "[1/3] Building and starting all Docker services..."
docker compose up -d --build

echo ""
echo "[2/3] Waiting 5 seconds for services to initialize..."
sleep 5

echo ""
echo "[3/3] System Status:"
docker compose ps

echo ""
echo "======================================================================"
echo "  ALL PAYTM PULSE SERVICES ARE RUNNING SUCCESSFULLY!                  "
echo "======================================================================"
echo "  -> Frontend Dashboard : http://localhost:5173"
echo "  -> Backend API        : http://localhost:8000"
echo "  -> Swagger API Docs   : http://localhost:8000/docs"
echo "  -> n8n Workflow Engine: http://localhost:5678"
echo "  -> Database           : Supabase PostgreSQL (via .env)"
echo "  -> Redis Fast Memory  : localhost:6379"
echo "======================================================================"
echo "  - To view logs        : docker compose logs -f"
echo "  - To stop all services: ./stop-all.sh (or docker compose down)"
echo "======================================================================"
