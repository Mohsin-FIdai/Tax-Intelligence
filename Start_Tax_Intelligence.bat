@echo off
title Tax Intelligence System Launcher
color 0B

echo ===================================================
echo   Starting Tax Intelligence Platform
echo ===================================================
echo.

echo [1/3] Starting Ollama Local AI...
start "Ollama AI" cmd /c "ollama serve"

echo [2/3] Starting Python Backend...
cd /d "c:\Users\Mohsin\.gemini\antigravity\scratch\tax-intelligence"
start "Tax Intelligence Backend" cmd /k ".\python_env\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

echo [3/3] Starting Next.js Frontend...
cd /d "c:\Users\Mohsin\.gemini\antigravity\scratch\tax-intelligence\frontend"
start "Tax Intelligence Frontend" cmd /k "npm run dev"

echo.
echo All services are launching in separate windows.
echo Waiting a few seconds for servers to warm up...
timeout /t 5 >nul

echo Opening your web browser to the dashboard...
start http://localhost:3000

exit
