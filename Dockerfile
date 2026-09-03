# KiLo 庫存調貨建議系統 — Zeabur / 通用 Docker 映像
# 依賴已預先安裝於 Docker Hub 上的基底映像（見 docker/Dockerfile.base 與 .github/workflows/build-base-image.yml），
# Zeabur 每次部署只須拉取基底映像 + 複製程式碼，不必逐次 pip install（省約 3~5 分鐘）。
# 基底映像只含公開 open-source 依賴（不含本專案程式碼），repo 保持 private 亦無洩漏風險。
ARG BASE_IMAGE=rickyyue315/kilo-reallocation-base:latest
FROM ${BASE_IMAGE}

WORKDIR /app

# 複製應用程式碼（變動頻率較高）
COPY . .

# Streamlit 預設埠；Zeabur 會注入 PORT 環境變數
ENV STREAMLIT_SERVER_PORT=8501
EXPOSE 8501

# 明確啟動命令：監聽 0.0.0.0、headless、停用檔案監看（生產環境）
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]