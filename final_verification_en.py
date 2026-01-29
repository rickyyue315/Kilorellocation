import pandas as pd
from data_processor import DataProcessor
from business_logic import TransferLogic

dp = DataProcessor()
df, stats = dp.preprocess_data(r'AMU_Reallocation_29Jan2026_AI.XLSX')

# Count marked stores from ALL column
marked_df = df[df['ALL'].notna() & (df['ALL'] != '')]
marked_count = len(marked_df)
unique_sites = len(marked_df['Site'].unique())

print('E mode (Forced Transfer) Analysis')
print('=' * 50)
print(f'Marked stores count: {marked_count}')
print(f'Unique marked sites: {unique_sites}')

logic = TransferLogic()
recs = logic.generate_transfer_recommendations(df, '強制轉出')

print(f'\nTransfer Recommendation Stats')
print('=' * 50)
print(f'Total recommendations: {len(recs)}')
articles = set(r['Article'] for r in recs)
transfer_sites = set(r['Transfer Site'] for r in recs)
receive_sites = set(r['Receive Site'] for r in recs)
print(f'Articles involved: {len(articles)}')
print(f'Transfer sites: {len(transfer_sites)}')
print(f'Receive sites: {len(receive_sites)}')
transfer_qty = sum(r['Transfer Qty'] for r in recs)
print(f'Total transfer qty: {transfer_qty}')

# Phase 3 Stats
phase3_recs = [r for r in recs if 'C模式回退' in r['Notes']]
print(f'\nPhase 3 (C-mode Fallback) Stats')
print('=' * 50)
print(f'Phase 3 recommendations: {len(phase3_recs)}')
phase3_qty = sum(r['Transfer Qty'] for r in phase3_recs)
print(f'Phase 3 transfer qty: {phase3_qty}')

logic.perform_quality_checks(df)
check_status = "PASSED" if logic.quality_check_passed else "FAILED"
print(f'\nQuality Check: {check_status} ({len(logic.quality_errors)} errors)')

if not logic.quality_check_passed:
    for error in logic.quality_errors[:5]:
        print(f'  - {error}')
