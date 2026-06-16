# D 系列 Excel Report 新增 ND 清貨完成分析頁

## 目標

為 D 系列（`D` 清貨轉貨、`D2` 清貨轉貨(ND限定)）的 Excel 報表增加第三頁，類似 F 系列現有的 `Target達成分析`。

當 ND 店舖的 SKU 未能完全清出時，報表需顯示：
1. **每個 SKU 未完成清貨的總件數**（所有 ND 轉出店轉出後剩餘庫存總和）。
2. **尚有 ND 未完全轉出的店舖數量**。

同時提供 per-store 明細，方便追蹤是哪些店舖還有剩餘。

## 背景與現狀

- F 系列（`F`/`F2`/`F3`/`NST`）在 `excel_generator.py:361` 會額外生成 `Target達成分析` 工作表，由 `services/statistics.py:compute_target_fulfillment_stats()` 計算數據。
- D 系列目前只有標準兩頁：`調貨建議 (Transfer Recommendations)` 與 `統計摘要 (Summary Dashboard)`。
- D 系列的 ND 來源類型為 `ND清貨轉出`（`strategies/b_special.py:33`），且 `compute_transfer_qty()` / `_adjust_d_family_remainder()` 會特別避免留下 1 件餘貨。
- 每條 recommendation 已帶有 `Original Stock`、`Transfer Qty`、`After Transfer Stock`，足以判斷單一來源店是否清完。
- `app.py:242` 呼叫 `generate_excel_file()` 時已傳入原始 `df`，因此可以仿照 F 系列的做法，用 `df` 補上「完全沒配對到」的 ND 清貨店。

## 設計決策

| 決策 | 選擇 | 說明 |
|---|---|---|
| 適用模式 | `D`、`D2` | 使用者說「D系列」。 |
| 未完成定義 | `After Transfer Stock > 0` 的 ND 來源 | 與現有 recommendation 欄位一致；即使原始庫存為 1 且成功轉出，也不會出現。 |
| 是否包含零配對的 ND 店 | **是** | 仿照 F 系列的 `df` 參數，從原始資料補上 `RP Type == ND` 且符合 D 系列清貨條件（Last Month=0、MTD=0、Net Stock>0）但無 recommendation 的店舖，這類店舖視為「完全未清出」。 |
| 工作表名稱 | `ND清貨完成分析` | 與 `Target達成分析` 對稱。 |
| 報表結構 | KPI + SKU 彙總 + per-store 明細 | SKU 彙總回答使用者兩個核心數字；明細提供追蹤能力。 |

## 需修改檔案

1. `services/statistics.py` — 新增 `compute_nd_clearance_stats()`。
2. `excel_generator.py` — 新增 `create_nd_clearance_sheet()`；在 `generate_excel_file()` 中對 D/D2 模式觸發。
3. `tests/test_excel_generator.py` — 新增 D 系列 ND 清貨分析頁測試。
4. `tests/test_mode_d.py` — 新增驗證 ND 未完成統計的測試案例。
5. `config.py` — bump `VERSION`。
6. `VERSION.md` — 新增版本記錄。
7. `app.py` — 更新 module docstring 版本號（如 `config.VERSION` 改變）。
8. `README.md` / `ui/tutorial.py` / `調貨模式詳解.txt` / `transfer_logic_ai_brief.md` — 視需要更新輸出內容說明（D 系列報表多一頁）。

## 實作步驟

### 1. `services/statistics.py` 新增 ND 清貨完成統計

新增函式：

```python
def compute_nd_clearance_stats(
    recommendations: List[Dict[str, Any]],
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    計算 D/D2 模式中 ND 清貨來源是否完全轉出。

    - 從 recommendations 中篩選 Source Type == 'ND清貨轉出' 的紀錄。
    - 以 (Article, Transfer Site) 為 key 彙總：Original Stock、總轉出件數、After Transfer Stock。
    - 若提供 df，補上 RP Type == ND、Last Month Sold == 0、MTD Sold == 0、
      SaSa Net Stock > 0 但無任何 recommendation 的店舖（完全未清出）。
    - 回傳 SKU 彙總與 per-store 明細。
    """
```

回傳結構：

```python
{
    "total_nd_sites": int,            # 符合清貨條件的 ND 店舖總數
    "fully_cleared_sites": int,       # 完全清出的店舖數
    "not_fully_cleared_sites": int,   # 未完成清出的店舖數
    "total_remaining_qty": int,       # 全部未完成清出的總件數
    "article_summary": [
        {
            "article": str,
            "brand": str,
            "product_desc": str,
            "total_remaining_qty": int,
            "not_fully_cleared_site_count": int,
            "total_nd_sites": int,
        },
        ...
    ],
    "details": [
        {
            "article": str,
            "brand": str,
            "product_desc": str,
            "transfer_om": str,
            "transfer_site": str,
            "original_stock": int,
            "total_transferred_qty": int,
            "after_transfer_stock": int,
            "is_fully_cleared": bool,
        },
        ...
    ],
}
```

