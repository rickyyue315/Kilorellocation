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

# 設置頁面配置
st.set_page_config(
    page_title="庫存調貨建議系統 v1.9",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 應用程序標題
st.title("📦 調貨建議生成系統 v1.9")
st.markdown("---")

# 側邊欄
st.sidebar.header("系統資訊")
st.sidebar.info("""
**版本：v1.9**
**開發者: Ricky**

**核心功能：**  
- ✅ 雙模式系統
- ✅ A模式(保守轉貨)/B模式(加強轉貨)
- ✅ ND/RF類型智慧識別
- ✅ 優先順序調貨匹配
- ✅ RF轉出限制控制
- ✅ 統計分析和圖表
- ✅ Excel格式匯出
""")

# 模式選擇
st.sidebar.subheader("模式選擇")
mode = st.sidebar.radio(
    "選擇轉貨模式",
    ["保守轉貨 (A模式)", "加強轉貨 (B模式)"],
    key="mode"
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

# 文件上傳區域
st.header("1. 上傳數據文件")
uploaded_file = st.file_uploader(
    "請上傳Excel文件（.xlsx格式）",
    type=['xlsx'],
    help="上傳包含庫存數據的Excel文件，必須包含以下欄位：Article, Article Description, OM, RP Type, Site, MOQ, SaSa Net Stock, Pending Received, Safety Stock, Last Month Sold Qty, MTD Sold Qty"
)

# 如果有文件上傳
if uploaded_file is not None:
    # 顯示文件信息
    st.success(f"文件上傳成功: {uploaded_file.name}")
    
    # 創建臨時文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
    
    try:
        # 數據預處理
        st.header("2. 數據預處理")
        with st.spinner("正在處理數據，請稍候..."):
            processor = DataProcessor()
            
            # 驗證文件格式
            file_valid, error_msg = processor.validate_file_format(uploaded_file)
            if not file_valid:
                st.error(f"文件格式驗證失敗: {error_msg}")
                os.unlink(tmp_file_path)
                st.stop()
            
            df, processing_stats = processor.preprocess_data(tmp_file_path)
        
        # 顯示處理統計
        col1, col2 = st.columns(2)
        with col1:
            st.metric("原始數據行數", processing_stats['original_stats']['total_rows'])
        with col2:
            st.metric("處理後數據行數", processing_stats['processed_stats']['total_rows'])
        
        # 顯示數據預覽
        st.subheader("數據預覽")
        st.dataframe(df.head(10))
        
        # 數據統計
        st.subheader("數據統計")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("商品數量", df['Article'].nunique())
        with col2:
            st.metric("OM數量", df['OM'].nunique())
        with col3:
            st.metric("店鋪數量", df['Site'].nunique())
        
        # 生成調貨建議
        st.header("3. 生成調貨建議")
        st.info(f"當前模式：{mode}")
        
        if st.button("生成調貨建議", type="primary"):
            with st.spinner("正在生成調貨建議，請稍候..."):
                # 創建業務邏輯對象
                transfer_logic = TransferLogic()
                
                # 轉換模式名稱
                mode_name = "保守轉貨" if mode == "保守轉貨 (A模式)" else "加強轉貨"
                
                # 生成調貨建議
                recommendations = transfer_logic.generate_transfer_recommendations(df, mode_name)
                
                # 執行質量檢查
                quality_passed = transfer_logic.perform_quality_checks(df)
                
                # 獲取統計信息
                statistics = transfer_logic.get_transfer_statistics()
            
            # 顯示結果
            if quality_passed:
                st.success("質量檢查通過！")
            else:
                st.error("質量檢查失敗，請查看錯誤信息")
                
                # 顯示錯誤信息
                with st.expander("質量檢查錯誤詳情"):
                    for error in transfer_logic.quality_errors:
                        st.error(error)
            
            # 顯示調貨建議統計
            st.subheader("調貨建議統計")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("總調貨建議數量", statistics.get('total_recommendations', 0))
            with col2:
                st.metric("總調貨件數", statistics.get('total_transfer_qty', 0))
            with col3:
                st.metric("涉及產品數量", statistics.get('unique_articles', 0))
            with col4:
                st.metric("涉及OM數量", statistics.get('unique_oms', 0))
            
            # 顯示調貨建議詳情
            if recommendations:
                st.subheader("調貨建議詳情")
                
                # 準備顯示數據
                display_data = []
                for rec in recommendations:
                    display_data.append({
                        'Article': rec['Article'],
                        'Product Desc': rec['Product Desc'],
                        'Transfer OM': rec['Transfer OM'],
                        'Transfer Site': rec['Transfer Site'],
                        'Receive OM': rec['Receive OM'],
                        'Receive Site': rec['Receive Site'],
                        'Transfer Qty': rec['Transfer Qty'],
                        'Source Type': rec.get('Source Type', ''),
                        'Destination Type': rec.get('Destination Type', '')
                    })
                
                # 創建DataFrame並顯示
                rec_df = pd.DataFrame(display_data)
                st.dataframe(rec_df, use_container_width=True)
                
                # 生成Excel文件
                st.header("4. 下載結果")
                excel_generator = ExcelGenerator()
                
                # 創建下載按鈕
                with st.spinner("正在生成Excel文件..."):
                    excel_path = excel_generator.generate_excel_file(recommendations, statistics)
                
                # 讀取Excel文件
                with open(excel_path, "rb") as file:
                    st.download_button(
                        label="下載調貨建議Excel文件",
                        data=file.read(),
                        file_name=excel_generator.output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # 顯示統計圖表
                st.subheader("統計圖表")
                
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
            else:
                st.info("沒有生成調貨建議，可能是當前數據條件不滿足調貨要求。")
    
    finally:
        # 清理臨時文件
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

# 使用說明
st.sidebar.markdown("---")
st.sidebar.subheader("使用說明")
st.sidebar.markdown("""
1. 上傳包含庫存數據的Excel文件
2. 選擇轉貨模式（保守轉貨或加強轉貨）
3. 點擊"生成調貨建議"按鈕
4. 查看調貨建議結果和統計信息
5. 下載生成的Excel文件

**注意事項：**
- 確保Excel文件包含所有必需的欄位
- Article欄位必須為12位文本格式
- 系統會自動處理缺失值和異常值
- RF過剩轉出：轉出後剩餘庫存不低於安全庫存
- RF加強轉出：轉出後剩餘庫存可能低於安全庫存
""")

# 系統信息
st.sidebar.markdown("---")
st.sidebar.subheader("系統信息")
st.sidebar.markdown(f"""
版本: v1.9  
更新時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
""")