"""
教學分頁 — 30 種調貨模式圖例教學（數據驅動版本）
"""

import json
import os
import streamlit as st

_TUTORIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tutorials")

_GROUP_DEFS = [
    ("basic", "基礎調貨模式（A / A1 / B）", "1"),
    ("b2", "B特別模式（B2 / B2a / B2L / B2La）", "2"),
    ("b3", "B跨OM特別模式（B3 / B3a / B3L / B3La）", "3"),
    ("c", "重點補0系列（C / C1 / C2）", "4"),
    ("d", "清貨模式（D / D2）", "5"),
    ("e", "強制轉出系列（E1 / E1b / E2）", "6"),
    ("f", "目標優化系列（F / F2 / F3）", "7"),
    ("nd_sku", "ND/SKU專項（ND1 / ND2 / ND3 / ND4 / 精簡SKU）", "8"),
]


def _flow_node(text, color="blue", width="auto"):
    color_class = f"flow-node--{color}"
    w = f"width:{width};" if width != "auto" else ""
    return (
        f'<div class="flow-node {color_class}" style="{w}">'
        f'{text}</div>'
    )


def _flow_arrow(label=""):
    lbl = f'<span style="font-size:11px;color:var(--text-muted);">{label}</span><br>' if label else ""
    return f'<div class="flow-arrow">{lbl}&#8595;</div>'


def _flow_row(items, gap="12px"):
    inner = "".join(
        f'<div style="flex:1;min-width:0;">{item}</div>' for item in items
    )
    return f'<div style="display:flex;gap:{gap};align-items:flex-start;">{inner}</div>'


def _scenario_table(headers, rows):
    ths = "".join(f"<th>{h}</th>" for h in headers)
    trs = ""
    for row in rows:
        tds = "".join(f"<td>{c}</td>" for c in row)
        trs += f"<tr>{tds}</tr>"
    return (
        '<table class="scenario-table"><thead><tr>'
        + ths
        + "</tr></thead><tbody>"
        + trs
        + "</tbody></table>"
    )


def _risk_badge(level):
    return (
        f'<span class="risk-badge risk-badge--'
        f'{"low" if level == "低" else "medium" if level == "中" else "high"}">'
        f'風險：{level}</span>'
    )


def _build_match_rows(match_order):
    if not match_order:
        return ""
    match_rows = ""
    for i, (src, dst) in enumerate(match_order, 1):
        match_rows += (
            f'<div class="match-row">'
            f'<span class="match-num">{i}</span>'
            f'<span class="match-src">{src}</span>'
            f'<span class="match-arrow">&#10132;</span>'
            f'<span class="match-dst">{dst}</span>'
            f'</div>'
        )
    return f'<div class="match-container">{match_rows}</div>'


def _render_flow_element(elem):
    t = elem.get("type")
    if t == "node":
        return _flow_node(elem["text"], elem.get("color", "blue"), elem.get("width", "auto"))
    if t == "arrow":
        return _flow_arrow(elem.get("label", ""))
    if t == "row":
        items_html = [_render_flow_element(item) for item in elem.get("items", [])]
        return _flow_row(items_html, elem.get("gap", "12px"))
    if t == "html":
        return elem.get("text", "")
    return ""


def _render_flow(flow_data):
    if isinstance(flow_data, list):
        return "".join(_render_flow_element(e) for e in flow_data)
    return str(flow_data)


def _render_table_data(table_data):
    if table_data is None:
        return None
    if isinstance(table_data, dict) and "headers" in table_data:
        return _scenario_table(table_data["headers"], table_data["rows"])
    return str(table_data) if table_data else None


def _build_mode_from_data(mode_data):
    source_html = _render_flow(mode_data.get("source_flow", []))
    dest_html = _render_flow(mode_data.get("dest_flow", []))
    match_html = _build_match_rows(
        [tuple(m) for m in mode_data["match_order"]] if mode_data.get("match_order") else None
    )
    scenario_table_html = _render_table_data(mode_data.get("scenario_table"))
    diff_table_html = _render_table_data(mode_data.get("diff_table"))

    parts = []
    parts.append('<div class="mode-section">')
    parts.append(f'<h4 class="mode-title">模式 {mode_data["code"]}：{mode_data["name"]} {_risk_badge(mode_data["risk"])}</h4>')
    parts.append(f'<p class="mode-scenario"><b>適用場景：</b>{mode_data["scenario"]}</p>')

    parts.append('<div class="flow-section">')
    parts.append('<p class="flow-label">&#128260; 轉出篩選流程</p>')
    parts.append(f'<div class="flow-container">{source_html}</div>')
    parts.append('</div>')

    parts.append('<div class="flow-section">')
    parts.append('<p class="flow-label">&#128230; 接收篩選流程</p>')
    parts.append(f'<div class="flow-container">{dest_html}</div>')
    parts.append('</div>')

    if match_html:
        parts.append('<div class="flow-section">')
        parts.append('<p class="flow-label">&#128279; 配對優先級</p>')
        parts.append(match_html)
        parts.append('</div>')

    if scenario_table_html:
        parts.append('<div class="flow-section">')
        parts.append('<p class="flow-label">&#128202; 情境範例</p>')
        parts.append(scenario_table_html)
        parts.append('</div>')

    extra_notes = mode_data.get("extra_notes")
    if extra_notes:
        parts.append(f'<p class="mode-notes">&#128161; {extra_notes}</p>')

    if diff_table_html:
        parts.append('<div class="flow-section">')
        parts.append('<p class="flow-label">&#128209; 模式對比</p>')
        parts.append(diff_table_html)
        parts.append('</div>')

    parts.append('</div>')
    parts.append('<hr class="mode-divider">')

    return "\n".join(parts)


