# KiLo 庫存調貨建議系統 v1.9.9

## 系統概述

KiLo 庫存調貨建議系統 v1.9.9 是一個基於 Streamlit 的智能庫存調配管理系統。專為零售運營設計，根據庫存、銷量、安全庫存和 MOQ 等數據，自動生成跨店鋪商品調貨建議，優化庫存分布並滿足銷售需求。

本系統採用**五模式設計**，靈活應對不同轉貨場景：
- **A 模式(保守轉貨)**：優先保護安全庫存，20% 轉出上限
- **B 模式(加強轉貨)**：積極處理滯銷品，50% 轉出上限
- **C 模式(重點補0)**：重點補充庫存為 0-1 的店鋪，30% 轉出上限
- **D 模式(清貨轉貨)**：針對 ND 店鋪無銷售記錄的清貨，特殊避免 1 件餘貨規則
- **E 模式(強制轉出)**：針對標記為 *ALL* 的商品全數強制轉出，優先同OM配對，支持跨OM(HD除外)

## 功能特點

- ✅ **五模式系統**：A(保守轉貨) / B(加強轉貨) / C(重點補0) / D(清貨轉貨) / E(強制轉出)
- ✅ **優先級匹配算法**：基於轉出類型和接收優先級的智能調配
- ✅ **ND/RF 店鋪智慧識別**：自動區分店鋪類型，應用不同規則
  - ND 店鋪：僅可轉出，不可接收
  - RF 店鋪：可轉出、可接收
- ✅ **轉出類型判斷**：
  - RF 過剩轉出（轉出後 ≥ 安全庫存）
  - RF 加強轉出（轉出後 < 安全庫存）
  - ND 轉出 / ND 清貨轉出（D 模式特有）
- ✅ **接收優先級管理**：
  - 緊急缺貨補貨（無庫存，曾有銷售）
  - 潛在缺貨補貨（庫存 < 安全庫存）
  - 重點補0（C 模式，庫存 ≤ 1）
- ✅ **數據預處理與驗證**：自動類型轉換、缺失值處理、異常值校正
- ✅ **質量檢查**：確保調貨建議準確、合理、無衝突
- ✅ **可視化分析**：調貨統計、轉出類型分布、接收優先級分析
- ✅ **Excel 批量導出**：生成包含調貨建議和統計摘要的完整報告
- ✅ **D 模式特殊功能**：避免 1 件餘貨規則，確保清貨效率
 
## 系統要求

- Python 3.8 或更高版本
- 依賴包：pandas, openpyxl, streamlit, numpy, xlsxwriter, matplotlib, seaborn
 
## 安裝與部署
 
### Windows用戶
 
1. 雙擊運行 `run.bat` 文件
2. 系統將自動創建虛擬環境並安裝依賴
3. 瀏覽器將自動打開應用程序
 
### Linux/macOS用戶
 
1. 在終端中運行：
```bash
chmod +x run.sh
./run.sh
```
 
2. 系統將自動創建虛擬環境並安裝依賴
3. 瀏覽器將自動打開應用程序
 
### 手動安裝
 
1. 克隆項目
```bash
git clone <repository-url>
cd inventory_transfer_system
```
 
2. 創建虛擬環境
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```
 
3. 安裝依賴
```bash
python install_dependencies.py
# 或者使用 pip install -r requirements.txt
```
 
4. 運行應用
```bash
streamlit run app.py
```
 
應用程序將在瀏覽器中打開，默認地址為 `http://localhost:8501`
 
## 依賴安裝問題解決
 
如果遇到依賴安裝問題，請嘗試以下解決方案：
 
### 1. 使用專用安裝腳本
 
```bash
python install_dependencies.py
```
 
這個腳本會檢查並安裝所有必需的依賴包，提供詳細的安裝狀態信息。
 
### 2. 手動安裝核心依賴
 
```bash
pip install pandas openpyxl streamlit numpy xlsxwriter matplotlib seaborn
```
 
