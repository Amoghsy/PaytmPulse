#!/usr/bin/env bash

# Paytm Pulse - Start Infrastructure Services (Redis & n8n via Docker)

echo "======================================================"
echo "  Starting Paytm Pulse Infra: Redis + n8n (Docker)    "
echo "======================================================"

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker daemon is not running. Please start Docker Desktop first."
  exit 1
fi

echo "Starting Redis and n8n containers..."
docker compose up -d redis n8n

echo ""
echo "Waiting for services to become ready..."
sleep 3

echo ""
echo "Infrastructure Container Status:"
docker compose ps redis n8n

echo ""
echo "======================================================"
echo "  INFRASTRUCTURE SERVICES ARE RUNNING!               "
echo "======================================================"
echo "  -> Redis (Port 6379) : localhost:6379"
echo "  -> n8n   (Port 5678) : http://localhost:5678"
echo "======================================================"
echo "  You can now run Backend and Frontend locally:"
echo "  - Backend  : cd backend && source venv/Scripts/activate && python -m uvicorn app.main:app --reload --port 8000"
echo "  - Frontend : cd frontend && npm run dev"
echo "======================================================"