def _load_group(group_key):
    path = os.path.join(_TUTORIALS_DIR, f"{group_key}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _render_group(group_title, icon, modes_data):
    with st.expander(f"{icon} {group_title}", expanded=False):
        for mode_data in modes_data:
            st.markdown(_build_mode_from_data(mode_data), unsafe_allow_html=True)


def _render_global_rules():
    st.markdown("### 全局規則（適用於所有模式）")

    flow = _flow_row([_flow_node("所有店舖資料", "blue")])
    flow += _flow_arrow()
    flow += _flow_row([_flow_node("ND 店舖？", "yellow")])
    flow += _flow_row([
        _flow_node("僅作轉出方<br>不可接收", "red"),
        _flow_node("RF 店舖", "green"),
    ])
    flow += _flow_arrow("RF 最高動銷店保護")
    flow += _flow_row([
        _flow_node("最高銷量店保護<br>不會被選為轉出方", "purple"),
        _flow_node("轉出候選", "green"),
    ])
    flow += _flow_arrow()
    flow += _flow_row([
        _flow_node("轉出店不可同時<br>作為同一SKU的接收店", "red"),
    ])
    flow += _flow_arrow("後處理")
    flow += _flow_row([
        _flow_node("消除單件調貨(Transfer Qty=1)<br>優先 Rebalance &#10132; 其次 Merge", "orange"),
    ])

    st.markdown(f'<div class="flow-container">{flow}</div>', unsafe_allow_html=True)

    st.markdown("""
**全局規則說明：**
1. **ND 店鋪限制**：ND 類型店鋪在所有模式下只能作為轉出方，不能作為接收方（ND1/ND2/ND3/ND4 及 F/F2/F3 模式下有 Target 的 ND 店舖除外）
2. **最高動銷店保護**：RF 類型中有效銷量（Last Month + MTD）最高的店鋪不會被選為轉出方
3. **避免雙重角色**：同一 SKU 的轉出店鋪絕對不能同時作為接收店鋪
4. **單件後處理**：所有模式輸出前統一消除 Transfer Qty = 1 的記錄（Rebalance 取 1 件補上 &#10132; Merge 合併至高銷量目標店）
""")


def _render_decision_guide():
    st.markdown("### 模式選擇決策指南")
    st.markdown("根據以下問題，快速找到適合你的調貨模式：")

    branches = [
        ("清理無銷售ND庫存？", "D / D2", "orange"),
        ("有Target目標數量？", "F / F2", "purple"),
        ("需強制轉出指定商品？", "E1 / E1b / E2", "red"),
        ("重點補零庫存店舖？", "C / C1 / C2", "blue"),
        ("有Type分類需求？", "B2~B3La系列", "green"),
        ("ND店舖互轉？", "ND1 / ND2 / ND3 / ND4", "blue"),
        ("SKU精簡？", "精簡SKU(同OM/跨OM/退D001)", "green"),
        ("基礎調貨", "A(保守) / B(加強)", "gray"),
    ]

    flow = _flow_row([_flow_node("你的調貨需求是什麼？", "yellow", "280px")])
    flow += _flow_arrow()

    branch_nodes = []
    for question, answer, color in branches:
        branch_nodes.append(
            _flow_node(f'<b>{question}</b><br><span style="font-size:12px;">&#10132; {answer}</span>', color)
        )

    flow += _flow_row(branch_nodes, gap="8px")

    st.markdown(f'<div class="flow-container">{flow}</div>', unsafe_allow_html=True)

    st.markdown("""
**進一步區分：**

| 問題 | 選擇 |
|------|------|
| 清貨但不想動RF庫存 | D2（僅ND清貨） |
| Target外也想補零庫存 | F（目標+補0） |
| Target外不需補貨 | F2（僅Target） |
| 強制轉出僅同OM | E1 |
| 強制轉出+優先Type接收 | E1b |
| 強制轉出可跨OM | E2 |
| 補0但僅限庫存&#8804;1 | C1 |
| 補0可跨OM | C2 |
| Type=L需保留2件 | B2L/B2La/B3L/B3La |
| Type=T不可出貨 | B2a/B2La/B3a/B3La |
| 需跨OM配對 | B3/B3a/B3L/B3La |
| ND互轉僅同OM | ND1 |
| ND互轉可跨OM | ND2 |
| ND店舖補零庫存+保留3件 | ND3 |
| ND店舖補零庫存+保留3件+僅限有銷售記錄Shop | ND4 |
| SKU精簡僅同OM | 精簡SKU(限同OM) |
| SKU精簡可跨OM | 精簡SKU(跨OM) |
| SKU精簡全退D001不配對 | 精簡SKU(退D001) |
| 僅同OM基礎調貨 | A（保守）/ B（加強） |
""")


def render_tutorial_page():
    _render_global_rules()

    st.markdown("---")
    st.markdown("### 30 種模式教學")
    st.markdown("按業務場景分為 8 組，展開查看詳細教學。")

    for group_key, group_title, icon in _GROUP_DEFS:
        modes_data = _load_group(group_key)
        _render_group(group_title, icon, modes_data)

    st.markdown("---")
    _render_decision_guide()
