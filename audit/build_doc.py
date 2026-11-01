"""
產生「30 模式邏輯審查」HTML + Markdown。
資料來源：audit/mode_spec.py（人工核對）+ audit/scenarios.py（真實執行）
"""
from __future__ import annotations

import hashlib
import html
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mode_spec as MS  # noqa: E402
import scenarios as SC  # noqa: E402

VERSION = "v2.38.5"
TODAY = date(2026, 11, 1).isoformat()
OUT_DIR = Path(__file__).resolve().parents[1] / "docs"
OUT_HTML = OUT_DIR / "KiLo_30模式邏輯審查.html"
OUT_MD = OUT_DIR / "KiLo_30模式邏輯審查.md"

E = html.escape
RISK_CLASS = {"低": "r-low", "低中": "r-midlow", "中": "r-mid", "中高": "r-highmid", "高": "r-high"}


def tint(hex_color: str, alpha: str = "14") -> str:
    return hex_color + alpha


# ────────────────────────────── SVG helpers ──────────────────────────────
def svg_text(lines, x, y, size=13, lh=22, weight=400, fill="#334155", anchor="start"):
    out = [f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">']
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else lh
        out.append(f'<tspan x="{x}" dy="{dy}">{E(line)}</tspan>')
    out.append("</text>")
    return "".join(out)


def svg_pipeline() -> str:
    stages = [
        ("1", "Excel 上載", ["Article / Site / 庫存", "銷量 / Safety / MOQ"], "#475569"),
        ("2", "前處理", ["型別、缺值、異常", "補 OM / Type"], "#475569"),
        ("3", "保底主體", ["Safety Stock", "或 Turnday × N 日"], "#0f766e"),
        ("4", "分組", ["同 OM：Article+OM", "跨 OM：Article"], "#7c3aed"),
        ("5", "來源識別", ["RP Type / 銷量", "Safety / 標記"], "#2563eb"),
        ("6", "接收識別", ["缺貨 / 補 0 / Target", "上限 / 排序"], "#d97706"),
        ("7", "配對", ["回合次序", "上限 / 鎖定"], "#dc2626"),
        ("8", "後處理輸出", ["單件合併 / 優先級", "Excel / 缺口"], "#0891b2"),
    ]
    parts = ['<svg viewBox="0 0 1100 330" role="img" aria-label="調貨流程圖">']
    parts.append('<defs><marker id="arrowP" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#94a3b8"/></marker></defs>')
    for i, (num, title, subs, color) in enumerate(stages):
        col = i % 4
        row = i // 4
        x = 24 + col * 268
        y = 24 + row * 160
        parts.append(f'<rect x="{x}" y="{y}" width="240" height="118" rx="12" fill="#ffffff" stroke="#e2e8f0"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="6" height="118" rx="3" fill="{color}"/>')
        parts.append(f'<circle cx="{x+28}" cy="{y+26}" r="13" fill="{tint(color, "1f")}"/>')
        parts.append(svg_text([num], x + 28, y + 31, 12, 0, 700, color, "middle"))
        parts.append(svg_text([title], x + 50, y + 31, 15, 0, 700, "#0f172a"))
        parts.append(svg_text(subs, x + 20, y + 62, 12, 20, 400, "#64748b"))
        if col < 3:
            ax1, ax2, ay = x + 240, x + 262, y + 59
            parts.append(f'<line x1="{ax1}" y1="{ay}" x2="{ax2}" y2="{ay}" stroke="#94a3b8" stroke-width="1.6" marker-end="url(#arrowP)"/>')
        if i == 3:
            parts.append(f'<path d="M{x+120},{y+118} V{y+136} H144 V{y+160}" fill="none" stroke="#94a3b8" stroke-width="1.6" marker-end="url(#arrowP)"/>')
    parts.append('<rect x="24" y="318" width="1052" height="1" fill="#e2e8f0"/>')
    parts.append("</svg>")
    return "".join(parts)


def svg_decision_tree() -> str:
    branches = [
        ("有 ALL 標記？", "指定貨品強制離開來源，不理 Safety、銷量", ["E1", "E1b", "E2"], "e"),
        ("有 Target？", "指定店舖優先補貨；Target 是追加量，不是補至量", ["F", "F2", "F3", "NST"], "f"),
        ("只補 0 / 極低庫存？", "先救幾乎無貨的店，每店少量補", ["C", "C1", "C2"], "c"),
        ("清 ND 死貨？", "ND 貨清往同 OM 的 RF 缺貨店", ["D", "D2"], "d"),
        ("ND 互相補貨？", "打破「ND 不可接收」，按銷量或補 0 分配", ["ND1", "ND2", "ND3", "ND4"], "nd"),
        ("常規加減 / 壓存貨？", "按 Safety 加減，或按 Cap 壓存貨", ["A", "A1", "B", "B2 家族", "B3 家族", "精簡 SKU"], "basic"),
    ]
    parts = ['<svg viewBox="0 0 1100 700" role="img" aria-label="模式決策索引">']
    parts.append('<defs><marker id="arrowT" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#cbd5e1"/></marker></defs>')
    # root
    parts.append('<rect x="24" y="286" width="238" height="118" rx="14" fill="#0f172a"/>')
    parts.append(svg_text(["先問：這批貨的", "「目的」是甚麼？"], 143, 334, 15, 28, 700, "#ffffff", "middle"))
    parts.append(svg_text(["6 個分支，按目的分流"], 143, 388, 11, 0, 400, "#94a3b8", "middle"))
    # bus
    parts.append('<path d="M262,345 H292 V72" fill="none" stroke="#cbd5e1" stroke-width="2"/>')
    parts.append('<path d="M292,72 V612" fill="none" stroke="#cbd5e1" stroke-width="2"/>')
    for i, (cond, sub, modes, fam) in enumerate(branches):
        color = MS.FAMILIES[fam]["color"]
        y = 26 + i * 108
        parts.append(f'<path d="M292,{y+46} H318" fill="none" stroke="#cbd5e1" stroke-width="2" marker-end="url(#arrowT)"/>')
        parts.append(f'<rect x="320" y="{y}" width="756" height="92" rx="12" fill="#ffffff" stroke="#e2e8f0"/>')
        parts.append(f'<rect x="320" y="{y}" width="5" height="92" rx="2.5" fill="{color}"/>')
        parts.append(svg_text([cond], 344, y + 32, 15, 0, 700, "#0f172a"))
        parts.append(svg_text([sub], 344, y + 56, 11.5, 0, 400, "#64748b"))
        # chips right side
        chip_x, chip_y = 720, y + 32
        for m in modes:
            w = 24 + len(m) * 7 if not any("\u4e00" <= ch <= "\u9fff" for ch in m) else 30 + len(m) * 7
            if chip_x + w > 1062:
                chip_x, chip_y = 720, chip_y + 34
            parts.append(f'<rect x="{chip_x}" y="{chip_y}" width="{w}" height="28" rx="14" fill="{tint(color, "14")}" stroke="{tint(color, "40")}"/>')
            parts.append(svg_text([m], chip_x + w / 2, chip_y + 19, 12, 0, 700, color, "middle"))
            chip_x += w + 7
    parts.append("</svg>")
    return "".join(parts)


def mode_flow_svg(mode: dict) -> str:
    fam = MS.FAMILIES[mode["family"]]
    color = fam["color"]
    flow = mode["flow"]
    steps = [
        ("STEP 1", "來源門檻", flow["src"]),
        ("STEP 2", "可轉量", flow["qty"]),
        ("STEP 3", "配對次序", flow["match"]),
        ("STEP 4", "接收門檻", flow["dest"]),
    ]
    mid = "arrowM-" + hashlib.md5(mode["code"].encode("utf-8")).hexdigest()[:8]
    parts = ['<svg viewBox="0 0 1100 262" role="img" aria-label="模式流程圖">']
    parts.append(f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#94a3b8"/></marker></defs>')
    for i, (step, title, lines) in enumerate(steps):
        x = 18 + i * 272
        y = 30
        parts.append(f'<rect x="{x}" y="{y}" width="240" height="158" rx="12" fill="#ffffff" stroke="#e2e8f0"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="240" height="4" rx="2" fill="{color}"/>')
        parts.append(svg_text([step], x + 16, y + 24, 10, 0, 700, "#94a3b8"))
        parts.append(svg_text([title], x + 16, y + 46, 14, 0, 700, "#0f172a"))
        parts.append(svg_text(lines[:4], x + 16, y + 74, 12.5, 21, 400, "#475569"))
        if i < 3:
            ax1 = x + 240
            parts.append(f'<line x1="{ax1}" y1="{y+79}" x2="{ax1+24}" y2="{y+79}" stroke="#94a3b8" stroke-width="1.6" marker-end="url(#{mid})"/>')
    meta = f'分組：{fam["group"]}　｜　風險：{mode["risk"]}　｜　後處理：{mode["post"][0]}'
    parts.append(f'<rect x="18" y="208" width="1064" height="38" rx="8" fill="{tint(color, "0f")}"/>')
    parts.append(svg_text([meta], 34, 232, 12, 0, 500, "#475569"))
    parts.append("</svg>")
    return "".join(parts)


# ────────────────────────────── data ──────────────────────────────
def load_results():
    out = {}
    for mode in MS.MODES:
        code = mode["code"]
        runs = []
        for key, params in SC.RUNS[code]:
            runs.append(SC.execute(code, key, params))
        out[code] = runs
    return out


RESULTS = load_results()


def fmt_params(params):
    if not params:
        return "—"
    mp = {"c1_threshold": "C1 門檻", "d2_site_limit_mode": "D2 接收店數"}
    return "、".join(f"{mp.get(k, k)}={v}" for k, v in params.items())


def input_table(rows) -> str:
    show_type = any(str(r["Type"]).strip() for r in rows)
    show_target = any(str(r["Target"]).strip() for r in rows)
    show_all = any(str(r["ALL"]).strip() for r in rows)
    show_pending = any(int(r["Pending Received"]) for r in rows)
    head = ["店舖", "RP", "Net"]
    if show_pending:
        head.append("Pending")
    head += ["Safety", "LM+MTD"]
    if show_type:
        head.append("Type")
    if show_target:
        head.append("Target")
    if show_all:
        head.append("ALL")
    out = ['<table class="tbl input-tbl"><thead><tr>']
    out += [f"<th>{h}</th>" for h in head]
    out.append("</tr></thead><tbody>")
    for r in rows:
        cells = [f"<td class='site'>{E(str(r['Site']))}</td>", f"<td>{E(str(r['RP Type']))}</td>",
                 f"<td class='n'>{int(r['SaSa Net Stock'])}</td>"]
        if show_pending:
            cells.append(f"<td class='n'>{int(r['Pending Received'])}</td>")
        cells += [f"<td class='n'>{int(r['Safety Stock'])}</td>",
                  f"<td class='n'>{int(r['Last Month Sold Qty'])}+{int(r['MTD Sold Qty'])}</td>"]
        if show_type:
            cells.append(f"<td>{E(str(r['Type']))}</td>")
        if show_target:
            cells.append(f"<td class='n'>{E(str(r['Target']))}</td>")
        if show_all:
            cells.append(f"<td>{E(str(r['ALL']))}</td>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def output_table(recs) -> str:
    if not recs:
        return '<p class="empty">此場景沒有產生任何調貨建議。</p>'
    out = ['<table class="tbl out-tbl"><thead><tr><th>來源</th><th>接收</th><th>件數</th><th>來源類型</th><th>接收類型</th><th>來源轉後</th></tr></thead><tbody>']
    for r in recs:
        out.append(
            "<tr>"
            f"<td class='site'>{E(str(r['Transfer Site']))}</td>"
            f"<td class='site'>{E(str(r['Receive Site']))}</td>"
            f"<td class='n qty'>{int(r['Transfer Qty'])}</td>"
            f"<td class='type'>{E(str(r['Source Type']))}</td>"
            f"<td class='type'>{E(str(r['Destination Type']))}</td>"
            f"<td class='n'>{int(r['After Transfer Stock'])}</td>"
            "</tr>"
        )
    total = sum(int(r["Transfer Qty"]) for r in recs)
    out.append(f"<tr class='total'><td colspan='2'>合計 {len(recs)} 條建議</td><td class='n qty'>{total}</td><td colspan='3'></td></tr>")
    out.append("</tbody></table>")
    return "".join(out)


# ────────────────────────────── findings ──────────────────────────────
FINDINGS = [
    ("高", "B2 / B3 家族", "接收優先級 3–4 永遠不會被配對：零銷量 T／M、Type=L、其他 Type 即使庫存 0 也不會補貨。",
     "配對回合只跑 dest_priority 1–2；模擬「T 零銷量 + L」場景結果為 0 條建議。",
     "文件已補上此限制；確認是否刻意只補高銷量 T／M；若否，加入 P3／P4 回合。"),
    ("高", "D 模式", "原文件說只清無銷量 ND，程式對有銷量的 ND 亦以「ND轉出」全數轉出；只有 D2 才限定無銷量。",
     "模擬 HA302（LM=2）在 D 轉出 5 件，D2 則跳過。",
     "文件已校正（D 全轉、D2 限無銷量）；確認 D 是否應加「只限無銷量」條件。"),
    ("中", "D 模式", "原文件說 RF 來源沿用 A（20%）規則，程式實際走 B 分支（50%、最低 2 件）。",
     "_compute_rf_transferable 的 else 分支；同數據（淨 10、Safety 4）D 出 5、A 出 2。",
     "文件已校正為 B 規則（50%）；若要保持保守，為 D 加獨立上限。"),
    ("中", "C 模式", "補貨目標是 max(Safety×0.5, 3)，不是原文件寫的「Safety 或 MOQ+1」；MOQ 全系統未參與計算。",
     "_dests_general C 分支；全 repo 只在讀檔／輸出使用 MOQ。",
     "文件已校正（max(S×0.5,3)、MOQ 不參與）；確認 MOQ 是否應參與取整。"),
    ("中", "F / F2 / F3", "原上載警告說「ND + Target>0 不會接收」，但程式與 README 都允許 ND Target 接收。",
     "f_mode dest 不篩 RP Type，validate_pair(check_nd_receive=False)；模擬 HA502 收到 3 件。",
     "上載警告已改為說明「ND + Target 會接收」；程式與文件一致。"),
    ("中", "A 模式", "單件上調可令來源剩餘 = Safety−1，Source Type 仍標「RF過剩轉出」。",
     "淨 4、Safety 3 → 轉 2、剩 2；上調後沒有重檢 Safety。",
     "文件已註明 1 件容差；若堅持嚴格保底，上調後重檢。"),
    ("中", "後處理", "單件合併排除 D／D2，D 可輸出 1 件線（同一來源多條線亦不合併）。",
     "post_processing 對 D_FAMILY_MODES 直接 return。",
     "文件已加 D／D2 例外；確認 D 是否也應消除 1 件。"),
    ("低", "精簡SKU(退D001)", "原文件說「允許跨 OM 配對」，實際全數退 D001；原文件又說 ND 不受 1 件限制，程式 ND 1 件同樣不退。",
     "SimplifiedSKUReturnD001Strategy.match 只建 D001 建議；return 迴圈對 RF/ND 的 remaining==1 一律 continue。",
     "文件已校正（不配對、ND 1 件亦不退）；確認 ND 1 件是否應退 D001。"),
    ("低", "備註顯示", "所有 RF 備註的 Safety 顯示為 0（例如「剩8件>Safety(0)」）。",
     "refresh_recommendation_fields 的 source_info 未帶 safety_stock。",
     "補回 safety_stock 欄位。"),
    ("低", "備註顯示", "ND 備註的「近2月銷／上限」、精簡 SKU 的「近2月銷」永遠顯示 0。",
     "dest_info 未帶 total_sales／max_receive_qty；source_info 未帶 last_2_month_sold_qty。",
     "補欄位或改用 rec 上的原始值。"),
    ("低", "資料驗證", "RP Type 無效值（非 ND／RF）沒有被修正為 RF，但 UI 訊息說「已自動修正為 RF」。",
     "convert_data_types 只正規化大寫，無效值原樣保留；後續 == 'RF' 篩選會漏掉該行。",
     "界面訊息已改為「不會修正，會被忽略」；如要真正修正，需改資料層。"),
    ("低", "C1", "強制最少 2 件可令最終庫存超出 target 1 件；品質檢查只比較「累收 ≤ target」，捕捉不到。",
     "例：現有 2、target 3、needed 1 → 強制 2，最終 4。",
     "在 QC 加入「現有 + 累收 ≤ target」檢查。"),
    ("低", "ND4", "後處理 fallback 在找不到合規 Target 時，可能超 target 1 件。",
     "optimize_nd4_avoid_one_remainder 的 fallback 候選未檢查 target。",
     "fallback 亦套用 target 上限。"),
    ("低", "B 模式", "「RF加強轉出」只在 Pending Received > 0 時出現；純淨庫存不會低於 Safety。",
     "base = 總庫存 − Safety，數學上保留 Safety。",
     "文件已補上「只在有在途時出現」；教學亦可加註。"),
    ("待確認", "F2 / F3 / NST", "只要該店任何一個 SKU 有 Target，該店全部 SKU 都不可作來源（全域保護）。",
     "跨 Article 測試：HT801 在 Article 1 有 Target、Article 2 有 20 件存貨；F 可出 5 件，F2/F3/NST 完全不出。",
     "確認是否符合營運預期（單 SKU Target 鎖全店）。"),
]

FINDING_SUMMARY = [
    ("高", "2", "會令部分店舖永遠收不到貨 / 清走有銷情貨（相關文件已校正）"),
    ("中", "5", "文件與程式行為不一致，影響營運預期（文件已校正，程式待確認）"),
    ("低", "7", "顯示、資料驗證與邊界問題（部分文件已校正）"),
    ("待確認", "1", "需要業務拍板的設計選擇（文件已如實描述）"),
]


# ────────────────────────────── HTML pieces ──────────────────────────────
def badge(text, cls):
    return f'<span class="badge {cls}">{E(text)}</span>'


def mode_card(mode, runs, extra="") -> str:
    fam = MS.FAMILIES[mode["family"]]
    color = fam["color"]
    result = runs[0]
    params = result["params"]
    params_txt = fmt_params(params) if params else "—"
    tag_map = {"設計": ("design", "設計"), "邊界": ("edge", "邊界"), "資料": ("data", "資料"),
               "風險": ("risk", "風險"), "高": ("risk", "風險"), "中": ("risk", "風險")}
    limits = "".join(
        f'<li><span class="ltag lt-{tag_map.get(tag, ("design", "設計"))[0]}">{tag_map.get(tag, ("design", "設計"))[1]}</span>{E(text)}</li>'
        for tag, text in mode["limits"]
    )
    rounds = "".join(f"<li><span>{E(a)}</span><b>→</b><span>{E(b)}</span></li>" for a, b in mode["match"])
    src = "".join(f"<li>{E(x)}</li>" for x in mode["source"])
    qty = "".join(f"<li>{E(x)}</li>" for x in mode["qty"])
    dest = "".join(f"<li>{E(x)}</li>" for x in mode["dest"])
    post = "".join(f"<li>{E(x)}</li>" for x in mode["post"])
    inputs = "".join(f'<span class="chip">{E(x)}</span>' for x in mode["inputs"])
    params_chip = f'<span class="chip chip-param">{E(params_txt)}</span>' if params else ""
    return f'''
<article class="mode-card" id="mode-{E(mode["code"])}" style="--accent:{color}">
  <header class="mode-head">
    <div class="mode-code">{E(mode["code"])}</div>
    <div class="mode-title">
      <h3>{E(mode["name"])}</h3>
      <p class="tagline">{E(mode["tagline"])}</p>
    </div>
    <div class="mode-badges">
      {badge("風險 " + mode["risk"], RISK_CLASS.get(mode["risk"], "r-mid"))}
      {badge(fam["group"], "b-group")}
    </div>
  </header>
  <p class="when"><b>何時用</b>　{E(mode["when"])}</p>
  <div class="chips"><span class="chip chip-label">輸入</span>{inputs}{params_chip}</div>
  <div class="flow-wrap">{mode_flow_svg(mode)}</div>
  <div class="rules">
    <div class="rule"><h4>① 來源</h4><ul>{src}</ul></div>
    <div class="rule"><h4>② 可轉量</h4><ul>{qty}</ul></div>
    <div class="rule"><h4>③ 接收</h4><ul>{dest}</ul></div>
    <div class="rule"><h4>④ 配對次序</h4><ol class="rounds">{rounds}</ol></div>
  </div>
  <div class="post-line"><b>後處理</b><ul>{post}</ul></div>
  <div class="example">
    <h4>模擬範例 <span class="ex-meta">（{E(result["scenario"])} 場景{("，" + E(params_txt)) if params else ""}；由真實程式執行）</span></h4>
    <div class="ex-grid">
      <div>{input_table(result["rows"])}</div>
      <div>{output_table(result["recs"])}</div>
    </div>
    <p class="calc"><b>計算</b>　{E(mode["calc"])}</p>
  </div>
  <div class="limits"><h4>不能處理的情景</h4><ul>{limits}</ul></div>
  {extra}
</article>'''


def variant_block(mode, runs) -> str:
    if mode["code"] == "C1" and len(runs) > 1:
        r0, r1 = runs[0], runs[1]
        return f'''
<div class="variant">
  <h4>參數對照：補 0 門檻 N</h4>
  <div class="ex-grid">
    <div><p class="v-label">N = 1（預設）</p>{output_table(r0["recs"])}</div>
    <div><p class="v-label">N = 0（只補零庫存）</p>{output_table(r1["recs"])}</div>
  </div>
  <p class="calc">同一組資料，N=0 時 HA104（total=1）被排除，建議由 2 條減為 1 條。</p>
</div>'''
    if mode["code"] == "D2" and len(runs) >= 4:
        rows = []
        for label, res in [("不限店舖（原有）", runs[1]), ("限 2 間（原有）", runs[2]), ("限 2 間（優化版）", runs[3])]:
            detail = "；".join(f"{r['Receive Site']} {r['Transfer Qty']} 件" for r in res["recs"])
            rows.append(f"<tr><td>{label}</td><td>{detail}</td><td class='n'>{sum(r['Transfer Qty'] for r in res['recs'])}</td></tr>")
        return f'''
<div class="variant">
  <h4>參數對照：接收店數三選一（同一 ND 來源 20 件、3 間各欠 8 件）</h4>
  <table class="tbl"><thead><tr><th>設定</th><th>配對結果</th><th>總轉出</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
  <p class="calc">限 2 間會把貨集中在兩間店；優化版把每間 target 放大 2 倍（8→16），補償店數減少。</p>
</div>'''
    return ""


def family_section(key, modes, results) -> str:
    fam = MS.FAMILIES[key]
    compare = "".join("<tr>" + "".join(f"<td>{E(c)}</td>" for c in row) + "</tr>" for row in fam["compare"][1:])
    head = "".join(f"<th>{E(h)}</th>" for h in fam["compare"][0])
    cards = "".join(mode_card(m, results[m["code"]], variant_block(m, results[m["code"]])) for m in modes)
    return f'''
<section class="family" id="fam-{key}" style="--accent:{fam["color"]}">
  <div class="family-head">
    <div class="family-kicker">{E(fam["en"])}</div>
    <h2>{E(fam["title"])}</h2>
    <p>{E(fam["intro"])}</p>
    <div class="family-meta"><span>分組：{E(fam["group"])}</span><span>模式數：{len(modes)}</span></div>
  </div>
  <table class="tbl compare"><thead><tr>{head}</tr></thead><tbody>{compare}</tbody></table>
  {cards}
</section>'''



def scenario_table():
    rows = [
        ("日常保守補貨，來源不可跌破 Safety", "A", "A1（不想來源剩 1 件）"),
        ("滯銷嚴重，要騰出空間", "B", "B2（ND／L 全轉）"),
        ("只想救零庫存／極低庫存店", "C1", "C（會回落一般缺貨）"),
        ("清走 ND 死貨", "D2", "D（會清有銷量 ND）"),
        ("指定貨品必須離開來源", "E1", "E2（可跨 OM）"),
        ("新店／重點店有 Target", "NST", "F2（較進取）"),
        ("ND 店之間互相補貨", "ND3", "ND4（只補有銷量）"),
        ("整體壓存貨、設上限", "精簡SKU(限同OM)", "跨 OM／退 D001"),
        ("Type=L 要保留 2 件", "B2L", "B3L（跨 OM）"),
        ("遊客鋪不可出貨", "B2a", "B3a（跨 OM）"),
    ]
    body = "".join(f"<tr><td>{E(a)}</td><td><b>{E(b)}</b></td><td>{E(c)}</td></tr>" for a, b, c in rows)
    return ("<table class='tbl'><thead><tr><th>營運情境</th><th>首選</th><th>次選 / 注意</th></tr></thead><tbody>"
            + body + "</tbody></table>")


def summary_table():
    rows = []
    for m in MS.MODES:
        fam = MS.FAMILIES[m["family"]]
        rows.append(
            f"<tr><td><a href='#mode-{E(m['code'])}'><b>{E(m['code'])}</b></a></td>"
            f"<td>{E(m['name'])}</td><td>{E(fam['title'].split('—')[0].strip())}</td>"
            f"<td>{E(fam['group'])}</td><td>{E(m['when'])}</td>"
            f"<td>{badge(m['risk'], RISK_CLASS.get(m['risk'], 'r-mid'))}</td></tr>"
        )
    return ("<table class='tbl summary'><thead><tr><th>模式</th><th>名稱</th><th>家族</th>"
            "<th>分組</th><th>典型用途</th><th>風險</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def findings_table():
    rows = []
    for i, (sev, area, finding, evidence, action) in enumerate(FINDINGS, 1):
        cls = {"高": "f-high", "中": "f-mid", "低": "f-low", "待確認": "f-tbd"}[sev]
        rows.append(
            f"<tr><td class='n'>{i}</td><td><span class='fsev {cls}'>{E(sev)}</span></td>"
            f"<td><b>{E(area)}</b></td><td>{E(finding)}</td><td class='evidence'>{E(evidence)}</td><td>{E(action)}</td></tr>"
        )
    return ("<table class='tbl findings'><thead><tr><th>#</th><th>嚴重度</th><th>範圍</th><th>發現</th>"
            "<th>依據 / 重現</th><th>建議</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def field_matrix():
    rows = []
    for m in MS.MODES:
        code = m["code"]
        need_type = "✓" if m["family"] in ("bspecial", "bcross") or code == "E1b" else ""
        need_target = "✓" if m["family"] == "f" else ""
        need_all = "✓" if m["family"] == "e" else ""
        note = {
            "bspecial": "Type 空白 → 全部 P4 → 0 建議",
            "bcross": "Type 空白 → 全部 P4 → 0 建議",
            "e": "ALL 空白 → 0 建議，不報錯",
            "f": "Target 非數字會被忽略",
        }.get(m["family"], "")
        if code == "精簡SKU(限同OM)" or code == "精簡SKU(跨OM)":
            note = "Last 2 Month Sold Qty 可選；缺失回落 Last Month"
        if code == "精簡SKU(退D001)":
            note = "同上；Supply source 1/4 不退"
        if code == "D2":
            note = "無銷量 ND 才作來源"
        rows.append(f"<tr><td><b>{E(code)}</b></td><td class='c'>✓</td><td class='c'>{need_type}</td>"
                    f"<td class='c'>{need_target}</td><td class='c'>{need_all}</td><td class='muted'>{E(note)}</td></tr>")
    return ("<table class='tbl'><thead><tr><th>模式</th><th>基本欄位</th><th>Type 值</th><th>Target 值</th>"
            "<th>ALL 值</th><th>備註</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def formula_table():
    rows = [
        ("總庫存", "SaSa Net Stock + Pending Received", "所有模式"),
        ("有效銷量", "Last Month Sold Qty + MTD Sold Qty", "最高銷量保護、ND、B2 Mix 保護"),
        ("A / A1 上限", "max(總×20%, 2)；轉後 ≥ Safety（單件上調例外）", "A、A1"),
        ("B 上限", "max(總×50%, 2)", "B、B2/B3 家族的 RF"),
        ("C 上限", "min(int(總×30%), 自訂上限 3–10)，最少 1", "C、C1、C2"),
        ("C1 下限", "可轉 ≥2；接收 needed <2 時強制 2", "C1"),
        ("補 0 目標", "max(Safety×0.5, 3)", "C、C1、C2、F 的 P2、ND3、ND4"),
        ("D 緊急目標", "max(Safety, 2)", "D、D2"),
        ("ND 接收上限", "2 ×（Last Month + MTD）", "ND1、ND2"),
        ("ND3 / ND4 保留", "ND3：保留 3；ND4：有銷量保留 3、無銷量全轉", "ND3、ND4"),
        ("NST RF 上限", "min(int(淨×75%), 淨−2)；淨 ≥3 才出", "NST"),
        ("精簡 SKU Cap", "max(Safety×2, 過去 2 個月銷量×2)", "精簡 SKU ×3"),
        ("D2 優化版", "接收 target ×2", "D2"),
        ("Turnday 保底", "ceil(有效銷量 ÷ 覆蓋日數 × N 日)；零銷量 = 0", "Turnday 主體（全模式）"),
        ("覆蓋日數", "上月日數 + MTD 數據日期日號", "Turnday 主體"),
    ]
    return ("<table class='tbl'><thead><tr><th>項目</th><th>公式 / 規則</th><th>適用</th></tr></thead><tbody>"
            + "".join(f"<tr><td><b>{E(a)}</b></td><td class='formula'>{E(b)}</td><td>{E(c)}</td></tr>" for a, b, c in rows)
            + "</tbody></table>")


def params_table():
    rows = [
        ("B2 / B2a / B2L / B2La / B3 / B3a / B3L / B3La / E1 / E1b / E2 / ND1–ND4",
         "每來源最多配對接收店數", "優先 1 間 / 最多 2 間 / 不限", "限制同一 SKU 的來源分散程度"),
        ("C / C1 / C2", "每店轉出件數上限", "3–10（預設 3）", "提高可減少調出店數，但每店抽更多"),
        ("C1", "補 0 門檻 N", "0–100（預設 1）", "只補 total ≤ N 的店"),
        ("D2", "接收店數", "不限 / 限 2 間 / 限 2 間優化", "優化版 target ×2"),
        ("F / F2 / F3 / NST", "HD 轉出", "不可（預設）/ 可（最後優先）", "只影響 F 系列（NST 另有同名開關）"),
        ("F / F2 / F3 / NST", "優先滿足小型目標", "勾選 / 不勾", "Target 需求由小到大排序"),
        ("NST", "同一 SKU 轉出店數上限", "10 / 20 / 不限", "控制來源分散"),
    ]
    return ("<table class='tbl'><thead><tr><th>模式</th><th>參數</th><th>選項</th><th>作用</th></tr></thead><tbody>"
            + "".join(f"<tr><td>{E(a)}</td><td><b>{E(b)}</b></td><td>{E(c)}</td><td>{E(d)}</td></tr>" for a, b, c, d in rows)
            + "</tbody></table>")


def glossary():
    rows = [
        ("RF / ND", "Retail Floor（門店）／ Non-Display（非陳列點／倉）", "ND 一般只出不入；ND1–4 例外"),
        ("OM", "Operation Manager 區組", "同 OM／跨 OM 是模式最重要的分界"),
        ("Safety Stock", "安全庫存（保底）", "Turnday 主體下會被換成日銷速×日數"),
        ("Pending Received", "在途未收", "計入總庫存，但不可轉出"),
        ("Effective Sold Qty", "有效銷量 = 上月 + MTD", "最高銷量保護、Mix 保護的基準"),
        ("Target", "指定接收量", "F 系列是「追加量」，不是「補至量」"),
        ("Cap", "存貨上限", "精簡 SKU 的 max(Safety×2, 2 月銷×2)"),
        ("P1 / P2", "優先級 1 / 2", "配對回合的先後，不是店舖等級"),
        ("Rebalance", "重新平衡", "後處理把 1 件線併入其他線"),
        ("D001", "中央倉／退回點", "精簡 SKU 的虛擬接收點"),
        ("Turnday", "日銷速 × 日數", "取代 Safety 的保底主體"),
    ]
    return ("<table class='tbl'><thead><tr><th>術語</th><th>英文 / 全稱</th><th>備註</th></tr></thead><tbody>"
            + "".join(f"<tr><td><b>{E(a)}</b></td><td>{E(b)}</td><td>{E(c)}</td></tr>" for a, b, c in rows)
            + "</tbody></table>")


# ────────────────────────────── CSS ──────────────────────────────
CSS = """
:root{
  --ink:#0f172a; --body:#334155; --muted:#64748b; --line:#e2e8f0;
  --bg:#f6f7f9; --card:#ffffff; --accent:#0f766e;
  --r-low:#15803d; --r-midlow:#0f766e; --r-mid:#b45309; --r-highmid:#c2410c; --r-high:#b91c1c;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--body);
  font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei","Hiragino Sans",system-ui,sans-serif;
  font-size:15px;line-height:1.72;-webkit-font-smoothing:antialiased}
a{color:#0f766e;text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:0 28px 80px}
.hero{background:#fff;border-bottom:1px solid var(--line);padding:46px 0 34px;margin-bottom:30px}
.hero .wrap{padding-bottom:0}
.kicker{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:#0f766e;font-weight:700}
h1{font-size:34px;line-height:1.28;margin:10px 0 12px;color:var(--ink);letter-spacing:-.01em}
.sub{font-size:16px;color:var(--muted);max-width:820px;margin:0 0 20px}
.meta{display:flex;flex-wrap:wrap;gap:10px;font-size:13px;color:var(--muted)}
.meta span{background:#f1f5f9;border:1px solid var(--line);padding:5px 12px;border-radius:999px}
.meta b{color:var(--ink)}
.toc{position:fixed;top:0;left:0;width:232px;height:100vh;overflow:auto;padding:28px 18px 40px;
  background:#fff;border-right:1px solid var(--line);font-size:13px;z-index:5}
.toc h5{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#94a3b8;margin:18px 0 8px}
.toc a{display:block;color:#475569;padding:4px 6px;border-radius:6px}
.toc a:hover{background:#f1f5f9;text-decoration:none}
.toc .toc-title{font-weight:800;color:var(--ink);font-size:14px;margin-bottom:14px}
.main{margin-left:232px}
@media(max-width:1100px){.toc{display:none}.main{margin-left:0}}
h2{font-size:25px;color:var(--ink);margin:46px 0 14px;letter-spacing:-.01em}
h3{font-size:19px;color:var(--ink);margin:0}
h4{font-size:13px;color:var(--ink);margin:0 0 8px;letter-spacing:.01em}
p{margin:0 0 12px}
.lede{font-size:16px;color:#475569;max-width:900px}
.box{background:#fff;border:1px solid var(--line);border-radius:14px;padding:22px 24px;margin:18px 0}
.box.accent{border-left:5px solid #0f766e}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:820px){.grid2,.grid3{grid-template-columns:1fr}}
.mini{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.mini b{color:var(--ink)}
.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}
.kpi div{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi strong{display:block;font-size:24px;color:var(--ink);line-height:1.2}
.kpi span{font-size:12px;color:var(--muted)}
.badge{display:inline-block;font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:999px;border:1px solid transparent;white-space:nowrap}
.r-low{background:#ecfdf5;color:var(--r-low);border-color:#a7f3d0}
.r-midlow{background:#f0fdfa;color:var(--r-midlow);border-color:#99f6e4}
.r-mid{background:#fffbeb;color:var(--r-mid);border-color:#fde68a}
.r-highmid{background:#fff7ed;color:var(--r-highmid);border-color:#fed7aa}
.r-high{background:#fef2f2;color:var(--r-high);border-color:#fecaca}
.b-group{background:#f8fafc;color:#64748b;border-color:var(--line)}
.tbl{width:100%;border-collapse:collapse;background:#fff;font-size:13.2px}
.tbl th{background:#f8fafc;color:#475569;text-align:left;font-weight:700;padding:9px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
.tbl td{padding:8px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top}
.tbl tr:last-child td{border-bottom:none}
.tbl .n{text-align:right;font-variant-numeric:tabular-nums}
.tbl .c{text-align:center}
.tbl .muted{color:var(--muted)}
.tbl .site{font-weight:700;color:var(--ink);font-family:"JetBrains Mono",Consolas,monospace;font-size:12.5px}
.tbl .qty{font-weight:800;color:#0f766e}
.tbl .type{font-size:12px;color:#475569}
.tbl .total td{background:#f8fafc;font-weight:700;color:var(--ink)}
.summary td{font-size:12.8px}
.summary td:nth-child(5){color:var(--muted);max-width:330px}
.input-tbl,.out-tbl{font-size:12.6px}
.input-tbl th,.out-tbl th{padding:7px 8px;font-size:11.5px}
.input-tbl td,.out-tbl td{padding:6px 8px}
.family{margin:54px 0 10px;border-top:1px solid var(--line);padding-top:26px}
.family-head .family-kicker{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:800}
.family-head h2{margin:6px 0 10px;color:var(--ink)}
.family-head p{max-width:900px}
.family-meta{display:flex;gap:18px;font-size:12px;color:var(--muted);margin-bottom:14px}
.compare{margin:0 0 26px}
.compare td:first-child{font-weight:700;color:var(--ink);white-space:nowrap}
.mode-card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:24px 26px;margin:24px 0;
  box-shadow:0 1px 2px rgba(15,23,42,.04);scroll-margin-top:20px}
.mode-head{display:flex;gap:16px;align-items:flex-start;border-bottom:1px solid #f1f5f9;padding-bottom:16px}
.mode-code{min-width:64px;height:64px;border-radius:14px;background:var(--accent);color:#fff;display:flex;
  align-items:center;justify-content:center;font-weight:800;font-size:15px;padding:0 10px;text-align:center;line-height:1.2}
.mode-title{flex:1}
.mode-title h3{font-size:22px;margin-bottom:4px}
.tagline{color:var(--muted);font-size:13.5px;margin:0}
.mode-badges{display:flex;flex-direction:column;gap:6px;align-items:flex-end}
.when{margin:14px 0 10px;font-size:13.6px}
.when b{color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 16px}
.chip{font-size:11.5px;background:#f8fafc;border:1px solid var(--line);color:#475569;padding:3px 9px;border-radius:6px}
.chip-label{background:var(--accent);color:#fff;border-color:transparent;font-weight:700}
.chip-param{background:#fffbeb;border-color:#fde68a;color:#92400e}
.flow-wrap{background:#fbfcfd;border:1px solid #f1f5f9;border-radius:12px;padding:8px 6px 2px;margin-bottom:16px}
.flow-wrap svg{width:100%;height:auto;display:block}
.rules{display:grid;grid-template-columns:1.05fr 1.05fr 1fr 1.1fr;gap:16px;margin:8px 0 4px}
@media(max-width:980px){.rules{grid-template-columns:1fr 1fr}}
@media(max-width:640px){.rules{grid-template-columns:1fr}}
.rule{background:#fbfcfd;border:1px solid #f1f5f9;border-radius:10px;padding:12px 14px}
.rule h4{color:var(--accent);font-size:12px;letter-spacing:.04em}
.rule ul{margin:0;padding-left:16px;font-size:12.6px;line-height:1.62}
.rule li{margin:3px 0}
.rounds{list-style:none;margin:0;padding:0;counter-reset:rd}
.rounds li{display:flex;gap:6px;align-items:center;font-size:12px;padding:3px 0;border-bottom:1px dashed #eef2f7}
.rounds li:last-child{border-bottom:none}
.rounds li b{color:#94a3b8;font-weight:400}
.rounds li span:first-child{color:#0f172a;font-weight:600;max-width:46%}
.rounds li span:last-child{color:#475569}
.post-line{font-size:12.3px;color:var(--muted);margin:10px 0 0;border-top:1px solid #f1f5f9;padding-top:10px}
.post-line b{color:var(--ink);margin-right:10px}
.post-line ul{display:inline;margin:0;padding:0;list-style:none}
.post-line li{display:inline}
.post-line li:after{content:" · ";color:#cbd5e1}
.post-line li:last-child:after{content:""}
.example{margin-top:18px;background:#fbfcfd;border:1px solid #f1f5f9;border-radius:12px;padding:16px}
.example h4{font-size:13px;color:var(--ink)}
.ex-meta{font-weight:400;color:var(--muted);font-size:11.5px}
.ex-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}
@media(max-width:880px){.ex-grid{grid-template-columns:1fr}}
.ex-grid .tbl{border:1px solid #eef2f7;border-radius:8px;overflow:hidden}
.calc{font-size:12.8px;background:#fff;border:1px dashed #cbd5e1;border-radius:8px;padding:10px 12px;margin:12px 0 0;color:#334155}
.calc b{color:#0f766e;margin-right:6px}
.limits{margin-top:18px;border-top:1px solid #f1f5f9;padding-top:14px}
.limits ul{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:8px 18px}
@media(max-width:860px){.limits ul{grid-template-columns:1fr}}
.limits li{font-size:12.7px;line-height:1.6;color:#334155}
.ltag{display:inline-block;font-size:10.5px;font-weight:800;padding:1px 6px;border-radius:4px;margin-right:7px;vertical-align:1px}
.lt-design{background:#eff6ff;color:#1d4ed8}
.lt-edge{background:#fffbeb;color:#b45309}
.lt-data{background:#f1f5f9;color:#475569}
.lt-risk{background:#fef2f2;color:#b91c1c}
.variant{margin:14px 0 0;background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px}
.v-label{font-size:12px;font-weight:700;color:var(--ink);margin:0 0 6px}
.findings td{font-size:12.4px}
.findings td:nth-child(4){min-width:260px}
.evidence{color:var(--muted);font-size:11.8px}
.fsev{display:inline-block;font-size:11px;font-weight:800;padding:2px 8px;border-radius:999px;white-space:nowrap}
.f-high{background:#fef2f2;color:#b91c1c}
.f-mid{background:#fffbeb;color:#b45309}
.f-low{background:#f1f5f9;color:#475569}
.f-tbd{background:#eff6ff;color:#1d4ed8}
.note{font-size:12.5px;color:var(--muted);border-left:3px solid #cbd5e1;padding-left:12px;margin:14px 0}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--muted);margin-top:10px}
.legend span{display:flex;align-items:center;gap:6px}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.pipeline-wrap{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 10px;margin:18px 0}
.pipeline-wrap svg{width:100%;height:auto;display:block}
.footer{margin-top:60px;padding-top:22px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}
@media print{
  @page{size:A4 landscape;margin:10mm}
  body{background:#fff;font-size:10.5pt;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .toc{display:none}.main{margin-left:0}
  .wrap{max-width:none;padding:0}
  .hero{padding:10mm 0 6mm}
  .mode-card{break-inside:auto;box-shadow:none;border-color:#d9dee7}
  .mode-head,.when,.chips{break-after:avoid}
  .flow-wrap,.rules,.example,.limits,.variant{break-inside:avoid}
  .family{break-before:page}
  .family:first-of-type{break-before:auto}
  a{color:#0f172a}
}
"""


def build_html() -> str:
    results = RESULTS
    toc_modes = "".join(f'<a href="#mode-{E(m["code"])}">{E(m["code"])}　{E(m["name"])}</a>' for m in MS.MODES)
    families = ""
    for key, fam in MS.FAMILIES.items():
        modes = [m for m in MS.MODES if m["family"] == key]
        families += family_section(key, modes, results)
    findings_summary = "".join(
        f'<div class="mini"><span class="fsev f-{ {"高":"high","中":"mid","低":"low","待確認":"tbd"}[sev] }">{E(sev)}</span>'
        f'<strong style="display:block;font-size:22px;color:#0f172a;margin-top:6px;">{n}</strong>'
        f'<span style="font-size:11.5px;color:#64748b;">{E(desc)}</span></div>'
        for sev, n, desc in FINDING_SUMMARY
    )
    return f"""<!DOCTYPE html>
<html lang="zh-Hant-HK">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KiLo 30 模式邏輯審查 — {VERSION}</title>
<style>{CSS}</style>
</head>
<body>
<nav class="toc">
  <div class="toc-title">KiLo 模式審查</div>
  <a href="#overview">0　一頁看懂</a>
  <a href="#pipeline">1　全局流程</a>
  <a href="#common">2　共通規則</a>
  <a href="#map">3　模式地圖</a>
  <a href="#index">4　30 模式總表</a>
  <h5>家族</h5>
  {''.join(f'<a href="#fam-{k}">{E(v["title"])}</a>' for k, v in MS.FAMILIES.items())}
  <h5>審查</h5>
  <a href="#findings">5　審查發現</a>
  <a href="#appendix">6　附錄</a>
  <h5>模式索引</h5>
  {toc_modes}
</nav>
<div class="main">
<header class="hero"><div class="wrap">
  <div class="kicker">Logic Audit · 30 Modes</div>
  <h1>KiLo 調貨系統：30 模式邏輯審查</h1>
  <p class="sub">逐個模式拆解「來源 → 可轉量 → 配對 → 接收 → 後處理」，附可重跑的模擬範例、不能處理的情景，以及文件與程式之間的落差。香港書面語，關鍵術語保留英文。</p>
  <div class="meta">
    <span>版本 <b>{VERSION}</b></span>
    <span>模式 <b>30</b>　家族 <b>9</b></span>
    <span>保底主體 <b>Safety / Turnday</b></span>
    <span>核對方式 <b>程式碼逐行 + 實際執行</b></span>
    <span>日期 <b>{TODAY}</b></span>
  </div>
</div></header>

<div class="wrap">

<section id="overview">
<h2>0　一頁看懂</h2>
<p class="lede">30 個模式不是 30 套獨立算法，而是同一個五段式管線上的開關組合。先看管線，再看家族，最後才看單一模式，會比較容易發現「為甚麼這個模式會這樣做」。</p>
<div class="pipeline-wrap">{svg_pipeline()}</div>
<div class="grid3">
  <div class="mini"><b>① 兩個保底主體</b><p style="margin:6px 0 0;font-size:12.8px;">Safety Stock（現行）或 Turnday（日銷速 × 日數）。Turnday 會把 Safety 欄換成計算值，其餘 30 個模式不變。</p></div>
  <div class="mini"><b>② 兩種分組</b><p style="margin:6px 0 0;font-size:12.8px;">同 OM 模式按 Article + OM 分組；跨 OM 模式只按 Article 分組，所有 OM 一起競爭來源。</p></div>
  <div class="mini"><b>③ 三種需求</b><p style="margin:6px 0 0;font-size:12.8px;">缺貨（Safety）、補 0（total ≤ 1 或 0）、Target（指定追加量）。模式之間最大的差別是「只認哪一種需求」。</p></div>
</div>
<div class="box accent">
  <h4>如何使用本文件</h4>
  <p style="margin:0;font-size:13.4px;">先用「模式地圖」定位你關心的模式 → 在家族比較表確認它與鄰近模式的分別 → 細讀該模式卡片的四段式流程與模擬範例 → 最後用「不能處理的情景」檢查你的營運場景是否踩到邊界。第 5 節列出 15 條審查發現，可直接當修正清單。</p>
</div>
<div class="box">
  <h4>核對方法與可信度</h4>
  <p style="margin:0 0 8px;font-size:13.2px;">本文件的規則由 <code>models/mode_registry.py</code>、<code>business_logic.py</code>、<code>strategies/*.py</code>、<code>services/*.py</code> 逐行核對；每個模式的示例數字均由 <code>audit/scenarios.py</code> 以真實 <code>TransferLogic</code> 執行後寫入，30 個模式共 35 次執行，品質檢查全部通過（<code>QC: True</code>）。</p>
  <p style="margin:0 0 6px;font-size:12.4px;color:#64748b;">另外就多個高風險邊界做定向測試：A 單件上調、B2 的 P3／P4 接收、C1 門檻與強制 2 件、D 的 1 件線、F 的 ND Target、F2 的全域 Target 保護、ALL=0、ND 1 件退 D001；結果與文中描述一致。</p>
  <p style="margin:0;font-size:12.4px;color:#64748b;">注意：示例使用虛構店舖（HC／HA／HT／HM／HL／HD／KD／KC 開頭）與單一 Article，數字只為展示規則，不代表真實營運結果。</p>
</div>
</section>

<section id="pipeline">
<h2>1　全局流程</h2>
<p>每次分析只跑一個模式。文件上載後，系統先做資料前處理與（可選）Turnday 換算，再按模式分組、識別來源與接收店、逐回合配對，最後做單件合併與優先級分組。</p>
<div class="grid2">
  <div class="box"><h4>輸入前設</h4>
    <ul style="margin:0;padding-left:18px;font-size:13px;">
      <li>Article 必須 1–12 位純數字；系統補零至 12 位。</li>
      <li>同一 Article + Site 只可一行；重複即中止。</li>
      <li>RP Type 只接受 ND／RF；空白行會被丟棄。</li>
      <li>上載上限：本機 50MB；雲端 8MB 與 12 萬行（可設定）。</li>
    </ul>
  </div>
  <div class="box"><h4>輸出</h4>
    <ul style="margin:0;padding-left:18px;font-size:13px;">
      <li>每條建議：來源／接收／件數／來源類型／接收類型／備註。</li>
      <li>優先級：🔴 高（≥100 件、P1、強制、退 D001）／🟡 中（≥30 件、P3、補 0）／🟢 低。</li>
      <li>排序：先按優先級，再按件數降序。</li>
      <li>另附統計、缺口報表、Target 達成分析（F 系列）、ND 清貨分析（D 系列）。</li>
    </ul>
  </div>
</div>
</section>

<section id="common">
<h2>2　共通規則（所有模式都適用）</h2>
<div class="grid2">
  <div class="mini"><b>身份與角色</b>
    <ul style="margin:8px 0 0;padding-left:18px;font-size:12.8px;">
      <li>ND 預設只出不入；例外：ND1–ND4 互轉、F/F2/F3/NST 的 Target ND。</li>
      <li>同一 SKU 的來源店不可同時做接收店。</li>
      <li>RF 最高有效銷量店受保護（部分模式）。</li>
      <li>接收店不能是來源店（dest 已在 transfer_sites 內即跳過）。</li>
    </ul>
  </div>
  <div class="mini"><b>跨 OM 限制</b>
    <ul style="margin:8px 0 0;padding-left:18px;font-size:12.8px;">
      <li>Windy 出貨只可到 Windy；Windy 可接收其他 OM。</li>
      <li>HD 不可轉到 HA／HB／HC。</li>
      <li>F/F2/F3/NST 可把 HD 設為「最後優先」；B3 不設此開關。</li>
      <li>B2／C／D／E1／E1b／ND1／ND3／ND4 不跨 OM。</li>
    </ul>
  </div>
  <div class="mini"><b>數量與上限</b>
    <ul style="margin:8px 0 0;padding-left:18px;font-size:12.8px;">
      <li>所有可轉量都以「淨庫存」封頂，不會轉出 Negative／超賣。</li>
      <li>總庫存 = 淨庫存 + 在途；在途可計入需求／上限，但不可轉出。</li>
      <li>MOQ 只讀入、不參與任何計算。</li>
      <li>不考慮箱規、陳列容量、有效期。</li>
    </ul>
  </div>
  <div class="mini"><b>後處理</b>
    <ul style="margin:8px 0 0;padding-left:18px;font-size:12.8px;">
      <li>同一來源若有多條 1 件線，會嘗試 Rebalance 或合併到高銷量店。</li>
      <li>D／D2 不做單件合併；A1／ND4 另有「來源剩 1 → +1」。</li>
      <li>品質檢查：Article 一致、正整數、累計不超原始庫存／可轉量、來源≠接收、ND 不可收、補 0 不超 target。</li>
      <li>每次分析獨立，不考慮已下達但未完成的調貨。</li>
    </ul>
  </div>
</div>
<div class="box">
  <h4>全局不處理（所有模式共同）</h4>
  <div class="grid3">
    <div class="mini" style="box-shadow:none;"><b>跨 Article</b><p style="margin:4px 0 0;font-size:12.6px;">替代品、組合包、同系列不同色／碼不會互相配對；每個 Article 獨立計算。</p></div>
    <div class="mini" style="box-shadow:none;"><b>包裝與容量</b><p style="margin:4px 0 0;font-size:12.6px;">不按 MOQ、箱規、陳列面、店舖容量或有效期取整。</p></div>
    <div class="mini" style="box-shadow:none;"><b>已下達調貨</b><p style="margin:4px 0 0;font-size:12.6px;">每次分析獨立，不扣減上一次已建議但未完成的數量。</p></div>
    <div class="mini" style="box-shadow:none;"><b>多模式並行</b><p style="margin:4px 0 0;font-size:12.6px;">一次只跑一個模式；模式之間不會自動分配或去重。</p></div>
    <div class="mini" style="box-shadow:none;"><b>營運成本</b><p style="margin:4px 0 0;font-size:12.6px;">不考慮運輸成本、時效、店舖拒收或人手限制。</p></div>
    <div class="mini" style="box-shadow:none;"><b>需求預測</b><p style="margin:4px 0 0;font-size:12.6px;">只用 Last Month + MTD 歷史銷量，不做季節性、推廣或新店爬坡預測。</p></div>
  </div>
</div>
<div class="note">共通規則看似簡單，但「ND 不可收」與「Windy／HD」在不同模式有不同例外；審查單一模式時，請以該卡片的「來源／接收」為準，不要只用這節的概括。</div>
</section>

<section id="map">
<h2>3　模式地圖：先問目的，再選模式</h2>
<p>同一個營運問題往往有 2–4 個模式可用。以下決策樹按「這批貨的目的」分流；如果同時符合多個分支，通常先處理強制（E）與 Target（F），再做補 0（C），最後才做常規加減（A／B）。</p>
<div class="pipeline-wrap">{svg_decision_tree()}</div>
<div class="box" style="margin-top:6px;">
  <h4>情境對照：同一個問題，通常有兩個模式可選</h4>
  {scenario_table()}
  <p class="note" style="margin:10px 0 0;">「首選」是較常用的一方；「次選」是常見替代，兩者的實際差異（上限、跨 OM、接收限制）見對應卡片。最終仍要按第 5 節的發現與營運限制選擇。</p>
</div>
<div class="legend">
  <span><i class="dot" style="background:#dc2626"></i>E 強制</span>
  <span><i class="dot" style="background:#0f766e"></i>F 目標</span>
  <span><i class="dot" style="background:#d97706"></i>C 補 0</span>
  <span><i class="dot" style="background:#b45309"></i>D 清貨</span>
  <span><i class="dot" style="background:#0891b2"></i>ND 互轉</span>
  <span><i class="dot" style="background:#2563eb"></i>A／B 基礎</span>
  <span><i class="dot" style="background:#475569"></i>精簡 SKU</span>
</div>
</section>

<section id="index">
<h2>4　30 模式總表</h2>
<p>按家族排列；點擊模式代號可跳到該卡片。模式名稱按閱讀需要加上空格與全形括號，程式與側邊欄以 code（A、B2、ND3…）為準。風險等級是「對營運的潛在影響」，不是系統穩定性。</p>
{summary_table()}
</section>

{families}

<section id="findings">
<h2>5　審查發現</h2>
<p>以下 15 條是逐行核對與模擬過程中確認的落差、邊界與待確認項。嚴重度以「對營運判斷的影響」衡量，不代表系統會 crash。</p>
<div class="kpi">{findings_summary}</div>
{findings_table()}
<div class="box accent">
  <h4>建議的執整次序</h4>
  <ol style="margin:0;padding-left:20px;font-size:13.2px;">
    <li><b>先確認業務意圖</b>：B2 的 P3／P4 是否刻意只補高銷量店？D 是否應清有銷量 ND？MOQ 是否應參與？這三條會改變模式定位，不宜直接改碼。</li>
    <li><b>再修文件與 UI</b>：D 的 RF 規則、C 的補貨目標、F 的 ND 警告、精簡 SKU 退 D001 的描述、備註的 Safety=0。這些不改邏輯，但直接影響用戶判斷。</li>
    <li><b>最後修邊界</b>：A 的單件上調重檢、C1 超收檢查、ND4 fallback、單件後處理是否涵蓋 D。</li>
  </ol>
</div>
</section>

<section id="appendix">
<h2>6　附錄</h2>
<h3 style="margin-top:22px;">6.1　公式與常數</h3>
{formula_table()}
<h3 style="margin-top:28px;">6.2　模式參數</h3>
{params_table()}
<h3 style="margin-top:28px;">6.3　欄位需求矩陣</h3>
<p style="font-size:13px;">「基本欄位」指 Article／OM／RP Type／Site／SaSa Net Stock／Pending Received／Safety Stock／Last Month Sold Qty／MTD Sold Qty／MOQ。Type／Target／ALL 即使缺失，系統也會自動建空欄，但結果會受影響。</p>
{field_matrix()}
<h3 style="margin-top:28px;">6.4　名詞對照</h3>
{glossary()}
<div class="footer">
  <p>KiLo 庫存調貨建議系統 · 30 模式邏輯審查 · {VERSION} · 產生日期 {TODAY}</p>
  <p>規則來源：<code>business_logic.py</code>、<code>models/mode_registry.py</code>、<code>strategies/</code>、<code>services/</code>。示例重跑：<code>python audit/scenarios.py</code>；文件重建：<code>python audit/build_doc.py</code>。</p>
</div>
</section>

</div>
</div>
</body>
</html>"""


# ────────────────────────────── Markdown ──────────────────────────────
def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("\n", " ") for c in r) + " |")
    return "\n".join(out)


def build_md() -> str:
    lines = [
        f"# KiLo 調貨系統：30 模式邏輯審查（{VERSION}）",
        "",
        f"> 產生日期：{TODAY}　｜　核對方式：程式碼逐行 + 實際執行模擬　｜　30 模式 / 9 家族 / 2 保底主體",
        "",
        "## 0　一頁看懂",
        "",
        "管線：Excel 上載 → 前處理 → 保底主體（Safety / Turnday）→ 分組（Article+OM 或 Article）→ 來源識別 → 接收識別 → 配對 → 後處理輸出。",
        "",
        "三種需求：缺貨（Safety）、補 0（total ≤ 1 或 0）、Target（指定追加量）。模式之間最大的差別是「只認哪一種需求」。",
        "",
        "## 1　共通規則",
        "",
        "- ND 預設只出不入；例外：ND1–ND4 互轉、F/F2/F3/NST 的 Target ND。",
        "- 同一 SKU 的來源店不可同時做接收店；RF 最高有效銷量店受保護（部分模式）。",
        "- Windy 出貨只可到 Windy；HD 不可轉到 HA／HB／HC。",
        "- 所有可轉量以淨庫存封頂；總庫存 = 淨庫存 + 在途；MOQ 不參與計算。",
        "- 後處理只合併同一來源的多條 1 件線；D／D2 不做單件合併。",
        "",
        "## 2　模式總表",
        "",
        md_table(["模式", "名稱", "家族", "分組", "風險"], [
            [m["code"], m["name"], MS.FAMILIES[m["family"]]["title"], MS.FAMILIES[m["family"]]["group"], m["risk"]]
            for m in MS.MODES
        ]),
        "",
    ]
    for key, fam in MS.FAMILIES.items():
        modes = [m for m in MS.MODES if m["family"] == key]
        lines += [f"## {fam['title']}", "", fam["intro"], "",
                  md_table(fam["compare"][0], fam["compare"][1:]), ""]
        for m in modes:
            res = RESULTS[m["code"]][0]
            lines += [f"### {m['code']}　{m['name']}", "", f"*{m['tagline']}*", "",
                      f"**何時用**：{m['when']}", "",
                      f"**輸入**：{'、'.join(m['inputs'])}　**參數**：{fmt_params(res['params'])}", "",
                      "**來源**", ""] + [f"- {x}" for x in m["source"]] + [""] + \
                     ["**可轉量**", ""] + [f"- {x}" for x in m["qty"]] + [""] + \
                     ["**接收**", ""] + [f"- {x}" for x in m["dest"]] + [""] + \
                     ["**配對次序**", ""] + [f"{i}. {a} → {b}" for i, (a, b) in enumerate(m["match"], 1)] + [""] + \
                     ["**後處理**", ""] + [f"- {x}" for x in m["post"]] + [""]
            # example
            rows = res["rows"]
            lines += [f"**模擬範例（{res['scenario']}）**", "",
                      md_table(["店舖", "RP", "Net", "Pending", "Safety", "LM+MTD", "Type", "Target", "ALL"],
                               [[r["Site"], r["RP Type"], r["SaSa Net Stock"], r["Pending Received"], r["Safety Stock"],
                                 f"{r['Last Month Sold Qty']}+{r['MTD Sold Qty']}", r["Type"], r["Target"], r["ALL"]] for r in rows]),
                      ""]
            if res["recs"]:
                lines += [md_table(["來源", "接收", "件數", "來源類型", "接收類型", "來源轉後"],
                                   [[r["Transfer Site"], r["Receive Site"], r["Transfer Qty"], r["Source Type"],
                                     r["Destination Type"], r["After Transfer Stock"]] for r in res["recs"]]), ""]
            else:
                lines += ["（此場景沒有產生任何調貨建議）", ""]
            lines += [f"**計算**：{m['calc']}", "", "**不能處理的情景**", ""]
            lines += [f"- 【{tag}】{text}" for tag, text in m["limits"]] + [""]
    lines += ["## 3　審查發現", "",
              md_table(["#", "嚴重度", "範圍", "發現", "依據 / 重現", "建議"],
                       [[i, sev, area, finding, evidence, action]
                        for i, (sev, area, finding, evidence, action) in enumerate(FINDINGS, 1)]), ""]
    lines += ["## 4　附錄：公式", "",
              md_table(["項目", "公式 / 規則", "適用"], [
                  ["總庫存", "SaSa Net Stock + Pending Received", "所有模式"],
                  ["有效銷量", "Last Month Sold Qty + MTD Sold Qty", "最高銷量保護、ND、Mix 保護"],
                  ["A / A1 上限", "max(總×20%, 2)；轉後 ≥ Safety（單件上調例外）", "A、A1"],
                  ["B 上限", "max(總×50%, 2)", "B、B2/B3 的 RF"],
                  ["C 上限", "min(int(總×30%), 自訂 3–10)，最少 1", "C、C1、C2"],
                  ["補 0 目標", "max(Safety×0.5, 3)", "C、C1、C2、F P2、ND3、ND4"],
                  ["ND 接收上限", "2 ×（Last Month + MTD）", "ND1、ND2"],
                  ["NST RF 上限", "min(int(淨×75%), 淨−2)；淨 ≥3", "NST"],
                  ["精簡 SKU Cap", "max(Safety×2, 過去 2 個月銷量×2)", "精簡 SKU ×3"],
                  ["Turnday", "ceil(有效銷量 ÷ 覆蓋日數 × N)；零銷量 = 0", "Turnday 主體"],
                  ["覆蓋日數", "上月日數 + MTD 日期日號", "Turnday 主體"],
              ]), "",
              "## 5　名詞", "",
              md_table(["術語", "英文 / 全稱", "備註"], [
                  ["RF / ND", "Retail Floor / Non-Display", "ND 一般只出不入；ND1–4 例外"],
                  ["OM", "Operation Manager 區組", "同 OM／跨 OM 是主要分界"],
                  ["Safety Stock", "安全庫存", "Turnday 下會被換算"],
                  ["Pending Received", "在途未收", "計入總庫存但不可轉出"],
                  ["Target", "指定接收量", "F 系列是追加量"],
                  ["Cap", "存貨上限", "精簡 SKU 的 max(Safety×2, 2 月銷×2)"],
                  ["P1 / P2", "優先級", "配對回合先後"],
                  ["D001", "中央倉／退回點", "精簡 SKU 的虛擬接收點"],
              ]), "",
              f"> 本文件由 `audit/build_doc.py` 產生；示例可用 `python audit/scenarios.py` 重跑。"]
    return "\n".join(lines)


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(build_html(), encoding="utf-8")
    OUT_MD.write_text(build_md(), encoding="utf-8")
    print("written:", OUT_HTML, OUT_HTML.stat().st_size)
    print("written:", OUT_MD, OUT_MD.stat().st_size)
