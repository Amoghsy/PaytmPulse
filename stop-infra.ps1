# Paytm Pulse - Stop Infrastructure Services (Redis & n8n)

Write-Host "Stopping Redis and n8n Docker containers..." -ForegroundColor Yellow
docker compose stop redis n8n
docker compose rm -f redis n8n

Write-Host "Redis and n8n services stopped." -ForegroundColor Green
