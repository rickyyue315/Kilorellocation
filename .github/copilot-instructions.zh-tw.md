# KiLo 庫存調貨建議系統 - AI 編碼代理指引

## 系統架構

這是一個**基於 Streamlit 的庫存調貨建議系統**，用於零售營運。程式碼遵循模組化架構，職責分離清晰：

- **app.py**: Streamlit 網頁介面（入口點，運行於 8501 端口）
- **data_processor.py**: Excel 檔案處理、資料驗證與預處理
- **business_logic.py**: 核心調貨匹配演算法與業務規則
- **excel_generator.py**: Excel 報表生成與格式化輸出
- **Geminiapp.py**: 舊版/替代實作（不再主動維護）

## 五種調貨模式（五模式系統）

系統實作**模式特定的調貨邏輯** - 修改業務規則時務必確認當前模式：

1. **模式 A（保守轉貨）**: 嚴格保護安全庫存，20% 轉出上限，僅使用 RF過剩轉出
2. **模式 B（加強轉貨）**: 積極調貨，50% 上限，允許 RF加強轉出（可低於安全庫存）
3. **模式 C（重點補0）**: 針對庫存 ≤1 的店鋪，30% 上限，特殊的「重點補0」接收類型
4. **模式 D（清貨轉貨）**: ND 店鋪零銷售記錄，**特殊的「避免留 1 件餘貨」規則**
5. **模式 E（強制轉出）**: 強制轉出標記的商品（透過 *ALL* 欄位），全數轉出，具特殊 OM/HD 店鋪邏輯

**關鍵**: 
- 模式 D 具有獨特邏輯，防止轉出後剩餘正好 1 件 - 見 [business_logic.py](business_logic.py#L430-L448)
- 模式 E 僅處理輸入檔案中被標記為 *ALL* 的商品 - 見 [business_logic.py](business_logic.py#L46-L75)

## 核心業務規則（通用規則）

### 店鋪類型限制
- **ND 店鋪**: 所有模式下只能作為轉出方（永不作為接收方）- 強制執行於 [business_logic.py](business_logic.py#L189-L190) 和 [business_logic.py](business_logic.py#L417-L418)
- **RF 店鋪**: 可同時作為轉出方和接收方
- **最高銷量 RF 店鋪**: 受保護不會作為轉出方（見 [business_logic.py](business_logic.py#L73-L76)）

### 優先級匹配順序
匹配遵循嚴格優先級（見 `_match_by_priority` 於 [business_logic.py](business_logic.py#L322-L398)）：
1. ND轉出 → 緊急缺貨補貨
2. ND轉出 → 潛在缺貨補貨
3. RF過剩轉出 → 緊急缺貨補貨
4. RF過剩轉出 → 潛在缺貨補貨
5. RF加強轉出 → 緊急缺貨補貨
6. RF加強轉出 → 潛在缺貨補貨
7. （僅模式 C）RF轉出 → 重點補0

### 調貨約束條件
- 同一店鋪不能自我調貨
- 作為轉出方的店鋪**不能同時作為接收方**（透過 `transfer_sites` 集合追蹤）
- 模式 C 追蹤每個店鋪的累計接收數量以達成目標

## 關鍵資料欄位

必需欄位（見 [data_processor.py](data_processor.py#L17-L22)）：
- `Article`（12 位數零填充字串 - 關鍵格式）
- `OM`、`RP Type`、`Site`
- `SaSa Net Stock`、`Pending Received`、`Safety Stock`
- `Last Month Sold Qty`、`MTD Sold Qty`、`MOQ`
- `Article Description`（備用欄位為 `Article Long Text (60 Chars)`）

選用欄位：
- `ALL`（模式 E 專用：標記商品強制轉出，不區分大小寫）

計算欄位：
- `Effective Sold Qty` = `Last Month Sold Qty` + `MTD Sold Qty`
- 總可用庫存 = `SaSa Net Stock` + `Pending Received`

## 開發工作流程

### 運行應用程式
```bash
# Windows（自動設置虛擬環境）
run.bat

# Linux/macOS
./run.sh

# 手動執行
streamlit run app.py
```

### 測試
- `test_mode_d.py`：模式 D 清貨邏輯的專用測試
- 透過 UI 使用範例 Excel 檔案進行手動測試

### 常見修改31)）
2. 更新 `identify_sources` 以定義轉出方選擇邏輯
3. 更新 `identify_destinations` 以定義接收方條件
4. 如需要，在 `match_transfers` 中新增模式特定匹配邏輯
5. 更新 [app.py](app.py#L69-L74出方選擇邏輯
3. 更新 `identify_destinations` 以定義接收方條件
4. 如需要，在 `match_transfers` 中新增模式特定匹配邏輯
5. 更新 [app.py](app.py#L69-L73) 中的 UI 下拉選單

**修改調貨上限**：
- 檢查 `identify_sources` 中模式特定的 `upper_limit` 計算（[business_logic.py](business_logic.py#L82-L163)）
- 模式 A：20% 上限，模式 B：50% 上限，模式 C：30% 上限且最多 3 件

## 關鍵模式

### Article ID 格式
務必使用 12 位數零填充字串：`df['Article'].astype(str).str.zfill(12)` - 見 [data_processor.py](data_processor.py#L49-L50)

### 接收類型命名
建議使用 `'Destination Type'`，但舊程式碼可能使用 `'Receive Type'` - 需同時處理（[excel_generator.py](excel_generator.py#L58-L59)）

### 避免 1 件餘貨
模式 D 實作特殊邏輯，確保剩餘庫存為 0 或 ≥2 - 永不剛好為 1 件（見 [business_logic.py](business_logic.py#L430-L448)）

## 外部相依套件

- **Streamlit**: Web 框架（預設無熱重載）
- **pandas**: 資料處理（注意資料型別轉換）
- **xlsxwriter**: Excel 匯出（由 `excel_generator.py` 使用）
- **matplotlib/seaborn**: 圖表（需要 SimHei 字型以顯示中文）

## 文件說明

- [README.md](README.md)：面向使用者的文件，含安裝與使用說明
- [VERSION.md](VERSION.md)：版本更新記錄，含詳細歷史
- [三種調貨模式詳解.txt](三種調貨模式詳解.txt)：業務邏輯中文詳解（涵蓋模式 A-E）

## 已知注意事項

- `Geminiapp.py` 為舊版替代實作 - 除非明確要求，否則避免修改
- 中文字型處理：使用 SimHei/Arial Unicode MS - 見 [app.py](app.py#L27-L28)
- 有銷售記錄的 ND 店鋪使用一般「ND轉出」分類，而非「ND清貨轉出」
- 模式 E 需要 Excel 中的 `ALL` 欄位以標記商品強制轉出（不區分大小寫）
- 模式 E 對 HD 店鋪有特殊邏輯，防止轉出至 HA/HB/HC 店鋪
