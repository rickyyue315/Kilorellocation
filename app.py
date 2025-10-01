"""
庫存調貨建議系統 v1.9 - Streamlit應用程序
簡化為雙模式系統：A(保守轉貨)/B(加強轉貨)
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import tempfile
from datetime import datetime
import logging
import matplotlib.pyplot as plt
import seaborn as sns
import time
from io import BytesIO

# 導入自定義模組
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設置matplotlib中文字體
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 1. 頁面配置
st.set_page_config(
    page_title="庫存調貨建議系統 v1.9",
    page_icon="📦",
    layout="wide"
)

# 2. 側邊欄設計
with st.sidebar:
    st.header("系統資訊")
    st.info(""" 
    **版本：v1.9** 
    **開發者: Ricky** 
    
    **核心功能：**  
    - ✅ 簡化雙模式系統
    - ✅ A模式(保守轉貨)/B模式(加強轉貨)
    - ✅ ND/RF類型智慧識別
    - ✅ 優先順序調貨匹配
    - ✅ RF轉出限制控制
    - ✅ 統計分析和圖表
    - ✅ Excel格式匯出
    """)
    
    st.sidebar.header("操作指引")
    st.sidebar.markdown("""
    1.  **上傳 Excel 文件**：點擊瀏覽文件或拖放文件到上傳區域。
    2.  **選擇轉貨模式**：在側邊欄選擇轉貨模式（保守轉貨或加強轉貨）。
    3.  **啟動分析**：點擊「生成調貨建議」按鈕開始處理。
    4.  **查看結果**：在主頁面查看KPI、建議和圖表。
    5.  **下載報告**：點擊下載按鈕獲取 Excel 報告。
    """)
    
    # 模式選擇
    st.sidebar.header("模式選擇")
    transfer_mode = st.radio(
        "選擇轉貨模式",
        ["A: 保守轉貨", "B: 加強轉貨"],
        key='transfer_mode',
        help="A模式優先保障安全庫存，B模式則更積極地處理滯銷品。"
    )
    
    # 模式說明
    with st.sidebar.expander("模式說明"):
        st.markdown("""
        **轉貨模式：**
        - **A模式(保守轉貨)**：轉出後剩餘庫存不低於安全庫存，轉出類型為RF過剩轉出
        - **B模式(加強轉貨)**：轉出後剩餘庫存可能低於安全庫存，轉出類型為RF加強轉出
        
        **轉出類型判斷：**
        - 如果轉出店鋪轉出後, 剩餘庫存不會低過Safety stock, 轉出類型定位為RF過剩轉出
        - 如果轉出店鋪轉出後, 剩餘庫存會低過Safety stock, 轉出類型定位為RF加強轉出
        
        **接收條件：**
        - SaSa Net Stock + Pending Received < Safety Stock，便需要進行調撥接收
        """)

# 3. 頁面頭部
st.title("📦 庫存調貨建議系統 v1.9")
st.markdown("---")

# 4. 主要區塊
# 4.1. 資料上傳區塊
st.header("1. 資料上傳")
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
        
        df, processing_stats = processor.preprocess_data(tmp_file_path)
        progress_bar.progress(60, text="數據預處理完成！")
        
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
        
        st.info(f"當前選擇的模式為： **{transfer_mode}**")
        
        if st.button("🚀 生成調貨建議", type="primary"):
            progress_bar.progress(70, text="正在分析數據並生成建議...")
            with st.spinner("演算法運行中，請稍候..."):
                # 轉換模式名稱
                mode_name = "保守轉貨" if transfer_mode == "A: 保守轉貨" else "加強轉貨"
                
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
                for rec in recommendations:
                    # 獲取轉出店鋪的原始數據
                    source_data = df[(df['Article'] == rec['Article']) & (df['Site'] == rec['Transfer Site'])]
                    source_stock = source_data['SaSa Net Stock'].iloc[0] if not source_data.empty else 0
                    source_pending = source_data['Pending Received'].iloc[0] if not source_data.empty else 0
                    source_safety = source_data['Safety Stock'].iloc[0] if not source_data.empty else 0
                    
                    # 獲取接收店鋪的原始數據
                    dest_data = df[(df['Article'] == rec['Article']) & (df['Site'] == rec['Receive Site'])]
                    dest_stock = dest_data['SaSa Net Stock'].iloc[0] if not dest_data.empty else 0
                    dest_pending = dest_data['Pending Received'].iloc[0] if not dest_data.empty else 0
                    dest_safety = dest_data['Safety Stock'].iloc[0] if not dest_data.empty else 0
                    
                    # 計算接收後的總貨量
                    dest_total_after = dest_stock + dest_pending + rec['Transfer Qty']
                    
                    display_data.append({
                        'Article': rec['Article'],
                        'Product Desc': rec['Product Desc'],
                        'Transfer OM': rec['Transfer OM'],
                        'Transfer Site': rec['Transfer Site'],
                        'Transfer Qty': rec['Transfer Qty'],
                        'Source Original Stock': source_stock,
                        'Source After Transfer Stock': source_stock - rec['Transfer Qty'],
                        'Receive OM': rec['Receive OM'],
                        'Receive Site': rec['Receive Site'],
                        'Receive Original Stock': dest_stock,
                        'Receive Pending': dest_pending,
                        'Receive Total After': dest_total_after,
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
                
                # 顯示統計圖表
                st.subheader("OM Transfer vs Receive Analysis Chart")
                
                # 創建OM Transfer vs Receive Analysis圖表
                fig, ax = plt.subplots(figsize=(12, 8))
                
                # 準備圖表數據
                om_stats = statistics.get('om_stats', {})
                if om_stats:
                    om_names = list(om_stats.keys())
                    transfer_qtys = [stats['total_qty'] for stats in om_stats.values()]
                    
                    # 創建橫條圖
                    y_pos = np.arange(len(om_names))
                    
                    if mode_name == "保守轉貨":
                        # A模式圖表
                        source_type_stats = statistics.get('source_type_stats', {})
                        nd_qtys = []
                        rf_excess_qtys = []
                        
                        for om in om_names:
                            # 計算每個OM的ND和RF轉出數量
                            nd_qty = 0
                            rf_excess_qty = 0
                            
                            for rec in recommendations:
                                if rec['Transfer OM'] == om:
                                    if rec.get('Source Type') == 'ND轉出':
                                        nd_qty += rec['Transfer Qty']
                                    elif rec.get('Source Type') == 'RF過剩轉出':
                                        rf_excess_qty += rec['Transfer Qty']
                            
                            nd_qtys.append(nd_qty)
                            rf_excess_qtys.append(rf_excess_qty)
                        
                        # 繪製四條形圖
                        width = 0.2
                        ax.barh(y_pos + width*1.5, nd_qtys, width, label='ND Transfer Out', color='skyblue')
                        ax.barh(y_pos + width*0.5, rf_excess_qtys, width, label='RF Excess Transfer Out', color='lightgreen')
                        
                    else:
                        # B模式圖表
                        source_type_stats = statistics.get('source_type_stats', {})
                        nd_qtys = []
                        rf_excess_qtys = []
                        rf_enhanced_qtys = []
                        
                        for om in om_names:
                            # 計算每個OM的ND和RF轉出數量
                            nd_qty = 0
                            rf_excess_qty = 0
                            rf_enhanced_qty = 0
                            
                            for rec in recommendations:
                                if rec['Transfer OM'] == om:
                                    if rec.get('Source Type') == 'ND轉出':
                                        nd_qty += rec['Transfer Qty']
                                    elif rec.get('Source Type') == 'RF過剩轉出':
                                        rf_excess_qty += rec['Transfer Qty']
                                    elif rec.get('Source Type') == 'RF加強轉出':
                                        rf_enhanced_qty += rec['Transfer Qty']
                            
                            nd_qtys.append(nd_qty)
                            rf_excess_qtys.append(rf_excess_qty)
                            rf_enhanced_qtys.append(rf_enhanced_qty)
                        
                        # 繪製五條形圖
                        width = 0.15
                        ax.barh(y_pos + width*1.5, nd_qtys, width, label='ND Transfer Out', color='skyblue')
                        ax.barh(y_pos + width*0.5, rf_excess_qtys, width, label='RF Excess Transfer Out', color='lightgreen')
                        ax.barh(y_pos - width*0.5, rf_enhanced_qtys, width, label='RF Enhanced Transfer Out', color='orange')
                    
                    # 計算接收類型數據
                    urgent_qtys = []
                    potential_qtys = []
                    
                    for om in om_names:
                        # 計算每個OM的緊急和潛在缺貨接收數量
                        urgent_qty = 0
                        potential_qty = 0
                        
                        for rec in recommendations:
                            if rec['Receive OM'] == om:
                                if rec.get('Destination Type') == '緊急缺貨補貨':
                                    urgent_qty += rec['Transfer Qty']
                                elif rec.get('Destination Type') == '潛在缺貨補貨':
                                    potential_qty += rec['Transfer Qty']
                        
                        urgent_qtys.append(urgent_qty)
                        potential_qtys.append(potential_qty)
                    
                    # 繪製接收類型
                    width = 0.2 if mode_name == "保守轉貨" else 0.15
                    ax.barh(y_pos - width*1.5, urgent_qtys, width, label='Urgent Shortage Receive', color='salmon')
                    ax.barh(y_pos - width*2.5, potential_qtys, width, label='Potential Shortage Receive', color='gold')
                    
                    # 設置圖表標籤和標題
                    ax.set_yticks(y_pos)
                    ax.set_yticklabels(om_names)
                    ax.invert_yaxis()  # 標籤從上到下
                    ax.set_xlabel('Transfer Quantity')
                    ax.set_title(f'OM Transfer vs Receive Analysis ({mode_name})')
                    ax.legend()
                    
                    # 顯示圖表
                    st.pyplot(fig)
                else:
                    st.info("沒有足夠的數據生成圖表")
                
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
版本: v1.9  
更新時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
""")