# 庫存調貨建議系統 v1.8

## 系統概述

庫存調貨建議系統v1.8是一個基於Streamlit的Web應用程序，旨在根據庫存、銷量和安全庫存數據，自動生成跨店鋪的商品調貨建議，以優化庫存分布，滿足銷售需求。

本版本支持**雙模式(雙組合)系統**：A(保守轉貨)/B(加強轉貨) + C(按OM調配)/D(按港澳調配)。

## 功能特點

- **雙模式(雙組合)系統**：支持A(保守轉貨)/B(加強轉貨) + C(按OM調配)/D(按港澳調配)的組合
- **智能調貨算法**：基於優先級的轉出/接收規則，實現庫存優化分配
- **數據預處理與驗證**：自動讀取Excel文件，處理數據類型轉換、缺失值和異常值
- **質量檢查**：確保調貨建議的準確性和合理性
- **可視化結果**：提供調貨建議詳情和統計圖表
- **Excel導出**：生成包含調貨建議和統計摘要的Excel文件

## 系統要求

- Python 3.8+
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
pip install -r requirements.txt
```

4. 運行應用
```bash
streamlit run app.py
```

應用程序將在瀏覽器中打開，默認地址為 `http://localhost:8501`

## 使用說明

### 1. 上傳數據文件

- 點擊"瀏覽文件"按鈕上傳Excel文件（.xlsx格式）
- 確保文件包含以下必需欄位：
  - Article（商品編號，12位文本格式）
  - Article Description（商品描述）
  - OM（OM編號）
  - RP Type（店鋪類型：ND或RF）
  - Site（店鋪代碼）
  - MOQ（最低派貨數量）
  - SaSa Net Stock（淨庫存）
  - Pending Received（待收貨數量）
  - Safety Stock（安全庫存）
  - Last Month Sold Qty（上月銷量）
  - MTD Sold Qty（本月銷量）

### 2. 選擇模式

在側邊欄選擇轉貨模式和調配模式：

**轉貨模式：**
- **A模式(保守轉貨)**：RF過剩轉出限制為庫存的20%，最少2件
- **B模式(加強轉貨)**：RF加強轉出限制為庫存的50%，最少2件，基於MOQ+1計算

**調配模式：**
- **C模式(按OM調配)**：僅允許相同產品編號且OM代號完全匹配的調撥
- **D模式(按港澳調配)**：允許相同產品跨OM調撥，HA*/HB*/HC*可互相互補

### 3. 數據預處理

- 系統自動讀取並驗證數據
- 執行數據類型轉換、缺失值處理和異常值校正
- 顯示處理結果和數據統計

### 4. 生成調貨建議

- 點擊"生成調貨建議"按鈕
- 系統基於選擇的模式生成調貨建議
- 執行質量檢查，確保建議的準確性

### 5. 查看結果

- 查看調貨建議統計和詳情
- 瀏覽統計圖表，了解轉出類型和接收優先級分布

### 6. 下載結果

- 點擊"下載調貨建議Excel文件"按鈕
- 獲取包含以下工作表的Excel文件：
  - 調貨建議（Transfer Recommendations）
  - 統計摘要（Summary Dashboard）

## 業務邏輯詳解

### 有效銷量計算

為了簡化銷量比較，系統定義"有效銷量"欄位：
- 優先使用"上月銷量"
- 若上月銷量為0或缺失，則使用"本月銷量"

### A模式(保守轉貨) - 轉出規則

**優先級1：ND類型轉出**
- 條件：RP Type為"ND"
- 可轉數量：全部SaSa Net Stock

**優先級2：RF類型過剩轉出**
- 條件1：RP Type為"RF"
- 條件2：庫存充足（SaSa Net Stock + Pending Received > Safety Stock）
- 條件3：該店鋪的有效銷量不是此Article+OM組合中的最高值
- 基礎可轉出 = (庫存+在途) - 安全庫存
- 上限控制 = (庫存+在途) × 20%，但最少2件
- 實際轉出 = min(基礎可轉出, max(上限控制, 2))

### B模式(加強轉貨) - 轉出規則

**優先級1：ND類型轉出**
- 條件：RP Type為"ND"
- 可轉數量：全部SaSa Net Stock

