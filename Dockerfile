# KiLo 庫存調貨建議系統 — 通用 Docker 映像（選用）
# 注意：Streamlit Community Cloud（share.streamlit.io）不使用 Dockerfile，
#       本檔僅保留給自架或其他容器主機（Railway / Render / VPS…）備用。
# 鎖定 Python 版本（3.13）以確保容器部署與本機開發環境一致；
# 勿改用 3.14：streamlit 1.51 限制 pyarrow<22，pyarrow 21 無 cp314 wheel。
FROM python:3.13-slim

# 效能與穩定性：停用位元組碼快取（容器內不需要）、管線輸出即時 flush
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 先僅複製依賴檔，利用 Docker layer cache 加速重建
COPY requirements.txt runtime.txt ./

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 再複製應用程式碼（變動頻率較高）
COPY . .

# Streamlit 預設埠；若主機注入 PORT 環境變數則自動沿用
ENV STREAMLIT_SERVER_PORT=8501
EXPOSE 8501

# 明確啟動命令：監聽 0.0.0.0、headless、停用檔案監看（生產環境）
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
