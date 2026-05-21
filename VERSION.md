# 版本更新記錄

## v2.15.0 (2026-05-21)

### 匹配引擎去重與代碼品質優化

#### matching_engine.py 去重
- 提取 `_clamp_target_qty()` 輔助函數，統一 b_special / 重點補0 / d_family 三向 target_qty 限制邏輯（原重複 2 次）
- 提取 `_adjust_d_family_remainder()` 輔助函數，統一 D 系列「避免剩餘1件」調整邏輯（原重複 2 次）
- 提取 `_mark_dest_saturated()` 輔助函數，統一飽和度檢查（原分散於 match_by_priority）
- `compute_transfer_qty` 從 72 行縮減至 ~40 行，消除重複代碼塊

#### can_transfer 冗餘修正
- 修正 B3 模式下跨 OM 檢查重複執行的問題（通用跨 OM 檢查 + B3 專屬檢查 → 改為 if/elif 互斥）

#### prep_temp_lists 統一
- 提取 `prep_temp_lists()` 共用函數至 matching_engine.py
- 消除 8 個策略檔案中重複的 temp_sources/temp_destinations 初始化樣板（b_special、f_mode、e1_mode、e2_mode、nd_mode、c2_mode、simplified_sku、matching_engine）

#### mode_info 快取
- `business_logic.py` 的 `_create_recommendation_note` 每次調用時不再重新建立 mode_info 字典
- 改為在 `__init__` 中預先快取所有 24 種模式的 mode_info（`_mode_info_cache`），查表取代 9 次 `_is_*_mode` 調用

#### 影響範圍
- 純內部重構，無外部 API 變更
- 所有 265 項測試全部通過
- 不影響 Zeabur 或 Streamlit Community Cloud 部署

## v2.14.0 (2026-05-21)

### 模式參數化表 + 效能架構準備

#### 模式註冊表（Mode Registry）
- `models/mode_registry.py`：新增 `ModeDef` dataclass + 24 筆 `MODE_DEFS` + 衍生查詢函式（`get_mode_def`、`get_mode_families`、`get_ui_options`、`get_receive_limit_codes` 等）
- `models/mode.py`：改為從 `mode_registry.py` 衍生（`MODE_NAME_MAP`、`MODE_DESCRIPTIONS`、`RECEIVE_SITE_LIMIT_MODE_CODES`），保持向後兼容匯出
- `ui/sidebar.py`：`_MODE_OPTIONS` 改為 `get_ui_options()` 自動生成，`RECEIVE_SITE_LIMIT_MODE_CODES` 改為 `get_receive_limit_codes()`
- `business_logic.py`：`__init__` 中 24 個 `self.mode_*` 常數改為從 registry 自動 `setattr`；`MODE_FAMILIES`、`_ALL_MODES`、`_CROSS_OM_*`、`_SOURCE_FILTER_MODES` 改為從 registry 衍生
- `business_logic.py`：`identify_sources/destinations` 路由改為 registry 查表；`generate_transfer_recommendations` 策略路由改為 `strategy_key` 查表

#### 效能架構準備
- `services/perf_timer.py`：新增可選計時 decorator，預設關閉（`KILO_PERF_TIMING=1` 才啟用）
- `services/matching_engine.py`：新增架構文檔 docstring（平行化準備說明）
- `business_logic.py`：`generate_transfer_recommendations` 加上 `@perf_timer` 裝飾

#### 測試新增
- `tests/test_mode_registry.py`：25 項測試涵蓋 registry 資料完整性、衍生查詢函式、向後兼容匯出

#### 影響範圍
- 純內部重構，無外部 API 變更
- 所有 268 項測試全部通過（243 既有 + 25 新增）
- 不影響 Zeabur 或 Streamlit Community Cloud 部署
- 新增第 25 種模式時，只需在 `MODE_DEFS` 加 1 筆記錄（+ 新策略類別如需要）

## v2.13.0 (2026-05-21)

### 程式碼重構與測試強化

#### 模組拆分
- `services/target_utils.py`：Target 解析、正規化、ND 衝突偵測等共用函式（從 `app.py` 及 `business_logic.py` 抽出）
- `services/matching_engine.py`：核心配對邏輯（`match_by_priority`、`can_transfer`、`compute_transfer_qty`、`match_general_mode`）從 `business_logic.py` 抽出
- `services/post_processing.py`：後處理邏輯（`optimize_single_piece_transfers`、`refresh_recommendation_fields`、銷量計算）從 `business_logic.py` 抽出
- `business_logic.py` 保留 `TransferLogic` 類別作為 facade，以薄委派（thin delegation）方式呼叫新模組，所有公開 API 不變

#### 測試新增
- `tests/test_data_processor.py`：31 項測試涵蓋 `read_excel_file`、`validate_columns`、`validate_file_format`、`convert_data_types`、`fill_default_store_data`、`handle_missing_values`、`correct_outliers`、`calculate_effective_sold_qty`、`preprocess_data`
- `tests/test_excel_generator.py`：10 項測試涵蓋 `generate_filename`、`_generate_remark`、`generate_excel_file`（回傳格式、雙工作表、空建議、欄位驗證等）

#### 影響範圍
- 純內部重構，無外部 API 變更
- 243 項既有 + 新增測試全部通過
- 不影響 Zeabur 或 Streamlit Community Cloud 部署

## v2.12.0 (2026-05-19)

### 新增模式教學分頁

#### 功能說明
- 新增「模式教學」分頁（`st.tabs`），位於系統頂部「調貨系統」旁邊
- 繁體中文圖例化教學，涵蓋全部 24 種調貨模式
- 無需額外套件，使用 HTML + inline CSS 繪製流程圖

#### 教學內容
- **全局規則**：ND 限制、最高動銷店保護、避免雙重角色、單件後處理（HTML 流程圖）
- **8 組模式教學**（延遲載入，expander 展開時才生成）：
  1. 基礎調貨（A / B）
  2. B 特別模式（B2 / B2a / B2L / B2La）
  3. B 跨 OM 特別模式（B3 / B3a / B3L / B3La）
  4. 重點補 0 系列（C / C1 / C2）
  5. 清貨模式（D / D2）
  6. 強制轉出系列（E1 / E1b / E2）
  7. 目標優化系列（F / F2）
  8. ND/SKU 專項（ND1 / ND2 / 精簡SKU(限同OM) / 精簡SKU(跨OM)）
