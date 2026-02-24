import pandas as pd
from data_processor import DataProcessor
from business_logic import TransferLogic

dp = DataProcessor()
df, _ = dp.preprocess_data(r'AMU_Reallocation_29Jan2026_AI.XLSX')
logic = TransferLogic()
recs = logic.generate_transfer_recommendations(df, '強制轉出')

# Check for HD violations
hd_violations = [r for r in recs 
                 if r['Transfer Site'].upper().startswith('HD') 
                 and r['Receive Site'].upper().startswith(('HA', 'HB', 'HC'))]

print(f'Total recommendations: {len(recs)}')
print(f'HD to HA/HB/HC violations: {len(hd_violations)}')

if hd_violations:
    print('\nFirst 5 violations:')
    for r in hd_violations[:5]:
        print(f"  {r['Article']}: {r['Transfer Site']} to {r['Receive Site']} ({r['Transfer Qty']} qty)")

# Quality check
logic.perform_quality_checks(df)
status = "PASSED" if logic.quality_check_passed else "FAILED"
print(f'\nQuality Check: {status} ({len(logic.quality_errors)} errors)')
if logic.quality_errors:
    for err in logic.quality_errors[:3]:
        print(f'  - {err}')
