"""模式教學圖片產生器 — 以純標準庫生成 SVG 邏輯圖。

設計目標（使用者：更容易選對模式）：
- 每個模式一張「邏輯總覽圖」：左＝轉出篩選 → 中＝配對順序 → 右＝接收篩選
- 每個模式一張「情境範例圖」：把 scenario_table 的數字畫成橫條圖
- 頂部一張「30 模式總覽圖」＋一張「決策樹圖」，先選場景再看細節

刻意零第三方依賴（只有 stdlib），避免 requirements 變動；
SVG 以字串回傳，由 ui/tutorial.py 用 st.image 呈現（與 turnday SVG 做法一致）。
"""

import html as _html
import re as _re
from xml.sax.saxutils import escape as _xesc

_FONT = "Inter, Arial, 'Microsoft JhengHei', 'PingFang TC', 'Noto Sans TC', sans-serif"

_RISK_COLOR = {
    "低": "#059669",
    "中": "#D97706",
    "高": "#DC2626",
}
_RISK_BG = {
    "低": "rgba(5,150,105,0.12)",
    "中": "rgba(217,119,6,0.12)",
    "高": "rgba(220,38,38,0.10)",
}


def _plain(value) -> str:
    """把教學 JSON 內的 HTML 片段轉成純文字（一行）。"""
    if value is None:
        return ""
    s = str(value).replace("<br/>", "\n").replace("<br />", "\n").replace("<br>", "\n")
    s = _re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = _re.sub(r"\s+", " ", s).strip()
    return s


def _collect_nodes(flow_data) -> list:
    """從 source_flow / dest_flow 結構中抽出所有 node 文字（保持原順序）。"""
    items: list = []

    def _walk(elems):
        for e in elems or []:
            if not isinstance(e, dict):
                continue
            t = e.get("type")
            if t == "node":
                items.append(_plain(e.get("text", "")))
            elif t == "row":
                _walk(e.get("items", []))
            elif t == "html":
                items.append(_plain(e.get("text", "")))

    _walk(flow_data)
    return [x for x in items if x]


def _wrap(text: str, per_line: int = 15, max_lines: int = 2) -> list:
    """按字數硬換行（中英文混排以字元計），最多 max_lines 行，超長加 …。"""
    s = text.strip()
    if not s:
        return [""]
    lines = [s[i:i + per_line] for i in range(0, len(s), per_line)][:max_lines]
    if len(s) > per_line * max_lines:
        lines[-1] = lines[-1][:-1] + "…"
    return lines


def _short(text: str, n: int = 60) -> str:
    s = text.strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# ── 單模式邏輯總覽圖 ──────────────────────────────────────────────

