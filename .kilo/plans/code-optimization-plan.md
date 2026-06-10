# 系統代碼優化方案與風險評估

> **目標**：針對庫存調貨建議系統（v2.23.0）進行結構優化，提升維護效率，同時確保零功能回歸。
>
> **執行進度**：Phase 1 ✅ | Phase 2 ✅ | Phase 3 ❌ 已取消 | Phase 4 ✅
>
> **最後更新**：2026-06-10
>
> **結論前提**：系統源碼約 11,000 行，代碼行數本身不影響運行速度。Python 只載入被 import 的模組。真正的優化著眼於維護性和依賴衛生。
>
> **⚠️ 明確排除項目**：Phase 3（`iterrows()` 向量化）已被取消。原因：店舖數量 ~90 間、每次上傳上限 ~10,000 行，每個 Article group 平均 50-100 行，`iterrows()` 的效能損失不到 0.5 秒，但改寫涉及 A/B/C/C1/D 等模式各自的 transferable_qty 計算分支，出錯風險遠大於收益。**嚴禁將 `iterrows()` 替換為向量化操作，以避免影響計算邏輯的正確性。**

---

## Phase 1：低風險基礎設施優化

### 1.1 提取共享工具函式到 `services/source_dest_factory.py` ✅ 已完成

**現狀問題**：
- `_make_source()` 和 `_make_dest()` 定義在 `business_logic.py`（第 63-105 行）
- `_compute_max_protected_sold()` 定義在 `business_logic.py`（第 108-114 行）
- `strategies/e2_mode.py` 透過 `from business_logic import _make_source` 反向引用（第 14、19 行），產生迴圈導入風險

**執行方案**：
1. 新建 `services/source_dest_factory.py`
2. 將 `_make_source`、`_make_dest`、`_compute_max_protected_sold`、`_safe_get_last2m` 移入該檔案
3. `business_logic.py` 改為 `from services.source_dest_factory import ...`
4. `strategies/e2_mode.py` 改為 `from services.source_dest_factory import ...`

**受影響檔案**：
- `services/source_dest_factory.py`（新建，~50 行）
- `business_logic.py`（修改 import，刪除 4 個函式定義）
- `strategies/e2_mode.py`（修改 2 處 import）

**風險評估**：🟢 低
- 純搬遷操作，不改變任何邏輯
- 可透過現有測試套件驗證（`pytest tests/` 共 18 個現行測試檔案）
- **回退方案**：Git revert 即可

**驗證方式**：
```bash
pytest tests/ -v --tb=short
```

---

### 1.2 統一 `logging.basicConfig()` 到 `app.py` ✅ 已完成

**現狀問題**：
- `business_logic.py` 第 53 行、`data_processor.py` 第 19 行、`excel_generator.py` 第 19 行各自呼叫 `logging.basicConfig()`
- 後續呼叫被 Python 靜默忽略，但散佈式配置不符合最佳實踐

**執行方案**：
1. 保留 `app.py` 第 42 行的 `logging.basicConfig(level=logging.INFO)`
2. 其他模組只保留 `logger = logging.getLogger(__name__)`
3. 刪除 `business_logic.py`、`data_processor.py`、`excel_generator.py` 的 `logging.basicConfig()` 呼叫

**受影響檔案**：3 個檔案各刪除 1 行

**風險評估**：🟢 低
- `app.py` 是 Streamlit 入口，必定最先載入
- `basicConfig()` 呼叫只生效一次，移除多餘呼叫不影響日誌輸出

**驗證方式**：手動上傳 Excel 並觀察 console 日誌是否正常輸出

---

### 1.3 清理 `tests/legacy/` 目錄 ✅ 已完成

**現狀問題**：
- `tests/legacy/` 包含 12 個舊版測試檔案（~1,800 行），不被主測試流程使用
- 增加 `grep`/搜尋噪音

**執行方案**：
1. 將 `tests/legacy/` 移至 `archive/tests-legacy/`
2. 或在 `pytest.ini` / `pyproject.toml` 中新增 `testpaths = tests` 並排除 `legacy`

**受影響檔案**：無源碼變動

**風險評估**：🟢 低
- 不影響任何生產代碼
- 舊測試仍可在 archive 中查閱

---

## Phase 2：結構優化 — 拆分 `business_logic.py`

### 2.1 將 source/destination 識別邏輯遷移至 Strategy 類別 ✅ 已完成

**現狀問題**：
- `business_logic.py` 有 974 行，其中 ~600 行是 `_sources_*` 和 `_dests_*` 方法
- 每種模式都有獨立的 source/dest 邏輯，但全部集中在一個類別中
- `identify_sources()` 和 `identify_destinations()` 透過 `mode_def.source_method` / `mode_def.dest_method` 分派，但方法本身仍在 `TransferLogic` 類內

**執行方案**：
1. 為每種需要特殊 source/dest 邏輯的模式建立獨立的策略類別
2. 現有策略已部分實現（`f_mode.py`, `e1_mode.py`, `e2_mode.py`, `nd_mode.py`, `b_special.py`, `c2_mode.py`, `simplified_sku.py`）
3. 擴充這些策略類別，加入 `identify_sources()` 和 `identify_destinations()` 方法
4. `TransferLogic` 只保留分派邏輯和 `generate_transfer_recommendations()` 主流程

**具體遷移對照表**：