### 3. 升級pip
 
```bash
python -m pip install --upgrade pip
```
 
### 4. 使用國內鏡像源
 
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```
 
## 使用說明

### 1. 上傳數據文件

上傳包含庫存和銷售數據的 Excel 文件（.xlsx 格式）。

**必需欄位：**
- `Article`：商品編號（12 位文本格式，系統會自動補零）
- `Article Description` 或 `Article Long Text (60 Chars)`：商品描述（二選一）
- `OM`：OM 編號
- `RP Type`：店鋪類型（ND 或 RF）
- `Site`：店鋪代碼
- `MOQ`：最低派貨數量
- `SaSa Net Stock`：淨庫存
- `Pending Received`：待收貨數量
- `Safety Stock`：安全庫存
- `Last Month Sold Qty`：上月銷量
- `MTD Sold Qty`：本月銷量

系統會自動計算：
- `Effective Sold Qty` = `Last Month Sold Qty` + `MTD Sold Qty`（有效銷量）
- 總庫存 = `SaSa Net Stock` + `Pending Received`

### 2. 選擇轉貨模式

在側邊欄選擇適合的轉貨模式：

| 模式 | 名稱 | 轉出上限 | 適用場景 | 特徵 |
|------|------|--------|--------|------|
| **A** | 保守轉貨 | 20% | 風險厭惡 | 優先保護安全庫存，轉出後 ≥ 安全庫存 |
| **B** | 加強轉貨 | 50% | 滯銷品清理 | 積極轉出，可能低於安全庫存 |
| **C** | 重點補0 | 30% / 3 件上限 | 零庫存補貨 | 重點補充庫存 ≤ 1 的店鋪 |
| **D** | 清貨轉貨 | N/A | ND 清貨 | ND 無銷售清貨，避免 1 件餘貨 |

### 3. 系統數據預處理

- 自動驗證數據格式和完整性
- 執行類型轉換（Article 轉為 12 位文本、數值驗證等）
- 處理缺失值和異常數據
- 計算派生欄位

### 4. 生成調貨建議

點擊「生成調貨建議」按鈕啟動分析流程：
- 識別轉出候選店鋪（Sources）
- 識別接收候選店鋪（Destinations）
- 執行優先級匹配算法
- 進行完整性質量檢查

### 5. 查看結果

系統呈現：
- 調貨建議統計（轉出總量、接收總量、涉及店鋪數等）
- 調貨建議詳情表格
- 轉出類型分布（RF 過剩 vs RF 加強 vs ND 轉出）
- 接收優先級分布（緊急缺貨 vs 潛在缺貨 vs 重點補0）

### 6. 下載結果

點擊「下載調貨建議 Excel 文件」按鈕獲取完整報告：

**包含工作表：**
1. **Transfer Recommendations**（調貨建議）
   - Article, OM, Transfer Site, Receive Site
   - Effective Sold Qty, Transfer Qty, Source Type, Receive Type
   - 轉出後庫存, 接收後庫存 等詳細信息

2. **Summary Dashboard**（統計摘要）
   - 調貨統計：轉出總量、接收總量、涉及店鋪
   - 轉出類型分析：RF 過剩 / RF 加強 / ND 轉出
   - 接收優先級分析：緊急缺貨 / 潛在缺貨 / 重點補0
 
## 業務邏輯詳解

### 核心概念

**有效銷量**
- 有效銷量 = `Last Month Sold Qty` + `MTD Sold Qty`
- 用於判斷店鋪銷售活躍度和優先級排序

**店鋪類型限制**
- **ND 店鋪**：在所有模式下只能作為轉出源，不可作為接收方
- **RF 店鋪**：可以既轉出也接收

**轉出上限規則**
- A 模式：min(基礎可轉出, 庫存 × 20%, 最少 2 件)
- B 模式：min(基礎可轉出, 庫存 × 50%, 最少 2 件)
- C 模式：min(基礎可轉出, 庫存 × 30%, 最多 3 件)
- D 模式：針對 ND 無銷售清貨，特殊避免 1 件餘貨邏輯

**同源限制**
- 同一 Article+OM 組合中，高銷量 RF 店鋪受保護（不能轉出）
- 轉出和接收店鋪不能相同
- 同一 SKU 的轉出店鋪不能同時接收該 SKU

---

### A 模式(保守轉貨) - 轉出規則

**優先級 1：ND 類型轉出**
- 條件：`RP Type == 'ND'` 且有庫存
- 可轉出量：全部 `SaSa Net Stock`
- 轉出類型：ND 轉出

**優先級 2：RF 類型過剩轉出**
- 條件 1：`RP Type == 'RF'`
- 條件 2：庫存充足 = `SaSa Net Stock + Pending Received > Safety Stock`
- 條件 3：該店鋪不是高銷售店鋪（有效銷量非最高值）
- 條件 4：轉出後剩餘 ≥ 安全庫存

計算公式：
```
基礎可轉出 = (SaSa Net Stock + Pending Received) - Safety Stock
上限控制 = max((SaSa Net Stock + Pending Received) × 20%, 2)
實際轉出 = min(基礎可轉出, 上限控制)
```

轉出類型：RF 過剩轉出

---

### B 模式(加強轉貨) - 轉出規則

**優先級 1：ND 類型轉出**
- 條件：`RP Type == 'ND'` 且有庫存
- 可轉出量：全部 `SaSa Net Stock`
- 轉出類型：ND 轉出

**優先級 2：RF 類型轉出**
- 條件 1：`RP Type == 'RF'`
- 條件 2：庫存 > MOQ + 1
- 條件 3：該店鋪不是高銷售店鋪

計算公式：
```
基礎可轉出 = (SaSa Net Stock + Pending Received) - (MOQ + 1)
上限控制 = max((SaSa Net Stock + Pending Received) × 50%, 2)
實際轉出 = min(基礎可轉出, 上限控制)
```

轉出類型判斷：
- 轉出後 ≥ Safety Stock → RF 過剩轉出
- 轉出後 < Safety Stock → RF 加強轉出

---

### C 模式(重點補0) - 轉出規則

**優先級 1：ND 類型轉出**
- 條件：`RP Type == 'ND'` 且有庫存
- 可轉出量：全部 `SaSa Net Stock`
- 轉出類型：ND 轉出

**優先級 2：RF 類型轉出**
- 條件 1：`RP Type == 'RF'`
- 條件 2：庫存 > MOQ + 1
- 條件 3：該店鋪不是高銷售店鋪

計算公式：
```
基礎可轉出 = (SaSa Net Stock + Pending Received) - (MOQ + 1)
上限控制 = max(min((SaSa Net Stock + Pending Received) × 30%, 3), 1)
實際轉出 = min(基礎可轉出, 上限控制)
```

轉出類型判斷：
- 轉出後 ≥ Safety Stock → RF 過剩轉出
- 轉出後 < Safety Stock → RF 加強轉出

**特殊接收規則（重點補0）**
- 目標：補充庫存 ≤ 1 的 RF 店鋪
- 目標數量：max(Safety Stock × 0.5, 3)
- 需求數量：max(0, 目標數量 - 總庫存)
- 追蹤累計接收，確保達到目標

---

### D 模式(清貨轉貨) - 轉出規則

**優先級 1：ND 類型清貨轉出**
- 條件 1：`RP Type == 'ND'`
- 條件 2：`Last Month Sold Qty == 0` AND `MTD Sold Qty == 0`（無銷售記錄）
- 可轉出量：全部 `SaSa Net Stock`
- 轉出類型：ND 清貨轉出

**特殊規則：避免 1 件餘貨**

D 模式實現核心邏輯以確保清貨效率，避免留下單件無法有效利用：

- 情況 1：如果轉出量會導致剩餘 1 件
  - 嘗試：多轉 1 件（剩餘 0 件）
  - 若不可行：少轉 1 件（剩餘 2 件）
  - 確保最終剩餘為 0 或 ≥ 2

代碼實現邏輯：
```python
remaining = sasa_net_stock - transfer_qty
if remaining == 1:
    # 嘗試多轉 1 件
    if transfer_qty + 1 <= sasa_net_stock and (transfer_qty + 1) <= need_qty:
        transfer_qty += 1  # 剩餘變為 0
    else:
        transfer_qty -= 1  # 多轉失敗，少轉改為 2 件
