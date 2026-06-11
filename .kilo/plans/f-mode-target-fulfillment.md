# F/F2/F3 模式 Target 達成分析與優化方案

## 背景

目前 F/F2/F3 模式下，系統能正確追蹤每個 rec 的 Target Qty 和 Cumulative Received Qty，配對期間也會在累計接收量 >= Target 時停止分配。但配對結束後：

1. **Target Qty / Cumulative Received Qty 未輸出至 Excel** — 這些欄位存在於 recommendation dict 中，但 `excel_generator.py` 沒有寫出
2. **沒有 Target 達成總結** — 無法一眼看出哪些 SKU+分店 已達成、哪些有缺口
3. **配對邏輯可優化** — 目前 priority-1 dest 按 needed_qty DESC（大目標優先），這可能導致一個大目標吸乾所有供應，讓多個小目標完全落空

---

## Part A — 新增「Target達成分析」Excel 工作表

### 檔案變更

#### 1. `excel_generator.py` — 新增方法 `create_target_fulfillment_sheet()`

觸發條件：僅當 `mode` 為 F/F2/F3 時生成此工作表。

**資料來源**：從 `recommendations` 列表重建每組 (Article, Receive Site) 的實際接收總量，比對其 Target Qty。

```python
def create_target_fulfillment_sheet(self, writer, recommendations, mode):
    # 僅 F/F2/F3 觸發
    if mode not in ("F模式(目標優化)", "F指定模式", "目標性補0"):
        return
    
    # 從 recommendations 聚合：key = (Article, Receive Site)
    # target_qty = rec['Target Qty']（取第一筆非零值）
    # actual_received = sum(rec['Transfer Qty'])
    # gap = target_qty - actual_received
    # status = "已達成" if gap <= 0 else "未達成|缺口N件"
    # 寫入新工作表 "Target達成分析"
```

**工作表欄位**：

| 欄位 | 說明 |
|------|------|
| Brand | 品牌 |
| Article | 商品編號 |
| Product Desc | 商品描述 |
| Receive OM | 接收方 OM |
| Receive Site | 接收方分店 |
| RP Type | ND / RF |
| Target Qty | 原始目標數量 |
| Actual Received | 實際接收總量（多筆建議加總） |
| Gap | 缺口（正數=未達成，0=達成） |
| Status | 已達成 / 未達成(缺口N件) |

**工作表底部匯總**：

| 指標 | 說明 |
|------|------|
| 總目標數 | 有 Target 的 (Article, Site) 組合總數 |
| 已達成 | 達成數量 |
| 達成率 | 百分比 |
| 未達成 | 缺口數量 |
| 總缺口件數 | 所有 gaps 加總 |

#### 2. `services/statistics.py` — 新增 `compute_target_fulfillment_stats()`

從 recommendations 計算達成率數據，供 UI dashboard 與 Excel 共用：

```python
def compute_target_fulfillment_stats(recommendations):
    # 返回 dict:
    # {
    #   'total_targets': int,
    #   'fulfilled': int,
    #   'unfulfilled': int,
    #   'fulfillment_rate': float,
    #   'total_gap': int,
    #   'details': List[Dict]  # 逐筆 (article, site, target, actual, gap)
    # }
```

#### 3. `ui/display.py` — KPI 卡片加入達成率（可選）

在主畫面 KPI 卡片中，若為 F/F2/F3 模式，新增一張「Target 達成率」卡片。

---

## Part B — 配對邏輯優化（提高 Target 達成數）

### B1. 新增「優先滿足小目標」選項

**檔案**：`models/mode_registry.py`

在 F/F2/F3 的 `ModeDef.extra_ui_options` 中加入 `'f_fulfill_small_first'`。

**檔案**：`ui/sidebar.py`

F/F2/F3 模式 sidebar 新增 checkbox/radio：「優先滿足小型目標」—— 預設關閉（維持現有行為）。

