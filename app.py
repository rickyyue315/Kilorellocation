"""
庫存調貨建議系統 v2.1.1 - Streamlit應用程序
支持六模式系統：A(保守轉貨)/B(加強轉貨)/C(重點補0)/D(清貨轉貨)/E(強制轉出)/F(目標優化)
"""

import streamlit as st
import pandas as pd
import os
import tempfile
from datetime import datetime
import logging
from io import BytesIO
import time

# 導入自定義模組
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. 頁面配置
st.set_page_config(
    page_title="庫存調貨建議系統 v2.1.1",
    page_icon="📦",
    layout="wide"
)

# 2. 側邊欄設計
with st.sidebar:
    st.header("系統資訊")
    st.info(""" 
    **版本：v2.1.1** 
    **開發者: Ricky** 
    
    **核心功能：**  
    - ✅ 六模式系統
    - ✅ A模式(保守轉貨)/B模式(加強轉貨)/C模式(重點補0)/D模式(清貨轉貨)/E模式(強制轉出)/F模式(目標優化)
    - ✅ ND/RF類型智慧識別
    - ✅ 優先順序調貨匹配
    - ✅ RF轉出限制控制
    - ✅ D模式特殊功能：避免1件餘貨
    - ✅ E模式特殊功能：標記商品強制轉出
    - ✅ F模式特殊功能：Target目標接收優先
    - ✅ 統計分析和圖表
    - ✅ Excel格式匯出
    """)
    
    st.sidebar.header("操作指引")
    st.sidebar.markdown("""
    1. **上傳 Excel 文件**：點擊瀏覽文件或拖放文件到上傳區域。
    2. **選擇轉貨模式**：在側邊欄選擇轉貨模式（保守轉貨、加強轉貨、重點補0或清貨轉貨）。
    3. **啟動分析**：點擊「生成調貨建議」按鈕開始處理。
    4. **查看結果**：在主頁面查看KPI、建議和圖表。
    5. **下載報告**：點擊下載按鈕獲取 Excel 報告。
    """)
    
    # 模式選擇
    st.sidebar.header("模式選擇")
    transfer_mode = st.radio(
        "選擇轉貨模式",
        ["A: 保守轉貨", "B: 加強轉貨", "C: 重點補0", "D: 清貨轉貨", "E: 強制轉出", "F: 目標優化"],
        key='transfer_mode',
        help="A模式優先保障安全庫存，B模式則更積極地處理滯銷品，C模式重點補充庫存為0或1的店鋪，D模式針對ND店鋪無銷售記錄時的清貨處理，E模式強制轉出標記為*ALL*的商品，F模式使用Target數字優先滿足接收目標。"
    )
    
    # 模式說明
    with st.sidebar.expander("模式說明"):
        st.markdown("""
        **轉貨模式：**
        - **A模式(保守轉貨)**：轉出後剩餘庫存不低於安全庫存，轉出類型為RF過剩轉出
        - **B模式(加強轉貨)**：轉出後剩餘庫存可能低於安全庫存，轉出類型為RF加強轉出
        - **C模式(重點補0)**：主要針對接收店鋪，當(SaSa Net Stock+Pending Received)<=1時，補充至該店鋪的Safety或MOQ+1的數量(取最低值)
        - **D模式(清貨轉貨)**：針對ND類型且無銷售記錄的店鋪進行清貨，避免1件餘貨
        - **E模式(強制轉出)**：針對標記為*ALL*的商品行，全數強制轉出。接收店鋪為RF，上限為Safety Stock的2倍。優先同OM配對，跨OM時HD不能轉到HA/HB/HC
        - **F模式(目標優化)**：Target欄位填數字作為優先接收目標；其他店鋪按C模式補0需求計算；允許跨OM配對，HD不能轉到HA/HB/HC
        
        **轉出類型判斷：**
        - 如果轉出店鋪轉出後, 剩餘庫存不會低過Safety stock, 轉出類型定位為RF過剩轉出
        - 如果轉出店鋪轉出後, 剩餘庫存會低過Safety stock, 轉出類型定位為RF加強轉出
        - D模式特殊：ND店鋪無銷售記錄時，轉出類型為ND清貨轉出
        - E模式特殊：所有轉出為E模式強制轉出
        - F模式特殊：Target數字優先接收
        
        **接收條件：**
        - SaSa Net Stock + Pending Received < Safety Stock，便需要進行調撥接收
        - C模式特殊條件：當(SaSa Net Stock+Pending Received)<=1時，補充至該店鋪的Safety或MOQ+1的數量(取最低值)
        - D模式特殊規則：避免1件餘貨，確保轉出後剩餘庫存為0件或≥2件
        - E模式特殊規則：所有RF店鋪可接收，上限為Safety Stock的2倍
        """)

