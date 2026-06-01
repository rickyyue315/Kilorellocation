# F3 模式（目標性補0）新增計劃

## 概述

新增第 26 種模式 **F3: 目標性補0**，基於 F2 架構，核心差異：

| 項目 | F2（現有） | F3（新增） |
|------|-----------|-----------|
| ND 轉出 | 全數轉出 | **相同** — 全數轉出 |
| RF 轉出量 | 全數淨庫存轉出 | **改為** `max(net_stock - 2, 0)`（保留 2 件） |
| RF 排序 | 銷量低優先 | **改為** 最高庫存優先 + 銷量低優先 |
| RF 跨OM 懲罰 | tier 2（降級） | **取消** — 同 OM / 跨 OM 同等排序 |
| HD 轉出選項 | 有（可設定） | **相同** — 有（可設定） |
| Windy 懲罰 | +5 | **相同** — +5 |
| Target 保護 | 有 | **相同** — 有 |
| 接收端 | 僅 Target > 0 | **相同** — 僅 Target > 0 |

版本號：**v2.17.0**

---

## 修改檔案清單

### 1. `models/mode_registry.py` — 新增 F3 ModeDef

在 F2 ModeDef 之後新增：

```python
ModeDef("F3", "目標性補0", "F2 + RF轉出後保留2件 + RF按最高庫存優先轉出 + RF跨OM不降級",
        attr_name="mode_f3",
        cross_om_grouping=True, cross_om_matching=True, source_filter=True,
        strategy_key='f_mode',
        source_method='_sources_f_mode', dest_method='_dests_f_mode',
        extra_ui_options=frozenset({'f2_hd_transfer'})),
```

### 2. `strategies/f_mode.py` — `_sort_key` 加入 F3 判斷

修改 `_sort_key()` 內部函數（約行 42-54），新增 F3 分支：

- 新增 `is_f3 = (mode == "目標性補0")` 判斷
- **tier 計算**：當 `is_f3` 時，RF 不分同 OM / 跨 OM，一律 tier = 1（等同同 OM RF）
  ```python
  if is_f3:
      tier = 0 if rp == 'ND' else 1  # F3: RF 跨OM 不降級
  else:
      tier = 0 if rp == 'ND' else (1 if same_om == 1 else 2)
  ```
- **hd_penalty** 和 **windy_penalty** 保持與 F2 相同邏輯

需要將 `mode` 參數傳入 `_sort_key`。目前 `_sort_key` 是 `match()` 方法內的閉包，已可存取 `mode`，所以只需讀取即可。

### 3. `business_logic.py` — `_sources_f_mode` 加入 F3 RF 邏輯

在 `_sources_f_mode()` 方法中（行 291-330），加入 F3 判斷：

**RF source 區塊**（行 308-327）的修改：

- 新增 `is_f3 = (mode == self.mode_f3)` 判斷（`self.mode_f3` 會透過 `setattr(self, d.attr_name, d.name)` 自動建立）
- **轉出量**：當 `is_f3` 時，`transferable_qty = max(net_stock - 2, 0)`；否則維持 `net_stock`
- **淨庫存門檻**：當 `is_f3` 時，需 `net_stock > 2` 才可轉出（因為至少保留 2 件）；否則維持 `net_stock > 0`
- **source_type 文字**：F3 使用 `'F3模式RF轉出(保留2件)'` 以區分

**Source 排序**（行 329）：
- 當 `is_f3` 時，改為 `sources.sort(key=lambda x: (x['priority'], -x.get('original_stock', 0), x.get('effective_sold_qty', 0)))`
  - 即：先按 priority（ND=1 先於 RF=2），再按 **最高庫存優先**（`-original_stock`），最後按 **最低銷量優先**
- `_make_source` 已有 `original_stock` 欄位（行 66），可直接使用

### 4. `ui/sidebar.py` — F3 也支援 HD 轉出選項

修改 HD 轉出選項的條件（行 133）：