def build_mode_logic_svg(mode_data: dict) -> str:
    """左轉出 → 中配對 → 右接收，三欄式總覽圖。"""
    code = str(mode_data.get("code", ""))
    name = str(mode_data.get("name", ""))
    risk = str(mode_data.get("risk", "中"))
    scenario = _plain(mode_data.get("scenario", ""))

    src = _collect_nodes(mode_data.get("source_flow", []))[:3]
    dst = _collect_nodes(mode_data.get("dest_flow", []))[:3]
    raw_match = mode_data.get("match_order") or []
    matches: list = []
    for m in raw_match[:4]:
        try:
            a, b = _plain(m[0]), _plain(m[1])
        except (IndexError, TypeError):
            continue
        if a or b:
            matches.append(f"{a} ➜ {b}")
    if not matches:
        matches = ["依通用規則配對"]

    n = max(2, len(src), len(dst), len(matches))
    row_h, panel_top = 64, 108
    panel_h = 40 + n * row_h + 10
    W = 1160
    H = panel_top + panel_h + 54
    risk_c = _RISK_COLOR.get(risk, "#D97706")
    risk_bg = _RISK_BG.get(risk, "rgba(217,119,6,0.12)")

    xs = [24, 404, 784]
    col_w = 352
    panels = [
        ("① 轉出篩選", "#059669", "rgba(5,150,105,0.08)", src, "（無特別轉出限制）"),
        ("② 配對順序", "#D97706", "rgba(217,119,6,0.08)", matches, ""),
        ("③ 接收篩選", "#2563EB", "rgba(37,99,235,0.08)", dst, "（無特別接收限制）"),
    ]

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{_FONT}">']
    p.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="16" fill="#FFFFFF" '
             f'stroke="#E2E8F0" stroke-width="1.5"/>')
    p.append(f'<text x="28" y="40" font-size="19" font-weight="bold" fill="#0F172A">'
             f'{_xesc("模式 " + code + "：" + name)}</text>')
    p.append(f'<rect x="{W - 148}" y="22" width="120" height="30" rx="15" '
             f'fill="{risk_bg}" stroke="{risk_c}" stroke-width="1.5"/>')
    p.append(f'<text x="{W - 88}" y="43" font-size="14" font-weight="bold" '
             f'fill="{risk_c}" text-anchor="middle">{_xesc("風險：" + risk)}</text>')
    p.append(f'<text x="28" y="62" font-size="12.5" fill="#64748B">'
             f'{_xesc("左 → 中 → 右：轉出（綠）➜ 配對（橙）➜ 接收（藍）　　" + _short(scenario, 48))}</text>')

    for (title, color, bg, lines, empty_tip), x in zip(panels, xs):
        p.append(f'<rect x="{x}" y="{panel_top}" width="{col_w}" height="{panel_h}" '
                 f'rx="12" fill="{bg}" stroke="{color}" stroke-width="1.5"/>')
        p.append(f'<rect x="{x + 12}" y="{panel_top + 10}" width="118" height="26" rx="13" '
                 f'fill="{color}"/>')
        p.append(f'<text x="{x + 71}" y="{panel_top + 28}" font-size="13" font-weight="bold" '
                 f'fill="#FFFFFF" text-anchor="middle">{_xesc(title)}</text>')
        shown = lines or ([empty_tip] if empty_tip else [])
        for i in range(n):
            by = panel_top + 46 + i * row_h
            txt = shown[i] if i < len(shown) else ""
            if not txt:
                continue
            is_num = i < len(lines)
            wrapped = _wrap(txt, 21, 3)
            box_h = 56
            p.append(f'<rect x="{x + 12}" y="{by}" width="{col_w - 24}" height="{box_h}" rx="8" '
                     f'fill="#FFFFFF" stroke="{color}" stroke-width="1.2" opacity="1"/>')
            if is_num:
                p.append(f'<circle cx="{x + 32}" cy="{by + box_h // 2}" r="11" fill="{color}"/>')
                p.append(f'<text x="{x + 32}" y="{by + box_h // 2 + 4}" font-size="12" font-weight="bold" '
                         f'fill="#FFFFFF" text-anchor="middle">{i + 1}</text>')
                tx = x + 52
            else:
                tx = x + 28
            base_y = by + 33 if len(wrapped) == 1 else by + 19
            for j, ln in enumerate(wrapped):
                p.append(f'<text x="{tx}" y="{base_y + j * 16}" '
                         f'font-size="12" fill="#0F172A">{_xesc(ln)}</text>')

    for ax in (380, 760):
        p.append(f'<text x="{ax}" y="{panel_top + panel_h // 2}" font-size="30" '
                 f'fill="#94A3B8" text-anchor="middle">➜</text>')

    p.append(f'<line x1="28" y1="{H - 34}" x2="{W - 28}" y2="{H - 34}" '
             f'stroke="#E2E8F0" stroke-width="1.5"/>')
    p.append(f'<text x="28" y="{H - 12}" font-size="12" fill="#64748B">'
             f'{_xesc("適用場景：" + _short(scenario, 64))}</text>')
    p.append("</svg>")
    return "".join(p)


# ── 情境範例圖 ────────────────────────────────────────────────────

