# Paytm Pulse - Start Infrastructure Services (Redis & n8n via Docker)

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  Starting Paytm Pulse Infra: Redis + n8n (Docker)    " -ForegroundColor Yellow
Write-Host "======================================================" -ForegroundColor Cyan

# Check Docker daemon
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Docker daemon is not running. Please start Docker Desktop first." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error: Docker command failed. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Redis and n8n containers..." -ForegroundColor Green
docker compose up -d redis n8n

Start-Sleep -Seconds 3

Write-Host "`nInfrastructure Container Status:" -ForegroundColor Green
docker compose ps redis n8n

Write-Host "`n======================================================" -ForegroundColor Cyan
Write-Host "  INFRASTRUCTURE SERVICES ARE RUNNING!               " -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  -> Redis (Port 6379) : localhost:6379" -ForegroundColor Yellow
Write-Host "  -> n8n   (Port 5678) : http://localhost:5678" -ForegroundColor Yellow
Write-Host "======================================================" -ForegroundColor Cyan
