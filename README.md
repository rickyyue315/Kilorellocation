# KiLo 庫存調貨建議系統 v2.19.0

## 系統概述

KiLo 是基於 Streamlit 的庫存調貨建議系統，依據庫存、銷量、安全庫存與 MOQ，自動產生跨店鋪調貨建議。

系統目前為 **二十七模式**：

- A：保守轉貨
- B：加強轉貨
- B2：附加 B 特別模式
- B2a：附加 B2a（T 遊客鋪不出貨）
- B2L：附加 B2L（Type=L 低銷量保留 2 件）
- B2La：附加 B2La（Type=L 低銷量保留 2 件 + T 遊客鋪不出貨）
- B3：附加 B 跨 OM 特別模式
- B3a：附加 B3a（跨 OM + T 遊客鋪不出貨）
- B3L：附加 B3L（跨 OM + Type=L 低銷量保留 2 件）
- B3La：附加 B3La（跨 OM + Type=L 低銷量保留 2 件 + T 遊客鋪不出貨）
- C：重點補 0
- C1：重點補 0（只補 0/1）
- C2：附加 C 跨 OM 重點補 0
- D：清貨轉貨
- **D2：清貨轉貨（ND 限定）**
- E1：強制轉出（僅同 OM）
- E1b：強制轉出（僅同 OM，優先類型接收）
- E2：強制轉出（可跨 OM）
- F：目標優化
- F2：F指定模式（僅 Target 店舖接收，可設定 HD 轉出選項；Windy 目標店優先從同 OM 無 Target 店提取）
- **F3：目標性補0（F2 + RF轉出保留2件 + RF按最高庫存優先轉出 + RF跨OM不降級）**
- **ND1：ND 同 OM 轉貨（ND 店舖互轉，限同 OM）**
- **ND2：ND 混合 OM 轉貨（ND 店舖互轉，允許跨 OM）**
- **ND3：ND 限同 OM 轉貨（補 0）（ND 同 OM 轉貨，轉出保留 3 件，只補零庫存 ND 店）**
- **精簡SKU（限同OM）：超出 Cap 轉出，僅同 OM**
- **精簡SKU（跨OM）：超出 Cap 轉出，允許跨 OM**
- **精簡SKU（退D001）：RF 超出 Cap 全數回退 D001，ND 全數回退 D001，不配對接收**

## 核心規則

- ND 店舖在所有模式下僅可轉出，不可接收（**ND1/ND2 模式例外**，允許 ND 互轉；**F/F2/F3 模式例外**，Target ND 店舖可接收）。
- RF 最高有效銷量店舖受保護，不會被選為轉出方。
- 同一 SKU 下，轉出店舖不可同時為接收店舖。
- D 模式會調整轉移量，避免轉出後剛好剩 1 件。
- **所有模式均套用後處理**：避免單筆調貨數量為 1 件（例外：若出貨店舖該 SKU 可調總量本身只有 1 件則保留）。
- E1/E1b/E2 僅處理 `ALL` 欄位有標記的行。
- B2/B2a/B2L/B2La/B3/B3a/B3L/B3La：若出貨店為 Type=M（Mix）且其總銷量高於目標店，該配對會被取消（`總銷量 = Last Month Sold Qty + MTD Sold Qty`）。
- B3/C2/E2/F/精簡SKU(跨OM) 的跨 OM 規則：
  - HD 來源不可轉到 HA/HB/HC。
  - Windy 來源僅可轉到 Windy。
- F2/F3 跨 OM 規則：
  - 預設 HD 來源不可轉到 HA/HB/HC；可切換為「HD 可轉出（最後優先）」，此時 HD 來源排在最低優先級，僅在其他來源不足時才使用。
  - Windy 來源僅可轉到 Windy。
  - **Windy 目標店（有 Target）優先從其他無 Target 的 Windy 店舖提取**；若 Windy 來源不足，才回落至非 Windy 來源。
- F3 額外規則：
  - RF 轉出後保留 2 件（net_stock > 2 才可轉出，轉出量 = net_stock - 2）
  - RF 按最高庫存優先轉出（同優先級內銷量最低優先）
  - RF 跨 OM 不降級（同 OM / 跨 OM 同等優先）
- **F/F2/F3 模式 Target 接收改善**：Target 數量直接作為接收量（不考慮現有庫存與在途），Target 店舖不論 ND/RF 均可接收。

## 功能重點