def _parse_qty(raw: str) -> int:
    s = _plain(raw)
    if not s or s in ("-", "–", "—", "/", "– ", "- "):
        return 0
    if "不接收" in s or "不處理" in s or "不轉" in s:
        return 0
    nums = _re.findall(r"[-+]?\d+", s)
    if not nums:
        return 0
    if "=" in s:  # 如 min(7, 8)=7 取最後一個（結果值）
        return int(nums[-1])
    try:
        return int(nums[0])
    except ValueError:
        return 0


def build_mode_scenario_svg(mode_data: dict) -> str:
    """把 scenario_table 前 4 列畫成橫條圖；無可用數字時回傳空字串。"""
    table = mode_data.get("scenario_table")
    if not isinstance(table, dict):
        return ""
    headers = [_plain(h) for h in table.get("headers", [])]
    rows = table.get("rows") or []
    if not headers or not rows:
        return ""

    def _find(*keys):
        for i, h in enumerate(headers):
            if any(k in h for k in keys):
                return i
        return None

    qty_idx = _find("調撥量", "轉出量", "調撥", "接收優先")
    if qty_idx is None:
        return ""
    role_idx = _find("角色", "優先", "階段", "說明")
    if role_idx is None:
        role_idx = min(4, len(headers) - 1)
    after_idx = _find("調撥後")
    stock_idx = _find("Net Stock", "庫存", "Target")
    if stock_idx is None:
        stock_idx = 2 if len(headers) > 2 else 0

    use_rows = rows[:3]
    parsed = []
    for r in use_rows:
        get = lambda i: _plain(r[i]) if i is not None and i < len(r) else ""
        shop = get(0) or "—"
        role = get(role_idx)
        qty = _parse_qty(get(qty_idx))
        after = get(after_idx) if after_idx is not None else ""
        stock = get(stock_idx)
        parsed.append((shop, role, qty, after, stock))
    if all(q == 0 for _, _, q, _, _ in parsed):
        return ""

    W = 1160
    n = len(parsed)
    H = 96 + n * 68
    max_abs = max(1, max(abs(q) for _, _, q, _, _ in parsed))

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{_FONT}">']
    p.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="16" fill="#FFFFFF" '
             f'stroke="#E2E8F0" stroke-width="1.5"/>')
    p.append(f'<text x="28" y="36" font-size="16" font-weight="bold" fill="#0F172A">'
             f'{_xesc("情境範例圖解 — " + str(mode_data.get("code", "")))}</text>')
    p.append(f'<text x="28" y="56" font-size="12" fill="#64748B">'
             f'橫條長度按調撥量比例繪製（綠＝轉出　藍＝接收　灰＝不參與）；詳細數字見下方表格</text>')
    p.append(f'<line x1="28" y1="68" x2="{W - 28}" y2="68" stroke="#E2E8F0" stroke-width="1"/>')

    for i, (shop, role, qty, after, stock) in enumerate(parsed):
        y0 = 84 + i * 68
        if "轉出" in role or "強制" in role or "來源" in role:
            color, tag = "#059669", "出"
        elif "接收" in role or "目標" in role or "補" in role:
            color, tag = "#2563EB", "入"
        elif "不" in role:
            color, tag = "#94A3B8", "—"
        else:
            color, tag = ("#059669", "出") if qty < 0 else ("#2563EB", "入") if qty > 0 else ("#94A3B8", "—")
        p.append(f'<rect x="28" y="{y0}" width="170" height="52" rx="8" fill="#F8FAFC" '
                 f'stroke="#E2E8F0" stroke-width="1.2"/>')
        p.append(f'<text x="44" y="{y0 + 21}" font-size="14" font-weight="bold" fill="#0F172A">'
                 f'{_xesc(_short(shop, 12))}</text>')
        p.append(f'<text x="44" y="{y0 + 38}" font-size="11" fill="#64748B">'
                 f'{_xesc(_short(role, 14) + (f" · 現貨{stock}" if stock and stock != "-" else ""))}</text>')
        # 軌道＋橫條
        p.append(f'<rect x="220" y="{y0 + 16}" width="560" height="20" rx="10" fill="#F1F5F9"/>')
        if qty == 0:
            p.append(f'<text x="500" y="{y0 + 31}" font-size="12" fill="#94A3B8" text-anchor="middle">'
                     f'{_xesc("不參與" if "不" in role else "無調撥")}</text>')
        else:
            bar_len = int(30 + 500 * abs(qty) / max_abs)
            bar_len = min(bar_len, 560)
            p.append(f'<rect x="220" y="{y0 + 16}" width="{bar_len}" height="20" rx="10" '
                     f'fill="{color}" opacity="0.85"/>')
            p.append(f'<text x="792" y="{y0 + 31}" font-size="13" font-weight="bold" fill="{color}">'
                     f'{_xesc(tag + " " + str(abs(qty)) + " 件")}</text>')
        if after and after != "-":
            p.append(f'<text x="900" y="{y0 + 31}" font-size="12" fill="#334155">'
                     f'{_xesc("調撥後 " + _short(after, 12))}</text>')
    p.append("</svg>")
    return "".join(p)