- 每個模式包含：適用場景、風險等級（低/中/高）、轉出篩選流程圖、接收篩選流程圖、配對優先級、數字情境範例表格、模式對比
- **模式選擇決策指南**：決策流程圖 + 進一步區分表格，幫助使用者根據業務需求選擇模式

#### 效能設計
- 延遲載入（lazy evaluation）：8 組教學內容以函數引用傳入 `st.expander`，僅在展開時才生成 HTML
- 全靜態內容，無數據處理，適合 Zeabur 部署
- 不影響現有調貨系統功能

#### 相關檔案
- [`ui/tutorial.py`](ui/tutorial.py)（新增）— 教學分頁渲染模組
- [`app.py`](app.py) — 新增 `st.tabs(["調貨系統", "模式教學"])` 雙分頁結構
- [`static/styles.css`](static/styles.css) — 新增教學頁面專用 CSS
- [`README.md`](README.md) — 功能重點、介面操作流程、專案結構更新

---

## v2.11.3 (2026-05-19)

### 匹配優先次序優化（P0/P1/P2）

#### 問題描述
經全面分析24種模式的匹配優先次序後，發現以下三個需優化的優先級問題：

##### P0 — C模式重點補0回合過晚（高嚴重性）
C模式的重點補0（零庫存店鋪補充）原本放在第7回合（最後），ND/RF庫存已被前6回合的緊急/潛在缺貨消耗殆盡，導致零庫存店得不到補貨。

##### P1 — B Special Local全轉出優先於RF過剩（中高嚴重性）
B2/B2a/B3/B3a模式中，`Local店舖全轉出`（Type=L低銷量店強制清空）排在第3-4回合，優先於`RF過剩轉出`（第5-6回合），導致激進的全轉出先於保守的RF過剩被執行。

##### P2 — C1模式回合未明確分離（中嚴重性）
C1模式依賴「沒有緊急/潛在缺貨目的地」的巧合來讓RF來源正確匹配重點補0，程式碼意圖不明確，依賴隱式行為。

#### 修改內容

**P0：C模式重點補0提前**（`business_logic.py` `match_transfers()`）
- 新增回合 `0a`：ND轉出 → 重點補0（C模式限定）
- 新增回合 `4a`：RF過剩轉出 → 重點補0（C模式限定）
- 新增回合 `6a`：RF加強轉出 → 重點補0（C模式限定）
- 每個來源層級（ND/RF過剩/RF加強）都先做重點補0，再做緊急缺貨/潛在缺貨
- 刪除舊的第7回合（RF轉出 → 重點補0，無來源類型區分）

**P1：B Special Local全轉出移後**（`strategies/b_special.py`）
- 回合順序變更：`RF過剩轉出` → `Local店舖全轉出` → `RF加強轉出`
- 確保保守的RF過剩先於激進的Local全轉出被使用

**P2：C1模式回合分離**（`business_logic.py` `match_transfers()`）
- 新增回合 `2a`：RF過剩轉出 → 重點補0（C1模式限定，附 `dest_type_filter='重點補0'`）
- 新增回合 `4b`：RF加強轉出 → 重點補0（C1模式限定，附 `dest_type_filter='重點補0'`）
- 確保RF過剩先於RF加強被選中，且未來修改標準回合時C1不受影響

#### 相關檔案
- [`business_logic.py`](business_logic.py) — 匹配回合重組
- [`strategies/b_special.py`](strategies/b_special.py) — Local全轉出移後
- [`調貨模式詳解.txt`](調貨模式詳解.txt) — 匹配優先級順序更新
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md) — 匹配流程更新
- [`README.md`](README.md) — 版本號更新
- [`VERSION.md`](VERSION.md) — 本版本記錄

#### 測試結果
- 137 項測試全部通過（0 失敗）
- 涵蓋所有24個模式的：dual-role防護、接收上限、單件優化、B Special Mix保護等

---

## v2.11.2 (2026-05-19)

### F2 模式 — Windy 目標店優先從同 OM 無 Target 店提取

#### 功能說明
- F2 模式下，當 Windy 目標店（有 Target > 0）需要接收時，優先從其他無 Target 的 Windy 店舖提取
- 僅在 Windy 來源不足時，才回落至非 Windy 來源（Ivy/Eva 等 OM）

#### 程式碼更新
- [`strategies/f_mode.py`](strategies/f_mode.py)
  - `_sort_key` 新增 `windy_penalty=5`：當目的地為 Windy 且來源非 Windy 時加 5，確保 Windy 來源排序於非 Windy 來源之前
- [`tests/test_f2_windy_priority.py`](tests/test_f2_windy_priority.py) (新增)
  - `test_f2_windy_source_prioritized_over_non_windy`：Windy 來源足夠時不使用非 Windy 來源
  - `test_f2_windy_falls_back_to_non_windy_when_insufficient`：Windy 來源不足時回落非 Windy 來源
  - `test_f2_windy_nd_source_prioritized_over_non_windy_nd`：Windy ND 來源優先於非 Windy ND 來源

#### 文件同步
- [`README.md`](README.md) — 模式列表、跨 OM 規則、模式對照表更新
- [`調貨模式詳解.txt`](調貨模式詳解.txt) — F2 核心特徵與轉出規則更新
- [`ui/sidebar.py`](ui/sidebar.py) — 特殊功能列表與 F2 模式說明更新
- [`models/mode.py`](models/mode.py) — F2 模式描述更新
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md) — F2 Extra constraints 新增 Windy source priority
- [`VERSION.md`](VERSION.md) — 本版本記錄

## v2.11.1-hotfix (2026-05-12)

### 系統架構重構（Phase 1-5）

#### 核心改動
本日進行了大規模系統架構重構，共計 12 個 commit，涵蓋以下範圍：

**Phase 1 — 清理**
- 刪除 `debug/` 目錄（30+ 除錯腳本）
- 刪除根目錄重複腳本（60+ 檔案）
- 刪除 `Geminiapp.py` 替代版本
- 將臨時測試腳本遷移至 `tests/legacy/`

