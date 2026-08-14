# Excel 欄位調動 + 新增 Type 欄位

## Goal

將調貨建議輸出由現有 19 欄改為新的 21 欄順序，並新增 `Transfer Site Type` / `Receive Site Type` 兩欄（值取自輸入資料的 `Type` 欄位）。

## Decisions (from user)

1. **套用範圍**：新欄位順序套用到**所有模式**的 Excel 輸出（不限 B 系模式）。非 B 系模式的 Type 欄位可能為空字串。
2. **UI 預覽**：`ui/display.py` 的 App 內結果預覽表同步更新，使其與新 Excel 欄位一致，**僅限 B 系模式**（B2/B2a/B2L/B2La/B3/B3a/B3L/B3La）；非 B 系模式預覽維持現狀。
3. Type 欄位輸出原始字母值（T/M/L/R），不加說明文字。

## 目標欄位順序（21 欄，全模式適用）

```
Brand, Article, Product Desc,
Transfer OM, Transfer Site, Transfer Site Type,
Transfer Site Last Month Sold Qty, Transfer Site MTD Sold Qty,
Transfer Original Stock, Transfer Safety Stock, Transfer After Transfer Stock,
Receive OM, Receive Site, Receive Site Type,
Receive Site Last Month Sold Qty, Receive Site MTD Sold Qty,
Receive Original Stock, Receive Site Safety Stock,
Transfer Qty, Remark, Notes
```

`精簡SKU(退D001)` 模式維持在最後追加 `D001 Receive Qty` 欄。

對應資料來源：
- `Transfer Site Type` = source 的 `store_type`（`make_source` 已填入）
- `Receive Site Type` = dest 的 `store_type`（`make_dest` 已填入）
- 其餘欄位映射不變（`Transfer Original Stock`=`Original Stock`、`Transfer Safety Stock`=`Safety Stock`、`Transfer After Transfer Stock`=`After Transfer Stock`、`Receive Site Safety Stock`=`Receive Safety Stock`）

## 變更清單

### 1. `services/recommendation_factory.py` — `build_recommendation()`
在 rec dict 中新增（放於 `'Receive Original Stock'` 之後）：
```python
'Transfer Site Type': source.get('store_type', ''),
'Receive Site Type': '' if is_d001_return else dest.get('store_type', ''),
```
此為所有 strategy 的唯一 rec 建構點，`refresh_recommendation_fields` 為 in-place 更新，不會刪除此兩鍵。

### 2. `excel_generator.py` — `create_transfer_recommendations_sheet()`
- 模組層定義常數：
  - `EXCEL_COLUMN_ORDER: List[str]` = 上述 21 欄清單
  - `EXCEL_COLUMN_WIDTHS: List[int]` 對應每欄寬度：
    `[14, 12, 25, 12, 12, 8, 18, 15, 18, 18, 20, 12, 12, 8, 18, 15, 15, 22, 10, 25, 75]`
- `row_data` 增加 `'Transfer Site Type': rec.get('Transfer Site Type', '')` 與 `'Receive Site Type': rec.get('Receive Site Type', '')`。
- DataFrame 改以固定欄序建立，取代 dict 插入順序：
  ```python
  cols = list(EXCEL_COLUMN_ORDER)
  if show_d001_col:
      cols.append('D001 Receive Qty')
  df = pd.DataFrame(df_data, columns=cols)
  ```
- 移除原本按英文字母 range 的 `set_column('A:A', ...)` 等硬編碼（現行 line 109–129 與 line 166–171），改以索引迴圈套用寬度與格式：
  ```python
  for idx, col_name in enumerate(cols):
      fmt = notes_format if col_name == 'Notes' else data_format
      width = EXCEL_COLUMN_WIDTHS[idx] if col_name != 'D001 Receive Qty' else 18
      worksheet.set_column(idx, idx, width, fmt)
  ```
- Header 寫入迴圈（`enumerate(df.columns.values)`）不需改動，會自動跟隨新欄序。
- 列寬順序會因此改變（Type 欄寬 8、Notes 維持 75 及 notes_format）。

### 3. `ui/display.py` — `_build_display_data()`
- 導入 `from models.mode_registry import get_mode_families`，並在函式內計算
  `is_b_special = mode in get_mode_families().get('b_special', set())`（即 B2/B2a/B2L/B2La/B3/B3a/B3L/B3La）。
