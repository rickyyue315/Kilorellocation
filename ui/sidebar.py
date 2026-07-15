"""
側邊欄 UI — 模式選擇、系統資訊、操作指引
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Optional

from config import VERSION
from models.mode import MODE_DESCRIPTIONS
from models.mode_registry import get_ui_options, get_receive_limit_codes
from services.perf_timer import ENABLE_PERF, get_perf_records, clear_perf_records
from ui.mojibake import fix_mojibake_text


_MODE_OPTIONS = get_ui_options()


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
            **二十九模式調貨系統:**
            - ✅ A模式(保守轉貨) / B模式(加強轉貨)
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
            
            1. **上傳 Excel 文件**
               - 點擊瀏覽文件或拖放文件到上傳區域
               - 確保包含所有必需欄位
            
             2. **選擇轉貨模式**
                    - 在側邊欄選擇適合的轉貨模式（A/B/B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/C/C1/C2/D/D2/E1/E1b/E2/F/F2/F3/NST/ND1/ND2/ND3/ND4/精簡SKU(限同OM)/精簡SKU(跨OM)/精簡SKU(退D001))
                - 查看模式說明了解各模式特點
                        - 若選擇 B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/E1/E1b/E2/ND1/ND2/ND3/ND4，可設定「同一SKU下單一出貨店舖配對接收店舖」：優先1間 / 最多2間 / 不限
                       - 若選擇 NST，可設定「HD店舖轉出」及「同一SKU轉出店舖數量上限：10間/20間/不限制」
            
            3. **啟動分析**
               - 點擊「生成調貨建議」按鈕開始處理
               - 系統會自動進行數據驗證和分析
            
            4. **查看結果**
               - 在主頁面查看KPI、調貨建議和統計圖表
               - 展開詳細統計了解更多信息
            
            5. **下載報告**
               - 點擊下載按鈕獲取 Excel 報告
               - 報告包含完整的調貨建議和統計信息
            """)

        st.markdown("---")

        st.markdown("### ⚙️ 選擇轉貨模式")
        transfer_mode = st.radio(
            "選擇轉貨模式",
            _MODE_OPTIONS,
            key='transfer_mode',
            help="選擇適合的調貨模式",
            label_visibility="collapsed"
        )
        transfer_mode = fix_mojibake_text(transfer_mode)
        mode_code = transfer_mode.split(":", 1)[0].strip() if ":" in transfer_mode else transfer_mode.strip()

        b_special_max_receive_sites_per_source: Optional[int] = None
        b_special_receive_site_limit_option = "最多 2 間"

        if mode_code in get_receive_limit_codes():
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
            c1_threshold = st.number_input(
                "C1 補0門檻（補 total_available ≤ N 的店舖）",
                min_value=0, max_value=100, value=1, step=1,
                key='c1_threshold',
                help="設定 C1 模式補0門檻：只補充總庫存（SaSa Net Stock + Pending Received）小於或等於此值的店舖。預設值 1 等同原有行為。"
            )
        else:
            st.session_state.pop('c1_threshold', None)
        if mode_code in ("C", "C1", "C2"):
            c1_ceiling = st.slider(
                "每店轉出件數上限",
                min_value=3, max_value=10, value=3, step=1,
                key='c1_ceiling',
                help="限制 C/C1/C2 模式每間源店最多轉出的件數。提高此值可減少調出店舖總數量。預設 3 等同原有行為。"
            )
        else:
            st.session_state.pop('c1_ceiling', None)

        st.caption(MODE_DESCRIPTIONS.get(transfer_mode, ""))

        with st.expander("📋 詳細模式說明", expanded=False):
            st.markdown("""
            ### 轉貨模式詳解
            
            **A模式(保守轉貨)**
            - 轉出後剩餘庫存不低於安全庫存
            - 轉出類型為RF過剩轉出
            - 適合保守型調貨策略
            - 單件自動上調：若可轉量=1且轉出後仍餘≥3件，上調至2件（放寬Safety Stock -1）
            
            **B模式(加強轉貨)**
            - 轉出後剩餘庫存可能低於安全庫存
            - 轉出類型為RF加強轉出
            - 更積極地處理滯銷品
            
            **B2模式(附加B特別模式)**
            - ND店舖全轉出
            - Type=L在銷量≤2時全轉出(含RF),若銷量>2則回到B模式
            - 其餘RF依B模式規則
            - Mix店舖若總銷量高於目標店則不可出貨（總銷量=Last Month Sold Qty+MTD Sold Qty）
            - 接收端依遊客區/混合型店舖優先級排序
            - 接收上限為Safety Stock的2倍
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

            **B2L模式(附加B2L特別模式)**
            - 參照B2模式,差異僅在 Type=L 特例
            - Type=L在銷量≤2時不再全轉出,改為保留2件（可轉出=max(淨庫存-2,0)）
            - 若 Type=L 淨庫存≤2，則不轉出
            - Mix店舖若總銷量高於目標店則不可出貨（總銷量=Last Month Sold Qty+MTD Sold Qty）
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限
            
            **B3模式(附加B跨OM特別模式)**
            - 參照B2,但允許跨OM配對
            - 同樣套用Mix店舖總銷量保護規則（總銷量=Last Month Sold Qty+MTD Sold Qty）
            - HD不能轉到HA/HB/HC
            - Windy轉出只能到Windy,Windy可接收其他OM
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

            **B2a模式(附加B2a特別模式)**
            - 參照B2模式
            - 新增限制：Type=T(遊客鋪)不可出貨
            - 同樣套用Mix店舖總銷量保護規則（總銷量=Last Month Sold Qty+MTD Sold Qty）
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

            **B3a模式(附加B3a跨OM特別模式)**
            - 參照B3模式
            - 新增限制：Type=T(遊客鋪)不可出貨
            - 同樣套用Mix店舖總銷量保護規則（總銷量=Last Month Sold Qty+MTD Sold Qty）
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

            **B2La模式(附加B2La特別模式)**
            - 參照B2L模式
            - 新增限制：Type=T(遊客鋪)不可出貨
            - Type=L低銷量維持保留2件規則

            **B3L模式(附加B3L跨OM特別模式)**
            - 參照B3模式,差異僅在 Type=L 特例
            - Type=L在銷量≤2時保留2件（可轉出=max(淨庫存-2,0)）
            - 保留B3跨OM規則（HD限制、Windy限制）

            **B3La模式(附加B3La跨OM特別模式)**
            - 參照B3L模式
            - 新增限制：Type=T(遊客鋪)不可出貨
            
            **C模式(重點補0)**
            - 主要針對接收店舖
            - 當(SaSa Net Stock+Pending Received)≤1時
            - 補充至該店舖的Safety或MOQ+1的數量(取最低值)
            
            **C1模式(重點補0-只補0/1(或自選數量))**
            - 參照C模式，但**僅處理total_available≤N的店舖**（N可於側邊欄設定）
            - 不回落到一般缺貨補貨（緊急缺貨、潛在缺貨）
            - 轉出門檻：淨庫存必須>2才可轉出
            - 轉出量下限：至少2件才參與配對
            - 每店轉出上限可調（3~10件，預設3），提高上限可減少調出店舖總數
            - 優先使用可轉量較大的來源（減少拆單）
            
            **C2模式(附加C跨OM重點補0)**
            - 參照C模式的轉出/接收邏輯
            - 允許跨OM配對
            - HD不能轉到HA/HB/HC
            - Windy轉出只能到Windy,Windy可接收其他OM
            
            **D模式(清貨轉貨)**
            - 針對ND類型且無銷售記錄的店舖進行清貨
            - 避免1件餘貨,確保轉出後剩餘庫存為0件或≥2件
            - 轉出類型為ND清貨轉出
            - RF店舖亦可作為過剩轉出源(沿用A模式規則)
            
            **D2模式(清貨轉貨ND限定)**
            - 按照D模式邏輯,但**僅ND Shop轉出，RF Shop只做接收不做轉出**
            - 僅針對無銷售記錄(Last Month=0且MTD=0)的ND店舖清貨轉出
            - 有銷售記錄的ND店舖不做轉出
            - RF店舖只作為接收方(緊急缺貨/潛在缺貨)
            - 仍限制同一組OM內配對
            - 避免1件餘貨邏輯同D模式
            - 可切換接收策略（三選一）：
              - 「不限店舖數量（原有設定）」：每間ND源可配對任意RF接收店，target_qty正常值
              - 「限制2間店舖接收（原有設定）」：每間ND源最多配對2間RF接收店，target_qty正常值
              - 「限制2間店舖接收（優化版）」：每間ND源最多配對2間RF接收店，target_qty放大至200%
            
            **E1模式(強制轉出)**
            - 針對標記為*ALL*的商品行,全數強制轉出
            - 接收店舖為RF,上限為Safety Stock的2倍
            - **僅同OM配對**,HD不能轉到HA/HB/HC
            - 轉出類型為E模式強制轉出
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

            **E1b模式(強制轉出優先類型接收)**
            - 使用E1模式轉出邏輯:標記為*ALL*的商品行全數強制轉出
            - **僅同OM配對**,HD不能轉到HA/HB/HC
            - 接收店舖為RF,上限為Safety Stock的2倍
            - 接收優先級參照B2:Type=T(遊客區)優先,其次Type=M(混合型)
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限
            
            **E2模式(強制轉出跨OM)**
            - 針對標記為*ALL*的商品行,全數強制轉出
            - 接收店舖為RF,上限為Safety Stock的2倍
            - 優先同OM配對,**可跨OM**,HD不能轉到HA/HB/HC
            - 轉出類型為E模式強制轉出
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限
            
            **F模式(目標優化)**
            - Target欄位填數字作為優先接收目標
            - 其他店舖按C模式補0需求計算
            - 允許跨OM配對,HD不能轉到HA/HB/HC

            **F2模式(F指定模式)**
            - Target欄位填數字作為唯一接收目標
            - 僅Target店舖可接收，非Target RF店舖不參與接收
            - 允許跨OM配對
            - HD轉出選項：預設HD不能轉到HA/HB/HC；可切換為「HD可轉出（最後優先）」，此時HD來源排在最低優先級，僅在其他來源不足時才使用
            - **Windy目標店優先**：若目標店為Windy（有Target），優先從其他無Target的Windy店舖提取；僅在Windy來源不足時才使用非Windy來源

            **F3模式(目標性補0)**
            - 繼承F2全部規則（僅Target接收、HD轉出選項、Windy目標優先）
            - **RF轉出保留2件**：RF店舖轉出後淨庫存不低於2件（net_stock > 2 才可轉出，轉出量=net_stock-2）
            - **RF最高庫存優先**：轉出時最高庫存店舖優先轉出（同優先級內銷量低優先）
            - **RF跨OM不降級**：RF跨OM配對與同OM配對同等優先（無tier懲罰）

            **NST模式(New Shop Target調貨)**
            - 繼承F2全部規則（僅Target接收、HD轉出選項、Windy目標優先）
            - **RF轉出保留≥2件**：RF店舖轉出後淨庫存不低於2件
            - **RF轉出上限75%**：RF店舖轉出量不超過淨庫存的75%（net_stock × 0.75）
            - **庫存<3不轉出**：RF店舖淨庫存少於3件時不參與轉出
            - **同一SKU轉出店數上限**：可設定10間/20間/不限制，控制每SKU最多多少間店舖可同時轉出
            - **目標可能未達100%**：因RF轉出限制，Target目標可能未能完全滿足，此為預期行為
            - 允許跨OM配對，HD轉出選項同F2
            - 配對後剩餘來源會自動填補尚未滿足的目標

            **ND1模式(ND同OM轉貨)**
            - 打破「ND不可接收」全局限制，ND店舖可互相調貨
            - **限制同OM**：轉出與接收店舖須屬同一OM組別
            - 轉出排序：過去2個月銷量=0(Last Month + MTD)優先轉出 → 銷量最低次選 → 最高銷量保護不轉
            - 接收優先級1：RF緊急缺貨(零庫存但有銷售記錄)
            - 接收優先級2：ND潛在缺貨(按過去2個月銷量降序，高銷量優先接收)
            - 接收上限：2×(Last Month Sold Qty + MTD Sold Qty)
            - 過去2個月銷量=0的ND店舖不可接收
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

            **NST模式(New Shop Target調貨)**
            - 繼承F2全部規則（僅Target接收、HD轉出選項、Windy目標優先）
            - **RF轉出保留≥2件**：RF店舖轉出後淨庫存不低於2件
            - **RF轉出上限75%**：RF店舖轉出量不超過淨庫存的75%（net_stock × 0.75）
            - **庫存<3不轉出**：RF店舖淨庫存少於3件時不參與轉出
            - **同一SKU轉出店數上限**：可設定10間/20間/不限制，控制每SKU最多多少間店舖可同時轉出
            - **目標可能未達100%**：因RF轉出限制，Target目標可能未能完全滿足，此為預期行為
            - 允許跨OM配對，HD轉出選項同F2

            **ND2模式(ND混合OM轉貨)**
            - 同ND1模式規則，但允許**跨OM**配對
            - Windy(澳門)轉出只能到Windy店舖
            - HD不能轉到HA/HB/HC
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

            **ND3模式(ND限同OM轉貨-補0)**
            - ND同OM轉貨，參考C1模式，僅針對零庫存ND店舖補貨
            - 轉出保留3件庫存（Net Stock>3才可轉出，轉出量=Net Stock-3）
            - 僅同OM配對，不跨OM
            - 不回落一般缺貨補貨（僅補零庫存ND店）
            - 接收目標：max(Safety Stock×0.5, 3)
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

            **ND4模式(ND限同OM轉貨-補0及有銷售記錄)**
            - 基於ND3架構，接收端僅限有銷售記錄Shop（Last Month Sold Qty + MTD Sold Qty > 0）
            - 無銷售記錄的零庫存ND店不收貨
            - **轉出端優化**：無銷量來源店不保留3件，全數可轉出；有銷量來源店保留3件（與ND3相同）
            - 接收目標：max(Safety Stock×0.5, 3)
            - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

            **精簡SKU(限同OM)模式**
            - RF店舖存貨上限=Max(Safety×2, 過去2個月銷量×2)，超出部分轉出
            - ND店舖全數可轉出
            - 轉給RF店舖最少2件起（參考C1模式）
            - 剩餘無法配對的數量一律退回D001（無數量限制）
            - 僅同OM配對

            **精簡SKU(跨OM)模式**
            - 同精簡SKU(限同OM)規則，但允許跨OM配對
            - Windy轉出只能到Windy店舖
            - HD不能轉到HA/HB/HC
            - 剩餘無法配對的數量一律退回D001
            
            **精簡SKU(退D001)模式**
            - RF店舖存貨上限=Max(Safety×2, 過去2個月銷量×2)，超出部分可轉出
            - ND店舖全數可轉出
            - 所有轉出數量一律退回D001，不進行RF接收配對
            - RF僅1件不回退D001（避免浪費人力），ND不受此限
            - 允許跨OM配對（Windy/HD限制適用）
            
            ### 轉出類型判斷
            
            - **RF過剩轉出**:轉出後剩餘庫存不會低於Safety Stock
            - **RF加強轉出**:轉出後剩餘庫存會低於Safety Stock
            - **ND清貨轉出**:D/D2模式特殊，ND店舖無銷售記錄時
            - **E模式強制轉出**:E1/E1b/E2模式特殊，標記商品強制轉出
            
            ### 接收條件說明
            
            **一般條件:**
            - SaSa Net Stock + Pending Received < Safety Stock 時需要調撥接收
            
            **特殊條件:**
            - C/C2模式：當(SaSa Net Stock+Pending Received)≤1時,補充至Safety或MOQ+1(取最低值)
            - C1模式：僅處理total_available≤N的店舖（N可於側邊欄設定），每店轉出上限可調3~10件，不回落一般缺貨補貨
            - D/D2模式：避免1件餘貨規則(D2僅ND清貨轉出，RF不轉出)
            - E1模式：所有RF店舖可接收,上限為Safety Stock的2倍(僅同OM)
            - E1b模式：所有RF店舖可接收,上限為Safety Stock的2倍(僅同OM，優先Type=T/M)
            - E2模式：所有RF店舖可接收,上限為Safety Stock的2倍(可跨OM)
            - B2/B2a/B2L/B2La/B3/B3a/B3L/B3La模式：接收上限為Safety Stock的2倍,並累計追蹤接收量
            - NST模式：可設定同一SKU轉出店舖數量上限：10間 / 20間 / 不限制
            - ND1/ND2模式：可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限
            - ND3模式：僅零庫存ND店舖可接收，目標=max(Safety×0.5, 3)，轉出店保留3件
            - ND4模式：繼承ND3 + 僅限有銷售記錄Shop接收 + 無銷量來源店不保留3件(全數可轉)
            - 接收優先級(B2/B2a/B2L/B2La/B3/B3a/B3L/B3La):遊客區店舖高銷量 → 混合型店舖高銷量 → 遊客區店舖高Safety → 混合型店舖高Safety
            """)

        st.markdown("---")
        st.caption(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        _render_perf_panel()

    return {
        'mode_code': mode_code,
        'transfer_mode': transfer_mode,
        'b_special_max_receive_sites_per_source': b_special_max_receive_sites_per_source,
        'b_special_receive_site_limit_option': b_special_receive_site_limit_option,
        'f2_allow_hd_transfer': f2_allow_hd_transfer,
        'd2_site_limit_mode': d2_site_limit_mode,
        'c1_threshold': c1_threshold,
        'c1_ceiling': c1_ceiling,
        'f_fulfill_small_first': f_fulfill_small_first,
        'nst_max_source_shops': nst_max_source_shops,
    }
