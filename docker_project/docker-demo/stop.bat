@echo off
echo Stopping all demo containers...
docker compose down -v
echo Done. All containers and volumes removed.
