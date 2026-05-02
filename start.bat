@echo off
TITLE PolicyAI — Startup

echo.
echo ==========================================
echo  AI-Based Policy Retrieval System Startup
echo ==========================================
echo.

:: ── Step 1: Start Ollama (Local LLM) ──────────────────────────────────────────
echo [1/4] Starting Ollama (Local LLM engine)...
start "Ollama" cmd /k ollama serve
timeout /t 3 /nobreak >nul

:: ── Step 2: Activate Python venv and start the FastAPI backend ────────────────
echo [2/4] Starting FastAPI Backend on port 8000...
start "Backend API" cmd /k "call .\.venv\Scripts\activate && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 4 /nobreak >nul

:: ── Step 3: Start the React frontend ──────────────────────────────────────────
echo [3/4] Starting React Frontend on port 5173...
start "Frontend" cmd /k "cd frontend && npm run dev"
timeout /t 5 /nobreak >nul

:: ── Step 4: Open browser ───────────────────────────────────────────────────────
echo [4/4] Opening browser...
start http://localhost:5173

echo.
echo ==========================================
echo  All services are starting!
echo  Frontend : http://localhost:5173
echo  Backend  : http://localhost:8000
echo  API Docs : http://localhost:8000/docs
echo ==========================================
echo.
pause
