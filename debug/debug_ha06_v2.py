import pandas as pd
from data_processor import DataProcessor
from business_logic import TransferLogic

dp = DataProcessor()
df, _ = dp.preprocess_data(r'AMU_Reallocation_29Jan2026_AI.XLSX')
logic = TransferLogic()
recs = logic.generate_transfer_recommendations(df, '強制轉出')

# 檢查HA06在哪些SKU中既是source又是destination
for article in ['110743402007', '110743502002']:
    print(f"\nArticle {article}:")
    article_recs = [r for r in recs if r['Article'] == article]
    
    # 作為source的
    sources_ha06 = [r for r in article_recs if r['Transfer Site'] == 'HA06']
    if sources_ha06:
        print(f"  HA06 as SOURCE: {len(sources_ha06)} times")
        for r in sources_ha06[:2]:
            print(f"    - Transfer to {r['Receive Site']}: qty {r['Transfer Qty']}")
    
    # 作為destination的
    dests_ha06 = [r for r in article_recs if r['Receive Site'] == 'HA06']
    if dests_ha06:
        print(f"  HA06 as DESTINATION: {len(dests_ha06)} times")
        for r in dests_ha06[:2]:
            print(f"    - Receive from {r['Transfer Site']}: qty {r['Transfer Qty']}")
