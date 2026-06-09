@echo off
echo ============================================
echo   Docker Monitor AI - Demo Environment
echo ============================================
echo.

REM Pull only the images actually used (lightweight)
echo [1/3] Pulling images...
docker pull nginx:1.25-alpine
docker pull node:20-alpine
docker pull python:3.11-alpine
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull alpine:3.18

echo.
echo [2/3] Starting all 10 containers...
docker compose up -d

echo.
echo [3/3] Waiting 15s for containers to settle...
timeout /t 15 /nobreak > nul

echo.
echo ============================================
echo   Container Status:
echo ============================================
docker compose ps
echo.
echo ============================================
echo   Expected States:
echo ============================================
echo   RUNNING    : nginx-web, postgres-db, redis-cache, prometheus, grafana, kibana
echo   UNHEALTHY  : elasticsearch  (health check fails - simulated)
echo   RESTARTING : rabbitmq-queue (crash loop   - simulated)
echo   EXITED     : react-frontend, fastapi-backend (intentional exit)
echo.
echo Open your Docker Monitor AI app at http://localhost:8501
echo and try these queries:
echo   - "show all containers"
echo   - "show unhealthy containers"
echo   - "which containers are restarting?"
echo   - "what crashed recently?"
echo   - "show database containers"
echo ============================================
