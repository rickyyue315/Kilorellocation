#!/bin/bash

echo "啟動庫存調貨建議系統 v1.8..."
echo

# 檢查Python是否安裝
if ! command -v python3 &> /dev/null; then
    echo "錯誤: 未檢測到Python3，請先安裝Python 3.8或更高版本"
    exit 1
fi

# 檢查虛擬環境是否存在
if [ ! -d "venv" ]; then
    echo "創建虛擬環境..."
    python3 -m venv venv
fi

# 激活虛擬環境
echo "激活虛擬環境..."
source venv/bin/activate

# 安裝依賴
echo "安裝依賴包..."
pip install -r requirements.txt

# 啟動應用
echo
echo "啟動應用程序..."
echo "瀏覽器將自動打開，如果沒有，請手動訪問 http://localhost:8501"
echo
echo "按 Ctrl+C 停止應用程序"
echo

streamlit run app.py