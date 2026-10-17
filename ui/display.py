"""
結果展示 UI — 欄位說明、資料查覽、KPI、結果表格、統計、下載按鈕
"""

import streamlit as st
import pandas as pd
from typing import Optional

from config import IS_CLOUD_RUNTIME, CLOUD_RESULT_PREVIEW_LIMIT
from models.mode_registry import get_mode_families


def _is_b_special_mode(mode: Optional[str]) -> bool:
    """檢查是否為 B 特別系列模式（B2/B2a/B2L/B2La/B3/B3a/B3L/B3La）"""
    if not mode:
        return False
    return mode in get_mode_families().get('b_special', set())


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


# 結果表中的整數欄位（兩種 schema 聯集），顯示時套用 column_config 數字格式
_INT_DISPLAY_COLUMNS = frozenset({
    'Transfer Qty', 'D001 Receive Qty',
    'Transfer Site Last Month Sold Qty', 'Transfer Site MTD Sold Qty',
    'Transfer Original Stock', 'Transfer Safety Stock', 'Transfer After Transfer Stock',
    'Receive Site Last Month Sold Qty', 'Receive Site MTD Sold Qty',
    'Receive Original Stock', 'Receive Site Safety Stock',
    'Source Original Stock', 'Source After Transfer Stock',
    'Source Safety Stock', 'Source MOQ',
    'Receive Total After', 'Receive Safety Stock', 'Receive MOQ',
})


def _int_column_config(df: pd.DataFrame) -> dict:
    """為 df 中存在的整數欄位產生 NumberColumn 設定（千分位整數格式）。"""
    return {
        col: st.column_config.NumberColumn(format="%d")
        for col in _INT_DISPLAY_COLUMNS & set(df.columns)
    }


