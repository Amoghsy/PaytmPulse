# Paytm Pulse - Full Stack Startup Script (PowerShell)
# Starts Redis, n8n, FastAPI Backend, and React Frontend in Docker containers (Database on Supabase)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "          PAYTM PULSE - REAL-TIME AI BUSINESS PARTNER                 " -ForegroundColor Yellow
Write-Host "          Starting Full Stack Services...                             " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify Docker Daemon is alive
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Docker is not running! Please launch Docker Desktop first." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERROR] Docker command failed. Ensure Docker Desktop is installed and running." -ForegroundColor Red
    exit 1
}

# 2. Build and launch all containers
Write-Host "[1/3] Building and starting all Docker services..." -ForegroundColor Green
docker compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] docker compose up failed." -ForegroundColor Red
    exit 1
}

# 3. Wait for services to become healthy
Write-Host "`n[2/3] Waiting 5 seconds for services to initialize..." -ForegroundColor Green
Start-Sleep -Seconds 5

# 4. Show container status
Write-Host "`n[3/3] Checking container status:" -ForegroundColor Green
docker compose ps

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "  ALL PAYTM PULSE SERVICES ARE RUNNING SUCCESSFULLY!                  " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  -> Frontend Dashboard : " -NoNewline; Write-Host "http://localhost:5173" -ForegroundColor Yellow
Write-Host "  -> Backend API        : " -NoNewline; Write-Host "http://localhost:8000" -ForegroundColor Yellow
Write-Host "  -> Swagger API Docs   : " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "  -> n8n Workflow Engine: " -NoNewline; Write-Host "http://localhost:5678" -ForegroundColor Yellow
Write-Host "  -> Database           : " -NoNewline; Write-Host "Supabase PostgreSQL (via .env)" -ForegroundColor Gray
Write-Host "  -> Redis Fast Memory  : " -NoNewline; Write-Host "localhost:6379" -ForegroundColor Gray
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  Commands:" -ForegroundColor White
Write-Host "  - View live logs      : docker compose logs -f" -ForegroundColor DarkGray
Write-Host "  - View backend logs   : docker compose logs -f backend" -ForegroundColor DarkGray
Write-Host "  - View frontend logs  : docker compose logs -f frontend" -ForegroundColor DarkGray
Write-Host "  - Stop all services   : .\stop-all.ps1 (or docker compose down)" -ForegroundColor DarkGray
Write-Host "======================================================================`n" -ForegroundColor Cyan
