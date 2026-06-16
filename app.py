"""
庫存調貨建議系統 v2.27.0 - Streamlit應用程序
支持二十八模式系統：A(保守轉貨)/B(加強轉貨)/B2(附加B特別模式)/B2a(附加B2a特別模式)/B2L(附加B2L特別模式)/B2La(附加B2La特別模式)/B3(附加B跨OM特別模式)/B3a(附加B3a跨OM特別模式)/B3L(附加B3L跨OM特別模式)/B3La(附加B3La跨OM特別模式)/C(重點補0)/C1(重點補0-只補0/1(或自選數量))/C2(附加C跨OM重點補0)/D(清貨轉貨)/D2(清貨轉貨ND限定)/E1(強制轉出)/E1b(強制轉出優先類型接收)/E2(強制轉出跨OM)/F(目標優化)/F2(F指定模式)/F3(目標性補0)/NST(New Shop Target調貨)/ND1(ND同OM轉貨)/ND2(ND混合OM轉貨)/ND3(ND限同OM轉貨補0)/精簡SKU(限同OM)/精簡SKU(跨OM)/精簡SKU(退D001)
含模式教學分頁：28種調貨模式圖例化教學（繁體中文）
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import logging

from config import VERSION, IS_ZEABUR_RUNTIME
from models.mode import MODE_NAME_MAP
from ui.mojibake import fix_mojibake_text, patch_streamlit_text_rendering
from ui.styles import load_css
from ui.sidebar import render_sidebar
from ui.display import (
    render_upload_requirements,
    render_data_preview,
    render_kpi_cards,
    render_results_by_priority,
    render_statistics,
    render_download_button,
    render_ai_executive_summary_button,
)
from ui.tutorial import render_tutorial_page
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator
from services.target_utils import find_f_mode_nd_target_conflicts


@st.cache_data(show_spinner=False)
def _cached_preprocess(file_bytes: bytes) -> tuple:
    import io
    processor = DataProcessor()
    df, stats = processor.preprocess_data(io.BytesIO(file_bytes))
    return df, stats


logging.basicConfig(level=os.getenv('KILO_LOG_LEVEL', 'WARNING' if IS_ZEABUR_RUNTIME else 'INFO').upper())
logger = logging.getLogger(__name__)


if os.getenv("KILO_FIX_MOJIBAKE", "0") == "1":
    patch_streamlit_text_rendering()

st.set_page_config(
    page_title=fix_mojibake_text(f"庫存調貨建議系統 {VERSION}"),
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(load_css(), unsafe_allow_html=True)

sidebar_result = render_sidebar()

mode_code = sidebar_result['mode_code']
transfer_mode = sidebar_result['transfer_mode']
b_special_max_receive_sites_per_source = sidebar_result['b_special_max_receive_sites_per_source']
b_special_receive_site_limit_option = sidebar_result['b_special_receive_site_limit_option']
f2_allow_hd_transfer = sidebar_result['f2_allow_hd_transfer']
d2_site_limit_mode = sidebar_result['d2_site_limit_mode']
c1_threshold = sidebar_result['c1_threshold']
c1_ceiling = sidebar_result['c1_ceiling']
f_fulfill_small_first = sidebar_result['f_fulfill_small_first']

st.markdown(f"""
<div class="app-header fade-in">
    <div class="app-header__logo">📦</div>
    <div>
        <h1 class="app-header__title">庫存調貨建議系統</h1>
        <p class="app-header__subtitle">{VERSION} · Intelligent Inventory Reallocation System</p>
    </div>
