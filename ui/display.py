"""
結果展示 UI — 欄位說明、資料查覽、KPI、結果表格、統計、下載按鈕
"""

import streamlit as st
import pandas as pd
from typing import Optional

from config import IS_ZEABUR_RUNTIME, ZEABUR_RESULT_PREVIEW_LIMIT


def render_upload_requirements(mode_code: str):
    if mode_code in ["A", "B", "C", "C1", "C2", "D", "D2"]:
        with st.expander("📋 必需欄位說明", expanded=False):
            st.markdown("""
            **基本欄位:**
            - Article, Article Description, OM, RP Type, Site
            
            **庫存欄位:**
            - SaSa Net Stock, Pending Received, Safety Stock, MOQ
            
            **銷量欄位:**
            - Last Month Sold Qty, MTD Sold Qty
            """)
    elif mode_code in ["B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La"]:
        with st.expander("📋 必需欄位說明", expanded=False):
            st.markdown("""
            **基本欄位:**
            - Article, Article Description, OM, RP Type, Site, **Type**
            
            **庫存欄位:**
            - SaSa Net Stock, Pending Received, Safety Stock, MOQ
            
            **銷量欄位:**
            - Last Month Sold Qty, MTD Sold Qty
            
            **⚠️ 特殊要求:**
            - **Type 欄位**:B2/B2a/B3/B3a 的 Type=L 且銷量≤2 店舖將全轉出(即使是RF)
            - **Type 欄位**:B2L/B2La/B3L/B3La 的 Type=L 且銷量≤2 店舖保留2件後轉出
            - **Type 說明**:Type=T 為遊客區店舖、Type=M 為混合型店舖;B2/B2a/B2L/B2La/B3/B3a/B3L/B3La接收優先級以此排序
            - **Mix 保護規則**:若出貨店舖 Type=M 且總銷量 > 目標店總銷量，該配對會被跳過（總銷量=Last Month Sold Qty+MTD Sold Qty）
            - **B2a/B2La/B3a/B3La 限制**:Type=T(遊客鋪)不可出貨
            """)
    elif mode_code in ["E1", "E1b", "E2"]:
        with st.expander("📋 必需欄位說明", expanded=False):
            st.markdown("""
            **基本欄位:**
            - Article, Article Description, OM, RP Type, Site, **ALL**(標記商品), Type
            
            **庫存欄位:**
            - SaSa Net Stock, Pending Received, Safety Stock, MOQ
            
            **銷量欄位:**
            - Last Month Sold Qty, MTD Sold Qty
            
            **⚠️ 特殊要求:**
            - **ALL 欄位**:請在要強制轉出的商品行填寫任意非空值(例如:*、Y、ALL 等)
            - E1/E1b/E2 模式只會處理標記的商品
            - E1/E1b 模式僅同OM配對,E2 模式可跨OM配對
            - E1b 接收優先級參照B2:Type=T(遊客區)優先,其次Type=M(混合型)
            """)
    elif mode_code in ["ND1", "ND2"]:
        with st.expander("📋 必需欄位說明", expanded=False):
            st.markdown("""
            **基本欄位:**
            - Article, Article Description, OM, RP Type, Site

            **庫存欄位:**
            - SaSa Net Stock, Pending Received, Safety Stock, MOQ

            **銷量欄位:**
            - Last Month Sold Qty, MTD Sold Qty

            **⚠️ 特殊要求:**
            - ND1 模式僅同OM配對；ND2 模式允許跨OM配對
            - ND 店舖在 ND1/ND2 模式可作為接收方，但過去2個月銷量=0 的 ND 店舖不可接收
            - 同一SKU下可設定單一出貨店舖最多配對接收店舖數：優先1間 / 最多2間 / 不限
            """)
    elif mode_code in ["精簡SKU(限同OM)", "精簡SKU(跨OM)"]:
        with st.expander("📋 必需欄位說明", expanded=False):
            st.markdown("""
            **基本欄位:**
            - Article, Article Description, OM, RP Type, Site

            **庫存欄位:**
            - SaSa Net Stock, Pending Received, Safety Stock, MOQ

            **銷量欄位:**
            - Last Month Sold Qty, MTD Sold Qty, **Last 2 Month Sold Qty**

            **⚠️ 特殊說明:**
            - RF店舖存貨上限 = Max(Safety Stock × 2, Last 2 Month Sold Qty × 2)
            - ND店舖全數可轉出，RF店舖超出上限部分可轉出
            - 轉給RF店舖最少2件起（參考C1模式），退回D001無數量限制
            - 剩餘無法配對的數量一律建議退回D001
            - 精簡SKU(限同OM)僅同OM配對；精簡SKU(跨OM)允許跨OM配對（Windy限制、HD限制）
            """)
    else:
        with st.expander("📋 必需欄位說明", expanded=False):
            st.markdown("""
            **基本欄位:**
            - Article, Article Description, OM, RP Type, Site, **Target**(目標接收數量)
            
            **庫存欄位:**
            - SaSa Net Stock, Pending Received, Safety Stock, MOQ
            
            **銷量欄位:**
            - Last Month Sold Qty, MTD Sold Qty
            
            **⚠️ 特殊要求:**
            - **Target 欄位**:填數字代表該店舖的優先接收目標數量
            - F模式:未填Target的店舖會按C模式補0需求計算
            - F2模式:未填Target的店舖不會接收
            - F2模式HD轉出選項:預設HD不能轉到HA/HB/HC；可切換為「HD可轉出（最後優先）」，此時HD來源排在最低優先級
            """)