def render_data_preview(df: pd.DataFrame, processing_stats: dict):
    st.markdown('<div class="section-title"><span class="section-title__badge">STEP 1</span>📊 資料查覽</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總行數", processing_stats['processed_stats']['total_rows'])
    with col2:
        st.metric("商品數", df['Article'].nunique())
    with col3:
        st.metric("店鋪數", df['Site'].nunique())
    with col4:
        if 'RP Type' in df.columns:
            _rp = df['RP Type'].astype(str).str.strip().str.upper().value_counts()
            _nd = int(_rp.get('ND', 0))
            _rf = int(_rp.get('RF', 0))
            st.metric("ND / RF 行數", f"{_nd:,} / {_rf:,}")
        else:
            st.metric("欄位數", len(df.columns))

    st.markdown("**資料樣本（前 10 行)**")
    preview = df.head(10).copy()
    for col in preview.columns:
        if preview[col].dtype == object:
            preview[col] = preview[col].astype(str)
    st.dataframe(preview, use_container_width=True, hide_index=True, height=320)


def render_kpi_cards(statistics: dict):
    cols = st.columns(4)
    metrics = [
        ("調貨建議", f"{statistics.get('total_recommendations', 0):,}", "📦"),
        ("調貨件數", f"{statistics.get('total_transfer_qty', 0):,}", "🔢"),
        ("產品數量", f"{statistics.get('unique_articles', 0):,}", "🏷️"),
        ("OM 數量", f"{statistics.get('unique_oms', 0):,}", "🗺️"),
    ]
    for col, (label, value, icon) in zip(cols, metrics):
        with col:
            st.metric(label=f"{icon} {label}", value=value)
    st.markdown("")


def render_charts(statistics: dict):
    """圖表概覽 — 轉出/接收類型、OM 分佈與 Top 商品長條圖（跟隨深色主題）。"""
    article_stats = statistics.get('article_stats', {})
    om_stats = statistics.get('om_stats', {})
    source_type_stats = statistics.get('source_type_stats', {})
    dest_type_stats = statistics.get('dest_type_stats', {})
    if not (article_stats or om_stats or source_type_stats or dest_type_stats):
        return

    with st.expander("📈 圖表概覽", expanded=False):
        if source_type_stats or dest_type_stats:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**轉出類型分佈（件數）**")
                if source_type_stats:
                    source_df = pd.DataFrame([
                        {'Source Type': t, 'Qty': s['qty']}
                        for t, s in source_type_stats.items()
                    ])
                    st.bar_chart(source_df, x='Source Type', y='Qty', use_container_width=True, height=260)
            with c2:
                st.markdown("**接收類型分佈（件數）**")
                if dest_type_stats:
                    dest_df = pd.DataFrame([
                        {'Destination Type': t, 'Qty': s['qty']}
                        for t, s in dest_type_stats.items()
                    ])
                    st.bar_chart(dest_df, x='Destination Type', y='Qty', use_container_width=True, height=260)

        if om_stats:
            st.markdown("**按 OM 轉出 vs 接收量**")
            om_df = pd.DataFrame([
                {
                    'OM': om,
                    'Transfer Qty': stats.get('transfer_qty', stats.get('total_qty', 0)),
                    'Receive Qty': stats.get('receive_qty', 0),
                }
                for om, stats in om_stats.items()
            ])
            st.bar_chart(om_df, x='OM', y=['Transfer Qty', 'Receive Qty'], use_container_width=True, height=280)

        if article_stats:
            st.markdown("**Top 10 商品轉出量**")
            top_df = pd.DataFrame([
                {'Article': article, 'Total Qty': stats['total_qty']}
                for article, stats in article_stats.items()
            ]).nlargest(10, 'Total Qty').sort_values('Total Qty')
            st.bar_chart(top_df, x='Total Qty', y='Article', horizontal=True, use_container_width=True, height=320)


def _build_stock_lookup(df: pd.DataFrame) -> dict:
    """建立 (Article, Site) → 庫存字典，供顯示層查詢。

    抽出為獨立函式以便多個優先級群組共用同一份查詢表，避免重複建構。
    Site 欄位正規化為大寫以與 recommendation 的 site key 一致。
    """
    temp = df[['Article', 'Site', 'SaSa Net Stock', 'Safety Stock', 'MOQ']].copy()
    temp['Site'] = temp['Site'].astype(str).str.strip().str.upper()
    return (
        temp.set_index(['Article', 'Site'])
        .rename(columns={'SaSa Net Stock': 'stock', 'Safety Stock': 'safety', 'MOQ': 'moq'})
        .to_dict('index')
    )


def _build_display_data(recommendations: list, df: pd.DataFrame, mode: str = None,
                        stock_lookup: dict = None) -> list:
    _stock_lookup = stock_lookup if stock_lookup is not None else _build_stock_lookup(df)

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

        if _is_b_special_mode(mode):
            row_data = {
                'Brand': rec.get('Product Hierarchy') or rec.get('Brand') or '',
                'Article': rec['Article'],
                'Product Desc': rec['Product Desc'],
                'Transfer OM': rec['Transfer OM'],
                'Transfer Site': rec['Transfer Site'],
                'Transfer Site Type': rec.get('Transfer Site Type', ''),
                'Transfer Site Last Month Sold Qty': rec.get('Transfer Site Last Month Sold Qty', 0),
                'Transfer Site MTD Sold Qty': rec.get('Transfer Site MTD Sold Qty', 0),
                'Transfer Original Stock': source_stock,
                'Transfer Safety Stock': source_safety,
                'Transfer After Transfer Stock': source_after_transfer_stock,
                'Receive OM': rec['Receive OM'],
                'Receive Site': rec['Receive Site'],
                'Receive Site Type': rec.get('Receive Site Type', ''),
                'Receive Site Last Month Sold Qty': rec.get('Receive Site Last Month Sold Qty', 0),
                'Receive Site MTD Sold Qty': rec.get('Receive Site MTD Sold Qty', 0),
                'Receive Original Stock': dest_stock,
                'Receive Site Safety Stock': dest_safety,
                'Transfer Qty': rec['Transfer Qty'],
                'Remark': f"{rec.get('Source Type', '')} → {rec.get('Destination Type', '')}",
                'Notes': rec.get('Notes', ''),
            }
        else:
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
        IS_CLOUD_RUNTIME
        and CLOUD_RESULT_PREVIEW_LIMIT > 0
        and total_recs > CLOUD_RESULT_PREVIEW_LIMIT
    )

    if use_preview_limit:
        st.info(
            f"雲端效能模式：目前先顯示前 {CLOUD_RESULT_PREVIEW_LIMIT:,} 行，"
            "避免大型結果表拖慢頁面。完整結果仍可下載，亦可按需展開。"
        )
        show_full_result_table = st.checkbox(
            "載入完整調貨建議表",
            value=False,
            key=f"show_full_result_table_{current_run_key}",
            help="僅在需要時渲染全部結果列，以減少雲端容器（Streamlit Community Cloud）上的前端與傳輸負擔。"
        )
        table_df = rec_df if show_full_result_table else rec_df.head(CLOUD_RESULT_PREVIEW_LIMIT)
        st.dataframe(table_df, use_container_width=True, hide_index=True, height=480, column_config=_int_column_config(table_df))
    else:
        st.dataframe(rec_df, use_container_width=True, hide_index=True, height=480, column_config=_int_column_config(rec_df))


