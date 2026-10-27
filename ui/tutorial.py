"""教學分頁 — 30 種調貨模式圖例教學（圖片為主＋文字為輔版本）
"""

import json
import os
from pathlib import Path

import streamlit as st

from models.mode_registry import get_mode_def_by_code
from ui import tutorial_diagrams as _td

_TUTORIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tutorials")
_ASSETS_DIR = Path(__file__).resolve().parent.parent / 'static' / 'tutorials'

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

# 組別用途（一句話）＋範圍標籤：總覽圖與篩選器共用
_GROUP_USE = {
    "basic": "日常缺貨補貨",
    "b2": "Type分類＋遊客區優先",
    "b3": "跨OM版B2",
    "c": "零庫存店補貨",
    "d": "ND死貨清倉",
    "e": "ALL標記強制清空",
    "f": "Target指定店補貨",
    "nd_sku": "ND互轉／撤SKU",
}
_GROUP_SCOPE = {
    "basic": "僅同OM",
    "b2": "僅同OM",
    "b3": "可跨OM",
    "c": "混合",
    "d": "僅同OM",
    "e": "混合",
    "f": "可跨OM",
    "nd_sku": "混合",
}

_SCENARIO_OPTIONS = ["全部場景"] + [_GROUP_USE[k] for k, _, _ in _GROUP_DEFS]
_RISK_OPTIONS = ["全部", "低", "中", "高"]
_OM_OPTIONS = ["全部", "僅同OM", "可跨OM"]


def _flow_node(text, color="blue", width="auto"):
    color_class = f"flow-node--{color}"
    w = f"width:{width};" if width != "auto" else ""
    return (
        f'<div class="flow-node {color_class}" style="{w}">'
        f'{text}</div>'
    )


def _flow_arrow(label=""):
    lbl = f'<span class="flow-arrow-label">{label}</span><br>' if label else ""
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


