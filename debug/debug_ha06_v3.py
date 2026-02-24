import pandas as pd
from data_processor import DataProcessor

dp = DataProcessor()
df, _ = dp.preprocess_data(r'AMU_Reallocation_29Jan2026_AI.XLSX')

# 檢查110743402007時，HA06是否在receiving_sites中
article = '110743402007'
article_df = df[df['Article'].astype(str).str.zfill(12) == article]

logic_obj = __import__('business_logic', fromlist=['TransferLogic']).TransferLogic()

# 手動執行identify_destinations來查看
destinations = logic_obj.identify_destinations(article_df, '強制轉出')
dest_sites = [d['site'] for d in destinations]
dest_om_not_in_e_mode = [d for d in destinations if d['om'] not in {'Queenie', 'Violet'}]

print(f"Article {article}:")
print(f"  E-mode OMs: Queenie (HA45), Violet (HB86)")
print(f"  All destinations count: {len(destinations)}")
print(f"  Non-E-mode destination OMs: {set(d['om'] for d in dest_om_not_in_e_mode)}")
print(f"  Non-E-mode destination sites: {set(d['site'] for d in dest_om_not_in_e_mode)}")

# 檢查HA06是否在非E模式destinations中
ha06_in_non_e_mode = [d for d in dest_om_not_in_e_mode if d['site'] == 'HA06']
if ha06_in_non_e_mode:
    print(f"  HA06 found in non-E-mode destinations: YES")
    for d in ha06_in_non_e_mode:
        print(f"    - OM: {d['om']}, needed_qty: {d['needed_qty']}")
else:
    print(f"  HA06 found in non-E-mode destinations: NO")