```

**優先級 2：RF 類型轉出**
- 遵循 A 模式的規則
- 條件 1：`RP Type == 'RF'`
- 條件 2：庫存充足
- 條件 3：該店鋪不是高銷售店鋪
- 條件 4：轉出後 ≥ Safety Stock

轉出類型：RF 過剩轉出（D 模式不使用 RF 加強轉出）

---

### 接收規則（所有模式通用）

**優先級 1：緊急缺貨補貨**
- 條件 1：`RP Type == 'RF'`（ND 店鋪不能接收）
- 條件 2：完全無庫存 = `SaSa Net Stock == 0`
- 條件 3：曾有銷售 = `Effective Sold Qty > 0`
- 需求數量：`Safety Stock`

**優先級 2：潛在缺貨補貨**
- 條件 1：`RP Type == 'RF'`
- 條件 2：庫存不足 = `SaSa Net Stock + Pending Received < Safety Stock`
- 條件 3：該店鋪是高銷售店鋪（有效銷量是最高值）
- 需求數量：`Safety Stock - (SaSa Net Stock + Pending Received)`

**優先級 3：重點補0（僅 C 模式）**
- 條件 1：`RP Type == 'RF'`
- 條件 2：總庫存 ≤ 1 = `SaSa Net Stock + Pending Received ≤ 1`
- 目標數量：`max(Safety Stock × 0.5, 3)`
- 需求數量：`目標數量 - 總庫存`
- 追蹤累計接收，防止超目標

---

### 匹配優先級順序

系統按以下順序進行優先級匹配：

**A/B/D 模式：**
1. ND 轉出（或 ND 清貨轉出） → 緊急缺貨
2. ND 轉出（或 ND 清貨轉出） → 潛在缺貨
3. RF 過剩轉出 → 緊急缺貨
4. RF 過剩轉出 → 潛在缺貨
5. RF 加強轉出 → 緊急缺貨（B 模式）
6. RF 加強轉出 → 潛在缺貨（B 模式）

**C 模式（特殊）：**
1. ND 轉出 → 緊急缺貨
2. ND 轉出 → 潛在缺貨
3. RF 過剩轉出 → 緊急缺貨
4. RF 過剩轉出 → 潛在缺貨
5. RF 加強轉出 → 緊急缺貨
6. RF 加強轉出 → 潛在缺貨
7. RF 轉出（任何類型） → 重點補0

**匹配數量計算：**
```
transfer_qty = min(轉出方可轉出, 接收方需求)
```

**數量優化（可選）：**
- 如果匹配 1 件且未違反安全庫存，嘗試調高到 2 件
- D 模式特殊處理：確保轉出後不會剩 1 件
 
## 質量檢查

系統自動執行以下驗證以確保調貨建議的準確性和完整性：

- ✓ 轉出與接收的 Article 必須完全一致
- ✓ Transfer Qty 必須為正整數
- ✓ Transfer Qty 不得超過轉出店鋪的原始 SaSa Net Stock
- ✓ Transfer Site 和 Receive Site 不能相同（禁止自轉）
- ✓ 最終 Article 欄位必須是 12 位文本格式
- ✓ 同一 SKU 的轉出店鋪不能同時作為接收店鋪
- ✓ 接收店鋪不能是 ND 類型（ND 店鋪在所有模式下都只能轉出）
- ✓ C 模式：檢查累計接收數量是否超過目標數量
- ✓ D 模式：驗證轉出後剩餘庫存不會恰好為 1 件
 
## 故障排除

### 常見問題

1. **文件上傳失敗**
   - 確保文件格式為 .xlsx（不支持 .xls）
   - 檢查文件是否損壞或被其他程序鎖定
   - 確認文件大小在合理範圍內（建議 < 50MB）
   - 嘗試重新保存文件

2. **數據處理錯誤**
   - 檢查文件是否包含所有必需欄位
   - 確認 Article 欄位包含數值數據（會自動轉換為 12 位文本）
   - 檢查數值欄位是否包含非法字符（特殊字符、文本混合等）
   - 驗證 RP Type 欄位只包含 "ND" 或 "RF"
   - 確認沒有完全空白的行

3. **沒有生成調貨建議**
   - 確認數據中同時包含 ND 和 RF 類型的店鋪
   - 檢查是否有足夠的庫存和銷售數據
   - 驗證是否所有 RF 店鋪都受保護（最高銷售店鋪不能轉出）
   - D 模式：確保有 ND 店鋪無銷售記錄的商品

4. **模式選擇問題**
   - 確認選擇了正確的轉貨模式（A/B/C/D）
   - 不同模式適用於不同場景，選擇應符合業務需求
   - 嘗試用不同模式重新分析，比較結果

5. **依賴安裝失敗**
   - 嘗試使用專用安裝腳本：`python install_dependencies.py`
   - 手動安裝核心依賴：`pip install pandas openpyxl streamlit numpy xlsxwriter matplotlib seaborn`
   - 升級 pip：`python -m pip install --upgrade pip`
   - 考慮使用國內鏡像源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/`
   - 確保 Python 版本 ≥ 3.8