```python
# 原本：
if mode_code == "F2":
# 改為：
if mode_code in ("F2", "F3"):
```

### 5. `app.py` — 更新模式檢查與 docstring

- **行 1-4（docstring）**：25→26 模式，新增 `F3(目標性補0)` 到列表
- **行 134**：`if mode_code in ["F", "F2"]:` → `if mode_code in ["F", "F2", "F3"]:`
- **行 164**：`current_run_key` 已包含 `f2_allow_hd_transfer`，無需修改
- **行 175**：`MODE_NAME_MAP.get(mode_code, "目標優化")` — F3 已在 mode_registry 註冊，無需修改

### 6. `config.py` — 版本號 bump

```python
VERSION = "v2.17.0"
```

### 7. `VERSION.md` — 新增版本記錄

在檔案頂部新增 v2.17.0 條目。

### 8. `README.md` — 文件同步

- 模式列表新增 `F3：目標性補0（F2 + RF轉出保留2件 + 最高庫存優先 + 跨OM不降級）`
- 跨 OM 規則新增 F3 區塊（HD 可轉出選項、Windy 規則同 F2、RF 跨 OM 不降級）
- 功能亮點更新
- 模式對照表新增 F3 行
- 教學分組更新為「目標優化系列（F / F2 / F3）」

### 9. `ui/tutorial.py` — 新增 F3 教學

在 `_render_f_group()` 函數中（行 704-772），新增 F3 教學內容：
- scenario：需要精準分配庫存到 Target 店舖，同時確保 RF 轉出店保留最低庫存
- source_flow：ND 全轉出 → RF 保留 2 件轉出（最高庫存優先）
- dest_flow：同 F2（僅 Target 接收）
- match_order、scenario_table、diff_table
- 返回列表從 `[content_f, content_f2]` 改為 `[content_f, content_f2, content_f3]`
- `render_tutorial_page()` 中的分組標題改為「目標優化系列（F / F2 / F3）」

### 10. `調貨模式詳解.txt` — 新增 F3 詳解

- 關鍵差異對比表新增 F3 列
- 新增「模式 F3：目標性補0」完整說明段落
- 應用場景建議新增 F3

### 11. `transfer_logic_ai_brief.md` — 新增 F3 說明

- Mode Overview 更新為 26 模式
- 新增 Mode F3 完整說明段落
- 視覺化關鍵字新增 F3

### 12. `tests/test_f3_mode.py` — 新增測試（新檔案）

測試覆蓋：
1. F3 RF 轉出後保留 2 件（net_stock=5 → transferable_qty=3）
2. F3 RF 淨庫存 ≤ 2 時不轉出
3. F3 RF 跨 OM 不降級（跨 OM RF 與同 OM RF 相同 tier）
4. F3 RF 最高庫存優先排序
5. F3 ND 仍全數轉出
6. F3 Target 店舖保護（不轉出）
7. F3 僅 Target > 0 接收
8. F3 HD 轉出選項（允許 / 不允許）
9. F3 Windy 懲罰 +5
10. F3 與 F2 對比測試（確認行為差異）

---

## 實作順序

1. `models/mode_registry.py` — 註冊 F3
2. `business_logic.py` — source 邏輯修改
3. `strategies/f_mode.py` — sort key 修改
4. `ui/sidebar.py` — HD 選項擴展
5. `app.py` — docstring + 模式檢查
6. `config.py` — 版本號
7. `tests/test_f3_mode.py` — 測試
8. `VERSION.md` — 版本記錄
9. `README.md` — 文件同步
10. `ui/tutorial.py` — 教學同步
11. `調貨模式詳解.txt` — 詳解同步
12. `transfer_logic_ai_brief.md` — AI brief 同步

---

## 驗證

- 執行 `pytest tests/` 確保全部測試通過
- 重點驗證 F3 RF 保留 2 件、跨 OM 不降級、最高庫存優先排序
