#!/bin/bash

echo "啟動庫存調貨建議系統 v1.8..."
echo

# 檢查Python是否安裝
if ! command -v python3 &> /dev/null; then
    echo "錯誤: 未檢測到Python3，請先安裝Python 3.8或更高版本"
    echo "下載地址: https://www.python.org/downloads/"
    exit 1
fi

# 檢查pip是否可用
if ! python3 -m pip --version &> /dev/null; then
    echo "錯誤: 未檢測到pip，請確保Python安裝正確"
    exit 1
fi

# 檢查虛擬環境是否存在
if [ ! -d "venv" ]; then
    echo "創建虛擬環境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "錯誤: 創建虛擬環境失敗"
        exit 1
    fi
fi

# 激活虛擬環境
echo "激活虛擬環境..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "錯誤: 激活虛擬環境失敗"
    exit 1
fi

# 升級pip
echo "升級pip..."
python -m pip install --upgrade pip

# 安裝依賴
echo "安裝依賴包..."
python install_dependencies.py
if [ $? -ne 0 ]; then
    echo "警告: 依賴安裝可能失敗，嘗試安裝核心依賴..."
    python -m pip install pandas openpyxl streamlit numpy xlsxwriter matplotlib seaborn
fi

# 檢查核心依賴是否安裝成功
python -c "import pandas, openpyxl, streamlit, numpy, xlsxwriter, matplotlib, seaborn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "錯誤: 核心依賴安裝失敗，請手動安裝"
    exit 1
fi

# 啟動應用
echo
echo "啟動應用程序..."
echo "瀏覽器將自動打開，如果沒有，請手動訪問 http://localhost:8501"
echo
echo "按 Ctrl+C 停止應用程序"
echo

streamlit run app.py