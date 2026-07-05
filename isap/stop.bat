@echo off
title ISAP - Stop

echo Stopping ISAP containers...
docker-compose down
echo.
echo Done! Press any key to close.
pause >nul