**Phase 2 — 模組抽取**
- 新增 `config.py`：集中所有魔術數字與配置常數
- 新增 `models/mode.py`：MODE_NAME_MAP、MODE_DESCRIPTIONS、RECEIVE_SITE_LIMIT_MODE_CODES
- 新增 `ui/` 目錄：sidebar.py、display.py、styles.py、mojibake.py
- `app.py` 從 1201 行精簡至 266 行

**Phase 3 — 工廠模式**
- 新增 `services/recommendation_factory.py`：`build_recommendation()` + `apply_transfer()` 統一建構
- 新增 `_make_source()` / `_make_dest()` 工廠函式
- 抽取 `_compute_transfer_qty()` 方法
- 抽取 `_note_source_analysis()` / `_note_dest_analysis()` 方法

**Phase 4 — 策略模式抽取**
- 新增 `strategies/base.py`：BaseMatchStrategy 抽象基類
- 新增 `strategies/predicates.py`：`is_hd_to_hk_restricted()` 共用判斷
- 新增 `strategies/simplified_sku.py`：SimplifiedSKUStrategy
- 新增 `strategies/c2_mode.py`：C2ModeStrategy
- 新增 `strategies/f_mode.py`：FModeStrategy
- 新增 `strategies/e1_mode.py`：E1ModeStrategy（E1/E1b）
- 新增 `strategies/nd_mode.py`：NDModeStrategy（ND1/ND2）
- 新增 `strategies/b_special.py`：BSpecialStrategy（委派至 `_match_by_priority`）

**Phase 5 — 程式碼清理**
- 刪除 6 個已抽取的死方法
- `business_logic.py` 從 3400+ 行精簡至 2144 行
- 統一所有模式使用 `build_recommendation()` + `apply_transfer()`

#### Bug 修復
- **ND 模式 NaN 崩潰**：`_make_dest()` 中 `int(row['Safety Stock'])` 在 NaN 時崩潰，新增 `pd.notna()` 防禦
- **Streamlit Cloud import 錯誤**：保留 `_parse_target_for_ui` 和 `_find_f_mode_nd_target_conflicts` 在 app.py 中的本地副本

#### 版本號修正
- `business_logic.py` class docstring：v2.11.0 → v2.11.1
- `data_processor.py` docstring：v2.10.0 → v2.11.1
- `excel_generator.py` docstring：v2.10.0 → v2.11.1
- `DEBUG_CHECKLIST.md` 版本：v2.10.0 → v2.11.1

#### 測試結果
- 全部 175 個測試通過（0 失敗）
- 涵蓋所有 24 個模式的：dual-role 防護、HD 限制、Windy 限制、Mix 銷量保護、接收上限、單件優化、ND 模式等

#### 已知限制（待後續處理）
1. `_parse_target_for_ui()` 和 `_find_f_mode_nd_target_conflicts()` 重複定義於 app.py 和 business_logic.py，待合併至共用模組
2. E2 模式匹配邏輯仍留在 business_logic.py 中（`_match_transfers_e_mode` + `_e_mode_phase3_c_fallback`），待抽取至 `strategies/e2_mode.py`
3. SimplifiedSKUStrategy 和 C2ModeStrategy 的 Notes 使用簡化格式，與其他策略的詳細格式不完全一致
4. 無 data_processor.py 和 excel_generator.py 的單元測試

---

## v2.11.1 (2026-05-11)

### 模式A單件調貨上調優化

#### 核心改動
- 模式A（保守轉貨）來源識別階段，當 `actual_transferable` 計算為 1 件且 `remaining_stock >= 3`（轉出 1 件後淨庫存餘 3 件以上）時，自動上調至 2 件轉出
- 上調後以 `Safety Stock - 1` 作為放寬安全線（數學等價於原始安全檢查，不降低實際安全水準）
- 避免來源店被限制只能轉出 1 件的低效調撥情況

#### 條件總結
1. `actual_transferable == 1`（由 `base_transferable = total_available - safety_stock` 限制所致）
2. `remaining_stock >= 3`（SaSa Net Stock ≥ 4，確保上調至 2 件後來源仍餘 ≥ 2 件）
3. `2 <= upper_limit`（20% 上限允許，因 floor=2 故本條件永遠成立）

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 版本升級至 v2.11.1
  - `identify_sources()` 模式 A 區塊新增上調邏輯（第 500-507 行）
  - 放寬安全線由數學等價性隱式保證，無需額外顯式檢查

#### 文件同步
- [`README.md`](README.md)
  - 版本號更新至 v2.11.1
- [`調貨模式詳解.txt`](調貨模式詳解.txt)
  - 模式A說明新增單件上調規則
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md)
  - 模式A說明新增上調規則

---

## v2.11.0 (2026-05-11)

### F2模式新增HD轉出選項

#### 核心功能
- F2模式新增「HD 店舖轉出設定」選項，提供兩種選擇：
  - **HD 不能轉出（預設）**：維持原有行為，HD 店舖不可轉貨到 HA/HB/HC 店舖
  - **HD 可轉出（最後優先）**：允許 HD 店舖轉貨到 HA/HB/HC，但排在最低優先級，僅在其他來源（ND、同OM RF、跨OM RF）都不足時才使用

#### 使用場景
- 當 HA/HB/HC 店舖不夠貨，且 HD 店舖有庫存可轉出時，可啟用此選項
- HD 轉出會被排在配對排序的最後，確保優先使用非 HD 來源

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 版本升級至 v2.11.0
  - `TransferLogic.__init__` 新增 `f2_allow_hd_transfer: bool = False` 參數
  - `_match_transfers_f_mode`：`_f_source_sort_key` 新增 `dest_site` 參數與 HD 懲罰項（`hd_penalty=10`）
  - `_match_transfers_f_mode`：HD 限制檢查改為條件式，F2 + `f2_allow_hd_transfer=True` 時不跳過
- [`app.py`](app.py)
  - 新增 F2 模式「HD 店舖轉出設定」radio button（僅 F2 模式下顯示）
  - 將 `f2_allow_hd_transfer` 傳入 `TransferLogic` 建構子
  - 更新模式描述、詳細模式說明、欄位說明

## v2.10.0 (2026-04-30)

### 新增精簡SKU模式（限同OM / 跨OM）+ F/F2模式改善