def render_data_preview(df: pd.DataFrame, processing_stats: dict):
    st.markdown("### 📊 資料查覽")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("總行數", processing_stats['processed_stats']['total_rows'])
    with col2:
        st.metric("商品數", df['Article'].nunique())
    with col3:
        st.metric("店鋪數", df['Site'].nunique())

    st.markdown("**資料樣本（前 10 行)**")
    st.dataframe(df.head(10), use_container_width=True)


def render_kpi_cards(statistics: dict):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("調貨建議", f"{statistics.get('total_recommendations', 0):,}")
    col2.metric("調貨件數", f"{statistics.get('total_transfer_qty', 0):,}")
    col3.metric("產品數量", f"{statistics.get('unique_articles', 0):,}")
    col4.metric("OM數量", f"{statistics.get('unique_oms', 0):,}")
    st.markdown("")


def _build_display_data(recommendations: list, df: pd.DataFrame, mode: str = None) -> list:
    _stock_lookup = (
        df[['Article', 'Site', 'SaSa Net Stock', 'Safety Stock', 'MOQ']]
        .set_index(['Article', 'Site'])
        .rename(columns={'SaSa Net Stock': 'stock', 'Safety Stock': 'safety', 'MOQ': 'moq'})
        .to_dict('index')
    )

    display_data = []
    cumulative_transfers = {}

    for rec in recommendations:
        src_key = (rec['Article'], rec['Transfer Site'])
        src_info = _stock_lookup.get(src_key, {})
        source_stock = src_info.get('stock', 0)
        source_safety = src_info.get('safety', 0)
        source_moq = src_info.get('moq', 0)

        dst_key = (rec['Article'], rec['Receive Site'])
        dst_info = _stock_lookup.get(dst_key, {})
        dest_stock = dst_info.get('stock', 0)
        dest_safety = dst_info.get('safety', 0)
        dest_moq = dst_info.get('moq', 0)

        source_key = f"{rec['Article']}_{rec['Transfer Site']}"
        if source_key not in cumulative_transfers:
            cumulative_transfers[source_key] = 0
        cumulative_transfers[source_key] += rec['Transfer Qty']
        source_after_transfer_stock = source_stock - cumulative_transfers[source_key]

        row_data = {
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
            'Receive Total After': dest_stock + rec['Transfer Qty'],
            'Receive Safety Stock': dest_safety,
            'Receive MOQ': dest_moq,
            'Source Type': rec.get('Source Type', ''),
            'Destination Type': rec.get('Destination Type', ''),
        }
        if mode == "精簡SKU(退D001)":
            row_data['D001 Receive Qty'] = rec['Transfer Qty']
        display_data.append(row_data)

    return display_data


