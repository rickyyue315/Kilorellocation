@echo off
echo 啟動庫存調貨建議系統 v1.8...
echo.

REM 檢查Python是否安裝
python --version >nul 2>&1
if errorlevel 1 (
    echo 錯誤: 未檢測到Python，請先安裝Python 3.8或更高版本
    echo 下載地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 檢查pip是否可用
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo 錯誤: 未檢測到pip，請確保Python安裝正確
    pause
    exit /b 1
)

REM 檢查虛擬環境是否存在
if not exist venv (
    echo 創建虛擬環境...
    python -m venv venv
    if errorlevel 1 (
        echo 錯誤: 創建虛擬環境失敗
        pause
        exit /b 1
    )
)

REM 激活虛擬環境
echo 激活虛擬環境...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo 錯誤: 激活虛擬環境失敗
    pause
    exit /b 1
)

REM 升級pip
echo 升級pip...
python -m pip install --upgrade pip

REM 安裝依賴
echo 安裝依賴包...
python install_dependencies.py
if errorlevel 1 (
    echo 警告: 依賴安裝可能失敗，嘗試安裝核心依賴...
    python -m pip install pandas openpyxl streamlit numpy xlsxwriter matplotlib seaborn
)

REM 檢查核心依賴是否安裝成功
python -c "import pandas, openpyxl, streamlit, numpy, xlsxwriter, matplotlib, seaborn" >nul 2>&1
if errorlevel 1 (
    echo 錯誤: 核心依賴安裝失敗，請手動安裝
    pause
    exit /b 1
)

REM 啟動應用
echo.
echo 啟動應用程序...
echo 瀏覽器將自動打開，如果沒有，請手動訪問 http://localhost:8501
echo.
echo 按 Ctrl+C 停止應用程序
echo.

streamlit run app.py

pause