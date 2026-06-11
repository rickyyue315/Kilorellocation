# Plan: New Shop Target調貨 (第28個模式)

## Summary

Add a **single new mode** (the 28th) called "New Shop Target調貨" (code: `NST`), similar to F2 (F指定模式) but with:
- RF shop transfer constraints (retain ≥2, 75% cap, skip if inventory <3)
- Per-SKU source shop count limit (10/20/unlimited)
- HD transfer option (same as F2)

---

## 1. New Strategy File: `strategies/nst_mode.py`

Create new file with `NewShopTargetStrategy` class extending `BaseMatchStrategy`.

### 1a. RF Source Rules (`identify_sources_nst_mode`)

ND shops: same as F2/F3 — full transfer (priority 1).

RF shops new constraints:
```
if net_stock < 3: skip (不轉出)
transferable_qty = min(int(net_stock * 0.75), net_stock - 2)
if transferable_qty <= 0: skip
source_type = 'NST模式RF轉出'
```
Sort: lowest `effective_sold_qty` first (same as F2).

### 1b. Destination Rules (`identify_destinations_nst_mode`)

Same as F2/F3: only stores with `Target > 0`, deduplicated by site. `dest_type = 'NST模式目標接收'`, `needed_qty = target_qty = target_value`.

### 1c. Matching (`NewShopTargetStrategy.match`)

Based on `FModeStrategy.match()` with these changes:

1. **Per-SKU source shop limit**: After sorting sources, track how many distinct source sites have been used. If `nst_max_source_shops` is set (10 or 20), cap the total number of unique source sites for this Article. Sources beyond the Nth unique site are not used. (Note: a source can still send multiple transfer lines to different destinations once admitted.)

2. **RF constraints**: The 75% cap and retain-2 are already applied in source identification. The matching itself works the same as F2.

3. **HD transfer option**: Same as F2 — `f2_allow_hd_transfer` (renamed to generic `hd_transfer` or keep name for compatibility).

4. **`f_fulfill_small_first`**: Same checkbox as F2.

5. **Post-match gap fill**: Same as F2.

### 1d. Constructor

```python
class NewShopTargetStrategy(BaseMatchStrategy):
    def __init__(self, create_note=None, nst_allow_hd_transfer=False,
                 f_fulfill_small_first=False, nst_max_source_shops=None):
```

---

## 2. Mode Registry: `models/mode_registry.py`

Add one entry to `MODE_DEFS`:

```python
ModeDef("NST", "New Shop Target調貨",
        "僅Target門市可接收，RF轉出保留≥2件且上限75%庫存，庫存<3不轉出，可設定HD轉出選項及同一SKU轉出店數上限",
        attr_name="mode_nst",
        cross_om_grouping=True, cross_om_matching=True, source_filter=True,
        strategy_key='nst_mode',
        source_method='_sources_f_mode', dest_method='_dests_f_mode',
        extra_ui_options=frozenset({'f2_hd_transfer', 'f_fulfill_small_first', 'nst_shop_limit'})),
```

Note: re-use `_sources_f_mode` and `_dests_f_mode` as method name hints, but actual routing goes through `strategy_key='nst_mode'`.

---

## 3. Business Logic: `business_logic.py`

### 3a. Constructor updates
- Add parameter `nst_max_source_shops: Optional[int] = None`
- Add `self.nst_max_source_shops = nst_max_source_shops`
- Add `self.mode_nst` attribute (auto-set from registry)
- Add `'nst_mode'` strategy init in `_init_strategies()`:
  ```python
  'nst_mode': NewShopTargetStrategy(
      create_note=self._create_recommendation_note,
      nst_allow_hd_transfer=self.f2_allow_hd_transfer,
      f_fulfill_small_first=self.f_fulfill_small_first,
      nst_max_source_shops=self.nst_max_source_shops,
  ),
  ```

### 3b. Match dispatch
In `match_transfers()` and `generate_transfer_recommendations()`, add NST mode to:
- F-mode dispatch condition: `if mode in (self.mode_f, self.mode_f_target_only, self.mode_f3, self.mode_nst)`
- Or use strategy_key routing (already handled by existing code)