6. **圖表無法顯示中文**
   - 系統默認使用 SimHei 字體
   - Windows：確保已安裝 SimHei 或 Arial Unicode MS 字體
   - Linux/Mac：安裝中文字體包（如 `apt-get install fonts-noto-cjk`）
   - 作為備選，系統會自動使用 DejaVu Sans（但無中文支持）

### 日誌查看

應用程序運行時會輸出日誌信息，包括：
- 數據處理進度和統計信息
- 轉出/接收候選識別結果
- 質量檢查詳細信息
- 錯誤和警告信息

在終端窗口查看實時日誌幫助調試問題。
 
## 技術架構

### 系統結構

```
KiLo Reallocation/
├── app.py                          # Streamlit Web UI 主程序 (v1.9.8)
├── business_logic.py               # 調貨業務邏輯模組 (v1.9.8)
├── data_processor.py               # 數據預處理和驗證 (v1.8.1)
├── excel_generator.py              # Excel 報告生成器 (v1.8)
├── Geminiapp.py                    # 遺留實現版本（不維護）
├── install_dependencies.py         # 依賴安裝腳本
├── requirements.txt                # 依賴包清單
├── README.md                       # 本文件
├── VERSION.md                      # 版本變更日誌
├── 三種調貨模式詳解.txt            # 中文業務邏輯詳解
├── run.bat                         # Windows 啟動腳本
├── run.sh                          # Linux/macOS 啟動腳本
├── test_mode_d.py                  # D 模式測試
└── __pycache__/                    # Python 緩存文件
```

