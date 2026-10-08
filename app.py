"""
庫存調貨建議系統 v2.37.0 - Streamlit應用程序
支持三十模式系統：A(保守轉貨)/A1(保守轉貨-轉出店舖不餘存貨1件)/B(加強轉貨)/B2(附加B特別模式)/B2a(附加B2a特別模式)/B2L(附加B2L特別模式)/B2La(附加B2La特別模式)/B3(附加B跨OM特別模式)/B3a(附加B3a跨OM特別模式)/B3L(附加B3L跨OM特別模式)/B3La(附加B3La跨OM特別模式)/C(重點補0)/C1(重點補0-只補0/1(或自選數量))/C2(附加C跨OM重點補0)/D(清貨轉貨)/D2(清貨轉貨ND限定)/E1(強制轉出)/E1b(強制轉出優先類型接收)/E2(強制轉出跨OM)/F(目標優化)/F2(F指定模式)/F3(目標性補0)/NST(New Shop Target調貨)/ND1(ND同OM轉貨)/ND2(ND混合OM轉貨)/ND3(ND限同OM轉貨補0)/ND4(ND限同OM轉貨補0及有銷售記錄)/精簡SKU(限同OM)/精簡SKU(跨OM)/精簡SKU(退D001)
含模式教學分頁：30種調貨模式圖例化教學（繁體中文）
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import logging

from config import VERSION, IS_ZEABUR_RUNTIME, FLOOR_BODY_SAFETY, FLOOR_BODY_TURNDAY
from models.mode import MODE_NAME_MAP
from ui.mojibake import fix_mojibake_text, patch_streamlit_text_rendering
from ui.styles import load_css
from ui.sidebar import render_sidebar
from ui.display import (
    render_upload_requirements,
    render_data_preview,
    render_kpi_cards,
    render_charts,
    render_results_by_priority,
    render_statistics,
    render_download_button,
    render_gap_report,
)
from ui.tutorial import render_tutorial_page
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator
from services.target_utils import find_f_mode_nd_target_conflicts
from services.turnday import apply_turnday_floor, compute_coverage_days, describe_coverage


def _render_workflow_steps(stage: int):
    """主流程步驟條（顯示層用，stage=1上傳/2分析/3結果/4下載）。"""
    steps = ["📂 上傳資料", "🚀 生成建議", "📈 檢視結果", "📥 下載報表"]
    html = '<div class="steps">'
    for i, label in enumerate(steps, 1):
        if i < stage:
            cls, num = "step step--done", "✓"
        elif i == stage:
            cls, num = "step step--active", str(i)
        else:
            cls, num = "step", str(i)
        html += f'<div class="{cls}"><span class="step__num">{num}</span>{label}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def _describe_extra_params(sidebar_result: dict) -> str:
    """將側邊欄參數濃縮為一行摘要（顯示層用）。"""
    parts = []
    if sidebar_result.get('b_special_receive_site_limit_option') and sidebar_result.get('mode_code') in (
        "B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La",
        "E1", "E1b", "E2", "ND1", "ND2", "ND3", "ND4",
    ):
        parts.append(f"配對{sidebar_result['b_special_receive_site_limit_option']}")
    if sidebar_result.get('mode_code') in ("F2", "F3", "NST"):
        parts.append("HD可轉出" if sidebar_result.get('f2_allow_hd_transfer') else "HD不轉出")
    if sidebar_result.get('f_fulfill_small_first'):
        parts.append("小型目標優先")
    if sidebar_result.get('mode_code') == "NST" and sidebar_result.get('nst_max_source_shops'):
        parts.append(f"轉出≤{sidebar_result['nst_max_source_shops']}店")
    if sidebar_result.get('mode_code') == "D2":
        _d2 = {"unlimited": "不限店數", "2site_original": "限2店(原設定)", "2site_optimized": "限2店(優化版)"}
        parts.append(_d2.get(sidebar_result.get('d2_site_limit_mode'), ""))
    if sidebar_result.get('mode_code') == "C1":
        parts.append(f"門檻≤{sidebar_result.get('c1_threshold')}")
    if sidebar_result.get('mode_code') in ("C", "C1", "C2"):
        parts.append(f"每店上限{sidebar_result.get('c1_ceiling')}件")
    return " · ".join(p for p in parts if p)


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
floor_body = sidebar_result['floor_body']
turnday_days = sidebar_result['turnday_days']
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
    _has_results = bool(st.session_state.get('recommendations'))
    _excel_ready_top = bool(st.session_state.get('excel_data'))
    if _excel_ready_top:
        _render_workflow_steps(4)
    elif _has_results:
        _render_workflow_steps(3)
    else:
        _render_workflow_steps(1)

    with st.container():
        st.markdown('<div class="section-title"><span class="section-title__badge">STEP 1</span>📂 資料上傳</div>', unsafe_allow_html=True)

        render_upload_requirements(mode_code)

        uploaded_file = st.file_uploader(
            "拖放或點擊上傳 Excel 文件",
            type=["xlsx", "xls"],
            help="支援 .xlsx 和 .xls 格式",
        )

        date_col, hint_col = st.columns([1, 1.4])
        with date_col:
            mtd_as_of_date = st.date_input(
                "MTD數據日期（數據覆蓋至該日，通常T-1）",
                value=(datetime.now() - timedelta(days=1)).date(),
                key='mtd_as_of_date',
                help="Turnday 保底主體用以計算日銷速的數據截止日期：覆蓋日數 = 上月日數 + 該日日號（例：8月15日 = 7月31日 + 15日 = 46日）。Safety 主體不使用此日期。"
            )
        with hint_col:
            if floor_body == FLOOR_BODY_TURNDAY:
                st.caption(describe_coverage(mtd_as_of_date))
            else:
                st.caption("目前為 Safety Stock 主體，此日期僅 Turnday 主體使用，可忽略。")

    if uploaded_file is None:
        st.markdown(
            '<div class="empty-state"><strong>👋 開始使用（3 步完成）：</strong>'
            '<ol><li>左側邊欄確認 <strong>步驟 1 保底主體</strong> 與 <strong>步驟 2 轉貨模式</strong>（已預設 Safety＋A 模式可直接試跑）</li>'
            '<li>上方拖放 Excel 文件（需含 Article / OM / RP Type / Site / 庫存 / 銷量 / MOQ 等基本欄位）</li>'
            '<li>點擊「🎯 生成調貨建議」，再按「📤 準備 Excel 報表」下載</li></ol>'
            '💡 不確定選哪個模式？先到「📖 模式教學」分頁看決策指南。</div>',
            unsafe_allow_html=True,
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

            if floor_body == FLOOR_BODY_TURNDAY:
                df = apply_turnday_floor(df, mtd_as_of_date, int(turnday_days))
                st.info(
                    f"🛡️ Turnday 保底主體已套用：保底 = 日銷速 × {int(turnday_days)}日"
                    f"（數據日期 {mtd_as_of_date.isoformat()}，覆蓋日數 {compute_coverage_days(mtd_as_of_date)}日）。"
                    f"Safety Stock 欄已換成 Turnday 保底值，原值保留於 Original Safety Stock。"
                )

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
            # 預處理階段結束，收起進度條（分析階段改用 st.status 呈現）
            progress_bar.empty()

            with st.container():
                st.markdown('<div class="section-title"><span class="section-title__badge">STEP 2</span>🚀 分析與建議</div>', unsafe_allow_html=True)

                floor_body_label = (
                    "Safety Stock（現行版本）" if floor_body == FLOOR_BODY_SAFETY
                    else f"Turnday（日銷速×{int(turnday_days)}日，數據日期 {mtd_as_of_date.isoformat()}）"
                )
                _extra_params = _describe_extra_params(sidebar_result)
                _extra_html = f"<br>⚙️ 參數 · {_extra_params}" if _extra_params else ""
                st.markdown(f"""
                <div class="current-config-banner">
                    <strong>當前模式</strong> · {transfer_mode}<br>
                    <strong>保底主體</strong> · {floor_body_label}{_extra_html}
                </div>
                """, unsafe_allow_html=True)

            nst_max_source_shops = sidebar_result.get('nst_max_source_shops')
            current_run_key = f"{mode_code}_{b_special_receive_site_limit_option}_{f2_allow_hd_transfer}_{d2_site_limit_mode}_{c1_threshold}_{c1_ceiling}_{f_fulfill_small_first}_{nst_max_source_shops}_{floor_body}_{turnday_days}_{mtd_as_of_date.isoformat()}_{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get('_run_key') != current_run_key:
                for k in ['recommendations', 'statistics', 'gap_report', 'quality_passed', 'quality_errors', 'excel_data', 'excel_filename', 'excel_run_key', 'active_mode_name']:
                    st.session_state.pop(k, None)
                for k in [k for k in st.session_state if k.startswith('_display_df_')]:
                    st.session_state.pop(k)
                st.session_state['_run_key'] = current_run_key

            if st.button("🎯 生成調貨建議", type="primary", use_container_width=True):
                with st.status("分析中...", expanded=True) as status:
                    st.write("演算法運行中，生成調貨建議...")
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

                    st.write("品質檢查...")
                    quality_passed = transfer_logic.perform_quality_checks(df, mode_name)

                    st.write("統計與缺口分析...")
                    statistics = transfer_logic.get_transfer_statistics()
                    gap_report = transfer_logic.get_gap_report()

                    st.session_state['recommendations'] = recommendations
                    st.session_state['statistics'] = statistics
                    st.session_state['gap_report'] = gap_report
                    st.session_state['quality_passed'] = quality_passed
                    st.session_state['quality_errors'] = transfer_logic.quality_errors
                    st.session_state['active_mode_name'] = mode_name

                    status.update(label="分析完成", state="complete", expanded=False)

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
                    st.markdown('<div class="section-title"><span class="section-title__badge">STEP 3</span>📈 分析結果</div>', unsafe_allow_html=True)
                    _total_qty = statistics.get('total_transfer_qty', 0)
                    st.caption(f"共 {len(recommendations):,} 條建議 · {int(_total_qty):,} 件 · {transfer_mode}")

                    render_kpi_cards(statistics)

                    render_charts(statistics)

                    render_results_by_priority(recommendations, df, current_run_key, st.session_state.get('active_mode_name', ''))

                    render_statistics(statistics)

                    render_gap_report(st.session_state.get('gap_report', {}), current_run_key)

                    with st.container():
                        st.markdown("---")
                        st.markdown('<div class="section-title"><span class="section-title__badge">STEP 4</span>📥 匯出報表</div>', unsafe_allow_html=True)
                        st.success("✅ 分析完成!")

                _excel_ready = (
                    st.session_state.get('excel_run_key') == current_run_key
                    and 'excel_data' in st.session_state
                )
                if not _excel_ready:
                    # 惰性生成：按下才產生 Excel，避免大型結果的無謂等待
                    if st.button(
                        "📤 準備 Excel 報表",
                        use_container_width=True,
                        help="按下後才生成 Excel 文件；生成完成會出現下載按鈕。大型結果可節省等待時間。",
                    ):
                        with st.spinner("生成 Excel 文件..."):
                            excel_generator = ExcelGenerator()
                            st.session_state['excel_data'] = excel_generator.generate_excel_file(
                                recommendations,
                                statistics,
                                mode=st.session_state.get('active_mode_name', ''),
                                df=df,
                                gap_report=st.session_state.get('gap_report', {}),
                                floor_body_label=floor_body_label,
                            )
                            st.session_state['excel_filename'] = excel_generator.output_filename
                            st.session_state['excel_run_key'] = current_run_key
                            _excel_ready = True

                if _excel_ready:
                    _excel_bytes = st.session_state.get('excel_data', b'')
                    _excel_filename = st.session_state.get('excel_filename', '調貨建議.xlsx')
                    render_download_button(_excel_bytes, _excel_filename, current_run_key)
            else:
                st.info("根據當前規則，沒有生成任何調貨建議。")

        except Exception as e:
            st.error(f"處理文件時發生錯誤: {e}")
            with st.expander("顯示詳細錯誤追蹤"):
                st.exception(e)
            if 'progress_bar' in locals():
                progress_bar.empty()

    st.markdown(f"""
    <div class="app-footer">
        <p>📦 庫存調貨建議系統 <strong>{VERSION}</strong></p>
        <p>Intelligent Inventory Reallocation System (2026) · Developed by Ricky Yue · 只限 RP Team 使用</p>
    </div>
    """, unsafe_allow_html=True)
