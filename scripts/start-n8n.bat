@echo off
echo ========================================================
echo Starting Paytm Pulse - Self-Hosted n8n Workflow Engine
echo ========================================================
echo.

docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Docker detected. Starting self-hosted n8n container via Docker Compose...
    docker compose up -d n8n
    echo.
    echo [SUCCESS] n8n is running in background!
    echo [INFO] Open in browser: http://localhost:5678
    echo [INFO] Webhook endpoint: http://localhost:5678/webhook/
) else (
    echo [INFO] Docker not found. Starting n8n via npx...
    npx n8n
)
