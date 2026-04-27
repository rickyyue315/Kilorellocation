# Transfer Logic Diagram Brief (for AI image)

## Purpose
Draw one logic image that lets users compare all current transfer modes and understand when each mode triggers, how sources and destinations are chosen, and special constraints.

## Entities and fields
- Article (12-digit string)
- OM (organization unit)
- Site (store)
- RP Type: ND or RF
- SaSa Net Stock, Pending Received, Safety Stock, MOQ
- Last Month Sold Qty, MTD Sold Qty
- Effective Sold Qty = Last Month Sold Qty + MTD Sold Qty
- Total Available = SaSa Net Stock + Pending Received

## Global (all modes) rules
1. ND store can only be SOURCE, never DESTINATION.
2. Highest Effective Sold Qty RF store is protected from being a SOURCE.
3. A site that is a SOURCE for a SKU cannot also be a DESTINATION for that SKU (no dual role).
4. Same site cannot transfer to itself.
5. For B2/B2a/B3/B3a only: if a Type=M (Mix) source store has higher total sales than destination store, the match is blocked.
  - Total sales = Last Month Sold Qty + MTD Sold Qty
6. Matching priority order (core flow):
   - ND source -> Emergency Replenishment
   - ND source -> Potential Replenishment
   - RF Surplus source -> Emergency Replenishment
   - RF Surplus source -> Potential Replenishment
   - RF Enhanced source -> Emergency Replenishment
   - RF Enhanced source -> Potential Replenishment
   - (Mode C only) RF source -> Priority Zero Replenishment
7. **Post-processing (all modes)**: after all matching, single-piece transfer lines (Transfer Qty = 1) are eliminated:
   - Strategy A (Rebalance): take 1 piece from another destination with qty ≥3 in same source group, making the 1-piece line become 2.
   - Strategy B (Merge): if no donor ≥3, merge the 1-piece into the highest-sales destination in the group (measured by Last Month Sold Qty + MTD Sold Qty), then remove the 1-piece record.
   - Exception: if the source store has only 1 transferable piece for that SKU in total, the single-piece line is preserved.

## Destination types (labels used in output)
- Emergency Replenishment: SaSa Net Stock = 0 and Effective Sold Qty > 0
- Potential Replenishment: Total Available < Safety Stock and highest Effective Sold Qty
- Priority Zero Replenishment: Total Available <= 1 (Mode C/C2 only)
- B2/B3 special destinations (Type T / Type M):
  - Type T High Sales, Type M High Sales
  - Type T Safety, Type M Safety
- E Mode Reception: RF stores, cap = Safety Stock * 2 (E1/E1b/E2 modes)
- F Mode Target Reception: Target priority (F mode)

## Source types (labels used in output)
- ND Transfer
- ND Clearance Transfer (Mode D/D2)
- RF Surplus Transfer
- RF Enhanced Transfer
- B2/B3 extra: Local Store Full Transfer (Type L with low sales)
- E Mode Forced Transfer (E1/E1b/E2 modes)
- F Mode ND Transfer / F Mode RF Transfer (F mode)

---

# Mode Overview (22 Modes: A, B, B2, B2a, B3, B3a, C, C1, C2, D, D2, E1, E1b, E2, F, F2, ND1, ND2)

## Mode A: Conservative
- Source rules: RF only, Surplus Transfer
- Transferable qty:
  - Base = Total Available - Safety Stock
  - Cap = max(20% of Total Available, 2)
  - Actual = min(Base, Cap, SaSa Net Stock)
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
- Transferable qty cap: 30% of Total Available, max 3 units, min 1
- Destination rules: Priority Zero + Emergency + Potential
- Track cumulative received to reach targets
- Goal: focus on near-zero stock stores

## Mode C1: Priority Zero Stock (0/1 Only)
- Source rules: same as Mode C (RF Surplus + RF Enhanced), but stricter:
  - Pre-condition: `SaSa Net Stock > 2` (vs C's `total_available > Safety Stock`)
  - Minimum transferable: 2 units (vs C's 1 unit)
  - Sources with transferable qty < 2 are skipped
  - Source priority: sorted by transferable qty descending (largest sources first)
- Destination rules: **only** total_available <= 1 (Priority Zero Replenishment)
  - Does NOT fall back to Emergency or Potential Replenishment
  - Target Qty = max(Safety Stock * 0.5, 3)
  - Needed Qty = Target Qty - Total Available
- Grouping: by Article + OM (same as C)
- Goal: precise zero-stock replenishment only, without triggering general shortage logic

## Mode C2: Cross-OM Priority Zero
- Same source/destination logic as Mode C
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
  - ND: full transfer (unless Target > 0 set for that site)
  - RF: can transfer (protect highest sales store)
- Destination priority:
  1. Sites with Target > current stock: receive up to Target
  2. Sites with Total Available <= 1: zero stock replenishment logic
- Grouping: by Article only (allow cross-OM)
- Extra constraints:
  - HD source cannot transfer to HA/HB/HC destinations
- Goal: Target-driven allocation, zero stock replenishment for non-Target sites

## Mode F2: Target-Only Optimization
- Source rules:
  - ND: full transfer (unless Target > 0 set for that site)
  - RF: can transfer (protect highest sales store)
- Destination priority:
  1. Sites with Target > current stock: receive up to Target
  2. Non-Target RF sites do not receive
- Grouping: by Article only (allow cross-OM)
- Extra constraints:
  - HD source cannot transfer to HA/HB/HC destinations
- Goal: Target-only allocation, concentrate transfer to designated stores

---

# Diagram layout suggestion (single image)

1. Start block: Input Excel -> Data validation -> Compute derived fields
2. Common Rules block (ND only source, protect highest RF, no dual role)
3. Split into modes A, B, B2, B3, C, C1, C2, D, D2, E1, E1b, E2, F (parallel columns)
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
  - B2/B2a/B3/B3a Type=L exception
  - B2a/B3a Type=T no-source restriction
  - C2 cross-OM + HD/Windy
  - D/D2 avoid 1 remainder
  - D2 ND-only source (RF receive-only)
  - E1 same OM only + ALL column force transfer
  - E1b same OM + priority type reception
  - E2 cross-OM + ALL column force transfer
  - F Target priority
  - F2 Target-only reception
