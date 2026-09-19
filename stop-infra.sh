#!/usr/bin/env bash

# Paytm Pulse - Stop Infrastructure Services (Redis & n8n)

echo "Stopping Redis and n8n Docker containers..."
docker compose stop redis n8n
docker compose rm -f redis n8n

echo "Redis and n8n services stopped."