勾選後：`priority-1 destinations` 排序改為 `needed_qty ASC`（小目標優先分配），提高整體達成數量。

### B2. 配對結束後缺口再分配（Post-Match Gap Filling）

**檔案**：`services/post_processing.py` 或 `strategies/f_mode.py`

在 `match()` 完成後，對仍有 gap 的 destination 進行最後一輪掃描：

```
1. 收集 temp_destinations 中 needed_qty > 0 且有 target_qty 的項目
2. 對每個有缺口的 dest：
   a. 重新掃描所有 temp_sources 剩餘 transferable_qty > 0 的來源
   b. 嘗試分配剩餘庫存（可放寬部分約束，視模式而定）
3. 只分配實際上可行的 transfer
```

**具體約束處理**：

| 約束 | 主配對 | 缺口填補 |
|------|--------|----------|
| ND→Target 可接收 | ✅ 允許 | ✅ 允許 |
| same-OM only (priority-2) | ✅ | ✅ 保持 |
| HD→HK 封鎖 | ✅ | ✅ 保持 |
| Windy→非Windy 封鎖 | ✅ | ✅ 保持 |
| F3 retain-2 | ✅ | ✅ 保持 |

缺口填補本質上是把主配對後剩餘的微小庫存碎片（尤其是 F3 RF 的 `net_stock - 2` 剩餘部分、或未被完全消耗的 ND 庫存）分配給有缺口的目標。

### B3. 回傳 fulfillment_data（為 Part A 提供資料源）

**檔案**：`strategies/f_mode.py`

修改 `match()` 方法，在配對完成後返回 fulfillment_data（或以 side-channel 傳遞），讓 `generate_transfer_recommendations()` 能取得並傳遞給 Excel generator。

**實施方式**：不走修改 match() 回傳值（會影響其他 strategy），改為：

1. 在 `FModeStrategy.match()` 結尾，將 `temp_destinations` 中有 target_qty 的 dest 的最終狀態寫入 `self._last_fulfillment_data`
2. `TransferLogic.generate_transfer_recommendations()` 在 f_mode match 後收集這些數據
3. 或者，直接在 `excel_generator.py` 中從 recommendations 重建（推薦：不需要改 match() 回傳值）

**推薦做法：從 recommendations 重建**（最簡單、最少改動）：
- 每個 rec 已攜帶 `Target Qty` 和 `Transfer Qty`
- 按 (Article, Receive Site) groupby：actual = sum(Transfer Qty), target = rec[Target Qty]
- 不需要碰 match() 的程式碼

---

## 實作順序

### Phase 1：可見性（新增 Excel 工作表）
1. `excel_generator.py` — 新增 `create_target_fulfillment_sheet()`
2. `excel_generator.py` — 在 `generate_excel()` 中呼叫新方法
3. `services/statistics.py` — 新增 `compute_target_fulfillment_stats()`

### Phase 2：優化邏輯
4. `models/mode_registry.py` — 新增 `'f_fulfill_small_first'` extra_ui_option
5. `ui/sidebar.py` — 加入 checkbox
6. `business_logic.py` — 傳遞 `f_fulfill_small_first` 給 `FModeStrategy`
7. `strategies/f_mode.py` — 根據 `f_fulfill_small_first` 調整 dest 排序

### Phase 3：文件同步（依 AGENTS.md 規範）
8. `README.md` — 更新 F/F2/F3 模式描述
9. `VERSION.md` — 新增版本記錄
10. `config.py` — bump VERSION
11. `app.py` — 同步 docstring 版本
12. `ui/tutorial.py` — 更新 F 模式教學內容
13. `調貨模式詳解.txt` — 更新模式詳解
14. `transfer_logic_ai_brief.md` — 更新 AI brief（若 matching 規則有變）

---

## 類別結構

所有 F/F2/F3 模式的 fulfillment data 提取和 sheet 生成均為獨立模組，不影響其他 24 種模式的現有行為。
