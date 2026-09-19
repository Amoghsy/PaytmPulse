# Paytm Pulse - Stop All Services (PowerShell)
Write-Host "Stopping all Paytm Pulse containers..." -ForegroundColor Yellow
docker compose down
Write-Host "All services stopped cleanly." -ForegroundColor Green
