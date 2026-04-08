# 版本更新記錄

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
