# Paytm Pulse - Self-Hosted n8n Launcher
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting Paytm Pulse - Self-Hosted n8n Workflow Engine" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$dockerAvailable = Get-Command docker -ErrorAction SilentlyContinue

if ($dockerAvailable) {
    Write-Host "[INFO] Docker detected. Launching n8n container..." -ForegroundColor Green
    docker compose up -d n8n
    Write-Host ""
    Write-Host "[SUCCESS] n8n container is active!" -ForegroundColor Green
    Write-Host "🔗 Access n8n UI: http://localhost:5678" -ForegroundColor Yellow
    Write-Host "📡 Webhook Endpoint: http://localhost:5678/webhook/" -ForegroundColor Yellow
} else {
    Write-Host "[INFO] Docker not found. Launching via npx n8n..." -ForegroundColor Cyan
    npx n8n
}