# 3. 頁面頭部
st.title("📦 庫存調貨建議系統 v2.1.1")
st.markdown("---")

# 4. 主要區塊
# 4.1. 資料上傳區塊
st.header("1. 資料上傳")

# 根據模式顯示所需欄位提示
if transfer_mode in ["A: 保守轉貨", "B: 加強轉貨", "C: 重點補0", "D: 清貨轉貨"]:
    st.info("""
    ✅ **必需欄位（A-D 模式）：**
    - 基本欄位：Article, Article Description, OM, RP Type, Site
    - 庫存欄位：SaSa Net Stock, Pending Received, Safety Stock, MOQ
    - 銷量欄位：Last Month Sold Qty, MTD Sold Qty
    """)
elif transfer_mode == "E: 強制轉出":
    st.info("""
    ✅ **必需欄位（E 模式）：**
    - 基本欄位：Article, Article Description, OM, RP Type, Site, **ALL**（標記商品）
    - 庫存欄位：SaSa Net Stock, Pending Received, Safety Stock, MOQ
    - 銷量欄位：Last Month Sold Qty, MTD Sold Qty
    
    ⚠️ **特殊要求：**
    - **ALL 欄位**：請在要強制轉出的商品行填寫任意非空值（例如：*、Y、ALL 等），E 模式只會處理標記的商品
    """)
else:  # F: 目標優化
    st.info("""
    ✅ **必需欄位（F 模式）：**
    - 基本欄位：Article, Article Description, OM, RP Type, Site, **Target**（目標接收數量）
    - 庫存欄位：SaSa Net Stock, Pending Received, Safety Stock, MOQ
    - 銷量欄位：Last Month Sold Qty, MTD Sold Qty
    
    ⚠️ **特殊要求：**
    - **Target 欄位**：填數字代表該店鋪的優先接收目標數量；未填Target的店鋪會按C模式補0需求計算
    """)

uploaded_file = st.file_uploader(
    "請上傳包含庫存和銷量數據的 Excel 文件",
    type=["xlsx", "xls"],
    help="必需欄位：Article, Article Description, OM, RP Type, Site, MOQ, SaSa Net Stock, Pending Received, Safety Stock, Last Month Sold Qty, MTD Sold Qty"
)

