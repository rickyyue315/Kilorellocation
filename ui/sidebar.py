"""
側邊欄 UI — 模式選擇、系統資訊、操作指引
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Optional

from config import (
    VERSION,
    FLOOR_BODY_SAFETY,
    FLOOR_BODY_TURNDAY,
    TURNDAY_DEFAULT_DAYS,
    TURNDAY_MIN_DAYS,
    TURNDAY_MAX_DAYS,
)
from models.mode import MODE_DESCRIPTIONS
from models.mode_registry import (
    get_mode_def_by_code,
    get_receive_limit_codes,
    get_ui_options,
)
from services.perf_timer import ENABLE_PERF, get_perf_records, clear_perf_records
from ui.mode_docs import MODE_DOCS, GENERAL_DOCS
from ui.mojibake import fix_mojibake_text


def _render_perf_panel():
    if not ENABLE_PERF:
        return
    records = get_perf_records()
    if not records:
        return
    with st.expander("⏱ 效能面板", expanded=False):
        total = sum(r['elapsed'] for r in records)
        st.markdown(f"**總耗時：{total:.3f}s**（共 {len(records)} 次呼叫）")
        for r in records:
            st.markdown(f"- `{r['label']}` — {r['elapsed']:.3f}s")
        if st.button("清除效能記錄", key="_clear_perf"):
            clear_perf_records()
            st.rerun()


def _required_columns_hint(mode_code: str) -> str:
    """回傳該模式的必填特殊欄位提示（顯示層用，不影響邏輯）。"""
    must_have = []
    if mode_code in ("B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La", "E1b"):
        must_have.append("Type")
    if mode_code in ("E1", "E1b", "E2"):
        must_have.append("ALL（標記商品）")
    if mode_code in ("F", "F2", "F3", "NST"):
        must_have.append("Target")
    if not must_have:
        return "基本欄位即可（Article / OM / RP Type / Site / 庫存 / 銷量 / MOQ）"
    return "除基本欄位外，另需：" + "、".join(must_have)


def render_sidebar() -> Dict:
    with st.sidebar:
        st.markdown("### 📦 系統資訊")
        st.markdown(f"""
        <div class="surface-card" style="margin-top: -8px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="color:var(--text-muted);font-size:13px;">系統版本</span>
                <span style="color:var(--accent-cyan);font-size:13px;font-weight:700;font-family:'JetBrains Mono',monospace;">{VERSION}</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
                <span style="color:var(--text-muted);font-size:13px;">開發者</span>
                <span style="color:var(--text-primary);font-size:13px;font-weight:600;">Ricky Yue</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("💡 核心功能", expanded=False):
            st.markdown("""
            **三十模式調貨系統:**
            - ✅ A模式(保守轉貨) / A1模式(保守轉貨-不餘存貨1件) / B模式(加強轉貨)
            - ✅ B2模式(附加B特別模式) / B2a模式(B2+T遊客鋪不出貨)
            - ✅ B2L模式(附加B2L:Type=L保留2件) / B2La模式(B2L+T遊客鋪不出貨)
            - ✅ B3模式(附加B跨OM特別模式) / B3a模式(B3+T遊客鋪不出貨)
            - ✅ B3L模式(附加B3L跨OM:Type=L保留2件) / B3La模式(B3L+T遊客鋪不出貨)
            - ✅ C模式(重點補0) / C1模式(重點補0-只補0/1(或自選數量)) / C2模式(附加C跨OM重點補0)
            - ✅ D模式(清貨轉貨) / D2模式(清貨轉貨ND限定)
            - ✅ E1模式(強制轉出) / E1b模式(強制轉出優先類型接收) / E2模式(強制轉出跨OM)
            - ✅ F模式(目標優化) / F2模式(F指定模式) / F3模式(目標性補0) / NST模式(New Shop Target調貨)
            - ✅ ND1模式(ND同OM轉貨) / ND2模式(ND混合OM轉貨) / ND3模式(ND限同OM轉貨-補0) / ND4模式(ND限同OM轉貨-補0及有銷售記錄)
            - ✅ 精簡SKU(限同OM) / 精簡SKU(跨OM) / 精簡SKU(退D001)

            **類型識別與匹配:**
            - ✅ ND/RF類型智慧識別
            - ✅ 優先順序調貨匹配
            - ✅ RF轉出限制控制
            - ✅ 跨OM配對支援(B3/C2/E/F/F2/F3模式，F2/F3 Windy目標店優先同OM提取）

            **特殊功能:**
            - ✅ D模式：避免1件餘貨
            - ✅ E1模式：標記商品強制轉出(僅同OM)
            - ✅ E1b模式：標記商品強制轉出(僅同OM，優先Type=T/M接收)
            - ✅ E2模式：標記商品強制轉出(跨OM)
            - ✅ F模式：Target目標接收優先
            - ✅ F2模式：僅Target店舖可接收，集中優先補貨；Windy目標店優先從同OM無Target店提取
            - ✅ F3模式：同F2 + RF轉出保留2件 + RF按最高庫存優先轉出 + RF跨OM不降級
            - ✅ NST模式：同F2 + RF轉出保留≥2件 + RF轉出上限75%庫存 + 庫存<3不轉出 + 可設定同一SKU轉出店數上限(10/20/不限)
            - ✅ B2/B2a模式：接收端依遊客區/混合型店舖優先排序
            - ✅ B2/B2a/B2L/B2La/B3/B3a/B3L/B3La模式：Mix店舖若總銷量高於目標店，禁止出貨（總銷量=Last Month Sold Qty+MTD Sold Qty）
            - ✅ B2a/B2La/B3a/B3La模式：T遊客鋪不作為出貨來源
            - ✅ B3/B3a/B3L/B3La/C2模式：跨OM配對規則(HD不能轉到HA/HB/HC；Windy轉出只能到Windy)
            - ✅ 所有模式：後處理避免單筆1件調貨（優先Rebalance，其次合並至高銷量目標店）
            **自動化功能:**
            - ✅ 預設店舖資料自動填充(OM、Type)
            - ✅ 統計分析和圖表
            - ✅ Excel格式匯出
            """)

        st.markdown("---")

        with st.expander("🎯 操作指引", expanded=False):
            st.markdown("""
**完整操作流程:**

1. **設定保底主體（步驟 1）**
   - Safety Stock（現行版本）或 Turnday（日銷速×日數）二選一

2. **選擇轉貨模式（步驟 2）**
   - 在「選擇轉貨模式」中選擇適合的轉貨模式（全部 30 個模式一次列出，不分類）
   - 下方會顯示該模式的必填欄位提示與詳解

3. **調整模式參數（步驟 3，如有）**
   - 若選擇 B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/E1/E1b/E2/ND1/ND2/ND3/ND4，可設定「同一SKU下單一出貨店舖配對接收店舖」：優先1間 / 最多2間 / 不限
   - 若選擇 F2/F3/NST，可設定「HD店舖轉出」；F/F2/F3/NST 可勾選「優先滿足小型目標」
   - 若選擇 NST，可設定「同一SKU轉出店舖數量上限：10間/20間/不限制」
   - 若選擇 D2，可設定「接收店舖數量限制」三選一；若選擇 C1，可設定補0門檻；C/C1/C2 可設定每店轉出件數上限

4. **上傳 Excel 並啟動分析**
   - 主頁上傳 Excel，核對 MTD 數據日期（僅 Turnday 主體使用）
   - 點擊「生成調貨建議」按鈕開始處理

5. **查看結果**
   - 在主頁面查看步驟進度、KPI、圖表概覽、調貨建議和統計
   - 可用關鍵字篩選調貨建議表；缺口分析可用模式／角色／狀態篩選

6. **下載報告**
   - 點擊「準備 Excel 報表」生成文件後，再點擊下載按鈕獲取報告
   - 報告包含完整的調貨建議和統計信息
            """)

        st.markdown("---")

        st.markdown('<div class="side-step"><span class="side-step__num">1</span>🛡️ 保底主體</div>', unsafe_allow_html=True)
        st.markdown('<div class="side-hint">與下方調貨模式可任意組合（2 主體 × 30 模式）</div>', unsafe_allow_html=True)
        floor_body_option = st.radio(
            "保底主體（與下方調貨模式可任意組合）",
            ["Safety Stock（現行版本）", "Turnday（日銷速×日數）"],
            index=0,
            key='floor_body_option',
            help="Safety Stock：沿用上載檔案的 Safety Stock 做保底（現行版本，行為不變）。Turnday：以日銷速×自選日數計算保底值取代 Safety Stock，全部模式的 Safety 觸點（轉出保底、缺貨目標、接收上限等）自動切換至 Turnday 基準。"
        )
        if floor_body_option == "Turnday（日銷速×日數）":
            floor_body = FLOOR_BODY_TURNDAY
            turnday_days = st.number_input(
                "Turnday 日數（保底 = 日銷速 × N日）",
                min_value=TURNDAY_MIN_DAYS, max_value=TURNDAY_MAX_DAYS,
                value=TURNDAY_DEFAULT_DAYS, step=1,
                key='turnday_days',
                help="保底庫存 = ceil(日銷速 × 此日數)。日銷速 = (Last Month Sold + MTD Sold) ÷ 覆蓋日數，覆蓋日數由主頁面的「MTD數據日期」計算。零銷量 SKU 保底為 0（可全數轉出）。"
            )
        else:
            floor_body = FLOOR_BODY_SAFETY
            turnday_days = None
            st.session_state.pop('turnday_days', None)

        st.markdown("---")

        st.markdown('<div class="side-step"><span class="side-step__num">2</span>⚙️ 選擇轉貨模式</div>', unsafe_allow_html=True)
        st.markdown('<div class="side-hint">30 個模式一次列出（不分類）；長按捲動瀏覽，下方即時顯示必填欄位與詳解</div>', unsafe_allow_html=True)
        transfer_mode = st.radio(
            "選擇轉貨模式",
            get_ui_options(),
            key='transfer_mode',
            help="選擇適合的調貨模式（全部 30 個模式，不分組）",
            label_visibility="collapsed",
        )
        transfer_mode = fix_mojibake_text(transfer_mode)
        mode_code = transfer_mode.split(":", 1)[0].strip() if ":" in transfer_mode else transfer_mode.strip()

        st.caption(MODE_DESCRIPTIONS.get(transfer_mode, ""))
        st.info(f"📌 必填欄位：{_required_columns_hint(mode_code)}", icon="🧾")

        st.markdown('<div class="side-step"><span class="side-step__num">3</span>🧩 模式參數</div>', unsafe_allow_html=True)
        st.markdown('<div class="side-hint">只顯示目前模式可用的參數；無參數的模式可直接到主頁上傳分析</div>', unsafe_allow_html=True)

        b_special_max_receive_sites_per_source: Optional[int] = None
        b_special_receive_site_limit_option = "最多 2 間"
        _has_mode_params = False

        if mode_code in get_receive_limit_codes():
            _has_mode_params = True
            b_special_receive_site_limit_option = st.radio(
                "出貨店舖配對接收店數限制",
                ["優先 1 間", "最多 2 間", "不限制"],
                index=1,
                key='b_special_receive_site_limit_option',
                help="控制同一SKU下，每個出貨店舖最多可分配到多少個接收店舖（優先1間：盡量只配1間；最多2間；不限制）"
            )
            if b_special_receive_site_limit_option == "優先 1 間":
                b_special_max_receive_sites_per_source = 1
            elif b_special_receive_site_limit_option == "最多 2 間":
                b_special_max_receive_sites_per_source = 2
        else:
            st.session_state.pop('b_special_receive_site_limit_option', None)

        f2_allow_hd_transfer = False
        if mode_code in ("F2", "F3", "NST"):
            _has_mode_params = True
            f2_hd_option = st.radio(
                "HD 店舖轉出設定",
                ["HD 不能轉出（預設）", "HD 可轉出（最後優先）"],
                index=0,
                key='f2_hd_transfer_option',
                help="控制HD店舖是否可轉貨到HA/HB/HC店舖。選擇「可轉出」時，HD來源會排在最低優先級，僅在其他來源不足時才使用。"
            )
            if f2_hd_option == "HD 可轉出（最後優先）":
                f2_allow_hd_transfer = True
        else:
            st.session_state.pop('f2_hd_transfer_option', None)

        f_fulfill_small_first = False
        if mode_code in ("F", "F2", "F3", "NST"):
            _has_mode_params = True
            f_fulfill_small_first = st.checkbox(
                "優先滿足小型目標",
                value=False,
                key='f_fulfill_small_first',
                help="勾選後，需Target的店舖按需求量由小到大排序分配，讓更多小型目標能被完全滿足。預設為大目標優先（現有行為）。"
            )
        else:
            st.session_state.pop('f_fulfill_small_first', None)

        nst_max_source_shops = None
        if mode_code == "NST":
            _has_mode_params = True
            nst_shop_limit_option = st.radio(
                "同一SKU轉出店舖數量上限",
                ["10 間", "20 間", "不限制"],
                index=2,
                key='nst_shop_limit_option',
                help="控制同一SKU最多可由多少間店舖轉出。因NST模式RF每店轉出有75%上限，可能需要多間店舖共同出貨。選擇「不限制」時不套用此限制。"
            )
            if nst_shop_limit_option == "10 間":
                nst_max_source_shops = 10
            elif nst_shop_limit_option == "20 間":
                nst_max_source_shops = 20
        else:
            st.session_state.pop('nst_shop_limit_option', None)

        # ── D2 模式接收店舖數量限制（3選1）─────────────────────────────
        # 選項1「不限店舖數量（原有設定）」：無限制，target_qty 為正常值
        #  - 沿用 identify_destinations_d_mode() + match_general_mode()
        #  - 每個 ND 源可配對任意數量 RF 接收店，每間 RF target_qty 為正常值
        # 選項2「限制2間店舖接收（原有設定）」：限 2 間，target_qty 為正常值
        #  - 沿用 identify_destinations_d_mode() + match_d2_mode()
        #  - 每個 ND 源最多配對 2 間 RF 接收店，每間 RF target_qty 為正常值
        #  - 營運上打包更集中，但接收量無放大
        # 選項3「限制2間店舖接收（優化版）」：限 2 間，target_qty × 2
        #  - 沿用 identify_destinations_d2_mode() + match_d2_mode()
        #  - 每個 ND 源最多配對 2 間 RF 接收店，每間 RF target_qty 放大至 200%
        #  - 補償接收店數量減少對總調貨量的影響
        d2_site_limit_mode = "unlimited"
        if mode_code == "D2":
            _has_mode_params = True
            d2_option = st.radio(
                "接收店舖數量限制",
                ["不限店舖數量（原有設定）", "限制2間店舖接收（原有設定）", "限制2間店舖接收（優化版）"],
                index=0,
                key='d2_site_limit_option',
                help="D2 模式的三種接收策略：1) 不限店舖數量 — 每個 ND 源可配對任意數量 RF 接收店，target_qty 為正常值（原有行為）；2) 限制 2 間（原有設定）— 每個 ND 源最多配對 2 間 RF 接收店，target_qty 為正常值（打包集中但無放大）；3) 限制 2 間（優化版）— 每個 ND 源最多配對 2 間 RF 接收店，target_qty 放大至 200%（補償接收店減少）。"
            )
            if d2_option == "限制2間店舖接收（原有設定）":
                d2_site_limit_mode = "2site_original"
            elif d2_option == "限制2間店舖接收（優化版）":
                d2_site_limit_mode = "2site_optimized"
        else:
            st.session_state.pop('d2_site_limit_option', None)

        c1_threshold = 1
        c1_ceiling = 3
        if mode_code == "C1":
            _has_mode_params = True
            c1_threshold = st.number_input(
                "C1 補0門檻（補 total_available ≤ N 的店舖）",
                min_value=0, max_value=100, value=1, step=1,
                key='c1_threshold',
                help="設定 C1 模式補0門檻：只補充總庫存（SaSa Net Stock + Pending Received）小於或等於此值的店舖。預設值 1 等同原有行為。"
            )
        else:
            st.session_state.pop('c1_threshold', None)
        if mode_code in ("C", "C1", "C2"):
            _has_mode_params = True
            c1_ceiling = st.slider(
                "每店轉出件數上限",
                min_value=3, max_value=10, value=3, step=1,
                key='c1_ceiling',
                help="限制 C/C1/C2 模式每間源店最多轉出的件數。提高此值可減少調出店舖總數量。預設 3 等同原有行為。"
            )
        else:
            st.session_state.pop('c1_ceiling', None)

        if not _has_mode_params:
            st.caption("此模式無額外參數，可直接到主頁上傳分析。")

        _floor_label = "Safety Stock" if floor_body == FLOOR_BODY_SAFETY else f"Turnday×{turnday_days}日"
        _mode_def = get_mode_def_by_code(mode_code)
        _mode_short = _mode_def.name if _mode_def else mode_code
        st.markdown(
            f'<div class="side-summary"><strong>目前選擇</strong><br>'
            f'模式：<strong>{mode_code}</strong>（{_mode_short}）<br>'
            f'保底：{_floor_label}<br>'
            f'欄位：{_required_columns_hint(mode_code)}</div>',
            unsafe_allow_html=True,
        )

        with st.expander(f"📋 目前模式詳解：{mode_code}", expanded=False):
            st.markdown(MODE_DOCS.get(mode_code, "（此模式暫無詳細說明，請參考「📖 模式教學」分頁。）"))
            st.caption("💡 完整 30 個模式的圖例教學，請切換上方「📖 模式教學」分頁。")

        with st.expander("📋 通用規則（轉出類型／接收條件）", expanded=False):
            st.markdown(GENERAL_DOCS)

        st.markdown("---")
        st.caption(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        _render_perf_panel()

    return {
        'mode_code': mode_code,
        'transfer_mode': transfer_mode,
        'floor_body': floor_body,
        'floor_body_option': floor_body_option,
        'turnday_days': turnday_days,
        'b_special_max_receive_sites_per_source': b_special_max_receive_sites_per_source,
        'b_special_receive_site_limit_option': b_special_receive_site_limit_option,
        'f2_allow_hd_transfer': f2_allow_hd_transfer,
        'd2_site_limit_mode': d2_site_limit_mode,
        'c1_threshold': c1_threshold,
        'c1_ceiling': c1_ceiling,
        'f_fulfill_small_first': f_fulfill_small_first,
        'nst_max_source_shops': nst_max_source_shops,
    }