實作注意：
- 以 `Source Type == 'ND清貨轉出'` 為準，避免混入 ND1/ND2/ND3 等其它模式產生的 ND 轉出紀錄。
- 同一店舖同一 SKU 可能有多筆 recommendation，需先加總 `Transfer Qty`，再用 `Original Stock - total_transferred` 計算剩餘。
- 若 `df` 提供，補零配對的 ND 店舖時，需同樣過濾 `Last Month Sold Qty == 0` 且 `MTD Sold Qty == 0`。

### 2. `excel_generator.py` 新增工作表

新增方法：

```python
def create_nd_clearance_sheet(
    self,
    writer,
    recommendations: List[Dict],
    df: Optional[pd.DataFrame] = None,
):
    """創建 ND清貨完成分析 工作表（僅 D/D2 模式）。"""
```

內容佈局（仿 `create_target_fulfillment_sheet`）：
- 標題列：`ND 清貨完成分析`
- KPI 橫幅：
  - ND 清貨店舖總數
  - 已完全清出店舖數
  - 未完成清出店舖數
  - 總剩餘件數
- SKU 彙總表：
  - Brand、Article、Product Desc、ND 清貨店舖數、未完成店舖數、總剩餘件數
- Per-store 明細表：
  - Brand、Article、Product Desc、Transfer OM、Transfer Site、Original Stock、Total Transferred、After Transfer Stock、Status（已完成 / 未完成）
- 格式：已清出用綠底，未完成用紅底；欄寬適中。

在 `generate_excel_file()` 中加入：

```python
if mode in ("清貨轉貨", "清貨轉貨(ND限定)"):
    self.create_nd_clearance_sheet(writer, recommendations, df)
```

### 3. 測試

#### `tests/test_excel_generator.py`

新增測試：
- `test_d_mode_adds_nd_clearance_sheet`：傳入 D 模式與含 `ND清貨轉出` 的 recommendations，驗證工作表存在。
- `test_d2_mode_adds_nd_clearance_sheet`：同上，D2 模式。
- `test_non_d_mode_no_nd_clearance_sheet`：F 模式不應出現此表。
- `test_nd_clearance_sheet_columns_and_values`：驗證欄位與數值正確（含部分清出、完全清出、完全未清出三種情境）。

#### `tests/test_mode_d.py`

新增測試：
- 建立 ND 店原始庫存 > 接收需求，導致無法完全清出的情境。
- 呼叫 `compute_nd_clearance_stats(recommendations, df)`。
- 驗證：
  - `total_remaining_qty` 正確。
  - `not_fully_cleared_sites` 正確。
  - 完全未配對的 ND 店舖也被納入統計。

### 4. 版本與文件

- `config.py`：將 `VERSION` 從 `v2.26.0` 升為 `v2.27.0`。
- `VERSION.md`：新增 `v2.27.0` 區塊，說明 D 系列新增 `ND清貨完成分析` Excel 頁。
- `app.py`：更新 module docstring 版本號。
- `README.md`：在輸出內容或模式對照表處補充「D/D2 報表含 ND清貨完成分析頁」。
- `ui/tutorial.py`：D/D2 教學中補充輸出報表結構說明（如適用）。
- `調貨模式詳解.txt`：D/D2 輸出內容補充。
- `transfer_logic_ai_brief.md`：D/D2 輸出格式補充。

## 風險與注意事項

1. **與 F 系列 `Target達成分析` 的區隔**：兩頁邏輯獨立，D/D2 模式不會同時觸發 Target 頁，因此不會衝突。
2. **D2 的 2-site limit**：即使 D2 啟用「限制2間店舖接收」，統計邏輯只依賴 recommendations + df，不受配對限制影響。
3. **後處理 `optimize_single_piece_transfers`**：此步驟會改變 `Transfer Qty` 與 `After Transfer Stock`，因此統計必須在 `generate_transfer_recommendations` 完成後、輸出 Excel 前進行，確保數字與最終報表一致。
4. **文件同步範圍**：本次變更屬於「報表輸出強化」，未修改 D/D2 的配對邏輯本身，因此 `business_logic.py` / `strategies/d_mode.py` / `strategies/b_special.py` / `models/mode.py` / `ui/sidebar.py` 的核心規則不需改動。但 AGENTS.md 的文件同步清單仍以「模式邏輯是否被修改」為判斷標準；本次只改輸出層，故主要同步 README / VERSION / config / app / tutorial / txt / ai_brief。

## 驗收標準

- [ ] D 模式與 D2 模式生成的 Excel 包含 `ND清貨完成分析` 工作表。
- [ ] 工作表正確列出每個 SKU 的總剩餘件數。
- [ ] 工作表正確列出每個 SKU 尚未完全清出的 ND 店舖數量。
- [ ] Per-store 明細正確顯示每家 ND 轉出店的 Original Stock / 總轉出 / 剩餘 / 狀態。
- [ ] 完全未配對的 ND 清貨店舖（當提供 df 時）也被納入統計。
- [ ] 非 D 系列模式不會產生此工作表。
- [ ] 既有測試全部通過；新增測試覆蓋上述情境。
- [ ] 版本號與相關文件已同步更新。
