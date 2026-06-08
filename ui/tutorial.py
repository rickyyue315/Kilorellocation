"""
教學分頁 — 27 種調貨模式圖例教學
"""

import streamlit as st


def _flow_node(text, color="blue", width="auto"):
    colors = {
        "blue": ("#0F1E3D", "#60A5FA", "#2563EB"),
        "green": ("#052E16", "#34D399", "#059669"),
        "red": ("#450A0A", "#FCA5A5", "#DC2626"),
        "yellow": ("#3D1D06", "#FCD34D", "#D97706"),
        "gray": ("#1E1E2E", "#E0E0F0", "#8080A0"),
        "purple": ("#250E4A", "#C4B5FD", "#7C3AED"),
        "orange": ("#431407", "#FDBA74", "#EA580C"),
    }
    bg, border, accent = colors.get(color, colors["blue"])
    w = f"width:{width};" if width != "auto" else ""
    return (
        f'<div style="background:{bg};border:2px solid {border};border-radius:8px;'
        f'padding:8px 12px;text-align:center;font-size:13px;{w}">'
        f'{text}</div>'
    )


def _flow_arrow(label=""):
    lbl = f'<span style="font-size:11px;color:#C0C0D0;">{label}</span><br>' if label else ""
    return f'<div style="text-align:center;margin:2px 0;">{lbl}<span style="font-size:18px;color:#909090;">&#8595;</span></div>'


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
    colors = {"低": "#10B981", "中": "#F5A623", "高": "#EF4444"}
    c = colors.get(level, "#71717A")
    return f'<span style="background:{c};color:#fff;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;">風險：{level}</span>'


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