- 二十七模式調貨策略。
- **模式教學分頁**：內建繁體中文圖例教學，涵蓋全部 27 種模式的適用場景、HTML/CSS 流程圖、配對優先級、數字情境範例與模式對比，附模式選擇決策指南。
- B2/B2a/B2L/B2La/B3/B3a/B3L/B3La 可在介面設定「單一出貨店舖最多配對接收店舖數」：`優先 1 間` / `最多 2 間` / `不限制`。
- B2/B2a/B2L/B2La/B3/B3a/B3L/B3La Mix 高銷量保護：避免高銷售 Mix 店舖被轉去較低銷售店舖。
- **單筆1件調貨後處理**：所有模式輸出後統一消除單件調貨，優先重新平衡（Rebalance），次選合併至高銷量目標店（Merge）。
- **精簡SKU模式**：RF 超出 Cap（Max(Safety×2, 過去2個月銷量×2)）部分轉出，ND 全轉出，剩餘退回 D001。
- **精簡SKU(退D001)特殊規則**：RF 僅1件不退回 D001（避免浪費人力），ND 不受此限。
- **F/F2/F3 Target 改善**：Target 數量直接作為接收量，不論 ND/RF 均可接收，不考慮在途。
- 自動資料預處理（型別轉換、缺值補齊、異常校正）。
- 內建店舖預設資料（缺少 OM/Type 時自動補值）。
- 輸出 Excel（調貨建議 + 統計摘要 + 可選 AI 分析摘要）。
- **可選 AI 功能**：AI 模式建議 / AI 邏輯審計 / Excel AI 分析摘要（需 OpenRouter API key，預設關閉）。

## AI 功能說明（可選）

系統支援三個非阻塞 AI 場景，預設關閉（`AI_ENABLED=false`），不會影響既有調貨流程：

1. **AI 模式建議（Advisor）**：上傳並預處理資料後，點擊按鈕可基於資料統計摘要推薦合適的調貨模式；僅供參考，不自動切換使用者選擇。
2. **AI 邏輯審計（Auditor）**：調貨建議生成後，點擊按鈕可獲得風險提示與正面檢查；不修改建議結果。
3. **Excel AI 分析摘要**：在生成 Excel 時，若有 AI advisor/auditor 結果，會新增 `AI分析摘要` sheet。

| AI 功能 | 觸發方式 | 影響範圍 | 安全性 |
|---|---|---|---|
| 模式建議 | 手動按鈕 | 僅顯示建議，不切換模式 | 只傳 aggregate summary，不傳原始資料 |
| 邏輯審計 | 手動按鈕 | 僅顯示風險提示 | 只傳 capped payload（最多 10 條樣本） |
| 報表摘要 | 自動（如有 AI 結果） | 新增 Excel sheet | 無額外 API 呼叫 |

### 啟用 AI 功能

**本地開發**：設定環境變數

```powershell
$env:OPENROUTER_API_KEY="sk-or-v1-xxxxx"
$env:AI_ENABLED="true"
```

**Zeabur 部署**：在 Service Secrets 設定

```text
OPENROUTER_API_KEY=sk-or-v1-xxxxx
AI_ENABLED=true
AI_MODEL=deepseek/deepseek-v4-flash
AI_MODEL_ADVISOR=deepseek/deepseek-v4-flash
AI_MODEL_AUDITOR=deepseek/deepseek-v4-flash
AI_REQUEST_TIMEOUT=30
OPENROUTER_SITE_URL=https://<your-zeabur-domain>
OPENROUTER_APP_TITLE=KiLo Reallocation
```

**AI 安全承諾**：AI 功能只提供建議與摘要，不會修改確定性調貨結果；缺少 API key 或 AI 失敗時核心流程完整可用。

## 系統需求

- Python 3.8+
- 依賴：`pandas`、`openpyxl`、`streamlit`、`numpy`、`xlsxwriter`、`ftfy`、`httpx`
- AI 功能（可選）：OpenRouter API key（見下方 AI 功能說明）

## 安裝與執行

### Windows

1. 直接執行 `run.bat`。
1. 系統會建立虛擬環境並安裝依賴。
1. 自動啟動 Streamlit。

### Linux / macOS

1. 在專案根目錄執行：

```bash
chmod +x run.sh
./run.sh
```

1. 系統會建立虛擬環境並安裝依賴。
1. 自動啟動 Streamlit。

