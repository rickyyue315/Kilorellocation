# C1 Mode Custom Threshold Plan

## Goal
Allow users to configure the C1 mode threshold via a numeric input in the sidebar, instead of the hardcoded `total_available <= 1` limit. Default value is `1` (backward compatible).

## Current Behavior
- C1 mode only processes RF destinations where `total_available <= 1` (i.e., stock of 0 or 1)
- Hardcoded at `business_logic.py:835`: `if total_available > 1: continue`

## Desired Behavior
- User can input a threshold number (default `1`) in the sidebar
- C1 processes RF destinations where `total_available <= user_input`
- e.g., user enters `10` → processes stores with stock ≤ 10

## Files to Modify

### 1. `config.py`
- Add `C1_MODE_DEFAULT_THRESHOLD = 1` (preserves backward compatibility)
- Bump `VERSION` to `"v2.22.0"`

### 2. `models/mode_registry.py`
- C1 ModeDef: add `extra_ui_options=frozenset({'c1_threshold'})` to enable UI rendering

### 3. `ui/sidebar.py`
- After the mode radio but before the C1 description (around line 157), add a `st.number_input` when `mode_code == "C1"`:
  - Label: `"C1 補0門檻（補 total_available ≤ N 的店舖）"`
  - `min_value=0`, `max_value=100`, default=`1`
  - Store as `c1_threshold` variable
- Update the C1 description text (lines 229-234) to reflect the configurable threshold

### 4. `app.py`
- Pass `c1_threshold` from sidebar to `TransferLogic(...)` constructor
- Add `c1_threshold` to the `current_run_key` string (line 166) to trigger re-run on threshold change
- Update module docstring version to match `config.VERSION`

### 5. `business_logic.py`
- `TransferLogic.__init__`: add `c1_threshold: int = 1` parameter, store as `self.c1_threshold`
- `_dests_c1_mode()` (line 835): replace `if total_available > 1:` with `if total_available > self.c1_threshold:`

### 6. Documentation (per AGENTS.md)
- **`README.md`** — Update C1 feature description mentioning configurable threshold
- **`VERSION.md`** — Add v2.22.0 entry describing the change
- **`ui/tutorial.py`** — Update C1 tutorial content
- **`調貨模式詳解.txt`** — Update C1 detailed description
- **`transfer_logic_ai_brief.md`** — Update AI brief if applicable

## Not Affected
- `services/matching_engine.py` — no changes needed (source sorting, matching rounds unchanged)
- `services/notes.py` — no changes needed (C1 notes already correct)
- All test files — existing tests call `TransferLogic()` with no threshold (default `1`), so they remain backward compatible
- Source-side logic (`_sources_general`, `_compute_rf_transferable`) — unchanged

## Edge Cases
- Input of `0`: only processes stores with `total_available <= 0` (essentially no stores, degenerate mode)
- Input of `100`: effectively processes all RF stores regardless of stock level