def render_results_table(recommendations: list, df: pd.DataFrame, current_run_key: str, mode: str = None):
    st.markdown("### 📋 調貨建議清單")

    cache_key = f"_display_df_{current_run_key}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = pd.DataFrame(_build_display_data(recommendations, df, mode))
    rec_df = st.session_state[cache_key]

    total_recs = len(rec_df)
    use_preview_limit = (
        IS_ZEABUR_RUNTIME
        and ZEABUR_RESULT_PREVIEW_LIMIT > 0
        and total_recs > ZEABUR_RESULT_PREVIEW_LIMIT
    )

    if use_preview_limit:
        st.info(
            f"Zeabur 效能模式：目前先顯示前 {ZEABUR_RESULT_PREVIEW_LIMIT:,} 行，"
            "避免大型結果表拖慢頁面。完整結果仍可下載，亦可按需展開。"
        )
        show_full_result_table = st.checkbox(
            "載入完整調貨建議表",
            value=False,
            key=f"show_full_result_table_{current_run_key}",
            help="僅在需要時渲染全部結果列，以減少 Zeabur 容器上的前端與傳輸負擔。"
        )
        table_df = rec_df if show_full_result_table else rec_df.head(ZEABUR_RESULT_PREVIEW_LIMIT)
        st.dataframe(table_df, use_container_width=True)
    else:
        st.dataframe(rec_df, use_container_width=True)


def _build_priority_groups(recommendations: list) -> dict:
    groups = {'🔴高優先': [], '🟡中優先': [], '🟢低優先': []}
    for rec in recommendations:
        p = rec.get('Priority', '🟢低優先')
        groups[p].append(rec)
    return groups


def render_results_by_priority(recommendations: list, df: pd.DataFrame, current_run_key: str, mode: str = None):
    st.markdown("### 📋 調貨建議清單（按優先級分組）")

    groups = _build_priority_groups(recommendations)
    total_recs = len(recommendations)
    total_qty = sum(r['Transfer Qty'] for r in recommendations)

    col1, col2, col3 = st.columns(3)
    col1.metric("🔴 高優先", f"{len(groups['🔴高優先']):,}")
    col2.metric("🟡 中優先", f"{len(groups['🟡中優先']):,}")
    col3.metric("🟢 低優先", f"{len(groups['🟢低優先']):,}")

    for priority_label, color, default_expanded in [
        ('🔴高優先', '#FF4444', True),
        ('🟡中優先', '#FFAA00', False),
        ('🟢低優先', '#00CC88', False),
    ]:
        items = groups[priority_label]
        if not items:
            continue
        group_qty = sum(r['Transfer Qty'] for r in items)
        with st.expander(
            f"{priority_label} — {len(items):,} 條建議，共 {group_qty:,} 件",
            expanded=default_expanded,
        ):
            cache_key = f"_display_priority_df_{current_run_key}_{priority_label}"
            if cache_key not in st.session_state:
                st.session_state[cache_key] = pd.DataFrame(_build_display_data(items, df, mode))
            st.dataframe(st.session_state[cache_key], use_container_width=True)


