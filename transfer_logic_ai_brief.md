# Transfer Logic Diagram Brief (for AI image)

## Purpose
Draw one logic image that lets users compare all current transfer modes and understand when each mode triggers, how sources and destinations are chosen, and special constraints.

## Entities and fields
- Article (12-digit string)
- OM (organization unit)
- Site (store)
- RP Type: ND or RF
- SaSa Net Stock, Pending Received, Safety Stock, MOQ
- Last Month Sold Qty, MTD Sold Qty, Last 2 Month Sold Qty
- Effective Sold Qty = Last Month Sold Qty + MTD Sold Qty
- Total Available = SaSa Net Stock + Pending Received
- Target (optional, for F/F2 modes)
- ALL (optional, for E1/E1b/E2 modes)
- Type (optional, for B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/E1b modes)

## Global (all modes) rules
1. ND store can only be SOURCE, never DESTINATION.
2. Highest Effective Sold Qty RF store is protected from being a SOURCE.
3. A site that is a SOURCE for a SKU cannot also be a DESTINATION for that SKU (no dual role).
4. Same site cannot transfer to itself.
5. For B2/B2a/B3/B3a only: if a Type=M (Mix) source store has higher total sales than destination store, the match is blocked.
  - Total sales = Last Month Sold Qty + MTD Sold Qty
6. Matching priority order (core flow, v2.11.3 optimized):
   - **C mode**: ND source -> Priority Zero Replenishment (highest priority for zero-stock stores)
   - ND source -> Emergency Replenishment
   - ND source -> Potential Replenishment
   - **C1 mode**: RF Surplus source -> Priority Zero Replenishment (sorted by transferable_qty desc)
   - RF Surplus source -> Emergency Replenishment
   - RF Surplus source -> Potential Replenishment
   - **B Special (B2/B2a/B3/B3a)**: RF Surplus > Local Full Transfer > RF Enhanced
   - **C mode**: RF Surplus source -> Priority Zero Replenishment
   - **C1 mode**: RF Enhanced source -> Priority Zero Replenishment
   - RF Enhanced source -> Emergency Replenishment
   - RF Enhanced source -> Potential Replenishment
   - **C mode**: RF Enhanced source -> Priority Zero Replenishment
   - (Mode C/C2) RF source -> Priority Zero Replenishment (legacy fallback)
   - (Mode F/F2) Target priority matching (ND/RF can receive)
   - (Mode 精簡SKU) RF-to-RF matching (min 2 pieces) -> D001 fallback
   - **Key changes v2.11.3**: 
     - C mode: Priority Zero Replenishment now served at EACH source priority level (before Emergency/Potential)
     - B Special: RF Surplus matched BEFORE Local Full Transfer (was reversed)
     - C1 mode: explicit Priority Zero rounds for RF Surplus then RF Enhanced
7. **Post-processing (all modes)**: after all matching, single-piece transfer lines (Transfer Qty = 1) are eliminated:
   - Strategy A (Rebalance): take 1 piece from another destination with qty ≥3 in same source group, making the 1-piece line become 2.
   - Strategy B (Merge): if no donor ≥3, merge the 1-piece into the highest-sales destination in the group (measured by Last Month Sold Qty + MTD Sold Qty), then remove the 1-piece record.
   - Exception: if the source store has only 1 transferable piece for that SKU in total, the single-piece line is preserved.

## Destination types (labels used in output)
- Emergency Replenishment: SaSa Net Stock = 0 and Effective Sold Qty > 0
- Potential Replenishment: Total Available < Safety Stock and highest Effective Sold Qty
- Priority Zero Replenishment: Total Available <= threshold (Mode C1 configurable, default 1)
- B2/B3 special destinations (Type T / Type M):
  - Type T High Sales, Type M High Sales
  - Type T Safety, Type M Safety
- E Mode Reception: RF stores, cap = Safety Stock * 2 (E1/E1b/E2 modes)
- F Mode Target Reception: Target priority (F/F2/F3 modes, ND/RF can receive)
- NST Mode Target Reception: Target priority (NST mode, ND/RF can receive)
- ND Emergency Replenishment (ND1/ND2 mode)
- ND Potential Replenishment (ND1/ND2 mode)
- ND3 Zero-Fill Reception (ND3 mode)
- 精簡SKU接收: RF stores, cap = Max(Safety×2, Last2Month×2)
- 退回D001: leftover surplus return

