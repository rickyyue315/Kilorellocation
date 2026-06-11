# 將 C1 的「每店轉出件數上限」功能擴展到 C 和 C2 模式

## 背景

目前 C1 模式在側邊欄有一個滑塊「C1 每店轉出件數上限」（3~10 件，預設 3），控制每間 RF 源店最多可轉出的件數。C 和 C2 模式使用硬編碼常數 `C_MODE_ABS_CAP = 3`，無法由用戶調整。

目標：讓 C 和 C2 模式也能使用相同的可調上限滑塊。

## 影響範圍

- **`_compute_rf_transferable`** (business_logic.py:230)：C、C1、C2 共用同一段邏輯，只需將 `self.c1_ceiling` 也套用到 C 和 C2
- **側邊欄 UI** (ui/sidebar.py:186)：擴展條件，讓 ceiling 滑塊在 C/C1/C2 時都顯示
- **ModeDef** (models/mode_registry.py:64,70)：C 和 C2 的 `extra_ui_options` 加入 `c1_ceiling`
- **文檔同步** (AGENTS.md 要求 7 個文件)

## 實作步驟

### 1. models/mode_registry.py
- C ModeDef (line 64)：`extra_ui_options` 加入 `'c1_ceiling'`
- C2 ModeDef (line 70)：`extra_ui_options` 加入 `'c1_ceiling'`

### 2. ui/sidebar.py
- 將 `if mode_code == "C1"` 拆成兩個條件：
  - `c1_threshold` number_input 保持在 `if mode_code == "C1"` 內（C1 獨有）
  - `c1_ceiling` slider 移到 `if mode_code in ("C", "C1", "C2")` 內
- UI 標籤從「C1 每店轉出件數上限」改為「每店轉出件數上限」
- `c1_ceiling` 預設值仍為 3，範圍 3~10

### 3. business_logic.py
- Line 230：`self.c1_ceiling if mode == self.mode_c1 else C_MODE_ABS_CAP`
  改為 `self.c1_ceiling if mode in (self.mode_c, self.mode_c1, self.mode_c2) else C_MODE_ABS_CAP`

### 4. config.py
- `VERSION` 從 `"v2.24.1"` 升至 `"v2.24.2"`

### 5. app.py
- Module docstring 版本號同步為 v2.24.2

### 6. 文檔同步（依 AGENTS.md 要求）
- **README.md**：更新模式列表（C 描述加入「每店轉出上限可調」）、功能亮點（合併重複的C1條目並加入 C/C2）、模式對照表
- **VERSION.md**：新增 v2.24.2 條目
- **ui/tutorial.py** / **data/tutorials/c.json**：更新 C 和 C2 的 `source_flow`、`extra_notes`、`diff_table`，反映上限可調
- **調貨模式詳解.txt**：更新 C 和 C2 的轉出規則描述
- **transfer_logic_ai_brief.md**：更新 C 和 C2 的 abs_cap 描述為 configurable

### 不影響的部分
- `c1_threshold`（補0門檻）仍是 C1 獨有，C 和 C2 不做變更
- matching_engine.py 無需修改（ceiling 僅影響 source transferable 計算，不影響匹配邏輯）
- `C1_MODE_MIN_TRANSFER`（最少 2 件）仍是 C1 獨有
- `C1_MODE_DEFAULT_THRESHOLD` 仍是 C1 獨有
