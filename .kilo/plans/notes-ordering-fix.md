# Notes Ordering Fix Plan

## Goal
Align the `Notes` column in `Transfer Recommendations` with the final displayed row order so the cumulative received values read in sequence and end at the true total, instead of reflecting the pre-sort generation order.

## Problem
- `services/post_processing.py` computes `Notes` while recommendations are still in generation order.
- `business_logic.py` then sorts `all_recommendations` by `Priority` and `Transfer Qty`.
- The Excel sheet is built from the sorted list, so the visible `Notes` values can appear out of sequence, e.g. `收累39` -> `收累110` -> `收累75`, even though the true final cumulative received total is `110`.

## Root Cause
The cumulative `receive_before` state is captured before the final sort, but the final sheet order is based on a different sort key. `Notes` therefore do not match the final row order.

## Proposed Change
1. Recalculate `Notes` after the final recommendation sort in `business_logic.py`.
2. Keep the existing note formatting logic in `services/notes.py` unchanged.
3. Add a regression test that proves the final sorted recommendations produce monotonically increasing cumulative received values within the displayed order.

## Files to Modify
### 1. `business_logic.py`
- After `all_recommendations.sort(...)`, call `_refresh_recommendation_fields(all_recommendations, mode)` again so `Notes` and `Cumulative Received Qty` reflect the final display order.
- Preserve existing single-piece optimization and priority assignment flow.
- Ensure the second refresh does not alter quantities, only recomputes dependent fields.

### 2. `tests/`
- Add a regression test covering a multi-row same-article/same-receive-site scenario where the pre-sort order differs from the final priority/quantity sort.
- Assert that the final `Notes` sequence matches the sorted rows and that the final row's cumulative received value equals the total received quantity.
- If useful, add a direct unit test around the post-processing refresh path to verify `Cumulative Received Qty` is recomputed after sorting.

## Validation
- Run the targeted tests for recommendation generation and Excel export.
- Verify the exported `Transfer Recommendations` sheet shows `Notes` cumulative values in the same order as the displayed rows.
- Confirm the final row cumulative value equals the actual total received quantity for that article/site group.

## Acceptance Criteria
- The displayed `Notes` values no longer jump backward after sorting.
- The final row for a grouped destination shows the true total cumulative received quantity.
- Existing note formatting and transfer logic remain unchanged.
- Regression tests pass.