### 3c. Target store protection
In `generate_transfer_recommendations()`, add `self.mode_nst` to the target_stores protection block (same as F2/F3).

### 3d. Quality checks
Add `self.mode_nst` to skip_nd_check modes (same as F2/F3).

---

## 4. Config: `config.py`

Add constants:
```python
NST_RF_RETAIN_STOCK = 2       # RF shop retain after transfer
NST_RF_TRANSFER_CAP = 0.75    # 75% of inventory
NST_RF_MIN_STOCK_TO_SOURCE = 3  # Skip if inventory < 3
```

Bump `VERSION` to `v2.25.0`.

---

## 5. UI Sidebar: `ui/sidebar.py`

### 5a. NST Shop Limit Option
Add after F2/F3 HD transfer panel:
```python
nst_max_source_shops = None
if mode_code == "NST":
    nst_shop_limit_option = st.radio(
        "同一SKU轉出店舖數量上限",
        ["10 間", "20 間", "不限制"],
        index=0,
        key='nst_shop_limit_option',
        help="控制同一SKU最多可由多少間店舖轉出。因RF轉出每店有75%上限，可能需要多間店舖共同出貨。"
    )
    if nst_shop_limit_option == "10 間":
        nst_max_source_shops = 10
    elif nst_shop_limit_option == "20 間":
        nst_max_source_shops = 20
```

### 5b. HD Transfer Option
Add `"NST"` to existing F2/F3 HD transfer radio block:
```python
if mode_code in ("F2", "F3", "NST"):
```

### 5c. Fulfill Small First
Add `"NST"` to checkbox:
```python
if mode_code in ("F", "F2", "F3", "NST"):
```

### 5d. Return dict
Add `'nst_max_source_shops': nst_max_source_shops`.

### 5e. Update mode description panels (核心功能, 操作指引)

---

## 6. App Entry: `app.py`

### 6a. Extract NST option
```python
nst_max_source_shops = sidebar_result.get('nst_max_source_shops')
```

### 6b. Pass to TransferLogic
```python
transfer_logic = TransferLogic(
    ...,
    nst_max_source_shops=nst_max_source_shops,
)
```

### 6c. Update run_key
Add `nst_max_source_shops` to run_key hash.

### 6d. Update docstring
Add `NST(New Shop Target調貨)` to mode list, update count to 二十八模式.

---

## 7. Documentation Sync (per AGENTS.md)

### 7a. `README.md`
- Add NST to mode list
- Add NST to mode comparison table
- Add NST feature highlights
- Update interface flow description

### 7b. `VERSION.md`
- Add v2.25.0 entry describing the new mode

### 7c. `config.py`
- Already handled: VERSION bump

### 7d. `app.py`
- Already handled: docstring update

### 7e. `ui/tutorial.py`
- Add NST mode tutorial content in the 目標優化系列 group (alongside F/F2/F3)
  - Scenario description
  - Risk badge
  - Source flow chart
  - Destination flow chart
  - Match order
  - Scenario table
  - Diff table
  - Extra notes

### 7f. `調貨模式詳解.txt`
- Add NST detailed description section

### 7g. `transfer_logic_ai_brief.md`
- Add NST mode entry with matching priority and constraints

---

## 8. Test Plan

Create `tests/test_nst_mode.py` with test cases:
1. RF shop with stock < 3 → not a source
2. RF shop with stock 10 → transferable = min(7, 8) = 7
3. RF shop with stock 4 → transferable = min(3, 2) = 2
4. ND shop → full transfer (unchanged)
5. Per-SKU shop limit = 10 → max 10 source sites used
6. HD transfer option → blocked by default, allowed with lowest priority when enabled
7. Target store receives correctly
8. Fulfill small first order
9. Post-match gap fill works

---

## Implementation Order

1. `config.py` — add constants + bump VERSION
2. `strategies/nst_mode.py` — create new strategy
3. `models/mode_registry.py` — add ModeDef
4. `business_logic.py` — wire up strategy, mode routing, target protection
5. `ui/sidebar.py` — add UI options
6. `app.py` — extract & pass options, update docstring
7. Documentation files (7 total)
8. `tests/test_nst_mode.py` — tests