def render_ai_executive_summary_button(recommendations: list, statistics: dict, mode_name: str):
    from services.ai_client import is_ai_enabled, chat_completion
    from config import AI_DEFAULT_MODEL
    import json

    if not is_ai_enabled():
        return

    st.markdown('<div class="ai-summary-btn">', unsafe_allow_html=True)
    if st.button("🤖 生成執行摘要", use_container_width=True,
                 help="AI 分析結果摘要（可選功能，非必要）"):
        with st.spinner("AI 生成中..."):
            summary_data = {
                'total_recs': statistics.get('total_recommendations', 0),
                'total_qty': statistics.get('total_transfer_qty', 0),
                'unique_articles': statistics.get('unique_articles', 0),
                'unique_oms': statistics.get('unique_oms', 0),
                'mode': mode_name,
                'high_priority_count': sum(1 for r in recommendations if r.get('Priority') == '🔴高優先'),
                'high_priority_qty': sum(r['Transfer Qty'] for r in recommendations if r.get('Priority') == '🔴高優先'),
                'medium_priority_count': sum(1 for r in recommendations if r.get('Priority') == '🟡中優先'),
                'medium_priority_qty': sum(r['Transfer Qty'] for r in recommendations if r.get('Priority') == '🟡中優先'),
                'source_type_distribution': statistics.get('source_type_stats', {}),
                'dest_type_distribution': statistics.get('dest_type_stats', {}),
            }
            messages = [
                {
                    "role": "system",
                    "content": "你是一個庫存調貨系統的分析助手。請根據以下聚合數據，生成一段約150字以內的繁體中文執行摘要，重點說明：①整體規模 ②優先級分佈 ③需要立即關注的事項。純文字輸出，無需markdown格式。"
                },
                {
                    "role": "user",
                    "content": json.dumps(summary_data, ensure_ascii=False)
                }
            ]
            result = chat_completion(messages, model=AI_DEFAULT_MODEL, temperature=0.1, max_tokens=512)
            if result:
                st.session_state['ai_executive_summary'] = result

    summary = st.session_state.get('ai_executive_summary')
    if summary:
        with st.expander("📊 AI 執行摘要", expanded=False):
            st.markdown(summary)
    st.markdown('</div>', unsafe_allow_html=True)


def render_statistics(statistics: dict):
    with st.expander("📊 詳細統計", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**按產品統計**")
            article_stats = statistics.get('article_stats', {})
            if article_stats:
                article_df = pd.DataFrame([
                    {
                        'Brand': stats.get('brand', ''),
                        'Article': article,
                        'Product Desc': stats.get('product_desc', ''),
                        'Total Qty': stats['total_qty'],
                        'Count': stats['count'],
                        'OM Count': stats['om_count'],
                    }
                    for article, stats in article_stats.items()
                ])
                st.dataframe(article_df, use_container_width=True)

            st.markdown("**轉出類型分佈**")
            source_type_stats = statistics.get('source_type_stats', {})
            if source_type_stats:
                source_df = pd.DataFrame([
                    {
                        'Source Type': source_type,
                        'Count': stats['count'],
                        'Qty': stats['qty'],
                    }
                    for source_type, stats in source_type_stats.items()
                ])
                st.dataframe(source_df, use_container_width=True)

        with col2:
            st.markdown("**按 OM 統計**")
            om_stats = statistics.get('om_stats', {})
            if om_stats:
                om_df = pd.DataFrame([
                    {
                        'OM': om,
                        'Transfer Qty': stats.get('transfer_qty', stats.get('total_qty', 0)),
                        'Receive Qty': stats.get('receive_qty', 0),
                        'Count': stats['count'],
                        'Article Count': stats['article_count'],
                    }
                    for om, stats in om_stats.items()
                ])
                st.dataframe(om_df, use_container_width=True)

            st.markdown("**接收類型分佈**")
            dest_type_stats = statistics.get('dest_type_stats', {})
            if dest_type_stats:
                dest_df = pd.DataFrame([
                    {
                        'Destination Type': dest_type,
                        'Count': stats['count'],
                        'Qty': stats['qty'],
                    }
                    for dest_type, stats in dest_type_stats.items()
                ])
                st.dataframe(dest_df, use_container_width=True)


def render_download_button(excel_data: bytes, excel_filename: str, current_run_key: str):
    _mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    st.download_button(
        "📥 下載 Excel 報表",
        data=excel_data,
        file_name=excel_filename,
        mime=_mime,
        type="primary",
        use_container_width=True,
        on_click="ignore",
        key=f"download_excel_{current_run_key}",
    )
