# 調貨後缺口報表（Store × SKU）— 實現計劃

## 目標

每次調貨完成後，產生涵蓋所有模式的統一缺口報表，同時顯示**目的地未滿足需求**與**來源剩餘可轉出量**，以 `(Site, Article)` 為維度。

## 設計決策

| 決策 | 選擇 |
|------|------|
| 缺口範圍 | 目的地缺口 + 來源缺口 |
| 缺口計算基準 | Matching 前快照（`needed_qty` / `transferable_qty`） |
| 來源缺口定義 | 原始可轉出量 − 實際轉出量（所有 source type） |
| 輸出形式 | UI 摘要 + Excel 新 Sheet `調貨缺口分析` |

## 改動步驟

### Step 1: 新增 Pre-Match 快照機制

**檔案：** `services/statistics.py`

- 新增 `PreMatchSnapshot` dataclass（或 NamedTuple）：
  - Destination：`site, om, article, mode, needed_qty, target_qty, dest_type, priority, current_stock, safety_stock`
  - Source：`site, om, article, mode, transferable_qty, original_stock, source_type, priority, safety_stock`
- 新增 `capture_pre_match_snapshot(sources, destinations, article, mode) → PreMatchSnapshot`
  - 對每個 destination/source 建立一筆記錄

**檔案：** `business_logic.py`

- 在 `generate_transfer_recommendations()` 的 source/dest identification **之後**、matching **之前**呼叫快照
- 快照資料累積到 `list[PreMatchSnapshot]`，與 `recommendations` 一起傳遞

> 不改動 matching engine 核心演算法。

### Step 2: 新增缺口計算函數

**檔案：** `services/statistics.py`

新增 `compute_gap_report(pre_match_snapshots, recommendations) → dict`：

- **目的地缺口：** 對每個 `(site, article)`：`gap = original_needed_qty − sum(Transfer Qty for receive_site)`
- **來源剩餘：** 對每個 `(site, article)`：`remaining = original_transferable_qty − sum(Transfer Qty for transfer_site)`

回傳結構：

```python
{
  'summary': {
    'total_dest_gaps': int,        # 有缺口的 destination 數
    'total_gap_qty': int,          # 總缺口件數
    'total_source_remaining': int,  # 有剩餘的 source 數
    'total_remaining_qty': int,    # 總剩餘件數
    'fulfillment_rate': float,     # 已滿足 / 總需求 %
  },
  'details': [                      # 每 (site, article) 一條
    {
      'article': str, 'site': str, 'om': str,
      'role': 'destination' | 'source',
      'mode': str,
      'original_need_or_surplus': int,
      'actual_qty': int,            # received 或 transferred_out
      'gap_or_remaining': int,
      'gap_pct': float,
      'status': str,                # 中文狀態
      'type_label': str,            # e.g. 重點補0, RF過剩轉出
    }
  ],
  'by_mode': { mode: { 'details': [...], 'summary': {...} } }
}
```

**Mode 特殊處理：**
- **D/D2 mode**：destination 無缺口概念，僅 source 剩餘（ND 未清完）
- **E mode**：destination 標示 `無缺口概念`（強制調撥）
- **F/F2/F3/NST**：複用現有 `compute_target_fulfillment_stats()`（不重造輪子）
- **簡化SKU modes**：使用 cap-based surplus/need

### Step 3: 新增 Excel Sheet

**檔案：** `excel_generator.py`

在 `generate_excel_file()` 新增 Sheet `調貨缺口分析`：

| 欄位 | 說明 |
|------|------|
| Article | SKU |
| Site | 店舖代碼 |
| OM | 區經理 |
| 角色 | 目的地 / 來源 |
| 模式 | e.g. A, B2, F |
| 原始需求/可轉量 | need 或 transferable_qty |
| 實際收/轉量 | received 或 transferred_out |
| 缺口/剩餘 | gap 或 remaining |
| 缺口% | gap / original |
| 類型 | 重點補0 / RF過剩轉出⋯ |
| 狀態 | 已滿足 / 未滿足 / 尚有剩餘 / 已配完 |

版面：目的地區段 → 來源區段，中間以 header row 分隔。

### Step 4: UI 顯示

**檔案：** `ui/display.py`

- 在 `render_results()` 新增折疊區塊 `📊 調貨缺口分析`
- KPI row（4 個 metric cards）：未滿足店數、未滿足件數、剩餘店數、剩餘件數
- 可排序表格（同 Excel 欄位）
- 模式下拉篩選：全部 / 特定 mode

**檔案：** `app.py`

- generate 流程中呼叫 `compute_gap_report()`
- 將結果傳遞給 display

### Step 5: 測試

**檔案：** `tests/test_statistics.py`（新增測試）

| 測試案例 | 說明 |
|---------|------|
| 基本缺口計算 | 已知 snapshot + recs → 驗證 gap/remaining 值 |
| 完全滿足 | gap=0, remaining=0 |
| 完全未滿足 | gap=need, received=0 |
| D mode | 無 destination 缺口，有 source 剩餘 |
| E mode | destination 標示無缺口概念 |
| 同一 site 多角色 | 同一 site 在不同 SKU 上為 source/dest |
| 所有 mode | 每種 mode family 跑一次完整 generate，驗證輸出合理 |

## 改動檔案一覽

| 檔案 | 動作 | 說明 |
|------|------|------|
| `services/statistics.py` | 新增函數 | `capture_pre_match_snapshot()`, `compute_gap_report()`, `PreMatchSnapshot` |
| `business_logic.py` | 修改 | 加入快照邏輯、傳遞 gap report |
| `excel_generator.py` | 修改 | 新增 Sheet `調貨缺口分析` |
| `ui/display.py` | 修改 | 新增缺口報表 UI 區塊 |
| `app.py` | 修改 | 串接 gap report 計算與顯示 |
| `tests/test_statistics.py` | 新增測試 | 所有缺口計算案例 |

## 不納入範圍

- ❌ 跨 session 的缺口趨勢比較（無資料庫）
- ❌ 自動補貨建議（基於缺口的第二輪調貨）
- ❌ 修改 matching engine 核心演算法

## 驗收標準

1. 所有 mode 產生的調貨都能看到對應的缺口報表
2. 目的地缺口 = `original_needed_qty − sum(received_qty)` 正確
3. 來源剩餘 = `original_transferable_qty − sum(transferred_qty)` 正確
4. D mode 不顯示無意義的 destination 缺口
5. E mode 標示無缺口概念
6. Excel Sheet 格式正確、可讀性高
7. UI 收合區塊操作流暢、篩選功能正常
