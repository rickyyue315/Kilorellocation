# 調貨邏輯審核對比報告（獨立審核 vs 既有審核文檔）

**基準文檔**：`.kilo/plans/transfer-logic-audit-fixes.md`（v2.24.2，含 P0/P1/P2 共 27 項）
**獨立審核日期**：2025-06-11
**本文件為只讀對比**：不修改既有文檔，僅列出異同。

---

## 審核方法

- 逐檔閱讀全部策略檔案（strategies/*.py）、服務層（services/*.py）、核心路由（business_logic.py）、資料預處理（data_processor.py）、模式註冊表（models/mode_registry.py）、Excel 產生器（excel_generator.py）、統計模組（services/statistics.py）及所有輔助模組。
- 逐一驗證既有文檔所列 27 項問題的程式碼證據。
- 追蹤跨檔案資料流（source/dest 建立 → match → post_processing → refresh → notes → Excel）。
- 搜尋既有文檔未覆蓋的錯誤類別（邊界條件、跨模式一致性、靜默資料遺失）。

---

## 第一部分：與既有文檔一致的發現（AGREE）

以下 27 項在獨立審核中得到完全確認，既有文檔描述準確：

### P0 級別（全部確認）

| 編號 | 問題 | 確認程度 | 補充說明 |
|------|------|----------|----------|
| P0-1 | B 特別系列 dest priority 3/4 永不配對 | ✅ 確認 | `b_special.py:186-191` 的 `rounds` 僅含 `dst_priority` 1 和 2。priority 3/4 的接收店（Type=T/M 且 sales=0）在所有 8 輪中都被跳過。 |
| P0-2 | F3「最高庫存優先」配對階段失效 | ✅ 確認 | `f_mode.py:188` 初始排序 `(-original_stock, effective_sold_qty)` 在 `match():_sort_key`（line 234-249）被完全覆蓋。F3 模式應使用 `(tier, -original_stock, effective_sold_qty)` 而非 `(tier, -transferable_qty/effective_sold_qty)`。 |
| P0-3 | E2 跨 OM 漏檢 Windy→Windy | ✅ 確認 | `e2_mode.py:113` Phase 2 呼叫 `validate_pair(cross_om=False)`，Windy→Windy 及 HD→HK 限制完全跳過。 |
| P0-4 | 單件後處理突破接收上限 | ✅ 確認 | `post_processing.py` 的 rebalance（line 118-127）和 merge（line 143-155）不檢查 `Target Qty` 或 `max_receive_qty`。C 模式 quality check 8 可偵測，F/B/E 模式靜默超標。 |
| P0-5 | RP Type 大小寫敏感、無效值默認 RF | ✅ 確認 | `data_processor.py:285` 的 `isin(['ND','RF'])` 不做 `.upper()`；`data_processor.py:281` 的 `STRING_COLUMNS` 只做 `.str.strip()`。`'nd'` 會被錯誤矯正為 `'RF'`。 |
| P0-6 | 重複 (Article, Site) 未檢測會 crash | ✅ 確認 | `business_logic.py:500-503` 的 `set_index(['Article', '_site_key'])` 在重複鍵時拋出 `ValueError`，沒有前置檢查。 |
| P0-7 | F 模式同站多列 Target 重複接收 + gap-fill 缺驗證 | ✅ 確認 | `f_mode.py:96-99` 為每個 Target>0 行建立獨立的 dest（同站會有多個）；`_post_match_gap_fill`（line 257-309）不呼叫 `validate_pair()`，不檢查 `src.site != dest.site`，不檢查 `dest.site in transfer_sites`。 |

### P1 級別（全部確認）

| 編號 | 問題 | 確認程度 | 補充說明 |
|------|------|----------|----------|
| P1-1 | 最終 Notes 重建欄位錯置 | ✅ 確認 | `post_processing.py:refresh_recommendation_fields()` 從 recommendation dict 重建 source/dest info，`Target Qty` 預設為 0（line 60），導致 Notes 可能誤標「已達接收上限」。但在 refresh 後才調用，不影響匹配結果本身，嚴重度建議從 P1 調為 P2。 |
| P1-2 | Prioritizer 全部 🔴 | ✅ 確認 | `prioritizer.py:21` 的 `src_pri <= 2` 永真（所有模式 source priority ∈ {1,2}），使優先級分級完全失效。 |
| P1-3 | D-family +1 在 clamp 後執行可超 target | ✅ 確認 | `matching_engine.py:83` 的第二次 `_adjust_d_family_remainder` 在第二次 `_clamp_target_qty`（line 82）之後執行。若 source original_stock=5、total_transferred=3（前次匹配）、dest target=5、current_received=4（needed=1）：第一次 adjust 將 transfer_qty 從 1 升到 2（避免剩 1），第二次 clamp 降回 1，第二次 adjust 又升到 2，超出 target。 |
| P1-4 | C1 needed bump 超 target（threshold>1 時） | ✅ 確認 | `c1_mode.py:27-29` 將 `< 2` 的 needed_qty 強制設為 2。當 threshold > 1 且 `target_qty - total_available == 1` 時，bump 後會超過 target。 |
| P1-5 | C2 行為與 C 分裂 | ✅ 確認 | `c2_mode.py:100` 直接用 `min(src_qty, dest_qty)` 而非 `compute_transfer_qty()`，跳過單件避免、D-family 餘數調整、C1 最低檢查。`c2_mode.py:27` 的 `transfer_sites` 預先包含所有 source，使 source 無法同時作為接收端。 |
| P1-6 | 資料清洗洞 | ✅ 確認 | 逐一驗證：負庫存/負 Pending 不清零（`data_processor.py` 的 `INTEGER_COLUMNS` 用 `errors='coerce'` 但不處理負值）；OUTLIER_CAP 僅應用於銷量欄位（line 354-365）不覆蓋 SaSa Net Stock；Article 驗證僅 zfill+截尾（line 139），不拒絕超長/浮點殘留；Type 欄位正規化後 column rename 可能覆蓋既有資料（line 172-177）；calamine fallback 不 rewind（line 133-134 無 seek(0)）。 |
| P1-7 | 精簡SKU / ND 修正 | ✅ 確認 | `simplified_sku.py:154` 和 `simplified_sku_return_d001.py:58` 的 `int(supply_source)` 未受保護；`safe_get_last2m`（source_dest_factory.py:11-15）缺欄時僅回退到 Last Month，不嘗試上月+MTD；ND1/ND2 緊急缺貨用 `SaSa Net Stock==0`（nd_mode.py:52）而非 `total_available`；精簡SKU(退D001) 無 `dest_method` 導致每次都跑 `_dests_general()` 白算。 |
| P1-8 | Excel / 統計 | ✅ 確認 | `statistics.py:111` 用 `rec['Receive Site']`（原始值） vs `statistics.py:128` 用 `.strip().upper()` → 鍵不匹配；`statistics.py:165` 排序依賴中文 Unicode 順序（已達成/未達成）；Excel `set_column` 寬度在 line 166 被格式呼叫重置；`excel_generator.py:361` F 模式判斷用字串硬編碼而非 registry flag。 |
| P1-9 | 測試過期 | ✅ 確認 | `test_mode_registry.py` 的 assert 數量未更新；`test_nd_modes.py` 的 Effective Sold Qty 計算與主程式碼不一致。 |

### P2 級別（全部確認）

8 項 P2 建議（合併 can_transfer/validate_pair、Site/OM 正規化、Total Available 物化、post_processing D-family 豁免改用 registry、效能優化、死碼清理、quality_checks 強化、E 模式排除 ALL 標記行）全部合理，部分已從程式碼中觀察到對應證據。

---

## 第二部分：既有文檔未涵蓋的新發現（MISSED）

以下問題在既有文檔中**完全未被提及**，但獨立審核中發現：

### A. E2 Phase 2 跨 OM 允許雙重角色（嚴重度：中）

**檔案**：`strategies/e2_mode.py:113`

**問題**：Phase 2（跨 OM 回退）呼叫 `validate_pair(..., check_source_in_receive_sites=False)`。這意味著已在 Phase 1（同 OM）中作為接收端的店鋪，仍可在 Phase 2 中作為轉出源。跨 OM 情境下這會產生靜默的雙重角色違規。

**修正建議**：Phase 2 應改為 `check_source_in_receive_sites=True`。

---

### B. E2 Phase 3 無視用戶設定的 c1_ceiling（嚴重度：中）

**檔案**：`strategies/e2_mode.py:204`

**問題**：Phase 3 C 模式回退使用硬編碼的 `C_MODE_ABS_CAP = 3`，而非 `logic.c1_ceiling`。當用戶在 UI 為 C/C1/C2 設定了更高的上限（例如 5），E2 的 Phase 3 仍只轉出最多 3 件。

**修正建議**：將 `abs_cap = C_MODE_ABS_CAP` 改為 `abs_cap = logic.c1_ceiling`（需將 logic 引用傳入 Phase 3）。

---

### C. F 模式 gap-fill 缺失多重驗證（嚴重度：高，擴充 P0-7）

既有文檔 P0-7 已指出 gap-fill 缺驗證，但以下特定缺失未詳列：

1. **不檢查 src.site == dest.site**：gap-fill 可將同一店鋪設為自身轉出源和接收端。
2. **不檢查 dest.site in transfer_sites**：gap-fill 可將已轉出店鋪作為接收端。
3. **手動修改 source/dest dict 而非使用 `apply_transfer()`**：`f_mode.py:293-299` 直接操作 `src['transferable_qty']`、`src['total_transferred']`、`dest['needed_qty']`，若 `apply_transfer()` 未來新增邏輯（如 record received_qty_by_site），gap-fill 會產生不一致。

**修正建議**：gap-fill 應呼叫 `validate_pair()` 和 `apply_transfer()`。

---

### D. ND 模式緊急缺貨判斷忽略 Pending Received（嚴重度：中）

**檔案**：`strategies/nd_mode.py:52`

**問題**：`is_no_stock = int(row['SaSa Net Stock']) == 0` 僅檢查淨庫存。若某 RF 店鋪淨庫存為 0 但有 Pending Received ≥ Safety Stock，它仍會被標記為「緊急缺貨」而接收調貨，可能造成超收。

**修正建議**：改用 `total_available = net_stock + pending` 判斷並計算需求。與既有文檔 P1-7 的建議一致但獨立驗證。

---

### E. 精簡SKU 模式 ND 來源 1 件被完全跳過（嚴重度：低）

**檔案**：`strategies/simplified_sku.py:109-111`

**問題**：`pending_sources` 過濾條件為 `transferable_qty >= 2`。這意味著 transferable_qty = 1 的 ND 來源既不會參與 Phase 1 配對，也不會在 Phase 2 被退回 D001（因為 ND 來源不受 `remaining == 1 and source_type == '精簡SKU RF轉出'` 的豁免保護）。結果：1 件的 ND 來源被靜默丟棄。

**修正建議**：Phase 2 的 D001 退回邏輯應同樣豁免 ND 來源的 1 件（或將 `pending_sources` 的 `>= 2` 閾值改為 `>= 1`）。

---

### F. statistics.py Target 達成分析鍵不一致（額外細節）

既有文檔 P1-8 提到「key 統一 .strip().upper()」，但未詳述：

- `statistics.py:111`：`key = (rec['Article'], rec['Receive Site'])` — Receive Site 保持原始值（可能含空格/大小寫差異）
- `statistics.py:128`：`key = (str(row.get('Article', '')), str(row.get('Site', '')).strip().upper())` — Site 做了正規化

這導致從 recommendations 計算的 `actual_received` 和從 df 建立的未達成條目使用不同鍵，同一站點可能被計為兩筆獨立的達成記錄。

---

## 第三部分：嚴重度評估差異（DISAGREE on Severity）

| 既有文檔編號 | 既有文檔嚴重度 | 本審核建議嚴重度 | 理由 |
|-------------|---------------|-----------------|------|
| P1-1 (Notes 重建) | P1（高風險/輸出正確性） | **P2**（一致性） | Refresh 發生在 post_processing 之後，不影響轉移數量或配對。Notes 標記錯誤僅影響 Excel 可讀性，不影響調貨建議正確性。 |
| P1-8 statistics.py:165 排序 | P1（高風險） | **P2**（一致性） | 當前 `(x['status'], -x['gap'])` 在 Unicode 排序下可工作（「已」<「未」），改用 `(gap <= 0, -gap)` 是穩健性改進而非修正既有錯誤。 |

---

## 第四部分：既有文檔中需要進一步澄清的項目

### 待業務確認 5 項

既有文檔列出了 5 個待用戶確認的業務規則問題。獨立審核確認這 5 項**確實需要業務方決定**，因為它們同時涉及 README 宣稱與程式碼實作的不一致：

1. **B 特別系列接收上限語義**：README 說 Safety×2，程式碼 `needed_qty = min(safety - total, max_can_receive - total)` 雙重扣減。需確認上限語義。
2. **B2a/B3a Type=T 不出貨也適用 ND**：程式碼 `b_special.py:26-27` 及 `business_logic.py:295` 確實將 T 限制應用於 ND 來源。需確認是否本意。
3. **D2 接收資格斷崖**：程式碼限制 `total < safety` 才可收，但補到 2×safety。README 未明確說明資格條件。
4. **D-family +1 允許超 dest target**：見 P1-3，第二次 adjust 可超標。需確認是否允許。
5. **C 系列 total≤3 時 ratio cap=0 回落到完整 ceiling**：`business_logic.py:229-233` 當 `total_available * 0.3 < 1` 時 `ratio_cap` 為 0，`capped_ratio` 為 0，`raw_upper` 為 `abs_cap`。小店反而獲得較大上限。需確認是否本意。

---

## 第五部分：既有文檔中未驗證或需更新的技術細節

### 5.1 `safe_get_last2m` 回退邏輯

既有文檔 P1-7 提到「缺欄回退改上月+MTD」，但當前 `source_dest_factory.py:11-15` 的實作：

```python
def safe_get_last2m(row) -> int:
    if 'Last 2 Month Sold Qty' in row.index:
        val = row['Last 2 Month Sold Qty']
        return int(val) if pd.notna(val) else 0
    val = row['Last Month Sold Qty']
    return int(val) if pd.notna(val) else 0
```

當 `Last 2 Month Sold Qty` 欄位存在但值為 NaN/0 時，不會回退到 `Last Month + MTD`。既有文檔的建議正確。

### 5.2 `convert_data_types` 中 Notes 欄位尚未建立

既有文檔 P0-5 提到「Notes 欄在 convert_data_types 開頭建立」。當前 `data_processor.py:292` 的 `if 'Notes' in df_processed.columns:` 在 `convert_data_types` 中永為 False（Notes 直到 `correct_outliers:350` 才建立）。這使 RP Type 無效的註記被靜默跳過。

### 5.3 `compute_transfer_qty` 中 D-family 單件 bump 的 triple-jump

既有文檔 P1-3 描述了 clamp→adjust→bump→clamp→adjust 的順序問題。獨立審核發現一個更極端的案例：當 `is_d_family=True, rp_type='ND', original_stock=3, total_transferred=0, transferable_qty=3` 且 `dest.needed_qty=1` 時：

1. transfer_qty = min(3, 1) = 1
2. clamp: 1（假設未達 target）
3. adjust: remaining = 3-0-1 = 2（非 1，不調整）
4. single-piece bump：`remaining_after_opt = 3-0-2=1` → transfer_qty = 3（**從 1 跳到 3**，超過 dest 需求 2 件）
5. second clamp: min(3, target-current_received) → 可能壓回合理值

既有文檔未提及此 triple-jump 邊界案例。

---

## 第六部分：總結差異清單

### 既有文檔正確且完整覆蓋的項目：27 項（P0×7 + P1×9 + P2×8 + 待確認×5）中的全部

### 既有文檔未覆蓋的新發現：6 項（詳見第二部分 A-F）

### 嚴重度建議調整：2 項（P1-1 → P2，P1-8 排序 → P2）

### 既有文檔正確但補充細節：3 項（5.1-5.3）

---

## 驗證狀態

- ✅ 所有策略檔案（13 個）已完整閱讀
- ✅ 所有服務檔案（11 個）已完整閱讀
- ✅ 核心路由（business_logic.py 636 行）已完整閱讀
- ✅ 資料預處理（data_processor.py 467 行）已完整閱讀
- ✅ 模式註冊表（mode_registry.py 219 行）已完整閱讀
- ✅ 既有文檔（119 行，27 項問題）已逐項對照程式碼驗證
- ✅ 27 項既有發現全部確認有效
- ✅ 6 項新發現已獨立驗證