### 手動安裝

1. 建立並啟用虛擬環境：

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

1. 安裝依賴：

```bash
pip install -r requirements.txt
```

1. 啟動應用：

```bash
streamlit run app.py
```

預設網址：`http://localhost:8501`

## 輸入資料欄位

### 必需欄位

- `Article`（12 位字串，系統會自動補零）
- `Article Description` 或 `Article Long Text (60 Chars)`
- `OM`
- `RP Type`
- `Site`
- `SaSa Net Stock`
- `Pending Received`
- `Safety Stock`
- `Last Month Sold Qty`
- `MTD Sold Qty`
- `MOQ`

### 模式專用欄位

- `ALL`：E1 / E1b / E2
- `Type`：B2 / B2a / B2L / B2La / B3 / B3a / B3L / B3La / E1b
- `Target`：F / F2 / F3

### 系統衍生欄位

- `Effective Sold Qty = Last Month Sold Qty + MTD Sold Qty`
- `Total Available = SaSa Net Stock + Pending Received`

## 模式對照

| 模式 | 名稱 | 重點 |
| --- | --- | --- |
| A | 保守轉貨 | 20% 上限，優先保護安全庫存 |
| B | 加強轉貨 | 50% 上限，可下探安全庫存 |
| B2 | 附加 B 特別模式 | Type=L 低銷量可全轉出，接收上限 Safety × 2，Mix 高銷量保護 |
| B2a | 附加 B2a | 參照 B2，且 Type=T 不可作為來源（含 Mix 高銷量保護） |
| B2L | 附加 B2L 特別模式 | 參照 B2，但 Type=L 低銷量改為保留 2 件後轉出（僅新 L 系列） |
| B2La | 附加 B2La 特別模式 | 參照 B2L，且 Type=T 不可作為來源（含 Mix 高銷量保護） |
| B3 | 附加 B 跨 OM 特別模式 | 參照 B2，允許跨 OM，含 HD/Windy 限制與 Mix 高銷量保護 |
| B3a | 附加 B3a 跨 OM 特別模式 | 參照 B3，且 Type=T 不可作為來源（含 Mix 高銷量保護） |
| B3L | 附加 B3L 跨 OM 特別模式 | 參照 B3，但 Type=L 低銷量改為保留 2 件後轉出（僅新 L 系列） |
| B3La | 附加 B3La 跨 OM 特別模式 | 參照 B3L，且 Type=T 不可作為來源（含 Mix 高銷量保護） |
| C | 重點補 0 | 30% 上限、最多 3 件，重點補低庫存 |
| C1 | 重點補 0（只補 0/1） | 參照 C，僅補 total_available ≤ 1，不回落一般缺貨 |
| C2 | 附加 C 跨 OM 重點補 0 | 參照 C，允許跨 OM，含 HD/Windy 限制 |
| D | 清貨轉貨 | ND 無銷售清貨，避免剩 1 件 |
| D2 | 清貨轉貨（ND 限定） | 僅 ND 清貨轉出，RF 不轉出只接收 |
| E1 | 強制轉出 | 僅同 OM，僅處理 `ALL` 標記 |
| E1b | 強制轉出優先類型接收 | 僅同 OM，接收優先 Type=T/M |
| E2 | 強制轉出跨 OM | 優先同 OM，可跨 OM，僅處理 `ALL` 標記 |
| F | 目標優化 | `Target` 優先接收（ND/RF 均可），Target 直接作為接收量，其餘按補 0 |
| F2 | F指定模式 | 僅 `Target` 店舖可接收（ND/RF 均可），Target 直接作為接收量；可設定 HD 轉出選項；Windy 目標店優先從同 OM 無 Target 店提取 |
| F3 | 目標性補0 | 繼承 F2 + RF轉出保留2件 + RF按最高庫存優先轉出 + RF跨OM不降級 |
| ND1 | ND 同 OM 轉貨 | ND 店舖可互轉（同 OM），按銷量智能排序，接收上限 2×過去2個月銷量，可限制單一出貨店配對接收店數 |
| ND2 | ND 混合 OM 轉貨 | ND 店舖可互轉（跨 OM），Windy 只轉 Windy，接收上限 2×過去2個月銷量，可限制單一出貨店配對接收店數 |
| ND3 | ND 限同OM轉貨(補0) | ND 同 OM 轉貨，轉出保留 3 件，只補零庫存 ND 店（參考C1），按銷量排序，可限制單一出貨店配對接收店數 |
| 精簡SKU(限同OM) | 精簡SKU 調貨 | RF 超出 Cap（Max(Safety×2, 過去2個月銷量×2)）部分轉出，ND 全轉出，剩餘退回 D001，僅同 OM |
| 精簡SKU(跨OM) | 精簡SKU 跨 OM 調貨 | 同精簡SKU(限同OM)，允許跨 OM，含 Windy/HD 限制 |
| 精簡SKU(退D001) | 精簡SKU 全數退回 D001 | RF 超出 Cap 全數回退 D001，ND 全數回退 D001，不配對 RF 接收 |