def _build_mode_content(
    code, name, risk, scenario, source_flow, dest_flow,
    match_order, scenario_table, extra_notes, diff_table,
):
    parts = []
    parts.append('<div class="mode-section">')
    parts.append(f'<h4 class="mode-title">模式 {code}：{name} {_risk_badge(risk)}</h4>')
    parts.append(f'<p class="mode-scenario"><b>適用場景：</b>{scenario}</p>')

    parts.append('<div class="flow-section">')
    parts.append('<p class="flow-label">&#128260; 轉出篩選流程</p>')
    parts.append(f'<div class="flow-container">{source_flow}</div>')
    parts.append('</div>')

    parts.append('<div class="flow-section">')
    parts.append('<p class="flow-label">&#128230; 接收篩選流程</p>')
    parts.append(f'<div class="flow-container">{dest_flow}</div>')
    parts.append('</div>')

    match_html = _build_match_rows(match_order)
    if match_html:
        parts.append('<div class="flow-section">')
        parts.append('<p class="flow-label">&#128279; 配對優先級</p>')
        parts.append(match_html)
        parts.append('</div>')

    if scenario_table:
        parts.append('<div class="flow-section">')
        parts.append('<p class="flow-label">&#128202; 情境範例</p>')
        parts.append(scenario_table)
        parts.append('</div>')

    if extra_notes:
        parts.append(f'<p class="mode-notes">&#128161; {extra_notes}</p>')

    if diff_table:
        parts.append('<div class="flow-section">')
        parts.append('<p class="flow-label">&#128209; 模式對比</p>')
        parts.append(diff_table)
        parts.append('</div>')

    parts.append('</div>')
    parts.append('<hr class="mode-divider">')

    return "\n".join(parts)


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
1. **ND 店鋪限制**：ND 類型店鋪在所有模式下只能作為轉出方，不能作為接收方（ND1/ND2 除外）
2. **最高動銷店保護**：RF 類型中有效銷量（Last Month + MTD）最高的店鋪不會被選為轉出方
3. **避免雙重角色**：同一 SKU 的轉出店鋪絕對不能同時作為接收店鋪
4. **單件後處理**：所有模式輸出前統一消除 Transfer Qty = 1 的記錄（Rebalance 取 1 件補上 &#10132; Merge 合併至高銷量目標店）
""")


def _render_group(group_title, icon, content_fn):
    with st.expander(f"{icon} {group_title}", expanded=False):
        for content in content_fn():
            st.markdown(content, unsafe_allow_html=True)


def _render_basic_group():
    content_a = _build_mode_content(
        "A", "保守轉貨", "低",
        scenario="追求穩定運營，嚴格保護安全庫存，不願承擔庫存風險",
        source_flow=(
            _flow_row([_flow_node("RF 店舖<br>庫存 > Safety Stock", "green")])
            + _flow_arrow("計算可轉量")
            + _flow_row([_flow_node("可轉 = min(<br>庫存-Safety,<br>max(庫存&#215;20%, 2),<br>Net Stock)", "blue")])
        ),
        dest_flow=_flow_row([
            _flow_node("緊急缺貨<br>Net Stock=0<br>有銷量", "red"),
            _flow_node("潛在缺貨<br>庫存 &lt; Safety<br>最高銷量店", "orange"),
        ]),
        match_order=[
            ("ND轉出", "緊急缺貨"),
            ("ND轉出", "潛在缺貨"),
            ("RF過剩轉出", "緊急缺貨"),
            ("RF過剩轉出", "潛在缺貨"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Net Stock", "Safety", "角色", "調撥量", "調撥後"],
            [
                ["HD001", "RF", "10", "4", "轉出(RF過剩)", "2", "8"],
                ["HD002", "RF", "0", "4", "接收(緊急)", "+2", "2"],
                ["HD003", "RF", "2", "4", "接收(潛在)", "- ", "2"],
                ["HA001", "ND", "5", "3", "轉出(ND)", "5", "0"],
            ]
        ),
        extra_notes="單件自動上調：若可轉量=1且轉出後仍餘&#8805;3件，自動上調至2件轉出",
        diff_table=_scenario_table(
            ["對比項", "A 保守", "B 加強"],
            [
                ["轉出比例上限", "20%", "50%"],
                ["安全庫存保護", "嚴格（不可低於）", "可下探"],
                ["轉出類型", "僅 RF 過剩", "RF 過剩 + RF 加強"],
                ["風險等級", "低", "中"],
            ]
        ),
    )

    content_b = _build_mode_content(
        "B", "加強轉貨", "中",
        scenario="需要積極處理滯銷庫存，最大化調貨效率，允許下探安全庫存",
        source_flow=(
            _flow_row([_flow_node("RF 店舖<br>庫存 > Safety Stock", "green")])
            + _flow_arrow("計算可轉量")
            + _flow_row([_flow_node("可轉 = min(<br>庫存-Safety,<br>max(庫存&#215;50%, 2),<br>Net Stock)", "blue")])
            + _flow_arrow("判斷類型")
            + _flow_row([
                _flow_node("轉出後 &#8805; Safety<br>&#10132; RF過剩轉出", "green"),
                _flow_node("轉出後 &lt; Safety<br>&#10132; RF加強轉出", "orange"),
            ])
        ),
        dest_flow=_flow_row([
            _flow_node("緊急缺貨<br>Net Stock=0<br>有銷量", "red"),
            _flow_node("潛在缺貨<br>庫存 &lt; Safety<br>最高銷量店", "orange"),
        ]),
        match_order=[
            ("ND轉出", "緊急缺貨"),
            ("ND轉出", "潛在缺貨"),
            ("RF過剩轉出", "緊急缺貨"),
            ("RF過剩轉出", "潛在缺貨"),
            ("RF加強轉出", "緊急缺貨"),
            ("RF加強轉出", "潛在缺貨"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Net Stock", "Safety", "角色", "調撥量", "調撥後"],
            [
                ["HD001", "RF", "10", "4", "轉出(RF過剩)", "5", "5"],
                ["HD002", "RF", "6", "4", "轉出(RF加強)", "3", "3"],
                ["HD003", "RF", "0", "4", "接收(緊急)", "+4", "4"],
                ["HD004", "RF", "2", "5", "接收(潛在)", "+4", "6"],
            ]
        ),
        extra_notes="B 模式更進取，RF 可轉出 50% 庫存（A 模式僅 20%），允許低於安全庫存轉出",
        diff_table=None,
    )

    return [content_a, content_b]


def _render_b2_group():
    content_b2 = _build_mode_content(
        "B2", "附加B特別模式", "中",
        scenario="有 Type=L 特殊店舖需優先清出，接收端需依遊客區/混合型店舖優先排序",
        source_flow=_flow_row([
            _flow_node("ND 店舖", "blue"),
            _flow_node("Type=L 且銷量&#8804;2<br>&#10132; 全數轉出", "orange"),
            _flow_node("其他 RF<br>&#10132; 50%上限", "green"),
        ]),
        dest_flow=_flow_row([
            _flow_node("1&#65039;&#8419; Type T<br>高銷量優先", "purple"),
            _flow_node("2&#65039;&#8419; Type M<br>高銷量優先", "purple"),
            _flow_node("3&#65039;&#8419; Type T<br>Safety優先", "green"),
            _flow_node("4&#65039;&#8419; Type M<br>Safety優先", "green"),
        ]),
        match_order=[
            ("ND轉出", "緊急缺貨"),
            ("ND轉出", "潛在缺貨"),
            ("RF過剩轉出", "緊急缺貨"),
            ("RF過剩轉出", "潛在缺貨"),
            ("Local店舖全轉出", "緊急缺貨"),
            ("Local店舖全轉出", "潛在缺貨"),
            ("RF加強轉出", "緊急缺貨"),
            ("RF加強轉出", "潛在缺貨"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "Type", "Net Stock", "Safety", "銷量", "角色", "調撥量"],
            [
                ["HD001", "L", "8", "4", "1", "轉出(Local全轉出)", "8"],
                ["HD002", "T", "0", "4", "6", "接收(T高銷量)", "+3"],
                ["HD003", "M", "2", "4", "4", "接收(M高銷量)", "+3"],
                ["HD004", "RF", "10", "4", "5", "轉出(RF過剩)", "5"],
            ]
        ),
        extra_notes="Mix 店舖保護：若出貨店 Type=M 且總銷量 &gt; 目標店總銷量，該配對被取消。接收上限 Safety&#215;2",
        diff_table=_scenario_table(
            ["對比項", "B2", "B2a", "B2L", "B2La"],
            [
                ["Type=L低銷量", "全數轉出", "全數轉出", "保留2件後轉出", "保留2件後轉出"],
                ["Type=T出貨", "可", "不可", "可", "不可"],
                ["Mix保護", "有", "有", "有", "有"],
            ]
        ),
    )

    content_b2a = _build_mode_content(
        "B2a", "附加B2a特別模式（T遊客鋪不出貨）", "中",
        scenario="與 B2 相同場景，但額外要求 Type=T（遊客鋪）不可作為出貨來源",
        source_flow=_flow_row([
            _flow_node("Type=T？<br>&#10132; 不可出貨", "red"),
            _flow_node("ND 店舖", "blue"),
            _flow_node("Type=L 且銷量&#8804;2<br>&#10132; 全數轉出", "orange"),
            _flow_node("其他 RF<br>&#10132; 50%上限", "green"),
        ]),
        dest_flow=_flow_row([_flow_node("同 B2 接收優先級", "purple")]),
        match_order=None,
        scenario_table=_scenario_table(
            ["店舖", "Type", "Net Stock", "角色", "說明"],
            [
                ["HD001", "T", "10", "不出貨", "Type=T 被排除"],
                ["HD002", "L", "8", "轉出(Local全轉出)", "Type=L 銷量&#8804;2"],
                ["HD003", "T", "0", "接收(T高銷量)", "遊客區接收優先"],
            ]
        ),
        extra_notes="B2a 在 B2 基礎上唯一差異：Type=T 店舖不可作為 source",
        diff_table=None,
    )

    content_b2l = _build_mode_content(
        "B2L", "附加B2L特別模式（Type=L保留2件）", "中",
        scenario="與 B2 相同場景，但 Type=L 低銷量店舖不全轉出，改為保留 2 件",
        source_flow=_flow_row([
            _flow_node("ND 店舖", "blue"),
            _flow_node("Type=L 且銷量&#8804;2<br>&#10132; 保留2件後轉出<br>max(Net-2, 0)", "orange"),
            _flow_node("其他 RF<br>&#10132; 50%上限", "green"),
        ]),
        dest_flow=_flow_row([_flow_node("同 B2 接收優先級", "purple")]),
        match_order=None,
        scenario_table=_scenario_table(
            ["店舖", "Type", "Net Stock", "銷量", "B2 轉出量", "B2L 轉出量"],
            [
                ["HD001", "L", "8", "1", "8(全轉)", "6(保留2)"],
                ["HD002", "L", "2", "0", "2(全轉)", "0(不轉)"],
            ]
        ),
        extra_notes="B2L 與 B2 差異僅在 Type=L 低銷量規則：B2 全轉出，B2L 保留 2 件後才轉出",
        diff_table=None,
    )

    content_b2la = _build_mode_content(
        "B2La", "附加B2La特別模式（Type=L保留2件 + T不出貨）", "中",
        scenario="結合 B2L（Type=L 保留 2 件）和 B2a（Type=T 不出貨）的限制",
        source_flow=_flow_row([
            _flow_node("Type=T？<br>&#10132; 不可出貨", "red"),
            _flow_node("ND 店舖", "blue"),
            _flow_node("Type=L 且銷量&#8804;2<br>&#10132; 保留2件後轉出", "orange"),
            _flow_node("其他 RF<br>&#10132; 50%上限", "green"),
        ]),
        dest_flow=_flow_row([_flow_node("同 B2 接收優先級", "purple")]),
        match_order=None,
        scenario_table=None,
        extra_notes="B2La = B2L + B2a 的限制合併：Type=L 保留 2 件 + Type=T 不可出貨",
        diff_table=None,
    )

    return [content_b2, content_b2a, content_b2l, content_b2la]


def _render_b3_group():
    content_b3 = _build_mode_content(
        "B3", "附加B跨OM特別模式", "中",
        scenario="B2 場景但需要跨 OM 配對，擴大調貨範圍",
        source_flow=(
            _flow_row([_flow_node("同 B2 轉出邏輯", "green")])
            + _flow_arrow("跨OM配對")
            + _flow_row([
                _flow_node("HD &#10132; 不能到 HA/HB/HC", "red"),
                _flow_node("Windy &#10132; 只能到 Windy", "orange"),
            ])
        ),
        dest_flow=_flow_row([_flow_node("同 B2 接收優先級", "purple")]),
        match_order=None,
        scenario_table=_scenario_table(
            ["轉出店", "OM", "接收店", "OM", "是否允許"],
            [
                ["HD001", "HD", "HA001", "HA", "不允許(HD限制)"],
                ["HD001", "HD", "HB001", "HB", "不允許(HD限制)"],
                ["HD001", "HD", "Windy001", "Windy", "允許"],
                ["Windy001", "Windy", "HD001", "HD", "不允許(Windy限制)"],
                ["Windy001", "Windy", "Windy002", "Windy", "允許"],
            ]
        ),
        extra_notes="B3 = B2 邏輯 + 跨 OM + HD/Windy 限制。同樣套用 Mix 保護規則",
        diff_table=_scenario_table(
            ["對比項", "B3", "B3a", "B3L", "B3La"],
            [
                ["Type=L低銷量", "全數轉出", "全數轉出", "保留2件後轉出", "保留2件後轉出"],
                ["Type=T出貨", "可", "不可", "可", "不可"],
                ["跨OM", "可", "可", "可", "可"],
            ]
        ),
    )

    content_b3a = _build_mode_content(
        "B3a", "附加B3a跨OM特別模式（T遊客鋪不出貨）", "中",
        scenario="B3 + Type=T 不可出貨",
        source_flow=_flow_row([
            _flow_node("Type=T？<br>&#10132; 不可出貨", "red"),
            _flow_node("同 B3 轉出邏輯", "green"),
        ]),
        dest_flow=_flow_row([_flow_node("同 B2 接收優先級", "purple")]),
        match_order=None,
        scenario_table=None,
        extra_notes="B3a = B3 + Type=T 不可出貨",
        diff_table=None,
    )

    content_b3l = _build_mode_content(
        "B3L", "附加B3L跨OM特別模式（Type=L保留2件）", "中",
        scenario="B3 + Type=L 低銷量保留 2 件",
        source_flow=(
            _flow_row([_flow_node("同 B2L 轉出邏輯", "green")])
            + _flow_arrow("跨OM配對")
            + _flow_row([_flow_node("HD/Windy 限制", "red")])
        ),
        dest_flow=_flow_row([_flow_node("同 B2 接收優先級", "purple")]),
        match_order=None,
        scenario_table=None,
        extra_notes="B3L = B3 跨OM + B2L 的 Type=L 保留 2 件規則",
        diff_table=None,
    )

    content_b3la = _build_mode_content(
        "B3La", "附加B3La跨OM特別模式（Type=L保留2件 + T不出貨）", "中",
        scenario="B3L + Type=T 不可出貨",
        source_flow=(
            _flow_row([
                _flow_node("Type=T？<br>&#10132; 不可出貨", "red"),
                _flow_node("同 B2L 轉出邏輯", "green"),
            ])
            + _flow_arrow("跨OM配對")
            + _flow_row([_flow_node("HD/Windy 限制", "red")])
        ),
        dest_flow=_flow_row([_flow_node("同 B2 接收優先級", "purple")]),
        match_order=None,
        scenario_table=None,
        extra_notes="B3La = B3L + Type=T 不可出貨",
        diff_table=None,
    )

    return [content_b3, content_b3a, content_b3l, content_b3la]


def _render_c_group():
    content_c = _build_mode_content(
        "C", "重點補0", "中",
        scenario="針對性補充極低庫存（&#8804;1件）的店舖，確保最低服務水平",
        source_flow=(
            _flow_row([_flow_node("ND 店舖<br>全數可轉出", "blue")])
            + _flow_arrow()
            + _flow_row([_flow_node("RF 店舖<br>可轉=min(庫存&#215;30%, 3件)<br>至少1件", "green")])
        ),
        dest_flow=_flow_row([
            _flow_node("重點補0<br>庫存&#8804;1<br>目標=max(Safety&#215;0.5, 3)", "purple"),
            _flow_node("緊急缺貨<br>Net Stock=0<br>有銷量", "red"),
            _flow_node("潛在缺貨<br>庫存 &lt; Safety", "orange"),
        ]),
        match_order=[
            ("ND轉出", "重點補0"),
            ("ND轉出", "緊急缺貨"),
            ("ND轉出", "潛在缺貨"),
            ("RF過剩轉出", "重點補0"),
            ("RF過剩轉出", "緊急缺貨"),
            ("RF過剩轉出", "潛在缺貨"),
            ("RF加強轉出", "重點補0"),
            ("RF加強轉出", "緊急缺貨"),
            ("RF加強轉出", "潛在缺貨"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "Net Stock", "Pending", "Safety", "角色", "調撥量"],
            [
                ["HD001", "0", "0", "4", "接收(重點補0)", "+3"],
                ["HD002", "1", "0", "5", "接收(重點補0)", "+3"],
                ["HD003", "10", "0", "4", "轉出(RF過剩)", "-3"],
                ["HD004", "0", "0", "4", "接收(緊急缺貨)", "+3"],
            ]
        ),
        extra_notes="C 模式獨有「重點補0」接收類型：庫存+在途&#8804;1 的店舖優先補至 max(Safety&#215;0.5, 3) 件",
        diff_table=_scenario_table(
            ["對比項", "C", "C1", "C2"],
            [
                ["接收類型", "重點補0+緊急+潛在", "僅重點補0", "重點補0+緊急+潛在"],
                ["轉出量下限", "1件", "2件", "1件"],
                ["跨OM", "否", "否", "是"],
                ["適用場景", "全面補低庫存", "精準只補零庫存", "跨OM重點補0"],
            ]
        ),
    )

    content_c1 = _build_mode_content(
        "C1", "重點補0（只補0/1）", "低",
        scenario="精準只補充零庫存或低庫存的店舖，門檻 N 可於側邊欄設定，不會觸發一般缺貨補貨",
        source_flow=(
            _flow_row([_flow_node("RF 店舖<br>Net Stock &gt; 2", "green")])
            + _flow_arrow("最少2件起轉")
            + _flow_row([_flow_node("可轉=min(庫存&#215;30%, 3件)<br>最少 2 件", "blue")])
        ),
        dest_flow=_flow_row([
            _flow_node("僅 total_available &#8804; N<br>N 可於側邊欄設定（預設1）<br>目標=max(Safety&#215;0.5, 3)", "purple"),
        ]),
        match_order=[
            ("ND轉出", "緊急缺貨"),
            ("RF過剩轉出", "重點補0"),
            ("RF加強轉出", "重點補0"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "Net Stock", "Pending", "Safety", "角色", "調撥量"],
            [
                ["HD001", "0", "0", "4", "接收(重點補0)", "+3"],
                ["HD002", "1", "0", "5", "接收(重點補0)", "+3"],
                ["HD003", "0", "4", "4", "不接收(非C1目標)", "-"],
                ["HD004", "10", "0", "4", "轉出(RF過剩)", "-3"],
            ]
        ),
        extra_notes="C1 與 C 最大差異：不回落到緊急/潛在缺貨補貨，僅處理 total_available&#8804;N 的店舖（N 可於側邊欄設定，預設 1）。轉出最低 2 件",
        diff_table=_scenario_table(
            ["對比項", "C", "C1", "C2"],
            [
                ["接收類型", "重點補0+緊急+潛在", "僅重點補0", "重點補0+緊急+潛在"],
                ["補0門檻", "total_available&#8804;1", "可自訂（預設1）", "total_available&#8804;1"],
                ["轉出量下限", "1件", "2件", "1件"],
                ["跨OM", "否", "否", "是"],
                ["適用場景", "全面補低庫存", "精準只補零庫存", "跨OM重點補0"],
            ]
        ),
    )

    content_c2 = _build_mode_content(
        "C2", "附加C跨OM重點補0", "中",
        scenario="需要跨 OM 重點補0，全局性零庫存補充策略",
        source_flow=(
            _flow_row([_flow_node("同 C 模式轉出邏輯", "green")])
            + _flow_arrow("跨OM配對")
            + _flow_row([
                _flow_node("HD &#10132; 不能到 HA/HB/HC", "red"),
                _flow_node("Windy &#10132; 只能到 Windy", "orange"),
            ])
        ),
        dest_flow=_flow_row([_flow_node("同 C 模式接收邏輯", "purple")]),
        match_order=None,
        scenario_table=_scenario_table(
            ["場景", "說明"],
            [
                ["OM-A 內無多餘庫存", "可從 OM-B 的店舖調貨到 OM-A 的零庫存店"],
                ["Windy &#10132; HD", "不允許（Windy 只能到 Windy）"],
                ["HD &#10132; HA", "不允許（HD 限制）"],
            ]
        ),
        extra_notes="C2 = C 模式邏輯 + 跨 OM + HD/Windy 限制",
        diff_table=None,
    )

    return [content_c, content_c1, content_c2]


def _render_d_group():
    content_d = _build_mode_content(
        "D", "清貨轉貨", "中",
        scenario="清理 ND 店舖無銷售記錄的滯銷庫存，避免留下 1 件餘貨",
        source_flow=(
            _flow_row([_flow_node("ND + 銷量=0<br>&#10132; ND清貨轉出<br>全數轉出", "red")])
            + _flow_arrow("避免1件餘貨")
            + _flow_row([_flow_node("餘1件？&#10132; 多轉1件(餘0)<br>或 少轉1件(餘&#8805;2)", "orange")])
            + _flow_arrow()
            + _flow_row([_flow_node("RF 過剩轉出<br>沿用A模式規則(20%)", "green")])
        ),
        dest_flow=_flow_row([
            _flow_node("緊急缺貨<br>沿用A模式", "red"),
            _flow_node("潛在缺貨<br>沿用A模式", "orange"),
        ]),
        match_order=[
            ("ND清貨轉出", "緊急缺貨"),
            ("ND清貨轉出", "潛在缺貨"),
            ("RF過剩轉出", "緊急缺貨"),
            ("RF過剩轉出", "潛在缺貨"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Net Stock", "銷量", "角色", "調撥量", "調撥後", "說明"],
            [
                ["HA001", "ND", "5", "0", "ND清貨轉出", "5", "0", "無銷售全轉"],
                ["HA002", "ND", "4", "0", "ND清貨轉出", "4", "0", "無銷售全轉"],
                ["HA003", "ND", "3", "2", "ND轉出", "3", "0", "有銷售也轉"],
                ["HD001", "RF", "0", "3", "接收(緊急)", "+5", "5", ""],
            ]
        ),
        extra_notes="D 模式獨有「避免1件餘貨」：轉出後若出貨店剩1件，自動調整為0件或&#8805;2件",
        diff_table=_scenario_table(
            ["對比項", "D", "D2"],
            [
                ["ND無銷售轉出", "全數轉出", "全數轉出"],
                ["ND有銷售轉出", "可轉出", "不轉出"],
                ["RF轉出", "沿用A模式(20%)", "完全不做"],
                ["避免1件餘貨", "有", "有"],
            ]
        ),
    )

    content_d2 = _build_mode_content(
        "D2", "清貨轉貨（ND限定）", "低",
        scenario="僅清理 ND 無銷售庫存，RF 店舖完全不做轉出，只做接收。可選擇是否啟用「限制2間店舖接收」優化",
        source_flow=_flow_row([
            _flow_node("ND + 銷量=0<br>&#10132; ND清貨轉出", "red"),
            _flow_node("ND + 銷量&gt;0<br>&#10132; 不轉出", "gray"),
            _flow_node("RF 店舖<br>&#10132; 完全不轉出", "gray"),
        ]),
        dest_flow=_flow_row([
            _flow_node("緊急缺貨", "red"),
            _flow_node("潛在缺貨", "orange"),
        ]),
        match_order=[
            ("ND清貨轉出", "緊急缺貨"),
            ("ND清貨轉出", "潛在缺貨"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Net Stock", "銷量", "D 模式", "D2 模式"],
            [
                ["HA001", "ND", "5", "0", "清貨轉出", "清貨轉出"],
                ["HA002", "ND", "3", "2", "ND轉出", "不轉出"],
                ["HD001", "RF", "10", "1", "RF過剩轉出", "不轉出(僅接收)"],
            ]
        ),
        extra_notes="D2 是最保守的清貨策略：僅 ND 無銷售店舖轉出，RF 只接收不轉出。可在側邊欄切換「限制2間店舖接收（優化版）」，啟動後每間 ND 轉出源最多配對 2 間 RF 接收店，接收量放大至 200%。",
        diff_table=None,
    )

    return [content_d, content_d2]


def _render_e_group():
    content_e1 = _build_mode_content(
        "E1", "強制轉出（僅同OM）", "高",
        scenario="季節性商品下架、新品試銷分配等，需強制清空指定商品。僅同 OM 配對",
        source_flow=(
            _flow_row([_flow_node("ALL 欄位有標記？", "yellow")])
            + _flow_arrow()
            + _flow_row([
                _flow_node("有標記 &#10132; 全數強制轉出<br>忽略安全庫存", "red"),
                _flow_node("無標記 &#10132; 不處理", "gray"),
            ])
        ),
        dest_flow=_flow_row([
            _flow_node("RF 店舖<br>接收上限 Safety&#215;2<br>僅同 OM", "purple"),
        ]),
        match_order=[("E模式強制轉出", "E模式接收")],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Net Stock", "ALL", "角色", "調撥量"],
            [
                ["HD001", "RF", "10", "Y", "強制轉出", "10"],
                ["HD002", "ND", "5", "Y", "強制轉出", "5"],
                ["HD003", "RF", "2", "Y", "強制轉出", "2"],
                ["HD004", "RF", "0", "", "不處理", "-"],
                ["HD005", "RF", "3", "", "接收(E模式)", "+5"],
            ]
        ),
        extra_notes="E1 需要 Excel 中有「ALL」欄位。僅處理標記的商品行。HD 不能轉到 HA/HB/HC",
        diff_table=_scenario_table(
            ["對比項", "E1", "E1b", "E2"],
            [
                ["轉出邏輯", "ALL標記全轉", "ALL標記全轉", "ALL標記全轉"],
                ["接收排序", "標準", "Type=T/M優先", "標準"],
                ["跨OM", "否", "否", "是"],
                ["C模式回退", "否", "否", "是(Phase3)"],
            ]
        ),
    )

    content_e1b = _build_mode_content(
        "E1b", "強制轉出（優先類型接收）", "高",
        scenario="E1 場景但希望優先分配給遊客區/混合型店舖",
        source_flow=_flow_row([_flow_node("同 E1 轉出邏輯", "red")]),
        dest_flow=_flow_row([
            _flow_node("1&#65039;&#8419; Type T 高銷量", "purple"),
            _flow_node("2&#65039;&#8419; Type M 高銷量", "purple"),
            _flow_node("3&#65039;&#8419; Type T Safety", "green"),
            _flow_node("4&#65039;&#8419; Type M Safety", "green"),
        ]),
        match_order=None,
        scenario_table=_scenario_table(
            ["店舖", "Type", "Net Stock", "Safety", "銷量", "接收優先級"],
            [
                ["HD001", "T", "0", "4", "8", "1&#65039;&#8419; Type T 高銷量"],
                ["HD002", "M", "0", "4", "6", "2&#65039;&#8419; Type M 高銷量"],
                ["HD003", "T", "2", "6", "3", "3&#65039;&#8419; Type T Safety"],
                ["HD004", "M", "1", "5", "1", "4&#65039;&#8419; Type M Safety"],
            ]
        ),
        extra_notes="E1b = E1 轉出 + B2 接收優先級。新品推廣重點放在遊客區店舖時使用",
        diff_table=None,
    )

    content_e2 = _build_mode_content(
        "E2", "強制轉出（跨OM）", "高",
        scenario="需要跨 OM 強制轉出，覆蓋更廣的店舖範圍",
        source_flow=(
            _flow_row([_flow_node("同 E1 轉出邏輯", "red")])
            + _flow_arrow("分階段配對")
            + _flow_row([
                _flow_node("Phase 1<br>同OM配對", "green"),
                _flow_node("Phase 2<br>跨OM配對", "orange"),
                _flow_node("Phase 3<br>C模式回退", "purple"),
            ])
        ),
        dest_flow=_flow_row([_flow_node("RF 接收上限 Safety&#215;2", "purple")]),
        match_order=None,
        scenario_table=_scenario_table(
            ["階段", "條件", "說明"],
            [
                ["Phase 1", "同OM有接收需求", "優先同OM配對"],
                ["Phase 2", "同OM不足", "跨OM配對(HD限制)"],
                ["Phase 3", "其他OM無E模式來源", "用C模式邏輯補充"],
            ]
        ),
        extra_notes="E2 三階段：同OM &#10132; 跨OM &#10132; C模式回退。HD 不能轉到 HA/HB/HC",
        diff_table=None,
    )

    return [content_e1, content_e1b, content_e2]


def _render_f_group():
    content_f = _build_mode_content(
        "F", "目標優化", "中",
        scenario="有明確接收目標量（Target），需要按指定數量分配到指定店舖",
        source_flow=(
            _flow_row([_flow_node("ND 店舖<br>Target&gt;0 &#10132; 接收方<br>否則全數轉出", "blue")])
            + _flow_arrow()
            + _flow_row([_flow_node("RF 店舖<br>可轉出(保護最高銷量店)", "green")])
        ),
        dest_flow=_flow_row([
            _flow_node("1&#65039;&#8419; Target&gt;0<br>直接按Target接收<br>不論ND/RF", "purple"),
            _flow_node("2&#65039;&#8419; 無Target且庫存&#8804;1<br>補0邏輯(僅RF)", "orange"),
        ]),
        match_order=[
            ("F模式ND/RF轉出", "F模式目標接收"),
            ("F模式ND/RF轉出", "重點補0"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Net Stock", "Target", "角色", "調撥量"],
            [
                ["HD001", "RF", "15", "-", "轉出(F模式RF)", "-8"],
                ["HD002", "ND", "5", "-", "轉出(F模式ND)", "-5"],
                ["HD003", "RF", "2", "5", "接收(目標)", "+5"],
                ["HD004", "ND", "0", "3", "接收(目標ND也可收)", "+3"],
                ["HD005", "RF", "0", "-", "接收(補0)", "+3"],
            ]
        ),
        extra_notes="F 模式打破 ND 不可接收限制（僅限有 Target 的 ND 店舖）。Target 數量直接作為接收量。跨 OM 允許",
        diff_table=_scenario_table(
            ["對比項", "F", "F2"],
            [
                ["Target 店接收", "是", "是"],
                ["非Target補0", "是(庫存&#8804;1的RF)", "否"],
                ["ND可接收", "有Target時可", "有Target時可"],
                ["Windy目標優先", "否", "是"],
                ["HD轉出選項", "預設限制", "可設定允許"],
            ]
        ),
    )

    content_f2 = _build_mode_content(
        "F2", "F指定模式", "中",
        scenario="需要集中補貨到指定 Target 店舖，非 Target 店舖完全不接收",
        source_flow=(
            _flow_row([_flow_node("同 F 模式轉出邏輯", "green")])
            + _flow_arrow("僅Target接收")
            + _flow_row([
                _flow_node("Target&gt;0 的店舖<br>直接按Target接收<br>不論ND/RF", "purple"),
                _flow_node("無Target的店舖<br>完全不接收", "gray"),
            ])
        ),
        dest_flow=_flow_row([
            _flow_node("Windy目標店<br>優先從同OM<br>無Target Windy提取", "orange"),
        ]),
        match_order=[("F模式ND/RF轉出", "F指定模式目標接收")],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Target", "F 模式", "F2 模式"],
            [
                ["HD001", "RF", "5", "接收(目標)", "接收(目標)"],
                ["HD002", "ND", "3", "接收(目標ND)", "接收(目標ND)"],
                ["HD003", "RF", "-", "接收(補0)", "不接收"],
                ["HD004", "RF", "-", "不接收", "不接收"],
            ]
        ),
        extra_notes="F2 = 僅 Target 店接收。Windy 目標店優先從同 OM 無 Target Windy 店提取。可設定 HD 可轉出（最後優先）",
        diff_table=None,
    )

    content_f3 = _build_mode_content(
        "F3", "目標性補0", "中",
        scenario="需要集中補貨到指定 Target 店舖，同時確保 RF 轉出店保留最低庫存（不低於2件），且 RF 跨 OM 同 OM 同等優先",
        source_flow=(
            _flow_row([_flow_node("ND 店舖<br>全數轉出", "blue")])
            + _flow_arrow("F3")
            + _flow_row([
                _flow_node("RF 店舖<br>轉出後保留2件<br>最高庫存優先轉出<br>跨OM不降級", "green"),
                _flow_node("保護最高銷量RF<br>不轉出", "purple"),
            ])
        ),
        dest_flow=_flow_row([
            _flow_node("同 F2<br>僅 Target>0 店<br>直接按Target接收", "purple"),
        ]),
        match_order=[("F模式ND轉出", "F指定模式目標接收"),
                     ("F3模式RF轉出(保留2件)", "F指定模式目標接收")],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Net Stock", "Target", "F2 轉出量", "F3 轉出量", "角色"],
            [
                ["HD001", "RF", "10", "-", "10", "8", "F3保留2件轉出"],
                ["HD002", "RF", "3", "-", "3", "1", "F3可轉1件"],
                ["HD003", "RF", "2", "-", "2", "0", "F3庫存≤2不轉"],
                ["HD004", "ND", "5", "-", "5", "5", "ND全轉"],
                ["HD005", "RF", "5", "8", "-", "-", "Target保護不轉"],
            ]
        ),
        extra_notes="F3 = F2 + RF轉出保留2件 + RF最高庫存優先轉出 + RF跨OM不降級。HD轉出選項、Windy目標優先同F2",
        diff_table=_scenario_table(
            ["對比項", "F2", "F3"],
            [
                ["RF轉出量", "net_stock全轉", "max(net_stock-2, 0)"],
                ["RF排序", "銷量低優先", "最高庫存優先→銷量低"],
                ["RF跨OM", "降級(tier+1)", "不降級(同OM同等)"],
                ["Target接收", "僅Target", "僅Target"],
                ["HD轉出選項", "可設定", "可設定"],
                ["Windy目標優先", "是", "是"],
            ]
        ),
    )

    return [content_f, content_f2, content_f3]


def _render_nd_sku_group():
    content_nd1 = _build_mode_content(
        "ND1", "ND同OM轉貨", "中",
        scenario="ND 店舖之間需要互相調貨，或 ND 轉給 RF 店舖。打破「ND 不可接收」限制",
        source_flow=(
            _flow_row([_flow_node("ND 店舖<br>按過去2個月銷量升序<br>(0銷量優先轉出)", "blue")])
            + _flow_arrow("保護最高銷量ND")
            + _flow_row([
                _flow_node("最高銷量 ND 店<br>不轉出", "purple"),
                _flow_node("其他 ND 店<br>ND智能轉出", "green"),
            ])
        ),
        dest_flow=_flow_row([
            _flow_node("1&#65039;&#8419; RF 緊急缺貨<br>Net Stock=0 有銷量", "red"),
            _flow_node("2&#65039;&#8419; ND 潛在缺貨<br>按過去2個月銷量降序<br>上限=2&#215;銷量", "orange"),
        ]),
        match_order=[
            ("ND智能轉出", "RF緊急缺貨"),
            ("ND智能轉出", "ND潛在缺貨"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Net Stock", "過去2個月銷量", "角色", "調撥量"],
            [
                ["HA001", "ND", "10", "0", "轉出(0銷量優先)", "-8"],
                ["HA002", "ND", "5", "3", "轉出(低銷量)", "-3"],
                ["HA003", "ND", "8", "10", "保護(最高銷量)", "-"],
                ["HD001", "RF", "0", "5", "接收(緊急)", "+5"],
                ["HA004", "ND", "1", "4", "接收(ND潛在)", "+3"],
            ]
        ),
        extra_notes="ND1 打破全局「ND不可接收」規則。過去2個月銷量=0 的 ND 店舖不可接收。同 OM 配對",
        diff_table=_scenario_table(
            ["對比項", "ND1", "ND2"],
            [
                ["配對範圍", "僅同OM", "跨OM"],
                ["Windy限制", "N/A", "Windy只轉Windy"],
                ["HD限制", "N/A", "HD不可到HA/HB/HC"],
            ]
        ),
    )

    content_nd2 = _build_mode_content(
        "ND2", "ND混合OM轉貨", "中",
        scenario="ND1 場景但需要跨 OM 配對",
        source_flow=(
            _flow_row([_flow_node("同 ND1 轉出邏輯", "green")])
            + _flow_arrow("跨OM配對")
            + _flow_row([
                _flow_node("Windy &#10132; 只到 Windy", "orange"),
                _flow_node("HD &#10132; 不可到 HA/HB/HC", "red"),
            ])
        ),
        dest_flow=_flow_row([_flow_node("同 ND1 接收邏輯", "purple")]),
        match_order=None,
        scenario_table=_scenario_table(
            ["場景", "說明"],
            [
                ["OM-A ND &#10132; OM-B RF", "允許跨OM"],
                ["Windy ND &#10132; HD RF", "不允許(Windy限制)"],
                ["HD ND &#10132; HA RF", "不允許(HD限制)"],
            ]
        ),
        extra_notes="ND2 = ND1 + 跨OM + HD/Windy 限制",
        diff_table=None,
    )

    content_nd3 = _build_mode_content(
        "ND3", "ND限同OM轉貨(補0)", "中",
        scenario="ND 店舖同 OM 補零庫存，轉出保留 3 件庫存，僅針對零庫存 ND 店舖補貨，參考 C1 模式",
        source_flow=(
            _flow_row([_flow_node("ND 店舖<br>按過去2個月銷量升序<br>(0銷量優先轉出)", "blue")])
            + _flow_arrow("保留 3 件")
            + _flow_row([
                _flow_node("Net Stock &#8804; 3<br>不轉出", "red"),
                _flow_node("Net Stock &gt; 3<br>轉出量 = Net Stock - 3<br>ND3智能轉出(保留3件)", "green"),
            ])
        ),
        dest_flow=_flow_row([
            _flow_node("ND 零庫存店舖<br>Net Stock = 0<br>目標量=max(Safety&#215;0.5, 3)<br>按銷量降序排序<br>ND3補0接收", "orange"),
        ]),
        match_order=[
            ("ND3智能轉出(保留3件)", "ND3補0接收"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Net Stock", "Safety", "過去2個月銷量", "角色", "調撥量"],
            [
                ["HA001", "ND", "10", "-", "0", "轉出(0銷量優先)", "-7"],
                ["HA002", "ND", "6", "-", "3", "轉出(低銷量)", "-3"],
                ["HA003", "ND", "2", "-", "5", "不轉出(&#8804;3)", "-"],
                ["HA004", "ND", "0", "4", "2", "接收(ND3補0)", "+3"],
                ["HA005", "ND", "3", "-", "-", "不轉出(&#8804;3)", "-"],
            ]
        ),
        extra_notes="ND3 參考 C1 模式，僅處理目標需求不回落。轉出必須保留 3 件庫存。接收目標量 = max(Safety&#215;0.5, 3)。同 OM 配對",
        diff_table=_scenario_table(
            ["對比項", "ND1", "ND3"],
            [
                ["轉出保留", "完全不保留", "保留 3 件"],
                ["接收對象", "RF緊急 + ND潛在", "僅零庫存 ND"],
                ["接收目標", "2&#215;銷量", "max(Safety&#215;0.5, 3)"],
                ["配對範圍", "僅同OM", "僅同OM"],
                ["參考", "-", "C1"],
            ]
        ),
    )

    content_sku_om = _build_mode_content(
        "精簡SKU(限同OM)", "精簡SKU調貨（同OM）", "中",
        scenario="SKU 精簡場景，將超出上限的庫存轉出至有需求的 RF 店舖，剩餘退回 D001",
        source_flow=(
            _flow_row([_flow_node("ND 店舖<br>全數轉出", "blue")])
            + _flow_arrow()
            + _flow_row([_flow_node("RF 店舖<br>超出Cap部分轉出<br>Cap=Max(Safety&#215;2, 過去2個月銷量&#215;2)", "green")])
        ),
        dest_flow=_flow_row([
            _flow_node("RF 接收<br>上限=Max(Safety&#215;2,<br>過去2個月銷量&#215;2)<br>最少2件", "purple"),
            _flow_node("剩餘未配對<br>&#10132; 退回D001", "orange"),
        ]),
        match_order=[
            ("精簡SKU ND轉出", "精簡SKU接收"),
            ("精簡SKU RF轉出", "精簡SKU接收"),
            ("精簡SKU ND/RF轉出", "退回D001"),
        ],
        scenario_table=_scenario_table(
            ["店舖", "類型", "Net Stock", "Safety", "過去2個月銷量", "Cap", "角色"],
            [
                ["HA001", "ND", "10", "-", "-", "-", "精簡SKU ND轉出(-10)"],
                ["HD001", "RF", "20", "4", "3", "8", "精簡SKU RF轉出(-12)"],
                ["HD002", "RF", "3", "4", "5", "10", "精簡SKU接收(+7)"],
                ["D001", "-", "-", "-", "-", "-", "退回D001(+15)"],
            ]
        ),
        extra_notes="精簡SKU 模式的 Cap = Max(Safety&#215;2, Last2Month&#215;2)。最少 2 件起轉。僅同 OM",
        diff_table=_scenario_table(
            ["對比項", "限同OM", "跨OM"],
            [
                ["配對範圍", "同OM", "跨OM"],
                ["Windy限制", "N/A", "Windy只到Windy"],
                ["HD限制", "N/A", "HD不可到HA/HB/HC"],
                ["退回D001", "是", "是"],
            ]
        ),
    )

    content_sku_cross = _build_mode_content(
        "精簡SKU(跨OM)", "精簡SKU調貨（跨OM）", "中",
        scenario="精簡SKU 但需要跨 OM 配對",
        source_flow=(
            _flow_row([_flow_node("同精簡SKU(限同OM)轉出", "green")])
            + _flow_arrow("跨OM配對")
            + _flow_row([
                _flow_node("Windy &#10132; 只到 Windy", "orange"),
                _flow_node("HD &#10132; 不可到 HA/HB/HC", "red"),
            ])
        ),
        dest_flow=_flow_row([
            _flow_node("同精簡SKU(限同OM)接收", "purple"),
            _flow_node("剩餘 &#10132; 退回D001", "orange"),
        ]),
        match_order=None,
        scenario_table=None,
        extra_notes="精簡SKU(跨OM) = 精簡SKU(限同OM) + 跨OM + HD/Windy 限制",
        diff_table=None,
    )

    content_sku_return_d001 = _build_mode_content(
        "精簡SKU(退D001)", "精簡SKU全數退回D001", "低",
        scenario="RF店舖存貨上限 = Max(Safety&#215;2, 過去2個月銷量&#215;2)，超出部分轉出；ND店舖全數可轉出。所有轉出的數量一律回退D001，RF僅1件不退回。不進行RF接收配對",
        source_flow=(
            _flow_row([
                _flow_node("ND店舖<br>SaSa Net Stock &gt; 0", "purple"),
                _flow_node("全數轉出", "green"),
            ])
            + _flow_arrow()
            + _flow_row([
                _flow_node("RF店舖<br>Total Available &gt; Cap<br>Cap=Max(Safety&#215;2, 過去2個月銷量&#215;2)", "blue"),
                _flow_node("超出部分轉出", "green"),
            ])
        ),
        dest_flow=_flow_row([
            _flow_node("無配對接收<br>所有轉出數量<br>直接回退D001", "yellow"),
        ]),
        match_order=None,
        scenario_table=_scenario_table(
            ["場景", "來源", "數量", "回退"],
            [
                ["ND店舖有庫存", "ND", "全數庫存", "D001"],
                ["RF店舖超出Cap", "RF", "超出Cap部分", "D001"],
            ]
        ),
        extra_notes="RF僅1件不退回（避免浪費人力），ND不受此限。不進行RF接收配對，每個來源店舖直接產出一行回退D001建議",
        diff_table=_scenario_table(
            ["項目", "精簡SKU(限同OM/跨OM)", "精簡SKU(退D001)"],
            [
                ["RF接收配對", "&#9989; 可配對RF店舖接收", "&#10060; 不配對，全退D001"],
                ["D001回退", "剩餘無法配對才退", "全部直接回退"],
                ["報告欄位", "標準", "新增D001 Receive Qty"],
            ]
        ),
    )

    return [content_nd1, content_nd2, content_nd3, content_sku_om, content_sku_cross, content_sku_return_d001]


def _render_decision_guide():
    st.markdown("### 模式選擇決策指南")
    st.markdown("根據以下問題，快速找到適合你的調貨模式：")

    branches = [
        ("清理無銷售ND庫存？", "D / D2", "orange"),
        ("有Target目標數量？", "F / F2", "purple"),
        ("需強制轉出指定商品？", "E1 / E1b / E2", "red"),
        ("重點補零庫存店舖？", "C / C1 / C2", "blue"),
        ("有Type分類需求？", "B2~B3La系列", "green"),
        ("ND店舖互轉？", "ND1 / ND2 / ND3", "blue"),
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
| SKU精簡僅同OM | 精簡SKU(限同OM) |
| SKU精簡可跨OM | 精簡SKU(跨OM) |
| SKU精簡全退D001不配對 | 精簡SKU(退D001) |
| 僅同OM基礎調貨 | A（保守）/ B（加強） |
""")


def render_tutorial_page():
    _render_global_rules()

    st.markdown("---")
    st.markdown("### 27 種模式教學")
    st.markdown("按業務場景分為 8 組，展開查看詳細教學。")

    _render_group("基礎調貨模式（A / B）", "1", _render_basic_group)
    _render_group("B特別模式（B2 / B2a / B2L / B2La）", "2", _render_b2_group)
    _render_group("B跨OM特別模式（B3 / B3a / B3L / B3La）", "3", _render_b3_group)
    _render_group("重點補0系列（C / C1 / C2）", "4", _render_c_group)
    _render_group("清貨模式（D / D2）", "5", _render_d_group)
    _render_group("強制轉出系列（E1 / E1b / E2）", "6", _render_e_group)
    _render_group("目標優化系列（F / F2 / F3）", "7", _render_f_group)
    _render_group("ND/SKU專項（ND1 / ND2 / ND3 / 精簡SKU）", "8", _render_nd_sku_group)

    st.markdown("---")
    _render_decision_guide()