#### 精簡SKU模式核心規則
- 新增兩個精簡SKU模式：`精簡SKU(限同OM)`、`精簡SKU(跨OM)`
- 針對 SKU 精簡場景設計，將超出上限的庫存轉出至有需求的 RF 店舖
- RF 店舖存貨上限 Cap = `Max(Safety Stock × 2, Last 2 Month Sold Qty × 2)`
- ND 店舖全數可轉出
- 轉給 RF 店舖最少 2 件起轉（參考 C1 模式）
- 剩餘無法配對的數量一律退回 D001（無數量限制）
- 精簡SKU(跨OM) 額外規則：Windy 只轉 Windy，HD 不能轉到 HA/HB/HC

#### F/F2 模式改善
- **Target 接收店舖不論 ND 或 RF 均可接收**（打破 ND 不可接收的全局限制）
- **Target 數量直接作為接收量**（`needed_qty = Target Qty`，不考慮現有庫存與在途數量）
- 現行邏輯：`needed_qty = Target - (SaSa Net Stock + Pending Received)`，僅 RF 可接收
- 改善後：`needed_qty = Target`，ND/RF 均可接收
- 非 Target 店舖邏輯不變（F 模式：RF 補0；F2 模式：不接收）

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 版本升級至 v2.10.0（二十四模式系統）
  - 新增 `mode_simplified_sku_same`、`mode_simplified_sku_cross` 常數
  - 新增 `_is_simplified_sku_mode()` 家族判斷
  - `identify_sources`：新增精簡SKU模式 ND 全轉出 + RF 超出 Cap 轉出邏輯
  - `identify_destinations`：新增精簡SKU模式 RF 接收上限邏輯
  - 新增 `_match_transfers_simplified_sku()` 專用匹配方法（Phase 1: RF-to-RF 配對，Phase 2: 剩餘退回 D001）
  - `generate_transfer_recommendations`：新增精簡SKU模式到驗證白名單與跨OM分組
  - `_create_recommendation_note`：新增精簡SKU模式 Notes 文案
- [`app.py`](app.py)
  - 版本升級至 v2.10.0（二十四模式系統）
  - 側欄模式選單新增 `精簡SKU(限同OM)`、`精簡SKU(跨OM)`
  - `mode_name_map`、模式說明、欄位要求同步更新
  - 核心功能說明新增精簡SKU模式
- [`excel_generator.py`](excel_generator.py)
  - 更新 docstring：二十四模式系統

#### 文件同步
- [`README.md`](README.md)
  - 系統概述改為二十四模式
  - 模式對照表新增精簡SKU(限同OM)、精簡SKU(跨OM) 行
  - F/F2 模式描述更新
  - 補回 D2 模式描述
- [`調貨模式詳解.txt`](調貨模式詳解.txt)
  - 標題改為「二十四種調貨模式詳解」
  - 新增精簡SKU(限同OM)、精簡SKU(跨OM) 完整說明段落
  - F/F2 模式接收規則更新（ND/RF 均可接收、Target 直接作為接收量）
  - 關鍵差異對比表新增精簡SKU 列
  - 應用場景建議新增精簡SKU 說明
  - 轉出/接收分類類型新增精簡SKU
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md)
  - 新增精簡SKU(限同OM)、精簡SKU(跨OM) 模式說明
  - 更新 Mode F / Mode F2 的 Destination rules

---

## v2.9.1 (2026-04-27)

### 正式加入 C1 模式（重點補0-只補0/1）

#### C1 模式核心規則
- 參照 C 模式，但**僅處理 total_available ≤ 1 的店舖**（重點補0）
- **不回落**到一般缺貨補貨（緊急缺貨、潛在缺貨）分支
- 轉出門檻提高：`SaSa Net Stock > 2` 才可轉出（C 模式僅要求 total_available > Safety Stock）
- 轉出量下限提高：至少 2 件才參與配對（C 模式最少 1 件），避免低效的單件來源
- 來源排序：優先使用可轉量較大的來源（按 transferable_qty 降序），減少拆單

#### 與 C 模式的差異
| 項目 | C 模式 | C1 模式 |
|------|--------|---------|
| 接收類型 | 重點補0 + 緊急缺貨 + 潛在缺貨 | **僅** 重點補0 |
| 轉出門檻 | total_available > Safety Stock | SaSa Net Stock > 2 |
| 轉出量下限 | 至少 1 件 | 至少 2 件 |
| 來源排序 | 標準排序 | 優先可轉量較大者 |
| 適用場景 | 全面補低庫存 | 精準只補零庫存/1件 |

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - C1 模式常數與邏輯早已存在於代碼中（`mode_c1`），本次僅更新 docstring
  - 更新模組 docstring：二十一模式 → 二十二模式系統
- [`app.py`](app.py)
  - 側欄模式選單新增 `C1: 重點補0(只補0/1)`
  - `mode_name_map` 新增 C1 對應
  - `mode_descriptions` 新增 C1 說明
  - 欄位提示群組新增 C1（與 C/C2/D/D2 共用基本欄位）
  - 更新 docstring：二十一模式 → 二十二模式系統
- [`excel_generator.py`](excel_generator.py)
  - 更新 docstring：十八模式 → 二十二模式系統（含 C1）

#### 文件同步
- [`README.md`](README.md)
  - 系統概述改為二十二模式
  - 功能重點更新
  - 模式對照表新增 C1 行
  - 介面操作流程更新
- [`調貨模式詳解.txt`](調貨模式詳解.txt)
  - 標題改為「二十二種調貨模式詳解」
  - 新增 C1 模式完整說明段落
  - 關鍵差異對比表新增 C1 列
  - 應用場景建議新增 C1 說明
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md)
  - 模式總覽新增 C1
  - 新增 C1 模式說明段落

---

## v2.9.0 (2026-04-24)

### 新增 B2L/B2La/B3L/B3La（Type=L 低銷量保留2件）

#### 新模式核心規則
- 新增四個 B-special L 系列模式：`B2L`、`B2La`、`B3L`、`B3La`
- **僅新 L 系列**套用 Type=L 低銷量保留2件：
  - 條件：`Type=L` 且 `max(Last Month Sold Qty, MTD Sold Qty) <= 2`
  - 轉出量：`max(SaSa Net Stock - 2, 0)`
  - 當淨庫存 `<= 2` 時不轉出
