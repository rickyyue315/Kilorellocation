import pandas as pd
from data_processor import DataProcessor
from business_logic import TransferLogic

dp = DataProcessor()
df, marked_stores = dp.preprocess_data(r'AMU_Reallocation_29Jan2026_AI.XLSX')

print('📊 E模式（強制轉出）分析')
print('=' * 50)
print(f'已標記店舖數: {len(marked_stores)}')
print(f'已標記的獨特站點: {len(set(marked_stores))}')
marked_stock = df.iloc[marked_stores]['SaSa Net Stock'].sum()
print(f'總標記庫存: {marked_stock}')

logic = TransferLogic()
recs = logic.generate_transfer_recommendations(df, '強制轉出')

print(f'\n📈 轉貨推薦統計')
print('=' * 50)
print(f'總推薦數: {len(recs)}')
articles = set(r['Article'] for r in recs)
transfer_sites = set(r['Transfer Site'] for r in recs)
receive_sites = set(r['Receive Site'] for r in recs)
print(f'涉及商品數: {len(articles)}')
print(f'涉及轉出店舖數: {len(transfer_sites)}')
print(f'涉及接收店舖數: {len(receive_sites)}')
transfer_qty = sum(r['Transfer Qty'] for r in recs)
print(f'轉移總量: {transfer_qty}')

# Phase 3統計
phase3_recs = [r for r in recs if 'Phase3' in r['Notes'] or 'C模式回退' in r['Notes']]
print(f'\nPhase 3（C模式回退）推薦數: {len(phase3_recs)}')
phase3_qty = sum(r['Transfer Qty'] for r in phase3_recs)
print(f'Phase 3轉移量: {phase3_qty}')

logic.perform_quality_checks(df)
check_status = "✅ 通過" if logic.quality_check_passed else f"❌ 失敗"
print(f'\n質量檢查: {check_status} ({len(logic.quality_errors)} errors)')

if not logic.quality_check_passed:
    for error in logic.quality_errors[:5]:
        print(f'  - {error}')
