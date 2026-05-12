# KiLo 庫存調貨建議系統 - AI Coding Agent Instructions

## Architecture (4-file pipeline)
- **app.py** (Streamlit UI): upload → preprocess → business logic → Excel download. Mode picker is a `st.radio` in sidebar; mode code (e.g. `"B2"`) maps to Chinese mode string (e.g. `"附加B(特別模式)"`) via `mode_name_map` dict (~line 700). Uses `st.session_state` to persist results across rerenders.
- **data_processor.py** (`DataProcessor`): Excel read → column validation → type conversion → `fill_default_store_data` (fills missing OM/Type from `DEFAULT_STORE_DATA` dict, ~90 stores hardcoded) → missing-value handling → outlier correction → `calculate_effective_sold_qty`. Pipeline entry: `preprocess_data(file_path)`.
- **business_logic.py** (`TransferLogic`, ~2300 lines): `identify_sources` → `identify_destinations` → `match_transfers` (or mode-specific `_match_transfers_*` methods) → `generate_transfer_recommendations`. Each source/destination is a `Dict` with keys like `site`, `om`, `transferable_qty`, `needed_qty`, `priority`, `store_type`.
- **excel_generator.py** (`ExcelGenerator`): two-sheet XLSX via xlsxwriter — "調貨建議" (recommendations) + "統計摘要" (summary dashboard).

## 15 Modes — Where to Edit
Modes: A, B, B2, B2a, B3, B3a, C, C2, D, E1, E1b, E2, F, ND1, ND2. Mode strings are instance attributes on `TransferLogic` (e.g. `self.mode_b_special = "附加B(特別模式)"`).

**To add/modify a mode, touch ALL of these:**
1. `TransferLogic.__init__` — add `self.mode_xxx` string constant
2. `identify_sources` / `identify_destinations` — add mode-specific branches
3. `match_transfers` or create `_match_transfers_xxx_mode` — matching logic
4. `generate_transfer_recommendations` — mode validation list, groupby choice (`Article` only for cross-OM; `Article+OM` otherwise), dispatch to correct match function
5. `app.py` — `st.radio` options list (~line 390), `mode_name_map` dict (~line 700), `mode_descriptions` dict, and field-requirement expanders
6. Update `README.md` mode table and `調貨模式詳解.txt`

## Critical Domain Rules (enforced in code)
- **ND = source-only** in all modes; RF can be source or destination.
- **Highest Effective Sold Qty RF store is protected** — never selected as source (in A/B/C/D modes; in F mode, protection skipped if all RF share same qty or all are 0).
- **No dual role**: a site sourcing a SKU cannot also receive that SKU. Enforced via `source_sites` set filtering in `generate_transfer_recommendations`.
- **D mode remainder rule**: never leave exactly 1 piece — adjust transfer qty to leave 0 or ≥2 (see `_match_by_priority`).
- **E modes**: only rows with non-empty `ALL` column are processed; full stock transfer. E1/E1b = same-OM only; E2 = cross-OM. E1b prioritizes T→M type reception.
- **B2/B2a/B3/B3a Mix sales guard**: if source is Type=M and its total sales (`last_month + mtd`) > destination total sales, the pair is skipped (see `_match_transfers_b_special`).
- **B2a/B3a**: Type=T stores cannot be sources (`_is_b_tourist_no_source_mode`).
- **Cross-OM constraint** (B3/B3a/C2/E2/F): HD sources cannot transfer to HA/HB/HC; Windy sources only to Windy destinations.
- **B2/B2a/B3/B3a receive-site limit**: configurable via `b_special_max_receive_sites_per_source` (1, 2, or None=unlimited), set in app sidebar.
- **Single-piece transfer post-processing** (all modes): after all matching, `_optimize_single_piece_transfers` eliminates any `Transfer Qty = 1` lines. Strategy A (Rebalance): borrow 1 from a donor with qty ≥3. Strategy B (Merge): merge into highest-sales destination. Exception: single source totals of 1 piece are preserved.

## Data Conventions
- `Article`: always 12-digit zero-padded string — `str.zfill(12).str[-12:]` in `read_excel_file`.
- `Effective Sold Qty` = `max(Last Month Sold Qty, MTD Sold Qty)` (not a sum — see `calculate_effective_sold_qty` using `np.where`). But **total sales for Mix guard** = `Last Month Sold Qty + MTD Sold Qty`.
- `Total Available` = `SaSa Net Stock + Pending Received` (computed inline, not a stored column).
- Column normalization: `ALL`, `Target`, `Type` are matched case-insensitively and renamed to canonical form in `read_excel_file`.
- Missing OM/Type auto-filled from `DEFAULT_STORE_DATA` dict keyed by site code (e.g. `'HA02'`).

## Workflows
- **Run**: `run.bat` (Windows) / `./run.sh` (macOS/Linux) / `streamlit run app.py`. Auto-creates venv + installs deps.
- **Dependencies**: `pandas`, `openpyxl`, `streamlit`, `numpy`, `xlsxwriter`, `matplotlib`, `seaborn`, `ftfy`.
- **Tests**: pytest-based in `tests/`. Run relevant subset:
  ```bash
  python -m pytest tests/test_modes_simple.py tests/test_b2_b3_source_receive_site_limit.py tests/test_single_qty_optimization.py -q
  ```
  Key test pattern: build mock DataFrame → run `TransferLogic.generate_transfer_recommendations` → assert no dual-role violations (source ∩ destination per Article).
- **Version tracking**: update `VERSION.md` header + version strings in docstrings of all 4 core files + `app.py` sidebar display.

## Code Conventions
- All UI text, comments, docstrings, and log messages are in **Traditional Chinese** (繁體中文).
- Business logic uses `Dict` (not dataclasses) for source/destination records — always include keys: `site`, `om`, `rp_type`, `priority`, `effective_sold_qty`, `last_month_sold_qty`, `mtd_sold_qty`.
- Mode membership checks use helper methods: `_is_b_special_mode()`, `_is_b3_family_mode()`, `_is_b_tourist_no_source_mode()`.
- Groupby strategy: cross-OM modes (`E2, F, B3, B3a, C2`) group by `Article` only; all others by `(Article, OM)`.

## Documentation Map
- Business rules and mode details: `調貨模式詳解.txt`
- User install/usage guide: `README.md`
- Change log: `VERSION.md`