- 舊模式 `B2/B2a/B3/B3a` 維持原行為（Type=L 低銷量全轉出）
- `B2La/B3La` 延續 a 系列限制：`Type=T` 不可作為出貨來源
- `B3L/B3La` 延續跨 OM 家族限制：HD/Windy 規則不變

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 新增四個模式常數與家族判斷
  - Type=L 低銷量特例新增「保留2件」分支（僅 L 系列）
  - 模式白名單、跨 OM 分組/分支與備註文案同步
- [`app.py`](app.py)
  - 側欄模式選單新增 B2L/B2La/B3L/B3La
  - 接收店數限制適用模式清單、模式描述、欄位要求與 Type 欄位驗證同步
  - `mode_name_map` 新增四模式對應
- 文件同步
  - [`README.md`](README.md)
  - [`調貨模式詳解.txt`](調貨模式詳解.txt)

#### 測試同步
- [`tests/test_b_special_mix_sales_guard.py`](tests/test_b_special_mix_sales_guard.py)
  - Mix 高銷量保護測試納入四新模式
- [`tests/test_b2a_b3a_t_no_source.py`](tests/test_b2a_b3a_t_no_source.py)
  - 新增 B2La/B3La Type=T 不可 source 測試
- [`tests/test_b2_b3_source_receive_site_limit.py`](tests/test_b2_b3_source_receive_site_limit.py)
  - 新增 B2L/B2La/B3L/B3La 接收店數上限測試
- [`tests/test_all_modes_comprehensive.py`](tests/test_all_modes_comprehensive.py)
  - 新增 B-L 系列整合測試（保留2件、邊界庫存、跨OM、a系列限制）

---

## v2.8.0 (2026-04-08)

### 新增 D2 模式（清貨轉貨ND限定）

#### D2 模式核心規則
- 按照 D 模式邏輯，但**僅 ND Shop 轉出，RF Shop 只做接收不做轉出**
- 僅針對無銷售記錄（Last Month Sold Qty = 0 且 MTD Sold Qty = 0）的 ND 店舖清貨轉出
- 有銷售記錄的 ND 店舖在 D2 模式下也不轉出（與 D 模式不同）
- RF 店舖完全不進入轉出候選，只作為接收方
- 仍限制同一 OM 內配對
- 繼承 D 模式的避免 1 件餘貨邏輯

#### 與 D 模式的差異
| 項目 | D 模式 | D2 模式 |
|------|--------|---------|
| ND 清貨轉出（無銷售） | ✅ | ✅ |
| ND 轉出（有銷售） | ✅ | ❌ |
| RF 過剩轉出 | ✅ (A模式規則) | ❌ |
| RF 接收 | ✅ | ✅ |

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 新增 `mode_d2 = "清貨轉貨(ND限定)"`
  - 新增 `_is_d_family_mode()` 共用 D/D2 邏輯判斷
  - `identify_sources`：D2 模式跳過所有 RF 轉出源，ND 僅清貨轉出
  - `identify_destinations`：D/D2 共用放寬接收條件
  - `_match_by_priority`：D/D2 共用避免 1 件餘貨邏輯
  - `_create_recommendation_note`：D2 使用 D2 標籤
  - `generate_transfer_recommendations`：新增 mode_d2 到驗證白名單
- [`app.py`](app.py)
  - 側邊欄新增 `D2: 清貨轉貨(ND限定)`
  - `mode_name_map`、模式說明同步更新
- 測試：D2 已納入 `test_all_modes_comprehensive.py`、`test_modes_simple.py`、`test_all_modes_no_dual_role.py` 模式清單

#### 文件同步
- [`調貨模式詳解.txt`](調貨模式詳解.txt)
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md)

---

## v2.7.0 (2026-03-30)

### 新增 F2 模式（F指定模式）

#### F2 模式核心規則
- 僅 `Target > 0` 的 RF 店舖可以接收
- 非 Target RF 店舖不再走補 0 接收流程
- 保留 F 模式的跨 OM 配對能力與 HD 限制（HD 不可轉到 HA/HB/HC）
- 轉出邏輯沿用 F 模式（ND 可全轉出；RF 保護最高銷量店）

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 新增 `mode_f_target_only = "F指定模式"`
  - `identify_sources` / `identify_destinations` / `match_transfers` / `generate_transfer_recommendations` 納入 F2 分支
  - F2 接收類型新增 `F指定模式目標接收`
- [`app.py`](app.py)
  - 側邊欄新增 `F2: F指定模式`
  - `mode_name_map`、模式說明、欄位要求與前置警示同步更新
- [`tests/test_all_modes_comprehensive.py`](tests/test_all_modes_comprehensive.py)
  - 新增 F2 僅 Target 接收測試
- [`tests/test_modes_simple.py`](tests/test_modes_simple.py)、[`tests/test_all_modes_no_dual_role.py`](tests/test_all_modes_no_dual_role.py)
  - 將 F2 納入模式清單

#### 文件同步
- [`README.md`](README.md)
- [`調貨模式詳解.txt`](調貨模式詳解.txt)
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md)

---

## v2.6.0 (2026-03-20)

### 新增 ND1/ND2 模式（ND 智能調貨）

#### ND1 模式（ND 同 OM 轉貨）
- ND 店舖可互相調貨，限同一 OM 組別及同一 Article
- 打破「ND 不可接收」全局規則（ND1/ND2 模式例外）
- 轉出排序：兩月銷量=0 優先 → 最低銷量次選 → 最高銷量保護
- 接收優先級 1：RF 緊急缺貨（零庫存有銷售記錄）
- 接收優先級 2：ND 潛在缺貨（按兩月銷量降序）
- 接收上限：2 × (Last Month Sold Qty + MTD Sold Qty)；銷量=0 不可接收

#### ND2 模式（ND 混合 OM 轉貨）
- 繼承 ND1 所有算法邏輯，但允許跨 OM
- Windy（澳門）轉出只能到 Windy；HD 不能轉到 HA/HB/HC

