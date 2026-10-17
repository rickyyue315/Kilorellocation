# 選用：僅供支援 Procfile 的容器主機使用（Streamlit Community Cloud 不會讀取此檔）
# Port／address 由環境變數注入，主機自動指派 PORT 時無需修改
web: streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