</div>
""", unsafe_allow_html=True)

tab_system, tab_tutorial = st.tabs(["🏠 調貨系統", "📖 模式教學"])

with tab_tutorial:
    render_tutorial_page()

with tab_system:
    with st.container():
        st.markdown("### 📂 資料上傳")

        render_upload_requirements(mode_code)

        uploaded_file = st.file_uploader(
            "拖放或點擊上傳 Excel 文件",
            type=["xlsx", "xls"],
            help="支援 .xlsx 和 .xls 格式",
        )

    if uploaded_file is not None:
        progress_bar = st.progress(0, text="準備開始處理文件...")
        try:
            progress_bar.progress(10, text="正在驗證文件格式...")

            progress_bar.progress(25, text="文件讀取成功!正在進行數據預處理...")
            processor = DataProcessor()

            file_valid, error_msg = processor.validate_file_format(uploaded_file)
            if not file_valid:
                st.error(f"文件格式驗證失敗: {error_msg}")
                st.stop()

            try:
                df, processing_stats = _cached_preprocess(uploaded_file.getvalue())
                progress_bar.progress(60, text="數據預處理完成!")
            except ValueError as e:
                st.error(f"❌ {str(e)}")
                st.stop()

            if mode_code in ["B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La"]:
                original_columns = processing_stats['original_stats'].get('columns', [])
                has_type_column = any(col.upper() == 'TYPE' for col in original_columns)
                if not has_type_column:
                    st.error("❌ B2/B2a/B2L/B2La/B3/B3a/B3L/B3La模式必須包含Type欄位(不分大小寫)。請確認Excel欄位後再上傳。")
                    st.stop()

            st.success("檔案上傳與數據預處理成功!")

            invalid_rp_count = processing_stats['processed_stats'].get('invalid_rp_type_count', 0)
            if invalid_rp_count > 0:
                invalid_rp_vals = processing_stats['processed_stats'].get('invalid_rp_types', [])
                st.warning(
                    f"⚠️ 資料品質提示：發現 {invalid_rp_count} 行 RP Type 欄位值不是 ND 或 RF "
                    f"（{', '.join(str(v) for v in invalid_rp_vals)}），已自動修正為 RF。請確認原始數據是否正確。"
                )

            if mode_code in ["F", "F2", "F3"]:
                f_mode_conflicts = find_f_mode_nd_target_conflicts(df)
                if not f_mode_conflicts.empty:
                    affected_sites = sorted(
                        set(f_mode_conflicts['Site'].astype(str).str.strip().str.upper())
                    )
                    site_text = "、".join(affected_sites[:8])
                    if len(affected_sites) > 8:
                        site_text += f" 等{len(affected_sites)}間店"

                    st.warning(
                        f"⚠️ {mode_code}模式提示：偵測到 {len(f_mode_conflicts)} 行資料為 ND 且 Target>0。"
                        f"此店因 ND 規則不會接收。"
                        f"受影響店舖：{site_text}"
                    )

                    preview_cols = [c for c in ['Article', 'OM', 'Site', 'RP Type', 'Target', 'SaSa Net Stock', 'Pending Received'] if c in f_mode_conflicts.columns]
                    with st.expander("檢視 ND + Target>0 明細", expanded=False):
                        st.dataframe(
                            f_mode_conflicts[preview_cols].head(50),
                            use_container_width=True,
                        )

            render_data_preview(df, processing_stats)

            with st.container():
                st.markdown("### 🚀 分析與建議")

                st.markdown(f"""
                <div class="surface-card">
                    <strong>當前模式</strong> · {transfer_mode}
                </div>
                """, unsafe_allow_html=True)

            nst_max_source_shops = sidebar_result.get('nst_max_source_shops')
            current_run_key = f"{mode_code}_{b_special_receive_site_limit_option}_{f2_allow_hd_transfer}_{d2_site_limit_mode}_{c1_threshold}_{c1_ceiling}_{f_fulfill_small_first}_{nst_max_source_shops}_{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get('_run_key') != current_run_key:
                for k in ['recommendations', 'statistics', 'quality_passed', 'quality_errors', 'excel_data', 'excel_filename', 'excel_run_key', 'active_mode_name',
                          'ai_executive_summary']:
                    st.session_state.pop(k, None)
                for k in [k for k in st.session_state if k.startswith('_display_df_')]:
                    st.session_state.pop(k)
                st.session_state['_run_key'] = current_run_key

            if st.button("🎯 生成調貨建議", type="primary", use_container_width=True):
                progress_bar.progress(70, text="正在分析數據並生成建議...")
                with st.spinner("演算法運行中,請稍候..."):
                    mode_name = MODE_NAME_MAP.get(mode_code, "目標優化")

                    transfer_logic = TransferLogic(
                        b_special_max_receive_sites_per_source=b_special_max_receive_sites_per_source,
                        f2_allow_hd_transfer=f2_allow_hd_transfer,
                        d2_site_limit_mode=d2_site_limit_mode,
                        c1_threshold=c1_threshold,
                        c1_ceiling=c1_ceiling,
                        f_fulfill_small_first=f_fulfill_small_first,
                        nst_max_source_shops=nst_max_source_shops,
                    )

                    recommendations = transfer_logic.generate_transfer_recommendations(df, mode_name)

                    quality_passed = transfer_logic.perform_quality_checks(df, mode_name)

                    statistics = transfer_logic.get_transfer_statistics()

                    st.session_state['recommendations'] = recommendations
                    st.session_state['statistics'] = statistics
                    st.session_state['quality_passed'] = quality_passed
                    st.session_state['quality_errors'] = transfer_logic.quality_errors
                    st.session_state['active_mode_name'] = mode_name

                progress_bar.progress(90, text="分析完成!正在準備結果展示...")

            recommendations = st.session_state.get('recommendations')
            statistics = st.session_state.get('statistics', {})
            quality_passed = st.session_state.get('quality_passed')

            if quality_passed is not None:
                if quality_passed:
                    st.success("質量檢查通過!")
                else:
                    st.error("質量檢查失敗,請查看錯誤信息")

                    with st.expander("質量檢查錯誤詳情"):
                        for error in st.session_state.get('quality_errors', []):
                            st.error(error)

            if recommendations:
                with st.container():
                    st.markdown("### 📈 分析結果")

                    render_kpi_cards(statistics)

                    render_results_by_priority(recommendations, df, current_run_key, st.session_state.get('active_mode_name', ''))

                    render_statistics(statistics)

                    render_ai_executive_summary_button(recommendations, statistics, st.session_state.get('active_mode_name', ''))

                    with st.container():
                        st.markdown("---")
                        st.success("✅ 分析完成!")

                _ai_summary = st.session_state.get('ai_executive_summary', '')
                _excel_cache_key = f"{current_run_key}_{hash(_ai_summary)}" if _ai_summary else current_run_key
                if st.session_state.get('excel_run_key') != _excel_cache_key or 'excel_data' not in st.session_state:
                    with st.spinner("生成 Excel 文件..."):
                        excel_generator = ExcelGenerator()
                        st.session_state['excel_data'] = excel_generator.generate_excel_file(
                            recommendations,
                            statistics,
                            mode=st.session_state.get('active_mode_name', ''),
                            ai_summary=_ai_summary or None,
                            df=df,
                        )
                        st.session_state['excel_filename'] = excel_generator.output_filename
                        st.session_state['excel_run_key'] = _excel_cache_key

                _excel_bytes = st.session_state.get('excel_data', b'')
                _excel_filename = st.session_state.get('excel_filename', '調貨建議.xlsx')

                render_download_button(_excel_bytes, _excel_filename, current_run_key)

                progress_bar.progress(100, text="處理完畢!")
            else:
                st.info("根據當前規則，沒有生成任何調貨建議。")
                progress_bar.progress(100, text="處理完畢!")

        except Exception as e:
            st.error(f"處理文件時發生錯誤: {e}")
            if st.checkbox("顯示詳細錯誤追蹤"):
                st.exception(e)
            if 'progress_bar' in locals():
                progress_bar.progress(100, text="處理失敗!")

    st.markdown(f"""
    <div class="app-footer">
        <p>📦 庫存調貨建議系統 <strong>{VERSION}</strong></p>
        <p>Intelligent Inventory Reallocation System (2026) · Developed by Ricky Yue · 只限 RP Team 使用</p>
    </div>
    """, unsafe_allow_html=True)