### 核心模組說明

| 模組 | 功能 | 版本 | 依賴 |
|------|------|------|------|
| `app.py` | Streamlit UI、用戶交互、結果展示 | v1.9.8 | streamlit, pandas, matplotlib, seaborn |
| `business_logic.py` | 轉出/接收識別、優先級匹配、調貨算法 | v1.9.8 | pandas, numpy |
| `data_processor.py` | Excel 讀取、數據驗證、類型轉換、預處理 | v1.8.1 | pandas, openpyxl |
| `excel_generator.py` | Excel 報告生成、格式化輸出 | v1.8 | xlsxwriter, pandas |

### 依賴包

| 包名 | 用途 | 最小版本 |
|------|------|---------|
| streamlit | Web 框架和 UI | 1.0+ |
| pandas | 數據處理和分析 | 1.1+ |
| openpyxl | Excel 讀取 | 3.0+ |
| xlsxwriter | Excel 寫入和格式化 | 3.0+ |
| numpy | 數值計算 | 1.19+ |
| matplotlib | 圖表繪製 | 3.3+ |
| seaborn | 統計圖表 | 0.11+ |

### 數據流

```
Excel 文件上傳
    ↓
data_processor.py (讀取、驗證、預處理)
    ↓
business_logic.py (識別源和目的地、優先級匹配)
    ↓
調貨建議生成
    ↓
excel_generator.py (格式化輸出報告)
    ↓
下載 Excel 文件
```