# ── 總覽圖＋決策樹圖 ──────────────────────────────────────────────

def build_overview_map_svg(groups: list) -> str:
    """30 模式總覽圖。groups: [(組名, [(code, risk)], 用途, 範圍標籤)]."""
    W = 1160
    top, gapx, gapy = 112, 16, 16
    card_w, card_h = 266, 158
    H = top + 2 * card_h + gapy + 48
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{_FONT}">']
    p.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="16" fill="#FFFFFF" '
             f'stroke="#E2E8F0" stroke-width="1.5"/>')
    p.append(f'<text x="28" y="42" font-size="21" font-weight="bold" fill="#0F172A">'
             f'30 種模式一圖看懂 — 先看場景，再看圖片細節</text>')
    p.append(f'<text x="28" y="66" font-size="13" fill="#64748B">'
             f'下方 8 張卡＝ 8 大場景；卡內 ● 顏色＝風險等級；右下標籤＝可否跨 OM</text>')
    p.append(f'<text x="{W - 28}" y="66" font-size="12" fill="#64748B" text-anchor="end">'
             f'● 低風險　● 中風險　● 高風險</text>')
    for idx, (title, modes, use, scope) in enumerate(groups):
        col, row = idx % 4, idx // 4
        x = 28 + col * (card_w + gapx)
        y = top + row * (card_h + gapy)
        scope_c = "#7C3AED" if "跨" in scope else ("#64748B" if "混合" in scope else "#059669")
        p.append(f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="12" '
                 f'fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1.5"/>')
        p.append(f'<circle cx="{x + 24}" cy="{y + 26}" r="12" fill="#D97706"/>')
        p.append(f'<text x="{x + 24}" y="{y + 31}" font-size="13" font-weight="bold" '
                 f'fill="#FFFFFF" text-anchor="middle">{idx + 1}</text>')
        p.append(f'<text x="{x + 44}" y="{y + 31}" font-size="13.5" font-weight="bold" '
                 f'fill="#0F172A">{_xesc(_short(title, 15))}</text>')
        # 模式代碼橫向流排（● 顏色＝風險），最多 3 行，超出顯示 +N
        cx, cy = x + 18, y + 58
        shown, hidden = 0, 0
        for mcode, mrisk in modes:
            label = _short(mcode, 12)
            w = 16 + len(label) * 12
            if cx + w > x + card_w - 12 and shown:
                cx = x + 18
                cy += 20
                if cy > y + 58 + 2 * 20:
                    hidden = len(modes) - shown
                    break
            dot = _RISK_COLOR.get(mrisk, "#D97706")
            p.append(f'<circle cx="{cx + 4}" cy="{cy - 4}" r="3.5" fill="{dot}"/>')
            p.append(f'<text x="{cx + 12}" y="{cy}" font-size="12" fill="#0F172A">'
                     f'{_xesc(label)}</text>')
            cx += w + 4
            shown += 1
        if hidden:
            p.append(f'<text x="{cx}" y="{cy}" font-size="12" fill="#64748B">+{hidden}…</text>')
        p.append(f'<text x="{x + 16}" y="{y + card_h - 36}" font-size="12" fill="#334155">'
                 f'{_xesc("👉 " + _short(use, 16))}</text>')
        p.append(f'<rect x="{x + card_w - 92}" y="{y + card_h - 34}" width="76" height="22" rx="11" '
                 f'fill="#FFFFFF" stroke="{scope_c}" stroke-width="1.2"/>')
        p.append(f'<text x="{x + card_w - 54}" y="{y + card_h - 18}" font-size="11.5" '
                 f'fill="{scope_c}" text-anchor="middle">{_xesc(scope)}</text>')
    p.append(f'<text x="28" y="{H - 16}" font-size="12" fill="#64748B">'
             f'選法：日常補貨→第1卡　零庫存→第4卡　清死貨→第5卡　強制清空→第6卡　指定目標→第7卡　ND互轉/撤SKU→第8卡</text>')
    p.append("</svg>")
    return "".join(p)