#### 技術架構
- [`business_logic.py`](business_logic.py)：`mode_nd1`/`mode_nd2` 常數、`_is_nd_transfer_mode()`、`_match_transfers_nd_mode(cross_om)` 共用核心
- [`perform_quality_checks(mode)`](business_logic.py) 新增 `mode` 參數，ND 模式豁免 ND 接收檢查
- [`app.py`](app.py)：新增兩個模式選項、說明、`mode_name_map`
- [`tests/test_nd_modes.py`](tests/test_nd_modes.py)：14 個單元測試，全部通過

---

## v2.5.0 (2026-03-11)

### 新增功能：所有模式後處理 — 避免單筆1件調貨

**核心改動：** 在 `generate_transfer_recommendations` 最後一步，加入通用後處理，對所有 13 個模式的輸出結果統一執行「避免單筆1件調貨」優化。

#### 規則說明
- **目標**：所有模式輸出中，同一出貨店舖（Transfer Site）同一 SKU（Article）的每筆調貨數量，不應出現 `Transfer Qty = 1`。
- **例外**：若該出貨店舖對該 SKU 的可調總量本身就只有 1 件，則允許保留（無法再重新分配）。
- **不影響** D 模式餘貨邏輯（D 模式處理的是「轉出後剩餘庫存」，本後處理處理的是「每筆調貨數量」，兩者互補）。

#### 兩種優化策略（依序嘗試）
1. **Rebalance（重新平衡）**：若同群組內有其他目標店數量 ≥ 3，從中取 1 件給單件店舖，使其變為 2 件，施方維持總量不變。
2. **Merge（合併）**：若無法 Rebalance（例如僅有 2+1 的情況），將 1 件合併至「接收店舖總銷量（Last Month + MTD）最高」的目標店，並移除原單件行。

#### 新增方法（`business_logic.py`）
| 方法名稱 | 用途 |
|----------|------|
| `_get_record_sales_total(rec, prefix)` | 計算某紀錄的 Last Month + MTD 總銷量 |
| `_refresh_recommendation_fields(recommendations, mode)` | 調整數量後重新計算 After Transfer Stock、Cumulative Received Qty、Notes 欄位 |
| `_optimize_single_piece_transfers(recommendations, mode)` | 主後處理函式：偵測並消除單件調貨記錄 |

#### 新增測試（`tests/test_single_qty_optimization.py`）
- `test_optimize_single_qty_rebalance_to_avoid_one_piece`：驗證 11+1 → 10+2 的 Rebalance 情境
- `test_optimize_single_qty_merge_to_higher_sales_destination`：驗證 2+1 → 3（合併至高銷量目標店）情境

#### 實際效果驗證
- `100008801001 / HA42`：(HA32:11, HA44:1) → (HA32:10, HA44:2) ✅
- `100314808024 / HC62`：(HC49:2, HC61:1) → (HC49:3) ✅

---

## v2.4.1 (2026-02-25)

### B 特別模式規則更新（2026-02-25）
- 新增 B2/B2a/B3/B3a 的 **Mix 店舖高銷量保護**：
  - 若出貨店舖為 Type=M（Mix），且其總銷量高於目標店舖總銷量，取消該配對。
  - 總銷量口徑統一為：**Last Month Sold Qty + MTD Sold Qty**。
- 已將上述規則同步至 App 介面與說明文件，確保系統行為與文件描述一致：
  - `app.py`（模式說明、欄位提示、核心功能文案）
  - `README.md`
  - `調貨模式詳解.txt`
  - `transfer_logic_ai_brief.md`

### 程式碼審查與清理
- 進行全面的程式碼審查
- 建立 .gitignore 檔案以排除不必要的檔案
- 從版本控制中移除大型 Excel 檔案
- 修正版本號不一致問題

### 專案結構優化
- 計劃重構 business_logic.py 為較小的模組
- 建立適當的目錄結構（tests/, debug/, legacy/）

---

## v2.3.0 (2026-02-10)

### 新增功能
- **新增 C2 模式（附加C跨OM重點補0）**：
  - 參照 C 模式的轉出/接收邏輯（重點補0）
  - 允許跨 OM 配對（分組僅按 Article，不按 OM）
  - **HD 限制**：HD 店鋪不能轉到 HA/HB/HC
  - **Windy 限制**：Windy 轉出只能到 Windy 的店鋪（Windy 可接收其他 OM）
  - 升級系統為九模式系統：A/B/B2/B3/C/C2/D/E/F

### 業務邏輯更新
- **C2 模式（附加C跨OM重點補0）**：
  - 轉出條件：完全沿用 C 模式（30% 上限 / 3 件上限 / 至少 1 件）
  - 接收條件：完全沿用 C 模式（total_available <= 1 的重點補0）
  - 目標數量：min(Safety Stock, MOQ + 1)
  - 跨 OM 配對：分組僅按 Article，不按 OM
  - HD 限制：HD 店鋪不能轉到 HA/HB/HC
  - Windy 限制：Windy 轉出只能到 Windy，但 Windy 可接收其他 OM

### 技術更新
- 更新 `business_logic.py` (v2.3.0)：
  - 新增 `mode_c2 = "附加C2(跨OM重點補0)"` 常量
  - 修改 `identify_sources` 方法：C2 模式使用 C 模式的轉出邏輯
  - 修改 `identify_destinations` 方法：C2 模式使用 C 模式的接收邏輯
  - 新增 `_match_transfers_c2_mode` 專用匹配方法，實現跨 OM 配對邏輯
  - 更新 `generate_transfer_recommendations`：將 C2 加入跨 OM 模式列表和驗證
  - 更新文檔字串為九模式系統

- 更新 `app.py` (v2.3.0)：
  - 更新頁面標題為 "庫存調貨建議系統 v2.3.0"
  - 增加 C2 模式選項與說明
  - 更新模式名稱轉換邏輯，支持 C2 模式
  - 更新系統資訊，添加 C2 模式特殊功能說明

- 更新 `excel_generator.py` (v2.3.0)：
  - 更新文檔字串為九模式系統

- 更新 `README.md`：
  - 系統概述改為九模式系統
  - 功能特點新增 C2 描述
  - 模式對比表新增 C2 列
  - 使用說明新增 C2 模式行
  - 業務邏輯詳解新增 C2 模式完整說明