- 當 `is_b_special` 為真時，改用與 Excel 一致的新 21 欄 row_data（key 順序即顯示順序）：
  - `Brand` = `rec.get('Product Hierarchy') or rec.get('Brand') or ''`
  - `Transfer Site Type` = `rec.get('Transfer Site Type', '')`、`Receive Site Type` = `rec.get('Receive Site Type', '')`
  - 沿用既有 stock lookup 的 `source_stock`/`source_safety`/`source_after_transfer_stock`/`dest_stock`/`dest_safety`
  - `Remark` = `f"{rec.get('Source Type','')} → {rec.get('Destination Type','')}"`
  - `Notes` = `rec.get('Notes', '')`
  - 移除預覽原有的 `Source MOQ`、`Receive MOQ`、`Receive Total After`、`Source Type`、`Destination Type`（僅 B 系模式預覽，與新 Excel 欄位一致）
- 非 B 系模式維持現有 row_data 建構邏輯不變。

### 4. Tests
- `tests/test_excel_generator.py`：
  - `_make_recommendation()` 加入 `"Transfer Site Type": "T"`、`"Receive Site Type": "M"` 預設值。
  - 新增 `test_new_column_order_all_modes`：以 mode=`加強轉貨` 與 mode=`附加B(特別模式)` 各生成一次，斷言 `df.columns.tolist() == EXCEL_COLUMN_ORDER`（含全部 21 欄、順序正確）。
  - 新增 `test_type_columns_values`：讀回 Excel 斷言 Type 欄位值與 rec 一致（T/M）。
  - 新增 `test_d001_mode_keeps_d001_column`：mode=`精簡SKU(退D001)` 時尾欄為 `D001 Receive Qty`。
  - 既有 `test_recommendation_columns`、`test_empty_recommendations` 應仍通過（空資料用 `pd.DataFrame(df_data, columns=cols)` 建構，不會 KeyError；空表讀回 `len(df)==0`）。
- 新增 `tests/test_recommendation_factory.py`（或併入既有檔案）：直接測試 `build_recommendation` 會把 source/dest 的 `store_type` 寫入 `Transfer Site Type` / `Receive Site Type`，且 `is_d001_return=True` 時 `Receive Site Type == ''`。

### 5. 文件同步（依 AGENTS.md 慣例）
- `config.py`：`VERSION = "v2.30.0"` → `"v2.31.0"`
- `app.py`：docstring `v2.30.0` → `v2.31.0`
- `VERSION.md`：新增 `## v2.31.0 (2026-08-14)` 條目，說明欄位調動與 Type 欄位新增
- `README.md`：於輸出/功能說明處補一句：Excel 輸出新欄序與 `Transfer Site Type`/`Receive Site Type`（Type=T 遊客區 / M 混合型 / L / R）
- `調貨模式詳解.txt`：更新「Excel輸出資料結構 → 主要工作表：調貨建議」段落（現行 line 843–867），改為新 21 欄順序並補 Type 欄說明
- `ui/tutorial.py`：於 B2~B3La 群組說明補一項「輸出 Excel 含 Transfer/Receive Site Type 欄」
- `transfer_logic_ai_brief.md`：無配對邏輯變更，不需更新

## 驗證

1. 執行既有測試套件：`python _run_tests.py`（或 `pytest tests/`）。
2. 手動冒煙測試：用 `data/` 下範例資料跑 `附加B(特別模式)` 與 `加強轉貨`，下載 Excel 檢查欄位順序、寬度、Type 值、Notes 換行格式；確認 `精簡SKU(退D001)` 尾欄 `D001 Receive Qty` 存在。
3. App 內預覽：B 系模式顯示 21 欄與 Excel 一致；非 B 系模式預覽不受影響。

## 風險 / 注意事項

- `df.to_excel` 的欄序由 DataFrame 欄序決定，header 迴圈已自動跟隨，不需額外調整。
- 空 recommendations 情境改用 `pd.DataFrame(df_data, columns=cols)` 避免 `df[cols]` KeyError，且不影響既有 empty 測試。
- UI 預覽僅 B 系模式改版（依使用者選擇）；若日後要全模式一致，把 `is_b_special` 判斷移除即可。