## Source types (labels used in output)
- ND Transfer
- ND Clearance Transfer (Mode D/D2)
- RF Surplus Transfer
- RF Enhanced Transfer
- B2/B3 extra: Local Store Full Transfer (Type L with low sales)
- E Mode Forced Transfer (E1/E1b/E2 modes)
- F Mode ND Transfer / F Mode RF Transfer / F3 Mode RF Transfer(Retain 2) (F/F3 mode)
- NST Mode ND Transfer / NST Mode RF Transfer (NST mode)
- ND Smart Transfer (ND1/ND2 mode)
- ND3 Smart Transfer (Retain 3) (ND3 mode)
- 精簡SKU ND轉出 / 精簡SKU RF轉出 (Simplified SKU modes)
- 精簡SKU(退D001) 退回D001 (Simplified SKU Return to D001 mode)

---

# Mode Overview (29 Modes: A, B, B2, B2a, B2L, B2La, B3, B3a, B3L, B3La, C, C1, C2, D, D2, E1, E1b, E2, F, F2, F3, NST, ND1, ND2, ND3, ND4, 精簡SKU(限同OM), 精簡SKU(跨OM), 精簡SKU(退D001))

## Mode A: Conservative
- Source rules: RF only, Surplus Transfer
- Transferable qty:
  - Base = Total Available - Safety Stock
  - Cap = max(20% of Total Available, 2)
  - Actual = min(Base, Cap, SaSa Net Stock)
- **Single-piece bump (v2.11.1)**: if Actual=1 and remaining stock after 1-piece transfer >= 3, bump to 2 with safety stock relaxed by -1 (mathematically equivalent to original safety check)
- Destination rules: Emergency Replenishment, Potential Replenishment
- Goal: stable operations, strict safety stock protection

## Mode B: Enhanced
- Source rules: RF Surplus + RF Enhanced
- Transferable qty:
  - Base = Total Available - Safety Stock
  - Cap = max(50% of Total Available, 2)
  - Actual = min(Base, Cap, SaSa Net Stock)
- Destination rules: Emergency Replenishment, Potential Replenishment
- Goal: aggressive transfers, allow below safety stock

## Mode B2: Enhanced Plus
- Source rules:
  1. ND: full transfer
  2. Type=L and max(Last Month Sold Qty, MTD Sold Qty) <= 2: full transfer (even RF)
  3. Other RF: follow Mode B cap (50%)
  4. Type=M source blocked if source total sales > destination total sales
     - Total sales = Last Month Sold Qty + MTD Sold Qty
- Destination rules:
  - RF only; cap = Safety Stock * 2; track cumulative received
  - Priority order:
    1) Type T by highest sales
    2) Type M by highest sales
    3) Type T by highest Safety Stock
    4) Type M by highest Safety Stock
- Destination labels: Type T High Sales, Type M High Sales, Type T Safety, Type M Safety
- Goal: stronger rebalancing with Type=L exception

## Mode B3: Enhanced Plus Cross-OM
- Same source/destination logic as Mode B2
- Grouping differs: allow cross-OM matching
- Extra constraints:
  - HD source cannot transfer to HA/HB/HC destinations
  - Windy source can only transfer to Windy destinations
- Also keeps B2 Mix guard rule (Type=M high-sales source cannot transfer to lower-sales destination)
- Goal: cross-OM enhanced transfers with Type=L exception

## Mode C: Priority Zero Stock
- Source rules: RF Surplus + RF Enhanced
- Special destination trigger: Total Available <= 1
  - Target Qty = max(Safety Stock * 0.5, 3)
  - Needed Qty = Target Qty - Total Available
- Transferable qty cap: 30% of Total Available
  - Absolute cap: configurable via sidebar slider (3~10, default 3), shared with C1/C2
  - Upper limit = max(1, min(30% × TA, configurable_ceiling))
- Destination rules: Priority Zero + Emergency + Potential
- Track cumulative received to reach targets
- Goal: focus on near-zero stock stores

