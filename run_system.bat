@echo off
netstat -ano | findstr ":8501" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
  start "" http://localhost:8501
  exit /b 0
)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --browser.gatherUsageStats false
pause