### 與 C 模式的差異
| 項目 | C 模式 | C2 模式 |
|------|--------|---------|
| 轉出邏輯 | 30% 上限 / 3 件上限 | 同 C 模式 |
| 接收邏輯 | total_available <= 1 | 同 C 模式 |
| 分組方式 | Article + OM | 僅 Article |
| 跨 OM 配對 | ❌ 不允許 | ✅ 允許 |
| HD 限制 | N/A | ✅ HD 不能轉到 HA/HB/HC |
| Windy 限制 | N/A | ✅ Windy 轉出只能到 Windy |

### 重要說明
- C2 模式的轉出/接收邏輯完全沿用 C 模式，差異僅在於允許跨 OM 配對
- HD/Windy 限制規則與 B3/E/F 模式一致
- C2 模式適用於需要跨 OM 重點補0的場景

---

## v2.2.2 (2026-02-10)

### 新增功能
- **新增 B3 模式（附加B跨OM特別模式）**：
  - 參照 B2 規則（Type=L 全轉出、接收上限 2 倍安全庫存、接收優先排序）
  - 允許跨 OM 配對
  - **HD 限制**：HD 店鋪不能轉到 HA/HB/HC
  - **Windy 限制**：Windy 轉出只能到 Windy（Windy 可接收其他 OM）

### 技術更新
- 更新 `business_logic.py`：
  - 新增 `mode_b3` 並支援跨 OM 分組
  - 在匹配階段加入 Windy/HD 限制
  - B2/B3 共用接收上限與優先排序
- 更新 `app.py`：
  - 增加 B3 模式選項與說明
  - B2/B3 共用 Type 欄位檢查
- 更新 `README.md`：
  - 補充 B3 模式規則與使用說明

---

## v2.2.1 (2026-02-10)

### 業務邏輯更新
- **B2 接收優先級**：
  - 依 Type T (遊客區店舖) / Type M (混合型店舖) 分層排序
  - 先比合計銷量 (MTD + Last Month)，再比 Safety Stock

### 輸出說明更新
- **Excel 接收類型文字**：
  - Type T → 遊客區店舖
  - Type M → 混合型店舖

### 測試
- 新增 `test_b2_priority.py`，驗證 B2 接收優先排序

---

## v2.2.0 (2026-02-09)

### 新增功能
  - 將 stores-template.csv 的 85 間店舖資料直接寫入程式內
  - 當用戶上傳的 Excel 缺少 OM 或 Type 資料時，系統會根據 Site 自動填充預設值
  - 如果用戶有自己的資料，系統會優先使用，不會覆蓋

### 業務邏輯更新
- **預設店舖資料**：
  - 包含 85 間店舖的預設資料（HA02-HD20）
  - 資料欄位：Site、Shop、Regional、Class 1、Class 2、Size、OM、Type
  - HK 區域：77 間店舖
  - MO 區域：8 間店舖
  - OM 分佈：Ivy、Violet、Queenie、Candy、Hippo、Eva、Windy

### 技術更新
- 更新 `data_processor.py`：
  - 新增 `DEFAULT_STORE_DATA` 常量，包含 85 間店舖的預設資料
  - 新增 `get_store_default_info(site)` 方法，根據店舖編號查詢預設資料
  - 新增 `fill_default_store_data(df)` 方法，批量填充缺失的 OM 和 Type
  - 修改 `preprocess_data()` 方法，在數據類型轉換後調用填充方法
  - 新增 `fill_stats` 統計，記錄填充的筆數和找不到的店舖

- 更新 `app.py`：
  - 更新頁面標題為 "庫存調貨建議系統 v2.2.0"
  - 更新系統資訊，添加「預設店舖資料自動填充」功能說明

### 使用場景
1. **用戶上傳的 Excel 有完整的 OM 和 Type 資料**：系統使用用戶提供的資料，不進行覆蓋
2. **用戶上傳的 Excel 缺少 OM 或 Type 資料**：系統根據 Site 欄位自動從預設資料中填充
3. **用戶上傳的 Excel 有部分 OM 或 Type 資料**：系統只填充缺失的欄位，已有資料不被覆蓋

### 重要說明
- 預設資料應定期更新以反映店舖資訊變更
- 如果需要更新預設資料，需要修改程式碼並重新部署
- 系統會記錄哪些資料是從預設值填充的（可在日誌中查看）

---

## v2.1.1 (2026-01-30)

### 新增功能
- **新增F模式：目標優化**
  - 針對Target欄位填數字作為優先接收目標
  - 其他店鋪按C模式補0需求計算
  - 支持跨OM配對，HD不能轉到HA/HB/HC
  - 更新系統為六模式系統：A/B/C/D/E/F

### 業務邏輯更新
- **F模式(目標優化)**：
  - 轉出條件：
    - ND類型：全數轉出
    - RF類型：可忽視最小庫存要求，但保護最高銷量店鋪
  - 轉出類型：F模式ND轉出 / F模式RF轉出
  - 接收條件：
    - Target數字：優先接收目標
    - 未標Target的店鋪：按C模式重點補0
  - 優先級邏輯：
    - Target數字優先接收
    - 其他店鋪按C模式補0需求計算
  - HD限制：
    - HD店鋪的轉出絕對不能到HA/HB/HC店鋪

### 技術更新
- 更新 `data_processor.py`：
  - 在 optional_columns 中添加 'Target' 欄位
  - 修改 `read_excel_file` 方法，能夠讀取並標準化 *Target* 欄位
  - 自動創建空 Target 欄位（若上傳文件中不存在）
  - 添加日誌記錄 *Target* 欄位的識別狀態

- 更新 `business_logic.py`：
  - 添加 `self.mode_f = "目標優化"`
  - 修改 `identify_sources` 方法，添加F模式的轉出識別邏輯
  - 修改 `identify_destinations` 方法，添加F模式的接收邏輯（Target優先+C模式補0）
  - 修改 `match_transfers` 方法，增加F模式路由到專用匹配方法
  - 新增 `_match_transfers_f_mode` 方法，實現F模式的Target優先和跨OM限制邏輯
  - 更新 `generate_transfer_recommendations` 方法的模式驗證，支持F模式
  - 更新所有相關方法的文檔字符串

