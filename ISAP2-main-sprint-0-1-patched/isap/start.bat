@echo off
title ISAP - Industrial Safety AI Platform

echo ========================================
echo   ISAP - Industrial Safety AI Platform
echo ========================================
echo.

:: Check Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker not installed or not running!
    pause
    exit /b 1
)

echo [1/3] Checking containers...
docker-compose ps --services --status running 2>nul | findstr "backend" >nul 2>&1
if %errorlevel% equ 0 (
    echo       Containers already running
) else (
    echo       Starting containers...
    docker-compose up -d
)

echo [2/3] Waiting for services (15 sec)...
timeout /t 15 /nobreak >nul

echo [3/3] Opening browser...
start http://localhost:3000

echo.
echo ========================================
echo   Services started:
echo   - Frontend:  http://localhost:3000
echo   - Backend:   http://localhost:8000
echo   - API Docs:  http://localhost:8000/docs
echo ========================================
echo.
echo   Press any key to stop...
pause >nul

echo.
echo Stopping containers...
docker-compose down
echo Done!