## 介面操作流程

1. 上傳 Excel。
2. 選擇模式。
3. 若為 B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/E1/E1b/E2/ND1/ND2/ND3，可設定接收店數限制。
4. 點擊「生成調貨建議」。
5. 檢視表格與統計。
6. 下載 Excel 報表。

### 模式教學分頁

系統頂部提供「模式教學」分頁，包含：

- **全局規則流程圖**：ND 限制、最高動銷店保護、避免雙重角色、單件後處理
- **8 組模式教學**（按業務場景分組）：
  1. 基礎調貨（A / B）
  2. B 特別模式（B2 / B2a / B2L / B2La）
  3. B 跨 OM 特別模式（B3 / B3a / B3L / B3La）
  4. 重點補 0 系列（C / C1 / C2）
  5. 清貨模式（D / D2）
  6. 強制轉出系列（E1 / E1b / E2）
   7. 目標優化系列（F / F2 / F3）
  8. ND/SKU 專項（ND1 / ND2 / ND3 / 精簡SKU）
- 每個模式含：適用場景、風險等級、轉出/接收篩選流程圖、配對優先級、數字情境範例、模式對比
- **模式選擇決策指南**：根據業務需求快速找到合適模式

## 輸出內容

- 工作表 1：`調貨建議 (Transfer Recommendations)`
- 調貨明細、來源/接收分類、庫存變化、備註
- 工作表 2：`統計摘要 (Summary Dashboard)`
- KPI、按 Article/OM 統計、來源/接收類型分佈

## 測試

建議先跑與本次模式改動最相關的測試：

```bash
python -m pytest tests/test_b2_b3_source_receive_site_limit.py tests/test_b2_priority.py tests/test_b2_fix.py tests/test_b2a_b3a_t_no_source.py tests/test_modes_simple.py -q
```

## 專案結構

- `app.py`：Streamlit 介面與操作流程（含雙分頁：調貨系統 / 模式教學）
- `business_logic.py`：來源/接收識別與配對規則
- `services/matching_engine.py`：核心配對引擎（轉移量計算、前置過濾、多回合匹配）
- `services/ai_client.py`：AI API 封裝（OpenRouter、session cache、錯誤降級）
- `services/ai_advisor.py`：AI 模式建議（summary builder、prompt、parser）
- `services/ai_auditor.py`：AI 邏輯審計（payload builder、prompt、parser）
- `data_processor.py`：Excel 讀取、驗證、欄位標準化、預設資料補齊
- `excel_generator.py`：報表匯出
- `ui/tutorial.py`：模式教學分頁（27 種模式圖例化教學）
- `調貨模式詳解.txt`：中文規則細節
- `VERSION.md`：版本紀錄

## 常見問題

### 為什麼沒有產生建議？

- 檢查是否同時存在可轉出來源與可接收需求。
- 檢查 `RP Type`、`Type`、`ALL`、`Target` 是否符合所選模式。
- 確認資料中沒有把所有 RF 店舖都變成受保護狀態。

### 哪些模式可以使用接收店數限制？

- 在側欄選擇 B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/E1/E1b/E2/ND1/ND2/ND3 後，會出現「出貨店舖接收店數限制」。
- 選 `優先 1 間`：同一 SKU 下，每個來源店最多配對 1 個接收店（最集中）。
- 選 `最多 2 間`：同一 SKU 下，每個來源店最多配對 2 個接收店。
- 選 `不限制`：不套用該限制。

### E 模式沒有作用？

- E1/E1b/E2 僅處理 `ALL` 欄位有標記的資料行。
- 請確認 `ALL` 欄位存在，且要轉出的行不是空白。

## 版本

- 目前版本：`v2.19.0`
- 詳細異動請見 `VERSION.md`