### 關鍵設計模式

**模式工廠模式**：不同轉貨模式共享相同接口，通過 `mode` 參數切換邏輯

**優先級隊列**：按優先級順序匹配，確保高優先級需求優先滿足

**貪心匹配**：每次匹配取最小可轉/需求數量，逐步消耗庫存和需求

**約束檢查**：多層次檢查確保數據完整性和業務規則合規性
 
## 更新日誌

### v1.9.8 (2026-01-26)

**新增功能：**
- ✨ 實現 D 模式（清貨轉貨）- 針對 ND 無銷售商品清貨
- ✨ D 模式特殊邏輯：避免 1 件餘貨規則
- ✨ 升級系統為真正的四模式系統（A/B/C/D）

**優化改進：**
- 📊 增強 ND 店鋪限制：所有模式下都只能轉出，不能接收
- 🔧 優化 D 模式轉出識別：準確判斷無銷售記錄的 ND 店鋪
- 📈 改進日誌記錄：更詳細的模式選擇和處理過程
- 📝 更新文檔和測試用例

**質量檢查增強：**
- ✓ 新增 D 模式餘貨檢查
- ✓ 優化 ND 店鋪限制驗證

**測試覆蓋：**
- 新增 `test_mode_d.py` 專項測試

---

### v1.9 (2025-10-01)

**架構調整：**
- 簡化系統設計：從複雜的模式組合回歸到清晰的四模式
- 規範模式命名和功能邊界

**轉出類型優化：**
- 實現轉出類型動態判斷：
  - RF 過剩轉出：轉出後 ≥ 安全庫存
  - RF 加強轉出：轉出後 < 安全庫存

**接收條件改進：**
- 統一接收判斷：`SaSa Net Stock + Pending Received < Safety Stock`
- 強化優先級管理

**統計分析增強：**
- 添加更詳細的轉出類型分析
- 包含庫存變化情況展示

---

### v1.8.1 (2025-10-01)

**Bug 修復：**
- 🐛 修復依賴安裝問題
- 🐛 修復 Excel 讀取格式兼容性

**功能增強：**
- ✨ 添加專用依賴安裝腳本
- ✨ 增強錯誤處理和日誌記錄
- ✨ 適配真實數據文件格式

**文檔改進：**
- 📝 改進安裝說明
- 📝 添加故障排除指南

---

### v1.8 (2025-10-01)

**主要功能：**
- ✨ 新增三模式系統：A(保守轉貨) / B(加強轉貨) + C(按 OM 調配)
- ✨ 實現分組功能和站點管理
- ✨ 添加 MOQ 欄位支持

**數據和展示：**
- 📊 新增數據可視化圖表
- 📊 更新 Excel 輸出格式
- 📊 完善統計摘要儀表板

**質量改進：**
- ✓ 增強數據驗證和錯誤處理
- ✓ 完善質量檢查機制

---

### v1.7 (2023-09-17)

**初始版本：**
- ✨ 基礎調貨建議功能
- ✨ 數據預處理和驗證
- ✨ Excel 導出支持
- ✨ 簡單統計分析
 