_GLOBAL_RULES = [
    ("1", "ND 店舖限制", "只能做轉出方，不可接收（ND1–ND4 / 有 Target 的 F 系列 ND 除外）",
     "#DC2626", "rgba(220,38,38,0.08)"),
    ("2", "最高動銷店保護", "RF 中有效銷量最高店不會被選為轉出方",
     "#7C3AED", "rgba(124,58,237,0.08)"),
    ("3", "避免雙重角色", "同一 SKU 的轉出店絕不能同時做接收店",
     "#DC2626", "rgba(220,38,38,0.08)"),
    ("4", "單件後處理", "消除 Transfer Qty = 1（優先 Rebalance，其次 Merge）",
     "#D97706", "rgba(217,119,6,0.08)"),
]


def build_global_rules_svg() -> str:
    """全局規則圖：4 條適用所有模式，垂直流程一覽。"""
    W = 1160
    top, row_h = 84, 76
    H = top + len(_GLOBAL_RULES) * row_h + 16
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{_FONT}">']
    p.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="16" fill="#FFFFFF" '
             f'stroke="#E2E8F0" stroke-width="1.5"/>')
    p.append(f'<text x="28" y="40" font-size="19" font-weight="bold" fill="#0F172A">'
             f'{_xesc("全局規則 — 4 條適用全部 30 個模式")}</text>')
    p.append(f'<text x="28" y="62" font-size="12.5" fill="#64748B">'
             f'{_xesc("由上而下：先過濾資格 ➜ 再配對 ➜ 最後整理單件")}</text>')
    for i, (num, title, desc, color, bg) in enumerate(_GLOBAL_RULES):
        y = top + i * row_h
        p.append(f'<rect x="28" y="{y}" width="{W - 56}" height="62" rx="10" '
                 f'fill="{bg}" stroke="{color}" stroke-width="1.5"/>')
        p.append(f'<circle cx="62" cy="{y + 31}" r="13" fill="{color}"/>')
        p.append(f'<text x="62" y="{y + 36}" font-size="13" font-weight="bold" '
                 f'fill="#FFFFFF" text-anchor="middle">{num}</text>')
        p.append(f'<text x="88" y="{y + 36}" font-size="13.5" fill="#0F172A">'
                 f'<tspan font-weight="bold">{_xesc(title)}</tspan>'
                 f'<tspan dx="10" fill="#334155">{_xesc(desc)}</tspan></text>')
        if i < len(_GLOBAL_RULES) - 1:
            p.append(f'<text x="{W // 2}" y="{y + 62 + 12}" font-size="14" '
                     f'fill="#94A3B8" text-anchor="middle">↓</text>')
    p.append("</svg>")
    return "".join(p)


