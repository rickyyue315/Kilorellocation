# KiLo 庫存調貨建議系統 v2.9.1

## 系統概述

KiLo 是基於 Streamlit 的庫存調貨建議系統，依據庫存、銷量、安全庫存與 MOQ，自動產生跨店鋪調貨建議。

系統目前為 **二十二模式**：

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
- E1：強制轉出（僅同 OM）
- E1b：強制轉出（僅同 OM，優先類型接收）
- E2：強制轉出（可跨 OM）
- F：目標優化
- F2：F指定模式（僅 Target 店舖接收）
- **ND1：ND 同 OM 轉貨（ND 店舖互轉，限同 OM）**
- **ND2：ND 混合 OM 轉貨（ND 店舖互轉，允許跨 OM）**

## 核心規則

- ND 店舖在所有模式下僅可轉出，不可接收（**ND1/ND2 模式例外**，允許 ND 互轉）。
- RF 最高有效銷量店舖受保護，不會被選為轉出方。
- 同一 SKU 下，轉出店舖不可同時為接收店舖。
- D 模式會調整轉移量，避免轉出後剛好剩 1 件。
- **所有模式均套用後處理**：避免單筆調貨數量為 1 件（例外：若出貨店舖該 SKU 可調總量本身只有 1 件則保留）。
- E1/E1b/E2 僅處理 `ALL` 欄位有標記的行。
- B2/B2a/B2L/B2La/B3/B3a/B3L/B3La：若出貨店為 Type=M（Mix）且其總銷量高於目標店，該配對會被取消（`總銷量 = Last Month Sold Qty + MTD Sold Qty`）。
- B3/C2/E2/F/F2 的跨 OM 規則：
- HD 來源不可轉到 HA/HB/HC。
- Windy 來源僅可轉到 Windy。

## 功能重點

- 二十二模式調貨策略。
- B2/B2a/B2L/B2La/B3/B3a/B3L/B3La 可在介面設定「單一出貨店舖最多配對接收店舖數」：`優先 1 間` / `最多 2 間` / `不限制`。
- B2/B2a/B2L/B2La/B3/B3a/B3L/B3La Mix 高銷量保護：避免高銷售 Mix 店舖被轉去較低銷售店舖。
- **單筆1件調貨後處理**：所有模式輸出後統一消除單件調貨，優先重新平衡（Rebalance），次選合併至高銷量目標店（Merge）。
- 自動資料預處理（型別轉換、缺值補齊、異常校正）。
- 內建店舖預設資料（缺少 OM/Type 時自動補值）。
- 輸出 Excel（調貨建議 + 統計摘要）。

## 系統需求

- Python 3.8+
- 依賴：`pandas`、`openpyxl`、`streamlit`、`numpy`、`xlsxwriter`、`ftfy`

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
- `Target`：F / F2

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
| E1 | 強制轉出 | 僅同 OM，僅處理 `ALL` 標記 |
| E1b | 強制轉出優先類型接收 | 僅同 OM，接收優先 Type=T/M |
| E2 | 強制轉出跨 OM | 優先同 OM，可跨 OM，僅處理 `ALL` 標記 |
| F | 目標優化 | `Target` 優先接收，其餘按補 0 |
| F2 | F指定模式 | 僅 `Target` 店舖可接收，非 Target RF 店舖不接收 |
| ND1 | ND 同 OM 轉貨 | ND 店舖可互轉（同 OM），按銷量智能排序，接收上限 2×兩月銷量，可限制單一出貨店配對接收店數 |
| ND2 | ND 混合 OM 轉貨 | ND 店舖可互轉（跨 OM），Windy 只轉 Windy，接收上限 2×兩月銷量，可限制單一出貨店配對接收店數 |

## 介面操作流程

1. 上傳 Excel。
2. 選擇模式。
3. 若為 B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/E1/E1b/E2/ND1/ND2，可設定接收店數限制。
4. 點擊「生成調貨建議」。
5. 檢視表格與統計。
6. 下載 Excel 報表。

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

- `app.py`：Streamlit 介面與操作流程
- `business_logic.py`：來源/接收識別與配對規則
- `data_processor.py`：Excel 讀取、驗證、欄位標準化、預設資料補齊
- `excel_generator.py`：報表匯出
- `調貨模式詳解.txt`：中文規則細節
- `VERSION.md`：版本紀錄

## 常見問題

### 為什麼沒有產生建議？

- 檢查是否同時存在可轉出來源與可接收需求。
- 檢查 `RP Type`、`Type`、`ALL`、`Target` 是否符合所選模式。
- 確認資料中沒有把所有 RF 店舖都變成受保護狀態。

### 哪些模式可以使用接收店數限制？

- 在側欄選擇 B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/E1/E1b/E2/ND1/ND2 後，會出現「出貨店舖接收店數限制」。
- 選 `優先 1 間`：同一 SKU 下，每個來源店最多配對 1 個接收店（最集中）。
- 選 `最多 2 間`：同一 SKU 下，每個來源店最多配對 2 個接收店。
- 選 `不限制`：不套用該限制。

### E 模式沒有作用？

- E1/E1b/E2 僅處理 `ALL` 欄位有標記的資料行。
- 請確認 `ALL` 欄位存在，且要轉出的行不是空白。

## 版本

- 目前版本：`v2.9.1`
- 詳細異動請見 `VERSION.md`