## Mode C1: Priority Zero Stock (Configurable Threshold + Ceiling)
- Source rules: same as Mode C (RF Surplus + RF Enhanced), but stricter:
  - Pre-condition: `SaSa Net Stock > 2` (vs C's `total_available > Safety Stock`)
  - Minimum transferable: 2 units (vs C's 1 unit)
  - Sources with transferable qty < 2 are skipped
  - Source priority: sorted by transferable qty descending (largest sources first)
- Transferable qty cap per source:
  - Ratio cap: 30% of Total Available
  - Absolute cap: configurable via sidebar slider (3~10, default 3)
  - Upper limit = max(2, min(30% × TA, configurable_ceiling))
- Destination rules: **only** total_available <= threshold (configurable via sidebar, default=1)
  - Threshold N is set via UI (st.number_input, range 0-100, default 1)
  - Does NOT fall back to Emergency or Potential Replenishment
  - Target Qty = max(Safety Stock * 0.5, 3)
  - Needed Qty = Target Qty - Total Available
- Grouping: by Article + OM (same as C)
- Goal: precise zero/low-stock replenishment only, without triggering general shortage logic. Higher ceiling = fewer source stores required per SKU.

## Mode C2: Cross-OM Priority Zero
- Same source/destination logic as Mode C (including configurable ceiling via sidebar slider)
- Grouping differs: group by Article only (allow cross OM matching)
- Extra constraints:
  - HD source cannot transfer to HA/HB/HC destinations
  - Windy source can only transfer to Windy destinations
- Goal: cross-OM zero stock replenishment

## Mode D: Clearance
- Source rules:
  - ND with Last Month Sold Qty = 0 and MTD Sold Qty = 0: full transfer
  - Source label: ND Clearance Transfer
  - RF sources follow Mode A (RF Surplus, strict safety stock)
- Special rule: avoid 1-piece remainder after transfer
  - If remaining stock would be 1, adjust transfer +/-1 to leave 0 or >=2
- Destination rules: same as Mode A
- Goal: clear ND dead stock without leaving 1 piece

## Mode D2: Clearance (ND Only)
- Source rules:
  - **Only ND** with Last Month Sold Qty = 0 and MTD Sold Qty = 0: full transfer
  - Source label: ND Clearance Transfer
  - **RF stores do NOT transfer out at all** (RF is receive-only)
  - ND with sales records (Last Month > 0 or MTD > 0): also skipped
- Special rule: same avoid 1-piece remainder as Mode D
- Destination rules: same as Mode D (Emergency + Potential Replenishment)
- **Optional UI toggle (3 choices)**: receiving store strategy
  - `"unlimited"` (default): unlimited receiving stores, normal target_qty; uses `_dests_d_mode()` + `match_general_mode()`
  - `"2site_original"`: max 2 receiving stores per source, normal target_qty; uses `_dests_d_mode()` + `match_d2_mode()`
  - `"2site_optimized"`: max 2 receiving stores per source, target_qty × 2 (200%) to compensate; uses `_dests_d2_mode()` + `match_d2_mode()`
- Grouping: same OM only (Article + OM)
- Goal: clear ND dead stock, RF stores only receive, never transfer out

## Mode E1: Force Transfer (Same OM Only)
- Only items marked ALL in input file are processed (case-insensitive)
- Force transfer all available stock for marked items
- **Same OM only**: transfer and receive sites must be in same OM
- ND stores remain source-only
- Reception cap: Safety Stock * 2 (RF stores only)
- Special OM/HD rules: HD stores cannot transfer to HA/HB/HC
- Goal: mandatory transfers for flagged items (same OM only)

## Mode E1b: Force Transfer (Same OM + Priority Type)
- Same transfer logic as E1: only items marked ALL, same OM only
- Reception priority follows B2 mode:
  - Type T (tourist area) by highest sales
  - Type M (mixed type) by highest sales
  - Type T by highest Safety Stock
  - Type M by highest Safety Stock
- Reception cap: Safety Stock * 2 (RF stores only)
- Special OM/HD rules: HD stores cannot transfer to HA/HB/HC
- Goal: mandatory transfers for flagged items (same OM only, priority type reception)

## Mode E2: Force Transfer (Cross OM)
- Only items marked ALL in input file are processed (case-insensitive)
- Force transfer all available stock for marked items
- **Cross OM allowed**: priority same OM, but can cross OM
- ND stores remain source-only
- Reception cap: Safety Stock * 2 (RF stores only)
- Special OM/HD rules: HD stores cannot transfer to HA/HB/HC
- Phase 3 fallback: if receiving OMs have no E-mode transfer sources, fall back to C-mode logic
- Goal: mandatory transfers for flagged items (cross-OM capable)

## Mode F: Target Optimization
- Source rules:
  - ND: full transfer (unless Target > 0 set for that site — then site becomes receiver)
  - RF: can transfer (protect highest sales store)
- Destination priority:
  1. Sites with Target > 0: receive exactly Target Qty (cross-OM allowed; regardless of ND/RF type, regardless of current stock or pending received)
  2. Sites with Total Available <= 1: zero stock replenishment logic (RF only; **same-OM only** — the C-mode fallback does not cross OM boundaries)
- Grouping: by Article only (allow cross-OM)
- Extra constraints:
  - HD source cannot transfer to HA/HB/HC destinations
  - Windy source can only transfer to Windy destinations
- Key change: Target Qty is used directly as needed_qty (no subtraction of current stock or pending); ND stores with Target can receive
- **New v2.23.0**: Optional "fulfill small targets first" checkbox — when checked, Priority-1 destinations are sorted by needed_qty ASC (smallest target first); post-match gap filling allocates leftover source stock to still-unfilled destinations; Excel output includes a "Target達成分析" sheet
- Goal: Target-driven allocation, zero stock replenishment for non-Target RF sites

## Mode F2: Target-Only Optimization
- Source rules:
  - ND: full transfer (unless Target > 0 set for that site — then site becomes receiver)
  - RF: can transfer (protect highest sales store)
- Destination priority:
  1. Sites with Target > 0: receive exactly Target Qty (cross-OM allowed; regardless of ND/RF type, regardless of current stock or pending received)
  2. Non-Target sites do not receive
- Grouping: by Article only (allow cross-OM)
- Extra constraints:
  - HD source cannot transfer to HA/HB/HC destinations (default behavior)
  - **HD transfer option (configurable)**: when `f2_allow_hd_transfer=True`, HD sources CAN transfer to HA/HB/HC destinations, but are sorted at the lowest priority tier (hd_penalty=10 added to sort key), only used when all other sources are insufficient
  - Windy source can only transfer to Windy destinations
  - **Windy source priority**: when a Windy store has Target (is a destination group), Windy sources without Target are prioritized over non-Windy sources (windy_penalty=5 added to sort key); non-Windy sources are only used when Windy sources are insufficient
- Key change: Target Qty is used directly as needed_qty (no subtraction of current stock or pending); ND stores with Target can receive
- **New v2.23.0**: Optional "fulfill small targets first" checkbox — when checked, Priority-1 destinations are sorted by needed_qty ASC; post-match gap filling allocates leftover source stock to still-unfilled destinations; Excel output includes a "Target達成分析" sheet
- Goal: Target-only allocation, concentrate transfer to designated stores

## Mode F3: Targeted Zero-Fill (目標性補0)
- Source rules:
  - ND: full transfer (unless Target > 0 set for that site — then site becomes receiver)
  - RF: can transfer (protect highest sales store)
  - **RF retain 2 units**: transferable_qty = max(net_stock - 2, 0); net_stock > 2 required
  - **RF sort**: highest stock first → lowest sales second (different from F2)
- Destination priority:
  1. Sites with Target > 0: receive exactly Target Qty (cross-OM allowed; regardless of ND/RF type, regardless of current stock or pending received)
  2. Non-Target sites do not receive
- Grouping: by Article only (allow cross-OM)
- Extra constraints:
  - HD source cannot transfer to HA/HB/HC destinations (default behavior)
  - **HD transfer option (configurable)**: when enabled, HD sources CAN transfer to HA/HB/HC at lowest priority (hd_penalty=10)
  - Windy source can only transfer to Windy destinations
  - **Windy source priority**: when a Windy store has Target, Windy sources prioritized over non-Windy (windy_penalty=5)
  - **RF cross-OM no penalty**: same OM and cross-OM RF sources have equal tier priority (only ND=tier0, RF=tier1)
- Key differences from F2:
  - RF transferable_qty = max(net_stock - 2, 0) instead of net_stock
  - RF sort by highest stock first (not lowest sales first)
  - RF cross-OM no tier downgrade (both same-OM and cross-OM RF are tier 1)
- **New v2.23.0**: Optional "fulfill small targets first" checkbox — when checked, Priority-1 destinations are sorted by needed_qty ASC; post-match gap filling allocates leftover source stock to still-unfilled destinations; Excel output includes a "Target達成分析" sheet
- Goal: Target-only allocation with RF minimum stock preservation and cross-OM fairness

## Mode NST: New Shop Target Transfer (New Shop Target調貨)
- Inherits all F2 rules (Target-only reception, HD transfer option, Windy target priority)
- Source rules:
  - ND: full transfer (unless Target > 0 set for that site)
  - RF: strict new constraints:
    - **Retain ≥2**: transferable_qty = min(int(net_stock * 0.75), net_stock - 2)
    - **75% cap**: max transfer is 75% of net_stock
    - **Min stock 3**: skip if net_stock < 3 (not qualified to be a source)
    - Protect highest sales store (same as F2)
    - Sort by lowest effective_sold_qty first (same as F2)
- Destination priority:
  1. Sites with Target > 0: receive exactly Target Qty (cross-OM allowed; regardless of ND/RF type, regardless of current stock or pending received)
  2. Non-Target sites do not receive
- **New UI option**: Per-SKU source shop limit (10/20/unlimited)
  - Limits the total number of distinct source stores that can transfer out for a given Article
  - Enforced during matching: once N unique source sites are used, new sources are skipped
  - Already-admitted sources can continue transferring to new destinations
- Grouping: by Article only (allow cross-OM)
- Extra constraints:
  - HD source cannot transfer to HA/HB/HC destinations (default behavior)
  - **HD transfer option (configurable)**: when enabled, HD sources CAN transfer to HA/HB/HC at lowest priority (hd_penalty=10)
  - Windy source can only transfer to Windy destinations
  - Windy target priority: Windy sources without Target are prioritized over non-Windy sources (windy_penalty=5)
- Optional "fulfill small targets first" checkbox — when checked, Priority-1 destinations sorted by needed_qty ASC
- Post-match gap filling allocates leftover source stock to still-unfilled destinations
- **Key difference from F2/F3**: Target fulfillment not guaranteed at 100% due to strict RF constraints; this is accepted behavior
- Source labels: NST模式ND轉出, NST模式RF轉出
- Dest labels: NST模式目標接收
- Goal: Target-only allocation with tightly controlled RF transfer limits, multi-store per SKU support

## Mode ND1: ND Same-OM Transfer
- Breaks global "ND cannot receive" rule: ND stores can transfer to each other
- Same OM only (grouped by Article + OM)
- Source: ND stores sorted by 2-month sales ascending (0 sales first); highest-sales ND protected
- Destination priority:
  1. RF Emergency: zero stock + has sales record
  2. ND Potential: sorted by 2-month sales descending; cap = 2 × (Last Month + MTD); 0-sales ND cannot receive
- Can configure max receive sites per source: 优先1间 / 最多2间 / 不限制
- Goal: ND intelligent rebalancing within same OM

## Mode ND2: ND Cross-OM Transfer
- Inherits all ND1 logic, but allows cross-OM matching
- Windy source can only transfer to Windy stores
- HD source cannot transfer to HA/HB/HC
- Goal: ND intelligent cross-OM rebalancing

## Mode ND3: ND Same-OM Zero-Fill (補0)
- Source rules:
  - ND stores with SaSa Net Stock > 3 (retain 3)
  - Transferable = SaSa Net Stock - 3
  - Highest-sales ND store protected
  - Sort by 2-month sales ascending (0 sales first)
- Destination rules:
  - ONLY ND stores with SaSa Net Stock == 0
  - Target Qty = max(Safety Stock * 0.5, 3) (like C1)
  - Sort by 2-month sales descending
- Same OM only (Article + OM grouping)
- Uses nd_mode strategy (same pairing logic as ND1)
- Can configure max receive sites per source
- Goal: precise zero-stock ND store replenishment with stock preservation

## Mode ND4: ND Same-OM Zero-Fill with Sales Record Filter (補0及有銷售記錄)
- Source rules: same as ND3 (retain 3, highest-sales protected, sort by 2-month sales ascending)
- Destination rules:
  - ND stores with SaSa Net Stock == 0
  - ADDITIONAL: Last Month Sold Qty + MTD Sold Qty > 0 (sales record required)
  - Target Qty = max(Safety Stock * 0.5, 3)
  - Sort by 2-month sales descending
- Same OM only (Article + OM grouping)
- Uses nd_mode strategy (same pairing logic as ND1)
- Can configure max receive sites per source
- Goal: precise zero-stock ND store replenishment restricted to stores with sales history

## Mode 精簡SKU(限同OM): Simplified SKU - Same OM
- Source rules:
  1. ND: full transfer (all SaSa Net Stock)
  2. RF: transfer surplus beyond Cap
     - Cap = Max(Safety Stock × 2, Last 2 Month Sold Qty × 2)
     - Transferable = min(Total Available - Cap, SaSa Net Stock)
     - Protect highest sales store
- Destination rules:
  - RF stores only
  - Receive Cap = Max(Safety Stock × 2, Last 2 Month Sold Qty × 2)
  - Minimum 2 pieces per transfer (reference C1 mode)
- Leftover: all unmatched surplus returns to D001 (no quantity limit)
- Grouping: by Article + OM (same OM only)
- Source labels: 精簡SKU ND轉出, 精簡SKU RF轉出
- Dest labels: 精簡SKU接收, 退回D001
- Goal: SKU rationalization within same OM

## Mode 精簡SKU(跨OM): Simplified SKU - Cross OM
- Same source/destination logic as 精簡SKU(限同OM)
- Grouping differs: allow cross-OM matching
- Extra constraints:
  - Windy source can only transfer to Windy destinations
  - HD source cannot transfer to HA/HB/HC destinations
- Goal: SKU rationalization across OMs

---

# Diagram layout suggestion (single image)

1. Start block: Input Excel -> Data validation -> Compute derived fields
2. Common Rules block (ND only source, protect highest RF, no dual role)
3. Split into modes A, B, B2, B2a, B2L, B2La, B3, B3a, B3L, B3La, C, C1, C2, D, D2, E1, E1b, E2, F, F2, F3, NST, ND1, ND2, ND3, 精簡SKU(限同OM), 精簡SKU(跨OM), 精簡SKU(退D001) (parallel columns)
4. For each mode, show:
   - Source criteria
   - Transfer caps
   - Destination criteria
   - Special constraints (if any)
5. Merge to: Matching Priority Order -> Output Recommendations

# Visual keywords to include in image
- ND source-only
- RF highest sales protected
- No dual role source/destination
- Priority matching order list
- Post-processing: eliminate single-piece (qty=1) transfer lines across all modes
- Special rules: 
  - B2/B2a/B2L/B2La/B3/B3a/B3L/B3La Type=L exception (full transfer or retain 2)
  - B2a/B2La/B3a/B3La Type=T no-source restriction
  - B2/B2a/B2L/B2La/B3/B3a/B3L/B3La Mix high-sales guard
  - C2 cross-OM + HD/Windy
  - D/D2 avoid 1 remainder
  - D2 ND-only source (RF receive-only)
  - E1 same OM only + ALL column force transfer
  - E1b same OM + priority type reception
  - E2 cross-OM + ALL column force transfer
  - F Target priority (ND/RF can receive, Target Qty = needed_qty)
  - F2 Target-only reception (ND/RF can receive, Target Qty = needed_qty)
   - ND1/ND2 ND mutual transfer (breaks ND-no-receive rule)
    - ND3 ND same-OM zero-fill (retain 3, only 0-stock ND dest, like C1)
    - ND4 ND same-OM zero-fill with sales filter (like ND3 but only receive stores with sales history)
   - 精簡SKU(限同OM) surplus beyond Cap + D001 fallback
   - 精簡SKU(跨OM) cross-OM + HD/Windy + D001 fallback
   - 精簡SKU(退D001) all surplus directly returns to D001, no RF receive pairing

## Mode 精簡SKU(退D001): Simplified SKU - Return All to D001
- source_method: `_sources_simplified_sku` (reuse existing)
- strategy: `simplified_sku_return_d001`
- Source rules:
  1. ND: full transfer (all SaSa Net Stock)
  2. RF: transfer surplus beyond Cap
     - Cap = Max(Safety Stock × 2, Last 2 Month Sold Qty × 2)
     - Transferable = min(Total Available - Cap, SaSa Net Stock)
     - Protect highest sales store
- **No RF receive pairing**: all transferred quantities directly return to D001
- **No minimum quantity limit for ND stores (even 1 piece can return to D001); RF stores: minimum 2 pieces (1 piece skipped for efficiency)**
- supply_source 1/4 excluded from return
- Source labels: 精簡SKU ND轉出, 精簡SKU RF轉出
- Dest labels: 退回D001
- Report includes additional "D001 Receive Qty" column (only this mode)
- Goal: SKU rationalization with all surplus returned to warehouse D001
