@echo off
SETLOCAL EnableDelayedExpansion

echo ======================================================================
echo           PAYTM PULSE - REAL-TIME AI BUSINESS PARTNER
echo           Starting Full Stack (Supabase DB, Redis, n8n, Backend, Frontend)
echo ======================================================================
echo.

:: Check Docker Daemon
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not running! Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [1/3] Building and starting all containers in background...
docker compose up -d --build

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start Docker Compose services.
    pause
    exit /b 1
)

echo.
echo [2/3] Waiting for services to initialize...
timeout /t 5 /nobreak >nul

echo.
echo [3/3] System Status:
docker compose ps

echo.
echo ======================================================================
echo   ALL SERVICES ARE RUNNING!
echo ======================================================================
echo   * Frontend Dashboard:   http://localhost:5173
echo   * Backend API:          http://localhost:8000
echo   * Swagger API Docs:     http://localhost:8000/docs
echo   * n8n Workflow Engine:  http://localhost:5678
echo   * Database:             Supabase PostgreSQL (Connected via .env)
echo   * Redis Fast Memory:    localhost:6379
echo ======================================================================
echo   - To view real-time logs:  docker compose logs -f
echo   - To view backend logs:    docker compose logs -f backend
echo   - To view frontend logs:   docker compose logs -f frontend
echo   - To stop all services:    stop-all.bat  (or docker compose down)
echo ======================================================================
echo.
pause
