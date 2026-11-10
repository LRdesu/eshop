@echo off
REM eshop one-click dev launcher
REM   backend  : http://127.0.0.1:8000  (uvicorn, hot-reload watches ./app only)
REM   frontend : http://localhost:5173  (vite)

cd /d "%~dp0backend"
start "eshop-backend :8000" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app"

cd /d "%~dp0frontend"
start "eshop-frontend :5173" cmd /k "npm run dev"

echo.
echo Started.
echo   Backend : http://127.0.0.1:8000/health
echo   Frontend: http://localhost:5173/
echo.
pause