if uploaded_file is not None:
    progress_bar = st.progress(0, text="準備開始處理文件...")
    try:
        # 文件上傳驗證
        progress_bar.progress(10, text="正在驗證文件格式...")
        
        # 創建臨時文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        # 數據預處理
        progress_bar.progress(25, text="文件讀取成功！正在進行數據預處理...")
        processor = DataProcessor()
        
        # 驗證文件格式
        file_valid, error_msg = processor.validate_file_format(uploaded_file)
        if not file_valid:
            st.error(f"文件格式驗證失敗: {error_msg}")
            os.unlink(tmp_file_path)
            st.stop()
        
        try:
            df, processing_stats = processor.preprocess_data(tmp_file_path)
            progress_bar.progress(60, text="數據預處理完成！")
        except ValueError as e:
            st.error(f"❌ {str(e)}")
            os.unlink(tmp_file_path)
            st.stop()
        
        # 清理臨時文件
        os.unlink(tmp_file_path)
        
        st.success("文件上傳與數據預處理成功！")
        
        # 4.2. 資料預覽區塊
        with st.expander("基本統計和資料樣本展示", expanded=False):
            st.subheader("資料基本統計")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("總行數", processing_stats['processed_stats']['total_rows'])
            with col2:
                st.metric("商品數量", df['Article'].nunique())
            with col3:
                st.metric("店鋪數量", df['Site'].nunique())
            
            st.subheader("資料樣本（前10行）")
            st.dataframe(df.head(10))
        
        # 4.3. 分析按鈕區塊
        st.header("2. 分析與建議")
        
        st.info(f"當前選擇的模式為：**{transfer_mode}**")
        
        if st.button("🚀 生成調貨建議", type="primary"):
            progress_bar.progress(70, text="正在分析數據並生成建議...")
            with st.spinner("演算法運行中，請稍候..."):
                # 轉換模式名稱
                if transfer_mode == "A: 保守轉貨":
                    mode_name = "保守轉貨"
                elif transfer_mode == "B: 加強轉貨":
                    mode_name = "加強轉貨"
                elif transfer_mode == "C: 重點補0":
                    mode_name = "重點補0"
                elif transfer_mode == "D: 清貨轉貨":
                    mode_name = "清貨轉貨"
                elif transfer_mode == "E: 強制轉出":
                    mode_name = "強制轉出"
                else:  # F: 目標優化
                    mode_name = "目標優化"
                
                # 創建業務邏輯對象
                transfer_logic = TransferLogic()
                
                # 生成調貨建議
                recommendations = transfer_logic.generate_transfer_recommendations(df, mode_name)
                
                # 執行質量檢查
                quality_passed = transfer_logic.perform_quality_checks(df)
                
                # 獲取統計信息
                statistics = transfer_logic.get_transfer_statistics()
                
                time.sleep(1)  # 模擬耗時操作
                
            progress_bar.progress(90, text="分析完成！正在準備結果展示...")
            
            if quality_passed:
                st.success("質量檢查通過！")
            else:
                st.error("質量檢查失敗，請查看錯誤信息")
                
                # 顯示錯誤信息
                with st.expander("質量檢查錯誤詳情"):
                    for error in transfer_logic.quality_errors:
                        st.error(error)
            
            if recommendations:
                # 4.4. 結果展示區塊
                st.header("3. 分析結果")
                
                # KPI 指標卡
                st.subheader("關鍵指標 (KPIs)")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("總調貨建議數量", statistics.get('total_recommendations', 0))
                col2.metric("總調貨件數", statistics.get('total_transfer_qty', 0))
                col3.metric("涉及產品數量", statistics.get('unique_articles', 0))
                col4.metric("涉及OM數量", statistics.get('unique_oms', 0))
                
                st.markdown("---")
                
                # 調貨建議表格
                st.subheader("調貨建議清單")
                
                # 準備顯示數據
                display_data = []
                
                # 創建一個字典來跟蹤每個店鋪的累計轉出量
                cumulative_transfers = {}
                
                for rec in recommendations:
                    # 獲取轉出店鋪的原始數據
                    source_data = df[(df['Article'] == rec['Article']) & (df['Site'] == rec['Transfer Site'])]
                    source_stock = source_data['SaSa Net Stock'].iloc[0] if not source_data.empty else 0
                    source_safety = source_data['Safety Stock'].iloc[0] if not source_data.empty else 0
                    source_moq = source_data['MOQ'].iloc[0] if not source_data.empty else 0
                    
                    # 獲取接收店鋪的原始數據
                    dest_data = df[(df['Article'] == rec['Article']) & (df['Site'] == rec['Receive Site'])]
                    dest_stock = dest_data['SaSa Net Stock'].iloc[0] if not dest_data.empty else 0
                    dest_safety = dest_data['Safety Stock'].iloc[0] if not dest_data.empty else 0
                    dest_moq = dest_data['MOQ'].iloc[0] if not dest_data.empty else 0
                    
                    # 計算接收後的總貨量
                    dest_total_after = dest_stock + rec['Transfer Qty']
                    
                    # 創建店鋪的唯一標識符
                    source_key = f"{rec['Article']}_{rec['Transfer Site']}"
                    
                    # 如果是第一次轉出，初始化累計轉出量
                    if source_key not in cumulative_transfers:
                        cumulative_transfers[source_key] = 0
                    
                    # 更新累計轉出量
                    cumulative_transfers[source_key] += rec['Transfer Qty']
                    
                    # 計算累減後的庫存
                    source_after_transfer_stock = source_stock - cumulative_transfers[source_key]
                    
                    display_data.append({
                        'Article': rec['Article'],
                        'Product Desc': rec['Product Desc'],
                        'Transfer OM': rec['Transfer OM'],
                        'Transfer Site': rec['Transfer Site'],
                        'Transfer Qty': rec['Transfer Qty'],
                        'Source Original Stock': source_stock,
                        'Source After Transfer Stock': source_after_transfer_stock,
                        'Source Safety Stock': source_safety,
                        'Source MOQ': source_moq,
                        'Receive OM': rec['Receive OM'],
                        'Receive Site': rec['Receive Site'],
                        'Receive Original Stock': dest_stock,
                        'Receive Total After': dest_total_after,
                        'Receive Safety Stock': dest_safety,
                        'Receive MOQ': dest_moq,
                        'Source Type': rec.get('Source Type', ''),
                        'Destination Type': rec.get('Destination Type', '')
                    })
                
                # 創建DataFrame並顯示
                rec_df = pd.DataFrame(display_data)
                st.dataframe(rec_df, use_container_width=True)
                
                st.markdown("---")
                
                # 統計圖表
                st.subheader("詳細統計分析 (Detailed Statistical Analysis)")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("#### 按產品統計 (Statistics by Article)")
                    article_stats = statistics.get('article_stats', {})
                    if article_stats:
                        article_df = pd.DataFrame([
                            {
                                'Article': article,
                                'Total Qty': stats['total_qty'],
                                'Count': stats['count'],
                                'OM Count': stats['om_count']
                            }
                            for article, stats in article_stats.items()
                        ])
                        st.dataframe(article_df)
                    
                    st.write("#### 轉出類型分佈 (Transfer Type Distribution)")
                    source_type_stats = statistics.get('source_type_stats', {})
                    if source_type_stats:
                        source_df = pd.DataFrame([
                            {
                                'Source Type': source_type,
                                'Count': stats['count'],
                                'Qty': stats['qty']
                            }
                            for source_type, stats in source_type_stats.items()
                        ])
                        st.dataframe(source_df)
                
                with col2:
                    st.write("#### 按OM統計 (Statistics by OM)")
                    om_stats = statistics.get('om_stats', {})
                    if om_stats:
                        om_df = pd.DataFrame([
                            {
                                'OM': om,
                                'Total Qty': stats['total_qty'],
                                'Count': stats['count'],
                                'Article Count': stats['article_count']
                            }
                            for om, stats in om_stats.items()
                        ])
                        st.dataframe(om_df)
                    
                    st.write("#### 接收類型分佈 (Receive Type Distribution)")
                    dest_type_stats = statistics.get('dest_type_stats', {})
                    if dest_type_stats:
                        dest_df = pd.DataFrame([
                            {
                                'Destination Type': dest_type,
                                'Count': stats['count'],
                                'Qty': stats['qty']
                            }
                            for dest_type, stats in dest_type_stats.items()
                        ])
                        st.dataframe(dest_df)
                
                st.markdown("---")
                
                st.success("分析完成！您現在可以下載建議。")
                
                # 生成Excel文件
                with st.spinner("正在生成Excel文件..."):
                    excel_generator = ExcelGenerator()
                    excel_path = excel_generator.generate_excel_file(recommendations, statistics)
                
                # 讀取Excel文件
                with open(excel_path, "rb") as file:
                    st.download_button(
                        label="📥 下載調貨建議 (Excel)",
                        data=file.read(),
                        file_name=excel_generator.output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                progress_bar.progress(100, text="處理完畢！")
            else:
                st.info("根據當前規則，沒有生成任何調貨建議。")
                progress_bar.progress(100, text="處理完畢！")
    
    except Exception as e:
        st.error(f"處理文件時發生嚴重錯誤: {e}")
        st.exception(e)  # 顯示詳細的錯誤追蹤信息
        if 'progress_bar' in locals():
            progress_bar.progress(100, text="處理失敗！")
        
        # 清理臨時文件
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

# 系統信息
st.sidebar.markdown("---")
st.sidebar.subheader("系統信息")
st.sidebar.markdown(f"""
版本: v2.1.1  
更新時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
""")

# 頁腳
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 12px; padding: 20px;">
庫存調貨建議系統 Reallocation Calculator (2026) - For RP team (Build up by Ricky Yue)
</div>
""", unsafe_allow_html=True)