def _build_priority_groups(recommendations: list) -> dict:
    groups = {'🔴高優先': [], '🟡中優先': [], '🟢低優先': []}
    for rec in recommendations:
        p = rec.get('Priority', '🟢低優先')
        groups[p].append(rec)
    return groups


def render_results_by_priority(recommendations: list, df: pd.DataFrame, current_run_key: str, mode: str = None):
    st.markdown('<div class="section-title"><span class="section-title__badge">STEP 3</span>📋 調貨建議清單（按優先級分組）</div>', unsafe_allow_html=True)

    keyword = st.text_input(
        "🔍 篩選調貨建議（Article / 店舖編號關鍵字）",
        value="",
        key=f"rec_filter_{current_run_key}",
        help="輸入 Article 或店舖編號的一部分，即時篩選三個優先級分組的顯示結果（不影響統計與 Excel 匯出）。",
    ).strip().upper()

    if keyword:
        _filtered = [
            r for r in recommendations
            if keyword in str(r.get('Article', '')).upper()
            or keyword in str(r.get('Transfer Site', '')).upper()
            or keyword in str(r.get('Receive Site', '')).upper()
        ]
        st.caption(f"篩選「{keyword}」：{len(_filtered):,} / {len(recommendations):,} 條建議")
    else:
        _filtered = recommendations

    groups = _build_priority_groups(_filtered)
    total_recs = len(recommendations)
    total_qty = sum(r['Transfer Qty'] for r in recommendations)

    _priority_stats = [
        ('🔴 高優先', len(groups['🔴高優先']), '#DC2626'),
        ('🟡 中優先', len(groups['🟡中優先']), '#D97706'),
        ('🟢 低優先', len(groups['🟢低優先']), '#059669'),
    ]
    _chips = "".join(
        f'<div style="flex:1;text-align:center;padding:calc(var(--space-3) + 2px) var(--space-3);'
        f'border:1px solid {color}55;border-left:3px solid {color};'
        f'border-radius:var(--radius-md);background:rgba(255,255,255,0.6);">'
        f'<div style="font-size:0.85rem;font-weight:600;color:var(--text-secondary);'
        f'letter-spacing:0.05em;">{label}</div>'
        f'<div style="font-size:1.5rem;font-weight:800;color:{color};line-height:1.3;'
        f"font-family:'JetBrains Mono',monospace;\">{count:,}</div>"
        f'</div>'
        for label, count, color in _priority_stats
    )
    st.markdown(
        f'<div style="display:flex;gap:var(--space-3);margin-bottom:var(--space-2);">{_chips}</div>',
        unsafe_allow_html=True,
    )

    # 只建立一次 stock lookup，三個優先級群組共用
    stock_lookup = _build_stock_lookup(df)

    for priority_label, default_expanded in [
        ('🔴高優先', True),
        ('🟡中優先', False),
        ('🟢低優先', False),
    ]:
        items = groups[priority_label]
        if not items:
            continue
        group_qty = sum(r['Transfer Qty'] for r in items)
        with st.expander(
            f"{priority_label} — {len(items):,} 條建議，共 {group_qty:,} 件",
            expanded=default_expanded,
        ):
            # 快取 key 包含關鍵字，避免篩選後命中未篩選的舊快取
            cache_key = f"_display_priority_df_{current_run_key}_{priority_label}_{keyword}"
            if cache_key not in st.session_state:
                st.session_state[cache_key] = pd.DataFrame(
                    _build_display_data(items, df, mode, stock_lookup=stock_lookup)
                )
            group_df = st.session_state[cache_key]
            st.dataframe(
                group_df,
                use_container_width=True,
                hide_index=True,
                height=min(480, 120 + len(group_df) * 28),
                column_config=_int_column_config(group_df),
            )


