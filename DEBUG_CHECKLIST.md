# 🔧 庫存調貨建議系統 — Debug 詳細清單（繁體中文）

> **適用版本**：v2.10.0（二十四模式系統）
> **最後更新**：2026-05-08

---

## 目錄

1. [系統架構概覽](#1-系統架構概覽)
2. [常見問題診斷流程](#2-常見問題診斷流程)
3. [Debug 方法論](#3-debug-方法論)
4. [各模組 Debug 清單](#4-各模組-debug-清單)
5. [改善前後對比](#5-改善前後對比)
6. [快速排查速查表](#6-快速排查速查表)

---

## 1. 系統架構概覽

### 模組結構

```
KiLo Reallocation/
├── app.py                 ← Streamlit 前端介面（UI、側欄、結果展示）
├── data_processor.py      ← 數據預處理（Excel 讀取、欄位驗證、型別轉換、預設填充）
├── business_logic.py      ← 核心調貨邏輯（24 種模式的轉出/接收/匹配算法）
├── excel_generator.py     ← Excel 報表輸出（格式、欄位、統計摘要）
├── tests/                 ← 單元測試與整合測試
├── debug/                 ← 歷史除錯腳本
└── stores-template.csv    ← 預設店舖資料（已內嵌於 data_processor.py）
```

### 數據處理管線

```
用戶上傳 Excel
    ↓
[DataProcessor] 讀取 + 欄位標準化 + 型別轉換 + 預設填充 + 異常值校正
    ↓
[TransferLogic]  轉出候選識別 → 接收候選識別 → 優先級匹配 → 後處理（避免單件）
    ↓
[ExcelGenerator] 生成報表 + 統計摘要
    ↓
用戶下載結果
```

---

## 2. 常見問題診斷流程

### 問題分類（依發生頻率排序）

| # | 問題類別 | 典型症狀 | 影響模組 |
|---|---------|---------|---------|
| 1 | 編碼/亂碼問題 | 中文字元顯示為 `ç³»çµ±` 或 `â€‹` | `app.py`, `data_processor.py` |
| 2 | 欄位缺失/不匹配 | `缺少必需欄位` 錯誤 | `data_processor.py` |
| 3 | 調貨建議數量異常 | 建議數量為 0 或遠超預期 | `business_logic.py` |
| 4 | Excel 輸出格式問題 | 欄寬/字體/資料遺失 | `excel_generator.py` |
| 5 | 模式邏輯錯誤 | 特定模式結果不符預期 | `business_logic.py` |
| 6 | ND/RF 角色衝突 | 轉出店同時出現在接收端 | `business_logic.py` |
| 7 | 跨 OM 限制失效 | HD 轉到 HA/HB/HC | `business_logic.py` |
| 8 | 單件調貨未消除 | 出現 Transfer Qty = 1 | `business_logic.py` |

---

## 3. Debug 方法論

### 3.1 系統化除錯五步法

```
Step 1: 重現問題
  ├─ 記錄使用的 Excel 文件、模式、參數設定
  ├─ 確認問題可穩定重現
  └─ 截圖/記錄錯誤訊息

Step 2: 縮小範圍
  ├─ 確認問題出在哪一層：數據預處理？邏輯計算？結果展示？
  ├─ 使用 logging 追蹤數據流
  └─ 建立 minimal reproducible example

Step 3: 假設驗證
  ├─ 提出 5-7 個可能的根因
  ├─ 排除明顯不可能的假設
  ├─ 聚焦到最可能的 1-2 個假設
  └─ 加入臨時 log/斷點驗證

Step 4: 修復與測試
  ├─ 最小化修改範圍
  ├─ 確保修復不影響其他模式
  └─ 執行相關測試套件

Step 5: 驗證與記錄
  ├─ 用真實數據回歸測試
  ├─ 記錄根因、修復方式、影響範圍
  └─ 更新文件/測試案例
```

### 3.2 日誌啟用方式

```python
# 在 business_logic.py 頂部調整日誌級別
import logging
logging.basicConfig(level=logging.DEBUG)  # INFO → DEBUG 獲取更詳細的日誌

# 關鍵調試日誌點（已在代碼中預設）
# data_processor.py:  數據讀取、欄位驗證、型別轉換、預設填充
# business_logic.py:  轉出/接收候選識別、匹配過程、後處理
# excel_generator.py: 報表生成過程
```

---

## 4. 各模組 Debug 清單

### 4.1 `data_processor.py` — 數據預處理層

#### 4.1.1 Excel 讀取失敗

**可能原因（5-7 個）：**
1. 文件編碼不是 UTF-8 / 文件損壞
2. 欄位名稱有隱藏空白或全形字元
3. Article 欄位包含非預期的混合型態（數字+文字）
4. Excel 文件被其他程式鎖定（共用衝突）
5. 文件副檔名與實際格式不符（.xls 實為 .xlsx）
6. 缺少必需欄位
7. 數據中存在合併儲存格

**最可能原因（1-2 個）：**
- 欄位名稱有隱藏空白或大小寫差異
- Article 欄位格式非純文字

**Debug 步驟：**

```python
# 步驟 1：確認欄位名稱
import pandas as pd
df = pd.read_excel('your_file.xlsx')
print("欄位列表:", df.columns.tolist())
print("欄位列表（去除空白後）:", [c.strip() for c in df.columns])

# 步驟 2：確認 Article 格式
print("Article dtype:", df['Article'].dtype)
print("Article 樣本:", df['Article'].head())
print("Article 位數:", df['Article'].astype(str).str.len().unique())

# 步驟 3：確認 RP Type 值
print("RP Type 分佈:", df['RP Type'].value_counts())
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| Article 處理 | 直接讀取，可能為數字型態 | `str.zfill(12).str[-12:]` 統一12位補零 |
| 欄位標準化 | 區分大小寫 | ALL/Target/Type 不分大小寫自動轉換 |
| RP Type 驗證 | 無容錯 | 非法值自動修正為 RF 並記錄警告 |
| 預設資料填充 | 無 | 自動根據 Site 填充缺失的 OM/Type |

---

#### 4.1.2 預設店舖資料填充問題

**可能原因：**
1. Excel 中 Site 欄位有空白/小寫（如 `ha02` 而非 `HA02`）
2. Site 編號不在 `DEFAULT_STORE_DATA` 中（新店舖）
3. 用戶 Excel 的 OM/Type 資料不完全為空（有空格）
4. `fill_default_store_data` 在型別轉換前執行

**Debug 步驟：**

```python
# 確認哪些店舖未被匹配
processor = DataProcessor()
df = processor.read_excel_file('your_file.xlsx')
df_filled = processor.fill_default_store_data(df)

print("OM 填充筆數:", processor.fill_stats['om_filled'])
print("Type 填充筆數:", processor.fill_stats['type_filled'])
print("找不到的店舖:", processor.fill_stats['sites_not_found'])
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| Site 比對 | 原始值比對 | 統一 `.strip().upper()` 後比對 |
| 填充方式 | 逐行 iterrows | 向量化 map 操作（O(1) 查詢） |
| 統計回報 | 無 | 回傳填充筆數 + 找不到的店舖清單 |
| 覆蓋策略 | 可能覆蓋用戶數據 | 只填空值，不覆蓋已有資料 |

---

### 4.2 `business_logic.py` — 核心邏輯層

#### 4.2.1 調貨建議數量為 0

**可能原因（5-7 個）：**
1. 所有店舖的庫存都 ≤ Safety Stock（無過剩可轉出）
2. 所有 RF 店舖的 Effective Sold Qty 相同（觸發全保護）
3. 轉出候選被「最高銷量保護」全部排除
4. 接收候選被「ND 不可接收」規則全部排除
5. 模式 A 的 20% 上限太保守，導致 actual_transferable ≤ 0
6. 跨 OM 模式中 HD/Windy 限制過嚴
7. B2/B2a 的 Type=T 不可出貨限制排除了大部分來源

**最可能原因：**
- 所有 RF 銷量相同 → `max_sold_qty = float('inf')` → 全部被保護
- A 模式 20% 上限在低庫存場景下導致轉出量為 0

**Debug 步驟：**

```python
# 針對特定 Article + OM 組合進行調試
logic = TransferLogic()
group = df[df['Article'] == '100314808024']

sources = logic.identify_sources(group, '保守轉貨')
print(f"轉出候選數量: {len(sources)}")
for s in sources:
    print(f"  Site={s['site']}, Type={s['source_type']}, "
          f"Qty={s['transferable_qty']}, Priority={s['priority']}")

destinations = logic.identify_destinations(group, '保守轉貨')
print(f"接收候選數量: {len(destinations)}")
for d in destinations:
    print(f"  Site={d['site']}, Type={d['dest_type']}, "
          f"Needed={d['needed_qty']}, Priority={d['priority']}")
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| 最高銷量保護 | 僅保護最高銷量店 | 若所有銷量相同，不保護任何店 |
| A 模式上限 | 無最低件數 | `max(20% total, 2)` 至少 2 件 |
| B 模式上限 | 無最低件數 | `max(50% total, 2)` 至少 2 件 |
| 空結果 | 無診斷信息 | 日誌記錄候選數量與排除原因 |

---

#### 4.2.2 轉出店同時出現在接收端（雙重角色）

**可能原因：**
1. `transfer_sites` 集合未正確傳遞
2. Phase 3（E2 模式 C 模式回退）時未檢查雙重角色
3. 精簡 SKU 模式 D001 退回邏輯未排除已是轉出店的 D001
4. 跨 OM 分組時，同一 Site 出現在不同分組中
5. 後處理 `_optimize_single_piece_transfers` 重新分配時引入雙重角色

**最可能原因：**
- E2 模式 Phase 3 C 模式回退未檢查已有的 `transfer_sites`
- 精簡 SKU D001 退回邏輯的邊界條件

**Debug 步驟：**

```python
# 在 generate_transfer_recommendations 中加入檢查
recommendations = logic.generate_transfer_recommendations(df, mode_name)

# 檢查是否有雙重角色
from collections import defaultdict
sku_sources = defaultdict(set)
sku_dests = defaultdict(set)

for rec in recommendations:
    sku = rec['Article']
    sku_sources[sku].add(rec['Transfer Site'])
    sku_dests[sku].add(rec['Receive Site'])

for sku in sku_sources:
    overlap = sku_sources[sku] & sku_dests[sku]
    if overlap:
        print(f"❌ Article {sku} 雙重角色: {overlap}")
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| 雙重角色檢查 | 僅在匹配階段 | 匹配階段 + 質量檢查（檢查6）雙重驗證 |
| E2 Phase 3 | 未檢查跨階段衝突 | 嚴格排除已作為轉出店的店舖 |
| 精簡SKU D001 | 可能退回給轉出店 | 檢查並排除已在 transfer_sites 中的店舖 |

---

#### 4.2.3 跨 OM 限制（HD/Windy）失效

**可能原因：**
1. Site 欄位未標準化（如 `hd02` 小寫）
2. OM 欄位的「Windy」拼寫有差異
3. `_is_hd_to_hk_restricted` 判斷邏輯未涵蓋所有 OM 前綴
4. 跨 OM 分組使用 `groupby('Article')` 但未在匹配時檢查限制

**Debug 步驟：**

```python
# 檢查 HD → HA/HB/HC 的非法配對
for rec in recommendations:
    src = rec['Transfer Site']
    dst = rec['Receive Site']
    if src.upper().startswith('HD') and dst.upper().startswith(('HA', 'HB', 'HC')):
        print(f"❌ HD 限制違規: {src} → {dst}")

# 檢查 Windy 限制
for rec in recommendations:
    if rec['Transfer OM'] == 'Windy' and rec['Receive OM'] != 'Windy':
        print(f"❌ Windy 限制違規: {rec['Transfer Site']}({rec['Transfer OM']}) → "
              f"{rec['Receive Site']}({rec['Receive OM']})")
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| HD 限制 | 部分模式遺漏 | B3/C2/E2/F/F2/ND2/精簡SKU(跨OM) 全覆蓋 |
| Windy 限制 | 僅限制出方向 | 出方向限制 + Windy 可接收其他 OM |
| Site 比對 | 區分大小寫 | `.upper().startswith()` 統一比對 |

---

#### 4.2.4 單件調貨（Transfer Qty = 1）未消除

**可能原因：**
1. 該店舖對該 SKU 的可調總量本身就只有 1 件（例外情況）
2. `_optimize_single_piece_transfers` 的 Rebalance/Merge 策略未找到合適目標
3. 後處理後未呼叫 `_refresh_recommendation_fields` 重算相關欄位
4. 分組鍵 `(Article, Transfer Site, Transfer OM)` 不一致

**Debug 步驟：**

```python
# 統計單件調貨
single_piece = [r for r in recommendations if r['Transfer Qty'] == 1]
print(f"單件調貨數量: {len(single_piece)}")

# 分析原因
from collections import defaultdict
groups = defaultdict(list)
for r in recommendations:
    key = (r['Article'], r['Transfer Site'], r['Transfer OM'])
    groups[key].append(r)

for key, recs in groups.items():
    total_qty = sum(r['Transfer Qty'] for r in recs)
    has_single = any(r['Transfer Qty'] == 1 for r in recs)
    if has_single and total_qty > 1:
        print(f"❌ 可消除但未消除: {key}, 總量={total_qty}")
        for r in recs:
            print(f"  → {r['Receive Site']}: {r['Transfer Qty']}")
    elif has_single and total_qty == 1:
        print(f"ℹ️ 例外（總量=1）: {key}")
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| 單件處理 | 無 | Rebalance + Merge 雙策略 |
| 例外處理 | 無 | 總量=1 時保留 |
| 欄位一致性 | 手動維護 | `_refresh_recommendation_fields` 自動重算 |
| 適用範圍 | 無 | 所有 24 種模式統一套用 |

---

#### 4.2.5 B2/B2a Mix 店舖高銷量保護誤觸發

**可能原因：**
1. `total_sales` 計算口徑不一致（Last Month + MTD vs. Effective Sold Qty）
2. Type=M 的判斷大小寫不一致
3. 無銷量時 `total_sales = 0` 導致 `0 > 0` 恆假
4. 比較時未區分 source 和 dest 的 total_sales

**Debug 步驟：**

```python
# 在 _match_by_priority 中加入臨時日誌
for source in sources:
    for dest in destinations:
        if source.get('store_type', '').upper() == 'M':
            src_sales = source.get('last_month_sold_qty', 0) + source.get('mtd_sold_qty', 0)
            dst_sales = dest.get('last_month_sold_qty', 0) + dest.get('mtd_sold_qty', 0)
            if src_sales > dst_sales:
                logger.debug(
                    f"Mix 保護觸發: Source={source['site']}({src_sales}) "
                    f"> Dest={dest['site']}({dst_sales})"
                )
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| Mix 保護 | 無 | Type=M 且 src_sales > dst_sales 時跳過配對 |
| 銷量口徑 | 不統一 | 統一為 `Last Month Sold Qty + MTD Sold Qty` |
| 適用模式 | 無 | B2/B2a/B2L/B2La/B3/B3a/B3L/B3La 全覆蓋 |

---

#### 4.2.6 D/D2 模式避免 1 件餘貨邏輯

**可能原因：**
1. `remaining_after_transfer` 計算未考慮多筆轉出的累計
2. `transfer_qty += 1` 或 `transfer_qty -= 1` 後未更新 `transferable_qty`
3. D2 模式下 RF 店舖仍參與轉出

**Debug 步驟：**

```python
# 驗證 D 模式無 1 件餘貨
for rec in recommendations:
    if 'ND清貨' in rec.get('Source Type', ''):
        remaining = rec.get('After Transfer Stock', -1)
        if remaining == 1:
            print(f"❌ D 模式餘貨 1 件: {rec['Article']}/{rec['Transfer Site']}")
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| 餘貨處理 | 無 | 自動調整 ±1 確保剩餘為 0 或 ≥ 2 |
| D2 RF 轉出 | 可能參與 | 完全排除 RF 轉出候選 |
| D2 ND 有銷售 | 正常轉出 | 跳過有銷售記錄的 ND |

---

### 4.3 `app.py` — 前端介面層

#### 4.3.1 繁體中文亂碼（Mojibake）

**可能原因（5-7 個）：**
1. Windows 終端機編碼為 Big5/CP950，Streamlit 輸出 UTF-8
2. Python 源碼檔案儲存為 Big5 編碼
3. Excel 文件中文字與代碼編碼不匹配
4. Streamlit 版本與 ftfy 庫衝突
5. 環境變數 `PYTHONIOENCODING` 未設定
6. Git 自動轉換行尾（CRLF/LF）影響中文
7. 字串在傳遞過程中被 double-encoding

**最可能原因：**
- Windows 本地環境的編碼差異
- 源碼檔案編碼不一致

**Debug 步驟：**

```python
# 確認檔案編碼
import chardet
with open('app.py', 'rb') as f:
    result = chardet.detect(f.read())
print(f"檔案編碼: {result}")

# 確認終端機編碼
import sys
print(f"stdout encoding: {sys.stdout.encoding}")
print(f"default encoding: {sys.getdefaultencoding()}")

# 測試 ftfy 修復
import ftfy
print(ftfy.fix_text('ç³»çµ±'))  # 應輸出「系統」
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| 編碼修復 | 手動逐文件修 | `ftfy.fix_text` 全局自動修復 |
| Streamlit 文字 | 可能在某些環境亂碼 | `_patch_streamlit_text_rendering` 攔截所有文字方法 |
| 啟用方式 | 預設啟用 | `KILO_FIX_MOJIBAKE=1` 環境變數控制，避免不必要的 CPU 開銷 |
| Zeabur 雲端 | 同樣亂碼 | Linux 容器無需啟用修復，避免額外開銷 |

---

#### 4.3.2 結果表格顯示效能問題（大型數據）

**可能原因：**
1. Streamlit `st.dataframe` 在大型 DataFrame 上渲染緩慢
2. 重複生成 Excel 文件（每次渲染都重算）
3. `_cached_preprocess` 快取未命中

**Debug 步驟：**

```python
# 確認快取是否生效
import time
start = time.time()
df, stats = _cached_preprocess(uploaded_file.getvalue())
print(f"預處理耗時: {time.time() - start:.2f}s")

# 確認 Zeabur 限制
print(f"IS_ZEABUR: {IS_ZEABUR_RUNTIME}")
print(f"Result limit: {ZEABUR_RESULT_PREVIEW_LIMIT}")
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| Excel 解析 | 每次渲染重複 | `@st.cache_data` 快取（相同文件只解析一次） |
| 結果展示 | 全量渲染 | Zeabur 環境預設只顯示前 1000 行，可展開 |
| Excel 生成 | 每次渲染重算 | `session_state` 快取，只在分析結果變化時重算 |
| 庫存查詢 | 逐行 iterrows | 預建字典 `_stock_lookup`，O(1) 查詢 |

---

### 4.4 `excel_generator.py` — 報表輸出層

#### 4.4.1 Excel 輸出欄位遺失或格式錯誤

**可能原因：**
1. `xlsxwriter` 引擎版本不相容
2. 欄位名稱含特殊字元（箭頭 `→`）
3. 數據型態不符（如 NaN 或 None）
4. 欄寬設定過窄導致內容被截斷

**Debug 步驟：**

```python
# 確認輸出數據完整性
import io
import pandas as pd
generator = ExcelGenerator()
excel_bytes = generator.generate_excel_file(recommendations, statistics)

# 讀回驗證
df_check = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=0)
print(f"輸出行數: {len(df_check)}")
print(f"輸出欄位: {df_check.columns.tolist()}")
print(f"空值統計:\n{df_check.isnull().sum()}")
```

**改善前後對比：**

| 項目 | 改善前 | 改善後 |
|------|--------|--------|
| 檔案生成 | 寫入磁碟臨時檔 | `BytesIO` 記憶體操作，無磁碟 I/O |
| 字體設定 | 預設字體 | 統一 Arial 10pt |
| 欄寬 | 過寬或過窄 | 適中設定（Article:12, Desc:25, Notes:75） |
| 銷售數據 | 無 | 新增 4 欄銷售數據（出貨端+接收端） |
| 接收原始庫存 | 無 | 新增 Receive Original Stock 欄位 |

---

## 5. 改善前後對比

### 5.1 整體系統改善對比

| 維度 | 改善前 (v1.x) | 改善後 (v2.10.0) |
|------|---------------|-----------------|
| **模式數量** | 4 模式 (A/B/C/D) | 24 模式（含跨OM、ND互轉、精簡SKU等） |
| **ND 接收限制** | 所有模式 ND 不可接收 | ND1/ND2 打破限制；F/F2 Target ND 可接收 |
| **跨 OM 能力** | 僅同OM | B3/C2/E2/F/F2/ND2/精簡SKU(跨OM) 支援 |
| **HD/Windy 限制** | 無 | 跨OM模式統一套用 |
| **單件調貨** | 允許 | 全模式後處理消除（Rebalance + Merge） |
| **1件餘貨** | 無處理 | D/D2 模式自動調整 ±1 |
| **預設店舖資料** | 無 | 85間店舖自動填充 OM/Type |
| **編碼處理** | 手動修 | ftfy 自動修復 + Streamlit 文字攔截 |
| **效能** | iterrows 逐行 | 向量化 + 字典預建 + 快取 |
| **Excel 格式** | 基礎 | Arial 10pt + 適中欄寬 + 銷售數據 + 統計摘要 |
| **質量檢查** | 基礎 | 8項檢查含雙重角色、ND接收、累計接收上限 |
| **測試覆蓋** | 少量 | 16 個測試文件覆蓋所有模式 |

### 5.2 核心邏輯改善對比（按模式）

| 模式 | 改善前行為 | 改善後行為 | 改善效果 |
|------|-----------|-----------|---------|
| **A** | 轉出比例無下限 | `max(20%, 2)` 至少2件 | 避免無意義的微量轉出 |
| **B** | 轉出比例無下限 | `max(50%, 2)` 至少2件 | 同上 |
| **B2** | 無 Mix 保護 | Type=M 高銷量保護 | 避免高銷量 Mix 店被抽貨 |
| **B2a** | 無 | Type=T 不可出貨 | 保護遊客鋪庫存 |
| **B2L/B3L** | 無 | Type=L 保留2件 | 避免 Type=L 店被完全清空 |
| **C** | 補0+緊急+潛在 | 同左 | 穩定不變 |
| **C1** | 無 | 僅補 total_available≤1，不回落 | 精準補零，不觸發一般缺貨 |
| **C2** | 無 | C模式 + 跨OM | 跨 OM 重點補0 |
| **D** | 可能留1件餘貨 | 自動調整避免1件 | 無尷尬餘貨 |
| **D2** | 無 | 僅ND清貨，RF只接收 | 保守清貨策略 |
| **E1** | 無 | 僅同OM強制轉出 | 同OM內強制清倉 |
| **E1b** | 無 | E1 + 優先 Type=T/M 接收 | 優先分配到高流量店 |
| **E2** | 無 | 跨OM強制轉出 + C模式回退 | 靈活跨OM清倉 |
| **F** | Target 扣減在途 | Target 直接作為接收量 | 更精確的目標分配 |
| **F2** | 無 | 僅Target接收 | 集中補貨到指定店 |
| **ND1** | 無 | ND同OM互轉 | ND店舖間智能調配 |
| **ND2** | 無 | ND跨OM互轉 | 跨OM ND調配 |
| **精簡SKU** | 無 | 超Cap轉出+退回D001 | SKU精簡場景專用 |

### 5.3 效能改善對比

| 操作 | 改善前 | 改善後 | 改善幅度 |
|------|--------|--------|---------|
| Excel 文件讀取 | 每次 Streamlit 渲染都重讀 | `@st.cache_data` 快取 | ~90% 減少重複解析 |
| 預設填充 | 逐行 iterrows + dict lookup | 向量化 map + 預建字典 | ~10x 加速 |
| 結果展示庫存查詢 | 逐行 iterrows | 預建 `_stock_lookup` 字典 O(1) | ~100x 加速 |
| Excel 文件生成 | 磁碟 I/O | BytesIO 記憶體操作 | 消除磁碟延遲 + 並發安全 |
| 大型結果渲染 | 全量渲染 | Zeabur 限制前 1000 行 + 可展開 | 頁面響應速度大幅提升 |

### 5.4 可靠性改善對比

| 維度 | 改善前 | 改善後 |
|------|--------|--------|
| **質量檢查** | 3 項基礎檢查 | 8 項完整檢查（含雙重角色、ND 接收驗證） |
| **錯誤回報** | 簡單 error message | 詳細 Quality Check 錯誤展開面板 |
| **邊界條件** | 未處理全同銷量 | `max_sold_qty = float('inf')` 避免全保護 |
| **無效 RP Type** | 報錯中斷 | 自動修正為 RF 並顯示警告 |
| **F 模式 ND+Target 衝突** | 靜默忽略 | 前置警告 + 明細展開 |
| **RP Type 無效值** | 中斷處理 | 自動修正為 RF，界面顯示警告 |

---

## 6. 快速排查速查表

### 按症狀快速定位

| 症狀 | 第一步 | 模組 | 關鍵方法 |
|------|--------|------|---------|
| 頁面空白/報錯 | 查看 Streamlit 終端機 log | `app.py` | — |
| 缺少必需欄位 | 確認 Excel 欄位名（去除空白） | `data_processor.py` | `validate_columns()` |
| 建議數量為 0 | 檢查轉出/接收候選數量 | `business_logic.py` | `identify_sources/destinations()` |
| 建議數量異常多 | 確認模式和參數設定 | `business_logic.py` | `generate_transfer_recommendations()` |
| 中文字亂碼 | 設定 `KILO_FIX_MOJIBAKE=1` | `app.py` | `_fix_mojibake_text()` |
| HD 轉到 HA/HB/HC | 確認 Site 欄位大小寫 | `business_logic.py` | `_is_hd_to_hk_restricted()` |
| ND 店出現在接收端 | 確認是否為 ND1/ND2/F/F2 模式 | `business_logic.py` | `_is_nd_transfer_mode()` |
| 出現 Transfer Qty=1 | 檢查可調總量是否確實只有1 | `business_logic.py` | `_optimize_single_piece_transfers()` |
| Excel 格式跑掉 | 確認 xlsxwriter 版本 | `excel_generator.py` | `generate_excel_file()` |
| 預設 OM/Type 未填充 | 確認 Site 是否在 DEFAULT_STORE_DATA | `data_processor.py` | `fill_default_store_data()` |
| Mix 保護誤觸發 | 確認 Type 欄位值和銷量數據 | `business_logic.py` | `_match_by_priority()` |
| Type=L 全轉出但應保留2件 | 確認是否使用 B2L/B3L 模式（非 B2/B3） | `business_logic.py` | `_is_b_l_retain_mode()` |

### 快速驗證指令

```powershell
# 1. 確認環境
python -c "import streamlit; import pandas; import xlsxwriter; print('依賴正常')"

# 2. 執行測試套件
python -m pytest tests/ -v --tb=short

# 3. 單獨測試特定模式
python -m pytest tests/test_modes_simple.py -v -k "B2"
python -m pytest tests/test_nd_modes.py -v
python -m pytest tests/test_single_qty_optimization.py -v

# 4. 啟動應用（開發模式）
streamlit run app.py

# 5. 啟動應用（啟用亂碼修復）
$env:KILO_FIX_MOJIBAKE="1"; streamlit run app.py
```

### 版本回溯指南

如需回溯到特定版本，參考 `VERSION.md` 的版本記錄：

| 版本 | 關鍵變更 |
|------|---------|
| v2.10.0 | 新增精簡SKU(限同OM/跨OM) + F/F2改善 |
| v2.9.1 | 正式加入 C1 模式 |
| v2.9.0 | 新增 B2L/B2La/B3L/B3La |
| v2.8.0 | 新增 D2 模式 |
| v2.7.0 | 新增 F2 模式 |
| v2.6.0 | 新增 ND1/ND2 模式 |
| v2.5.0 | 全模式後處理避免單件 |
| v2.4.1 | B特別模式 Mix 保護 + 程式碼審查 |
| v2.3.0 | 新增 C2 模式 |
| v2.2.2 | 新增 B3 模式 |
| v2.2.1 | B2 接收優先級優化 |
| v2.2.0 | 預設店舖資料自動填充 |
| v2.1.1 | 新增 F 模式 |
| v1.9.9 | 新增 E 模式 |
| v1.9.8 | 新增 D 模式 |

---

## 附錄：測試覆蓋矩陣

| 測試文件 | 覆蓋內容 |
|---------|---------|
| `test_all_modes_comprehensive.py` | 全模式整合測試（含邊界條件） |
| `test_all_modes_no_dual_role.py` | 全模式雙重角色檢查 |
| `test_b_special_mix_sales_guard.py` | B2/B2a/B2L/B2La/B3/B3a/B3L/B3La Mix 保護 |
| `test_b2a_b3a_t_no_source.py` | Type=T 不可出貨限制 |
| `test_b2_b3_source_receive_site_limit.py` | 接收店數限制（1/2/不限） |
| `test_b2_priority.py` | B2 接收優先級排序 |
| `test_b2_fix.py` | B2 模式修復驗證 |
| `test_c1_dual_role.py` | C1 模式雙重角色 |
| `test_c1_source_constraints.py` | C1 轉出門檻與下限 |
| `test_hd_fix.py` | HD 限制修復 |
| `test_mode_d.py` | D 模式（清貨 + 避免1件餘貨） |
| `test_modes_simple.py` | 各模式基本功能快速驗證 |
| `test_nd_modes.py` | ND1/ND2 模式完整測試 |
| `test_single_qty_optimization.py` | 後處理避免單件（Rebalance + Merge） |

---

> **維護者**：Ricky
> **系統版本**：v2.10.0
> **文件更新日期**：2026-05-08