_FLOOR_SAFETY_POINTS = [
    "保底 = 上載檔 Safety Stock",
    "固定值，不隨銷速變化",
    "風險低 · 行為同 v2.31",
]
_FLOOR_TURNDAY_POINTS = [
    "保底 = ceil(日銷速 × N日)",
    "快銷高保底 · 滯銷低保底",
    "零銷量 = 0，可全數轉出",
]


def build_floor_body_svg() -> str:
    """保底主體圖：Safety vs Turnday 雙分支，下接 30 模式。"""
    W = 1160
    y_top_box, top_box_h = 80, 46
    y_panels = 156
    panel_w = 460
    xs = [90, 610]
    row_h = 54
    panel_h = 38 + len(_FLOOR_SAFETY_POINTS) * row_h + 10
    y_bottom = y_panels + panel_h + 36
    H = y_bottom + 52 + 40
    panels = [
        ("Safety 主體", "#059669", "rgba(5,150,105,0.08)", _FLOOR_SAFETY_POINTS),
        ("Turnday 主體", "#7C3AED", "rgba(124,58,237,0.08)", _FLOOR_TURNDAY_POINTS),
    ]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{_FONT}">']
    p.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="16" fill="#FFFFFF" '
             f'stroke="#E2E8F0" stroke-width="1.5"/>')
    p.append(f'<text x="28" y="40" font-size="19" font-weight="bold" fill="#0F172A">'
             f'{_xesc("保底主體 — Safety vs Turnday（可與 30 模式任意組合）")}</text>')
    p.append(f'<text x="28" y="62" font-size="12.5" fill="#64748B">'
             f'{_xesc("先選保底點樣計 ➜ 再選調貨模式；兩者正交組合")}</text>')
    p.append(f'<rect x="380" y="{y_top_box}" width="400" height="{top_box_h}" rx="10" '
             f'fill="rgba(37,99,235,0.08)" stroke="#2563EB" stroke-width="1.5"/>')
    p.append(f'<text x="580" y="{y_top_box + 29}" font-size="13.5" fill="#0F172A" '
             f'text-anchor="middle">{_xesc("上載 Excel ＋ MTD數據日期（T-1）")}</text>')
    p.append(f'<text x="580" y="{y_top_box + top_box_h + 18}" font-size="16" '
             f'fill="#94A3B8" text-anchor="middle">↓</text>')
    for (title, color, bg, points), x in zip(panels, xs):
        p.append(f'<rect x="{x}" y="{y_panels}" width="{panel_w}" height="{panel_h}" '
                 f'rx="12" fill="{bg}" stroke="{color}" stroke-width="1.5"/>')
        p.append(f'<rect x="{x + 12}" y="{y_panels + 8}" width="150" height="26" rx="13" '
                 f'fill="{color}"/>')
        p.append(f'<text x="{x + 87}" y="{y_panels + 26}" font-size="13" font-weight="bold" '
                 f'fill="#FFFFFF" text-anchor="middle">{_xesc(title)}</text>')
        for j, pt in enumerate(points):
            by = y_panels + 42 + j * row_h
            p.append(f'<rect x="{x + 12}" y="{by}" width="{panel_w - 24}" height="44" rx="8" '
                     f'fill="#FFFFFF" stroke="{color}" stroke-width="1.2"/>')
            p.append(f'<circle cx="{x + 32}" cy="{by + 22}" r="4" fill="{color}"/>')
            p.append(f'<text x="{x + 46}" y="{by + 27}" font-size="13" fill="#0F172A">'
                     f'{_xesc(pt)}</text>')
    for ax in (xs[0] + panel_w // 2, xs[1] + panel_w // 2):
        p.append(f'<text x="{ax}" y="{y_panels + panel_h + 24}" font-size="16" '
                 f'fill="#94A3B8" text-anchor="middle">↓</text>')
    p.append(f'<rect x="180" y="{y_bottom}" width="800" height="52" rx="10" '
             f'fill="rgba(217,119,6,0.12)" stroke="#D97706" stroke-width="1.8"/>')
    p.append(f'<text x="580" y="{y_bottom + 32}" font-size="14" font-weight="bold" '
             f'fill="#0F172A" text-anchor="middle">'
             f'{_xesc("所有 Safety 觸點自動切換 ➜ 30 個模式同一套邏輯")}</text>')
    p.append(f'<text x="580" y="{H - 12}" font-size="11.5" fill="#94A3B8" text-anchor="middle">'
             f'{_xesc("固定保底不受主體影響：C1 淨存>2 / F3·NST 保留2件 / ND3·ND4 保留3件 / NST 75%上限")}</text>')
    p.append("</svg>")
    return "".join(p)


_DEFAULT_BRANCHES = [
    ("清理無銷售 ND 庫存？", "D / D2", "#D97706"),
    ("有 Target 目標數量？", "F / F2 / F3 / NST", "#7C3AED"),
    ("需強制轉出指定商品？", "E1 / E1b / E2", "#DC2626"),
    ("重點補零庫存店？", "C / C1 / C2", "#2563EB"),
    ("有 Type 分類需求？", "B2～B3La 系列", "#059669"),
    ("ND 店互轉？", "ND1～ND4", "#2563EB"),
    ("SKU 精簡／退倉？", "精簡SKU 系列", "#059669"),
    ("基礎日常調貨", "A（保守）/ B（加強）", "#64748B"),
]


def build_decision_tree_svg(branches=None) -> str:
    """模式選擇決策樹圖（8 個分支兩排）。"""
    branches = branches or _DEFAULT_BRANCHES
    W = 1160
    card_w, card_h, gapx, gapy = 266, 148, 16, 16
    top = 130
    H = top + 2 * card_h + gapy + 16
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{_FONT}">']
    p.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="16" fill="#FFFFFF" '
             f'stroke="#E2E8F0" stroke-width="1.5"/>')
    p.append(f'<rect x="{W // 2 - 170}" y="20" width="340" height="52" rx="26" '
             f'fill="rgba(217,119,6,0.12)" stroke="#D97706" stroke-width="2"/>')
    p.append(f'<text x="{W // 2}" y="53" font-size="17" font-weight="bold" '
             f'fill="#0F172A" text-anchor="middle">你的調貨需求是什麼？</text>')
    p.append(f'<text x="{W // 2}" y="98" font-size="26" fill="#94A3B8" text-anchor="middle">↓</text>')
    for idx, (q, a, color) in enumerate(branches[:8]):
        col, row = idx % 4, idx // 4
        x = 28 + col * (card_w + gapx)
        y = top + row * (card_h + gapy)
        p.append(f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="12" '
                 f'fill="#FFFFFF" stroke="{color}" stroke-width="1.8"/>')
        p.append(f'<circle cx="{x + 24}" cy="{y + 30}" r="12" fill="{color}"/>')
        p.append(f'<text x="{x + 24}" y="{y + 35}" font-size="13" font-weight="bold" '
                 f'fill="#FFFFFF" text-anchor="middle">{idx + 1}</text>')
        for j, ln in enumerate(_wrap(q, 14, 2)):
            p.append(f'<text x="{x + 44}" y="{y + 26 + j * 18}" font-size="13.5" '
                     f'font-weight="bold" fill="#0F172A">{_xesc(ln)}</text>')
        p.append(f'<line x1="{x + 16}" y1="{y + 66}" x2="{x + card_w - 16}" y2="{y + 66}" '
                 f'stroke="#E2E8F0" stroke-width="1"/>')
        p.append(f'<text x="{x + 16}" y="{y + 92}" font-size="12" fill="#64748B">適合模式</text>')
        for j, ln in enumerate(_wrap(a, 15, 2)):
            p.append(f'<text x="{x + 16}" y="{y + 112 + j * 19}" font-size="13.5" '
                     f'font-weight="bold" fill="{color}">{_xesc(ln)}</text>')
    p.append("</svg>")
    return "".join(p)