def render_statistics(statistics: dict):
    _stats_int_config = {
        col: st.column_config.NumberColumn(format="%d")
        for col in ('Total Qty', 'Count', 'OM Count', 'Qty', 'Transfer Qty', 'Receive Qty', 'Article Count')
    }
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
                st.dataframe(article_df, use_container_width=True, hide_index=True, height=320, column_config=_stats_int_config)

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
                st.dataframe(source_df, use_container_width=True, hide_index=True, column_config=_stats_int_config)

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
                st.dataframe(om_df, use_container_width=True, hide_index=True, column_config=_stats_int_config)

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
                st.dataframe(dest_df, use_container_width=True, hide_index=True, column_config=_stats_int_config)


def render_gap_report(gap_report: dict, current_run_key: str = ""):
    """Render the post-transfer gap report in an expandable section."""
    if not gap_report or not gap_report.get('details'):
        return

    summary = gap_report.get('summary', {})
    details = gap_report.get('details', [])
    # 篩選狀態按 run 隔離，換 run 自動重置（與結果表快取行為一致）
    key_suffix = current_run_key or "default"

    with st.expander("📊 調貨缺口分析", expanded=False):
        # KPI row（計數皆為「店×SKU」組數，非獨立店數）
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("未滿足店×SKU", summary.get('total_dest_gaps', 0))
        k2.metric("缺口件數", summary.get('total_gap_qty', 0))
        k3.metric("剩餘店×SKU", summary.get('total_source_remaining', 0))
        k4.metric("剩餘件數", summary.get('total_remaining_qty', 0))

        # 分母為 0（如 E 模式無適用目的地）時顯示「不適用」，避免 0.0% 誤讀
        dest_count = summary.get('total_dest_count', 0)
        dest_rate = f"{summary.get('fulfillment_rate', 0)}%" if dest_count > 0 else "不適用"
        qty_rate = f"{summary.get('qty_fulfillment_rate', 0)}%" if dest_count > 0 else "不適用"

        k5, k6, k7, k8 = st.columns(4)
        k5.metric("目的地總數", dest_count)
        k6.metric("目的地滿足率(店×SKU)", dest_rate)
        k7.metric("件數滿足率", qty_rate)
        k8.metric("來源轉出率(可轉量)", f"{summary.get('source_transfer_rate', 0)}%")

        over_total = summary.get('total_over_transferred_qty', 0)
        if over_total and over_total > 0:
            st.warning(
                f"⚠️ 偵測到超量轉出：來源店累計轉出超出可轉量合計 {over_total} 件"
                f"（請檢查後處理與安全庫存保護）"
            )

        st.caption(
            "「剩餘」= 可轉量（政策上限，如 A 20%／B 50%／C 30%）− 實際轉出，非店內實體庫存；"
            "「轉後店內庫存」= 原始庫存 − 實際轉出。"
        )

        st.markdown("")

        # Build DataFrame for display（空值用 None 維持數值型別，比率欄存 0-100 float 供 ProgressColumn 顯示）
        # E 模式（不適用）的數值欄為 None → 顯示為空，不會誤示 0／100%
        rows = []
        for d in details:
            is_dest = d.get('role') == '目的地'
            is_source = d.get('role') == '來源'
            over = d.get('over_transferred_qty', 0) or 0
            gap = d.get('gap_or_remaining')
            gap_pct = d.get('gap_pct')
            rem_pct = d.get('remaining_pct')
            status_text = d.get('status', '')
            if is_source and over > 0:
                status_text = f"{status_text}；超額警告"
            rows.append({
                'Article': d.get('article', ''),
                'Site': d.get('site', ''),
                'OM': d.get('om', ''),
                '角色': d.get('role', ''),
                '模式': d.get('mode', ''),
                '原始需求/可轉量': d.get('original_need_or_surplus', 0),
                '實際收/轉量': d.get('actual_qty', 0),
                '缺口': gap if is_dest else None,
                '缺口%': gap_pct if is_dest else None,
                '未轉出可轉量': gap if is_source else None,
                '轉後店內庫存': d.get('after_transfer_stock') if is_source else None,
                '超過可轉量': over if over > 0 else None,
                '達成率': round(max(100 - gap_pct, 0), 1) if (is_dest and gap_pct is not None) else None,
                '轉出率': round(max(100 - rem_pct, 0), 1) if (is_source and rem_pct is not None) else None,
                '類型': d.get('type_label', ''),
                '狀態': status_text,
            })

        gap_df = pd.DataFrame(rows)

        # 三個篩選器並排（原本垂直堆疊佔用大量高度）
        f1, f2, f3 = st.columns(3)
        # Mode filter
        by_mode = gap_report.get('by_mode', {})
        mode_options = ['全部'] + sorted(by_mode.keys())
        with f1:
            selected_mode = st.selectbox(
                "篩選模式",
                options=mode_options,
                key=f"gap_report_mode_filter_{key_suffix}",
            )

        if selected_mode != '全部':
            filtered_df = gap_df[gap_df['模式'] == selected_mode]
        else:
            filtered_df = gap_df

        # Role filter
        role_options = ['全部', '目的地', '來源']
        with f2:
            selected_role = st.selectbox(
                "篩選角色",
                options=role_options,
                key=f"gap_report_role_filter_{key_suffix}",
            )
        if selected_role != '全部':
            filtered_df = filtered_df[filtered_df['角色'] == selected_role]

        # Status filter
        status_options = ['全部'] + sorted(gap_df['狀態'].unique())
        with f3:
            selected_status = st.selectbox(
                "篩選狀態",
                options=status_options,
                key=f"gap_report_status_filter_{key_suffix}",
            )
        if selected_status != '全部':
            filtered_df = filtered_df[filtered_df['狀態'] == selected_status]

        st.caption(f"顯示 {len(filtered_df):,} / {len(gap_df):,} 列")
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            height=420,
            column_config={
                '原始需求/可轉量': st.column_config.NumberColumn(format="%d"),
                '實際收/轉量': st.column_config.NumberColumn(format="%d"),
                '缺口': st.column_config.NumberColumn(format="%d"),
                '缺口%': st.column_config.NumberColumn(format="%.1f%%"),
                '未轉出可轉量': st.column_config.NumberColumn(format="%d"),
                '轉後店內庫存': st.column_config.NumberColumn(format="%d"),
                '超過可轉量': st.column_config.NumberColumn(format="%d"),
                '達成率': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                '轉出率': st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
            },
        )


def render_download_button(excel_data: bytes, excel_filename: str, current_run_key: str):
    _mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    st.download_button(
        "📥 下載 Excel 報表",
        data=excel_data,
        file_name=excel_filename,
        mime=_mime,
        type="primary",
        use_container_width=True,
        key=f"download_excel_{current_run_key}",
    )