- 更新 `app.py`：
  - 更新頁面標題為 "庫存調貨建議系統 v2.1.1"
  - 更新模式選擇，添加 "F: 目標優化" 選項
  - 更新模式說明，添加F模式的詳細說明
  - 更新模式名稱轉換邏輯，支持F模式

### 重要說明
- *Target* 欄位識別不分大小寫，系統會自動標準化為 'Target'
- F模式上傳的Excel文件需要包含 *Target*、Target 或其他大小寫組合的欄位
- F模式下，Target數字優先接收，未標Target的店鋪會按C模式補0需求計算
- HD和其他OM的限制規則遵循客戶的業務規則：HD不能轉到同一OM集群的其他OM

---

## v1.9.9 (2026-01-29)

### 新增功能
- **新增E模式：強制轉出**
  - 針對標記為 *ALL* 的商品行進行全數強制轉出
  - 只有被標記為 *ALL* 的行才會成為轉出源
  - 接收店鋪限制為RF類型，接收上限為Safety Stock的2倍
  - 優先同OM配對，當該OM無法接收時放寬跨OM配對
  - HD店鋪絕對不能轉到HA/HB/HC的店鋪
  - 更新系統為五模式系統：A/B/C/D/E

### 業務邏輯更新
- **E模式(強制轉出)**：
  - 轉出條件：該行在 *ALL* 欄位中有任何非空白文字
  - 轉出數量：全數轉出（不考慮安全庫存）
  - 轉出類型：E模式強制轉出
  - 接收條件：
    - 只接收RF店鋪
    - 當前庫存(SaSa Net Stock + Pending Received) < Safety Stock × 2
    - 接收上限 = Safety Stock × 2
  - 優先級邏輯：
    - Phase 1：優先配對同OM的接收店鋪
    - Phase 2：當同OM無法接收時，放寬跨OM配對（但受HD限制）
    - **Phase 3：C模式回退** - 當其他OM未有店舖涉及強制轉出時，可按照C模式照常做重點補0
  - HD限制：
    - HD店鋪的轉出絕對不能到HA/HB/HC店鋪

### 技術更新
- 更新 `data_processor.py`：
  - 在 optional_columns 中添加 'ALL' 欄位
  - 修改 `read_excel_file` 方法，能夠讀取並標準化 *ALL* 欄位（不分大小寫）
  - 自動創建空 ALL 欄位（若上傳文件中不存在）
  - 添加日誌記錄 *ALL* 欄位的識別狀態

- 更新 `business_logic.py`：
  - 添加 `self.mode_e = "強制轉出"`
  - 修改 `identify_sources` 方法，添加E模式的強制轉出識別邏輯
  - 修改 `identify_destinations` 方法，添加E模式的接收邏輯（RF限制+上限為2倍Safety Stock）
  - 修改 `match_transfers` 方法，增加E模式路由到專用匹配方法
  - 新增 `_match_transfers_e_mode` 方法，實現E模式的優先級和跨OM限制邏輯
  - 更新 `generate_transfer_recommendations` 方法的模式驗證，支持E模式
  - 更新所有相關方法的文檔字符串

- 更新 `app.py`：
  - 更新頁面標題為 "庫存調貨建議系統 v1.9.9"
  - 更新模式選擇，添加 "E: 強制轉出" 選項
  - 更新模式說明，添加E模式的詳細說明
  - 更新模式名稱轉換邏輯，支持E模式

### 重要說明
- *ALL* 欄位識別不分大小寫，系統會自動標準化為 'ALL'
- E模式上傳的Excel文件需要包含 *ALL*、ALL 或其他大小寫組合的欄位
- E模式下，只有被標記的行才會進行轉出，其他行被忽略
- HD和其他OM的限制規則遵循客戶的業務規則：HD不能轉到同一OM集群的其他OM

---

## v1.9.8 (2026-01-26)

### 新增功能
- **新增D模式：清貨轉貨**
  - 針對ND類型且無銷售記錄的店鋪進行清貨處理
  - 實現避免1件餘貨的特殊邏輯
  - 更新系統為四模式系統：A/B/C/D

### 業務邏輯更新
- **D模式(清貨轉貨)**：
  - 轉出條件：ND類型且 Last Month Sold Qty = 0 且 MTD Sold Qty = 0
  - 轉出類型：ND清貨轉出
  - 特殊規則：避免1件餘貨
    - 如果轉出後會剩餘1件，則嘗試多轉1件（使剩餘為0）
    - 若無法多轉，則少轉1件（使剩餘為2）
    - 確保轉出後剩餘庫存為0件或≥2件
  - 接收規則：遵循A模式(保守轉貨)的接收規則

### 技術更新
- 更新 `business_logic.py`：
  - 添加 `self.mode_d = "清貨轉貨"`
  - 修改 `identify_sources` 方法，添加D模式的ND清貨轉出識別
  - 修改 `_match_by_priority` 方法，添加避免1件餘貨的特殊處理
  - 修改 `_create_recommendation_note` 方法，添加ND清貨轉出的說明
  - 更新模式驗證邏輯，支持D模式
  - 更新所有相關方法的文檔字符串
  - 更新版本號至 v1.9.8

- 更新 `app.py`：
  - 更新頁面標題為 "庫存調貨建議系統 v1.9.8"
  - 更新模式選擇，添加 "D: 清貨轉貨" 選項
  - 更新模式說明，添加D模式的詳細說明
  - 更新模式名稱轉換邏輯，支持D模式
  - 更新操作指引，添加D模式的說明
  - 更新系統資訊，更新版本號和核心功能描述
  - 更新圖表顯示邏輯，支持D模式的ND清貨轉出類型

- 更新 `README.md`：
  - 更新系統概述，改為四模式系統
  - 更新功能特點，添加D模式特殊功能說明
  - 更新使用說明，添加D模式的說明
  - 更新業務邏輯詳解，添加D模式的完整說明
  - 更新更新日誌，添加v1.9.8的版本記錄

- 新增 `test_mode_d.py`：
  - 創建D模式專用測試腳本
  - 驗證ND清貨轉出邏輯的正確性
  - 驗證避免1件餘貨功能的有效性
  - 提供詳細的測試結果和統計分析

---

**開發者：Ricky**
**最後更新：2026-02-10**