**優先級2：RF類型加強轉出**
- 條件1：RP Type為"RF"
- 條件2：(庫存+在途) > (MOQ數量+1件)
- 條件3：該店鋪的有效銷量不是此Article+OM組合中的最高值
- 基礎可轉出 = (庫存+在途) – (MOQ數量+1件)
- 上限控制 = (庫存+在途) × 50%，但最少2件
- 實際轉出 = min(基礎可轉出, max(上限控制, 2))

### 接收規則（兩種模式通用）

**優先級1：緊急缺貨補貨**
- 條件1：RP Type為"RF"
- 條件2：完全無庫存（SaSa Net Stock = 0）
- 條件3：曾有銷售記錄（Effective Sold Qty > 0）
- 需求數量：Safety Stock

**優先級2：潛在缺貨補貨**
- 條件1：RP Type為"RF"
- 條件2：庫存不足（SaSa Net Stock + Pending Received < Safety Stock）
- 條件3：該店鋪的有效銷量是此Article+OM組合中的最高值
- 需求數量：Safety Stock - (SaSa Net Stock + Pending Received)

### C模式(按OM調配) - 匹配規則

- 數據按Article和OM進行分組
- 在每個分組內識別轉出和接收候選店鋪
- 按優先級順序執行匹配
- 確保同一產品同一OM才能匹配

### D模式(按港澳調配) - 匹配規則

- 數據按Article進行分組
- 根據站點代碼自動分組：
  - HA*/HB*/HC*系列站點歸為一組（HABC）
  - HD*系列站點獨立分組（HD）
- 在每個分組內識別轉出和接收候選店鋪
- 按優先級順序執行匹配
- 允許相同產品跨OM調撥

### 匹配算法

1. 按優先級順序進行匹配：
   - ND轉出 → 緊急缺貨
   - ND轉出 → 潛在缺貨
   - RF轉出 → 緊急缺貨
   - RF轉出 → 潛在缺貨
2. 每次匹配的轉移數量為min(轉出方的可轉數量, 接收方的需求數量)
3. 更新雙方的剩餘可轉數量和需求數量
4. 調貨數量優化：如果只有1件，嘗試調高到2件（前提是不影響轉出店鋪安全庫存）

## 質量檢查

系統自動執行以下質量檢查：

- [ ] 轉出與接收的Article必須完全一致
- [ ] Transfer Qty必須為正整數
- [ ] Transfer Qty不得超過轉出店鋪的原始SaSa Net Stock
- [ ] Transfer Site和Receive Site不能相同
- [ ] 最終輸出的Article欄位必須是12位文本格式

## 故障排除

### 常見問題

1. **文件上傳失敗**
   - 確保文件格式為.xlsx
   - 檢查文件是否損壞
   - 確認文件大小在允許範圍內

2. **數據處理錯誤**
   - 檢查文件是否包含所有必需欄位
   - 確認Article欄位為12位文本格式
   - 檢查數據中是否有特殊字符

3. **沒有生成調貨建議**
   - 確認數據中同時包含ND和RF類型的店鋪
   - 檢查庫存和銷量數據是否合理
   - 確認安全庫存和MOQ設置是否正確

4. **模式選擇錯誤**
   - 確認選擇了正確的轉貨和調配模式組合
   - 僅允許A+C、A+D、B+C、B+D四種組合

### 日誌查看

應用程序運行時會生成日誌，可在控制台查看詳細錯誤信息。

## 技術架構

```
inventory_transfer_system/
├── app.py                 # Streamlit主應用 v1.8
├── data_processor.py      # 數據預處理模組 v1.8
├── business_logic.py      # 業務邏輯模組 v1.8
├── excel_generator.py     # Excel輸出模組 v1.8
├── requirements.txt       # 依賴包列表
├── README.md             # 使用說明
├── VERSION.md            # 版本更新記錄
├── run.bat               # Windows運行腳本
└── run.sh                # Linux/macOS運行腳本
```

## 更新日誌

### v1.8 (2025-10-01)
- 新增雙模式(雙組合)系統：A(保守轉貨)/B(加強轉貨) + C(按OM調配)/D(按港澳調配)
- 添加MOQ欄位支持
- 實現站點分組功能
- 添加數據可視化圖表
- 更新Excel輸出格式
- 增強數據驗證和錯誤處理

### v1.7 (2023-09-17)
- 初始版本發布
- 實現基本調貨建議功能
- 添加數據預處理和質量檢查
- 支持Excel文件導出

## 聯繫方式

如有問題或建議，請通過以下方式聯繫：
- 開發者：Ricky
- 郵箱：[your-email@example.com]
- 電話：[your-phone-number]