## 開發指南

### 環境設置

**1. 克隆或下載項目**
```bash
git clone <repository-url>
cd kilo-reallocation
```

**2. 創建虛擬環境**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**3. 安裝依賴**
```bash
python install_dependencies.py
# 或
pip install -r requirements.txt
```

### 運行應用

**Windows：**
```bash
run.bat
```

**Linux/macOS：**
```bash
chmod +x run.sh
./run.sh
```

**手動運行：**
```bash
streamlit run app.py
```

應用將在 `http://localhost:8501` 打開。

### 項目結構說明

**核心邏輯文件：**
- `business_logic.py`：轉出/接收識別、匹配算法的核心實現
  - `TransferLogic` 類：主業務邏輯類
  - `identify_sources()`：識別轉出候選
  - `identify_destinations()`：識別接收候選
  - `match_transfers()`：優先級匹配和生成建議

- `data_processor.py`：數據讀取和預處理
  - `DataProcessor` 類：數據處理主類
  - `read_excel()`：讀取 Excel 文件
  - `validate_data()`：數據驗證

- `excel_generator.py`：結果輸出
  - `ExcelGenerator` 類：Excel 報告生成
  - `write_recommendations()`：寫入調貨建議
  - `write_summary()`：寫入統計摘要

- `app.py`：Streamlit UI
  - 頁面佈局和交互
  - 結果展示和圖表
  - 文件下載

### 添加新的轉貨模式

1. 在 `business_logic.py` 的 `TransferLogic.__init__()` 中添加模式常量
2. 在 `identify_sources()` 中實現轉出邏輯
3. 在 `identify_destinations()` 中實現接收邏輯（如需特殊處理）
4. 在 `match_transfers()` 中添加匹配優先級（如需特殊順序）
5. 在 `app.py` 的模式選擇中添加新選項
6. 在 `_perform_quality_checks()` 中添加相關檢查

### 修改業務規則

**修改轉出上限：**
- 在 `business_logic.py` 的 `identify_sources()` 中調整 `upper_limit` 計算
- 例如：A 模式的 20% → `upper_limit = int(total_available * 0.20)`

**修改接收優先級：**
- 在 `identify_destinations()` 中調整優先級條件
- 更新 `_match_by_priority()` 中的匹配順序

**添加新的質量檢查：**
- 在 `_perform_quality_checks()` 方法中添加新的檢查邏輯

### 測試

運行測試文件以驗證改動：
```bash
python test_mode_d.py        # D 模式測試
python -m pytest test_*.py   # 運行所有測試（若有）
```

### 常見修改場景

**場景 1：調整 RF 過剩轉出的上限百分比**
```python
# business_logic.py - identify_sources() 方法
# A 模式示例，改為 25%
upper_limit = max(int(total_available * 0.25), 2)
```

**場景 2：改變 ND 店鋪轉出優先級**
```python
# business_logic.py - identify_sources() 方法
# 改變 ND 識別邏輯
nd_sources = group_df[group_df['RP Type'] == 'ND']
# 添加額外條件...
```

**場景 3：新增特殊接收條件（如 C 模式）**
```python
# business_logic.py - identify_destinations() 方法
if mode == self.mode_c:
    # C 模式特殊接收邏輯
    special_condition = (total_stock <= 1)
```

### 調試技巧

**查看日誌：**
- 終端會實時輸出日誌信息
- 使用 Python logging 模組添加調試日誌

**測試數據：**
- 使用小規模測試數據驗證新邏輯
- 逐步增加複雜度進行完整性測試

**數據檢查：**
- 在關鍵步驟添加 `print()` 或 logging 輸出
- 使用 pandas 的 `.head()` 檢查中間結果

## 聯繫和支持

- **開發者：** Ricky
- **項目位置：** [本地路徑]
- **報告問題：** 請附帶日誌、數據樣本和步驟說明