| 方法 | 目標策略檔案 |
|------|-------------|
| `_sources_simplified_sku` + `_dests_simplified_sku` | `strategies/simplified_sku.py` |
| `_sources_nd_mode` + `_dests_nd_mode` + `_sources_nd3_mode` + `_dests_nd3_mode` | `strategies/nd_mode.py` |
| `_sources_f_mode` + `_dests_f_mode` | `strategies/f_mode.py` |
| `_sources_e_mode` + `_dests_e_mode` | `strategies/e1_mode.py` |
| `_identify_nd_sources` + `_identify_b_special_type_l_sources` + `_dests_b_special` | `strategies/b_special.py` |
| `_dests_d_mode` + `_dests_d2_mode` | `strategies/d_mode.py`（新建） |
| `_dests_c1_mode` | `strategies/c1_mode.py`（新建） |
| `_sources_general` + `_dests_general` + `_compute_rf_transferable` | 保留在 `business_logic.py` |

**預期效果**：
- `business_logic.py` 從 974 行降至 ~350 行
- 每個策略檔案 80-200 行，職責單一

**受影響檔案**：
- `business_logic.py`（大幅縮減）
- `strategies/*.py`（8 個檔案擴充）
- `tests/`（可能需要調整 import，但行為不變）

**風險評估**：🟡 中
- 涉及 `self` 上下文的遷移（`self.mode_a`, `self.MODE_FAMILIES` 等屬性引用）
- 需要謹慎處理策略類別對 `TransferLogic` 屬性的依賴
- **緩解措施**：每遷移一個方法就跑一次完整測試套件

**回退方案**：每個策略的遷移都是獨立的 Git commit，可逐個 revert

**驗證方式**：
```bash
pytest tests/ -v --tb=short  # 全部通過
pytest tests/test_all_modes_comprehensive.py -v  # 27 模式完整覆蓋
```

---

## ~~Phase 3：效能優化 — 向量化替代 `iterrows()`~~ ❌ 已取消

> **取消原因**：
> - 店舖數量固定 ~90 間，每次上傳上限 ~10,000 行
> - 按 Article 分組後每個 group 平均 50-100 行
> - `iterrows()` 在此數據量級下的效能損失不到 0.5 秒
> - 改寫涉及 A/B/C/C1/D 等模式各自的 `transferable_qty` 條件分支邏輯，出錯風險高
> - A 模式特有的「單件自動上調至 2 件」邏輯、C1 模式的 `stock > 2` 前置過濾等條件，向量化時容易因布林遮罩優先級錯誤導致計算結果偏差
> - **結論：效能收益極小，計算邏輯出錯風險高，不值得執行**
>
> **⚠️ 嚴禁指示：任何 AI agent 或開發者不得將 `iterrows()` 替換為向量化操作（包括 `np.where`、布林遮罩、`df.apply()` 等），除非未來資料量超過 20,000 行且經過效能測量確認瓶頸。**

---

## Phase 4：長期維護性優化（可選）

### 4.1 `ui/tutorial.py` HTML 內容外部化 ✅ 已完成

**現狀**：1,013 行，27 種模式的教學內容全部以 Python f-string HTML 寫在函式中

**執行方案**：
- 將每個模式的教學內容改為 YAML/JSON 格式，放在 `data/tutorials/` 目錄
- `tutorial.py` 只負責渲染邏輯

**風險評估**：🟢 低（純 UI 層，不影響業務邏輯）

### 4.2 `perf_timer.py` 效能監控擴展 ✅ 已完成

**現狀**：已有 `@perf_timer` 裝飾器用於 `generate_transfer_recommendations`

**執行方案**：
- 在 `identify_sources`、`identify_destinations`、`match_transfers` 加入 `@perf_timer`
- 輸出至 Streamlit sidebar 的效能面板，方便用戶了解處理耗時

**風險評估**：🟢 低

---

## 執行優先級總覽

| 順序 | Phase | 工作項目 | 狀態 | 風險 | 影響範圍 |
|------|-------|---------|------|------|---------|
| 1 | Phase 1.1 | 提取 `_make_source`/`_make_dest` 到獨立模組 | ✅ 完成 | 🟢 低 | 3 檔案 |
| 2 | Phase 1.2 | 統一 logging 配置 | ✅ 完成 | 🟢 低 | 3 檔案 |
| 3 | Phase 1.3 | 清理 legacy 測試 | ✅ 完成 | 🟢 低 | 0 檔案 |
| 4 | Phase 2.1 | 拆分 `business_logic.py` source/dest 方法 | ✅ 完成 | 🟡 中 | ~10 檔案 |
| ~~5~~ | ~~Phase 3~~ | ~~向量化 `iterrows()`~~ | ❌ **已取消** | — | — |
| 5 | Phase 4.1 | tutorial 外部化（可選） | ✅ 完成 | 🟢 低 | 2 檔案 |
| 6 | Phase 4.2 | perf_timer 擴展（可選） | ✅ 完成 | 🟢 低 | 2 檔案 |

---

## 不建議做的事

1. **❌ 嚴禁向量化改寫 `iterrows()`** — 在 ~90 間店舖、10,000 行資料量的場景下，效能收益不到 0.5 秒，但 A/B/C/C1/D 模式的條件分支邏輯複雜，改寫極易導致計算結果偏差
2. **不建議過度拆分微服務** — 這是一個單體 Streamlit 應用，拆分為微服務會增加部署複雜度而無實質效能收益
3. **不建議引入 async** — 調貨邏輯是 CPU-bound（pandas 運算），async 不會帶來效能提升
4. **不建議重寫為其他語言** — Python + pandas 是此類數據處理的最佳選擇

---

## 驗證策略

每個 Phase 完成後執行：

```bash
# 1. 完整測試套件
pytest tests/ -v --tb=short

# 2. 27 模式綜合測試
pytest tests/test_all_modes_comprehensive.py -v

# 3. 手動煙霧測試：上傳 Excel，執行 A/B/C/D/F 模式，確認輸出一致
```
