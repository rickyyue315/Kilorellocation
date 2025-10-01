@echo off
echo 啟動庫存調貨建議系統 v1.8...
echo.

REM 檢查Python是否安裝
python --version >nul 2>&1
if errorlevel 1 (
    echo 錯誤: 未檢測到Python，請先安裝Python 3.8或更高版本
    pause
    exit /b 1
)

REM 檢查虛擬環境是否存在
if not exist venv (
    echo 創建虛擬環境...
    python -m venv venv
)

REM 激活虛擬環境
echo 激活虛擬環境...
call venv\Scripts\activate.bat

REM 安裝依賴
echo 安裝依賴包...
pip install -r requirements.txt

REM 啟動應用
echo.
echo 啟動應用程序...
echo 瀏覽器將自動打開，如果沒有，請手動訪問 http://localhost:8501
echo.
echo 按 Ctrl+C 停止應用程序
echo.

streamlit run app.py

pause