@st.cache_data(show_spinner=False, max_entries=2)
def _load_group(group_key):
    path = os.path.join(_TUTORIALS_DIR, f"{group_key}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 圖片版教學（新增） ────────────────────────────────────────────

def _show_svg(svg_str, center=5):
    """呈現 SVG 字串；預設收窄置中（約七成闊），一眼望清不壓迫。

    center：中欄比例（全份 7），總覽／決策樹等大圖可用 center=7 全闊。
    """
    if not svg_str:
        return
    if center >= 7:
        st.image(svg_str, width="stretch")
        return
    side = (7 - center) / 2
    _, mid, _ = st.columns([side, center, side])
    with mid:
        st.image(svg_str, width="stretch")


def _mode_scope_label(mode_code):
    try:
        d = get_mode_def_by_code(mode_code)
    except Exception:
        d = None
    if d is not None and getattr(d, "cross_om_matching", False):
        return "🔀 可跨OM"
    return "🔒 僅同OM"


def _all_modes_index():
    """[(group_key, group_title, mode_data)] 全量索引（供總覽圖＋篩選用）。"""
    indexed = []
    for group_key, group_title, _icon in _GROUP_DEFS:
        for mode_data in _load_group(group_key):
            indexed.append((group_key, group_title, mode_data))
    return indexed


def _render_mode_card(mode_data, group_key=None):
    """單一模式：圖片為主（邏輯圖＋情境圖），文字收合為輔。"""
    code = mode_data.get("code", "")
    name = mode_data.get("name", "")
    risk = mode_data.get("risk", "中")
    scenario = mode_data.get("scenario", "")
    with st.container(border=True):
        st.markdown(
            f'<h4 class="mode-title">模式 {code}：{name} {_risk_badge(risk)}</h4>',
            unsafe_allow_html=True,
        )
        meta = f"{_mode_scope_label(code)} · 風險{risk}"
        if group_key and group_key in _GROUP_USE:
            meta += f" · 👉 {_GROUP_USE[group_key]}"
        st.caption(meta)
        st.markdown(f"**適用場景：**{scenario}")
        _show_svg(_td.build_mode_logic_svg(mode_data))
        scen_svg = _td.build_mode_scenario_svg(mode_data)
        if scen_svg:
            _show_svg(scen_svg)
        with st.expander("📝 文字詳解（篩選流程 / 配對順序 / 範例表格 / 對比）", expanded=False):
            st.markdown(_build_mode_from_data(mode_data), unsafe_allow_html=True)
        extra_notes = mode_data.get("extra_notes")
        if extra_notes:
            st.caption(f"💡 {extra_notes}")


def _render_overview(indexed):
    st.markdown("### 🖼️ 一圖看懂 30 種模式")
    st.caption("先按場景選大類（8 張卡），再看每張模式圖（左轉出 → 中配對 → 右接收），最後才展開文字看數字。")
    groups = []
    for group_key, group_title, _icon in _GROUP_DEFS:
        modes = [(m["code"], m.get("risk", "中")) for gk, _, m in indexed if gk == group_key]
        groups.append((group_title, modes, _GROUP_USE[group_key], _GROUP_SCOPE[group_key]))
    _show_svg(_td.build_overview_map_svg(groups), center=7)


def _render_snapshot(indexed):
    st.markdown("### 👀 30 模式速覽（一眼望清）")
    st.caption("先睇表搵啱場景同風險（可點擊欄頭排序），再用下方篩選／分組睇圖片詳解。")
    import pandas as pd
    rows = []
    for group_key, _group_title, m in indexed:
        code = m.get("code", "")
        try:
            d = get_mode_def_by_code(code)
        except Exception:
            d = None
        cross = bool(d is not None and getattr(d, "cross_om_matching", False))
        rows.append({
            "模式": code,
            "名稱": m.get("name", ""),
            "用途": _td._plain(m.get("scenario", ""))[:30],
            "風險": m.get("risk", ""),
            "範圍": "可跨OM" if cross else "僅同OM",
            "場景": _GROUP_USE.get(group_key, ""),
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=420)


def _render_jump(indexed):
    codes = [m.get("code", "") for _, _, m in indexed]
    jump = st.selectbox("🚀 直接跳去某模式（睇圖片詳解）", ["— 請選擇 —"] + codes, key="tut_jump")
    if jump != "— 請選擇 —":
        for group_key, _group_title, m in indexed:
            if m.get("code") == jump:
                _render_mode_card(m, group_key=group_key)
                break
        return True
    return False


def _render_filters(indexed):
    st.markdown("### 🔍 幫我選模式")
    col1, col2, col3 = st.columns(3)
    with col1:
        scen = st.selectbox("我想解決的問題…", _SCENARIO_OPTIONS, key="tut_scenario")
    with col2:
        risk = st.radio("風險承受度", _RISK_OPTIONS, horizontal=True, key="tut_risk")
    with col3:
        om = st.radio("OM 範圍", _OM_OPTIONS, horizontal=True, key="tut_om")
    filtered = []
    for group_key, _group_title, mode_data in indexed:
        if scen != "全部場景" and _GROUP_USE.get(group_key) != scen:
            continue
        if risk != "全部" and mode_data.get("risk") != risk:
            continue
        if om != "全部":
            scope = _mode_scope_label(mode_data.get("code", ""))
            if om == "僅同OM" and "僅同OM" not in scope:
                continue
            if om == "可跨OM" and "可跨OM" not in scope:
                continue
        filtered.append((group_key, mode_data))
    return scen, risk, om, filtered


def _render_group(group_title, icon, modes_data, group_key=None, expanded=False):
    with st.expander(f"{icon} {group_title}（{len(modes_data)} 個模式 · 圖片版）", expanded=expanded):
        for mode_data in modes_data:
            _render_mode_card(mode_data, group_key=group_key)


def _render_global_rules():
    st.markdown("### 全局規則（適用於所有模式）")
    st.caption("以下 4 條適用全部 30 個模式，先看圖記重點。")
    _show_svg(_td.build_global_rules_svg(), center=6)

    st.markdown("""
#### 全局規則說明
1. **ND 店鋪限制**：ND 類型店鋪在所有模式下只能作為轉出方，不能作為接收方（ND1/ND2/ND3/ND4 及 F/F2/F3 模式下有 Target 的 ND 店舖除外）
2. **最高動銷店保護**：RF 類型中有效銷量（Last Month + MTD）最高的店鋪不會被選為轉出方
3. **避免雙重角色**：同一 SKU 的轉出店鋪絕對不能同時作為接收店鋪
4. **單件後處理**：所有模式輸出前統一消除 Transfer Qty = 1 的記錄（Rebalance 取 1 件補上 &#10132; Merge 合併至高銷量目標店）
""")


def _render_floor_body_guide():
    st.markdown("### 保底主體（Safety / Turnday）— 適用於所有模式")

    st.markdown("""
v2.32.0 起，側邊欄提供兩種**保底主體**，可與全部 30 個調貨模式任意組合（2 主體 × 30 模式）：
- **Safety Stock（現行版本）**：沿用上載檔的 Safety Stock 做保底（預設，行為與以往完全一致）。
- **Turnday（日銷速×日數）**：保底 = ceil(日銷速 × 自選日數 N)，讓保底隨實際銷速自動調節 —— 快銷店保底更高、滯銷店更低。
""")

    _show_svg(_td.build_floor_body_svg(), center=6)

    _formula_svg = _ASSETS_DIR / 'turnday_formula.svg'
    if _formula_svg.exists():
        _show_svg(_formula_svg.read_text(encoding="utf-8"), center=6)

    st.markdown("""
**計算公式（通式）：**

```
覆蓋日數 = 上月日數 + MTD數據日期日號      例：8月15日 = 7月31日 + 15日 = 46日
日銷速   = Effective Sold Qty ÷ 覆蓋日數    例：92 ÷ 46 = 2.0 件/日
保底     = ceil(日銷速 × 自選日數 N)        例：ceil(2.0 × 14) = 28 件
```
""")

    _compare_svg = _ASSETS_DIR / 'turnday_compare.svg'
    if _compare_svg.exists():
        st.markdown("#### 保底效果對比（N=14日示例）")
        _show_svg(_compare_svg.read_text(encoding="utf-8"), center=6)

    st.markdown("""
**模式受影響程度：**

| 類別 | 模式 | Turnday 主體下的變化 |
|------|------|------|
| 全面受影響 | A/A1/B/C/C2/B2系列/E1/E1b/E2/D/D2/ND1/ND2/精簡SKU×2 | 轉出保底＋接收目標全部改用 Turnday 基準（S→T） |
| 部分受影響 | C1、F/F2/F3、NST、ND3/ND4 | 僅接收端 Safety 觸點切換（如補0目標 max(S×0.5,3) → max(T×0.5,3)）；固定保底（淨存>2、保留2件、75%上限、保留3件）不變 |
| 接收上限語義 | B2系列/E1/精簡SKU | S×2 → T×2 = 2N 日用量上限；補0目標 S×0.5 → N/2 日用量 |

""")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Safety 主體")
        st.markdown(_risk_badge("低"), unsafe_allow_html=True)
        st.markdown("""
- 保底為固定值，不隨銷速變化
- 適合 Safety 值已反映實際業務經驗的品類
- 行為與 v2.31 完全一致
""")
    with col2:
        st.markdown("#### Turnday 主體")
        st.markdown(_risk_badge("中"), unsafe_allow_html=True)
        st.markdown("""
- ⚠️ 零銷量 SKU 保底 = 0，該店存貨可被全數轉出（清死貨利好，惟需接受陳列歸零）
- ⚠️ 快銷店保底可能遠高於原 Safety，轉出量減少屬預期
- ⚠️ 日銷速依賴 MTD 數據日期正確性，請核對上載區顯示的覆蓋日數
- 日數建議：日常補貨 7–14 日；季節品/前置期長 21–30 日
""")


def _render_decision_guide():
    st.markdown("### 模式選擇決策指南")
    st.markdown("根據以下問題，快速找到適合你的調貨模式：")

    _show_svg(_td.build_decision_tree_svg(), center=7)

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
            _flow_node(f'<b>{question}</b><br><span style="font-size:13px;">&#10132; {answer}</span>', color)
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
    _render_floor_body_guide()

    st.markdown("---")
    indexed = _all_modes_index()
    _render_overview(indexed)

    st.markdown("---")
    _render_snapshot(indexed)

    st.markdown("---")
    if _render_jump(indexed):
        st.markdown("---")
        _render_decision_guide()
        return

    st.markdown("---")
    scen, risk, om, filtered = _render_filters(indexed)

    st.markdown("---")
    st.markdown("### 30 種模式教學")
    if scen != "全部場景" or risk != "全部" or om != "全部":
        st.markdown(f"已篩出 **{len(filtered)}** 個模式（場景：{scen} · 風險：{risk} · OM：{om}），每張卡先看圖、再展開文字。")
        if not filtered:
            st.warning("沒有符合條件的模式，請放寬篩選（例如風險選「全部」）。")
        for group_key, mode_data in filtered:
            _render_mode_card(mode_data, group_key=group_key)
    else:
        st.markdown("按業務場景分為 8 組，展開查看圖片版詳細教學（每模式先看邏輯圖＋情境圖）。")
        expand_all = st.toggle("全部展開 8 組", value=False, key="tutorial_expand_all")
        st.info(
            "💡 **保底主體提示**：以下各模式公式中的「Safety / Safety Stock」字樣，在 Turnday 主體下會自動替換為 "
            "Turnday 保底（ceil(日銷速 × N日)，計算方法見上方教學）；各模式的固定保底"
            "（C1 淨存>2、F3/NST 保留2件、ND3/ND4 保留3件、NST 75%上限）不受主體影響。"
        )
        for group_key, group_title, icon in _GROUP_DEFS:
            modes_data = _load_group(group_key)
            _render_group(group_title, icon, modes_data, group_key=group_key, expanded=expand_all)

    st.markdown("---")
    _render_decision_guide()
