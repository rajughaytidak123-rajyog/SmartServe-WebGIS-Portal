@echo off
title SmartServe GIS - Full System Launcher
echo ======================================================================
echo   SMARTSERVE GIS - STARTING BACKEND AND FRONTEND
echo ======================================================================

echo [1/2] Launching FastAPI Backend on http://127.0.0.1:8000 ...
start "SmartServe Backend" cmd /k "python backend/run.py"

echo [2/2] Launching WebGIS Frontend on http://127.0.0.1:5500 ...
start "SmartServe Frontend" cmd /k "python frontend/serve.py"

echo.
echo ======================================================================
echo Both servers have been launched in separate windows!
echo - WebGIS Portal:    http://127.0.0.1:5500
echo - Swagger API Docs: http://127.0.0.1:8000/docs
echo ======================================================================
pause
