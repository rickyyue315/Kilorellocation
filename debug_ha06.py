import pandas as pd
from data_processor import DataProcessor
from business_logic import TransferLogic

dp = DataProcessor()
df, _ = dp.preprocess_data(r'AMU_Reallocation_29Jan2026_AI.XLSX')
logic = TransferLogic()

# 檢查110743402007在HA06的情況
article = '110743402007'
article_df = df[df['Article'].astype(str).str.zfill(12) == article]
ha06_data = article_df[article_df['Site'] == 'HA06']

if not ha06_data.empty:
    row = ha06_data.iloc[0]
    print(f"Article {article} at HA06:")
    print(f"  OM: {row['OM']}")
    print(f"  RP Type: {row['RP Type']}")
    print(f"  ALL: {row.get('*ALL*', 'N/A')}")
    print(f"  SaSa Net Stock: {row['SaSa Net Stock']}")
    print(f"  Safety Stock: {row['Safety Stock']}")
    print(f"  Effective Sold Qty: {row['Effective Sold Qty']}")
    print()

# 檢查該Article的所有sources
sources = logic.identify_sources(article_df, '強制轉出')
print(f"Sources for {article}: {[s['site'] for s in sources]}")

# 檢查該Article的所有destinations
dests = logic.identify_destinations(article_df, '強制轉出')
ha06_dest = [d for d in dests if d['site'] == 'HA06']
if ha06_dest:
    print(f"HA06 as destination: YES - needed_qty={ha06_dest[0]['needed_qty']}")
else:
    print(f"HA06 as destination: NO")

# 檢查HA06是否會被識別為C模式source
print("\nChecking if HA06 will be C-mode source:")
total_available = int(ha06_data.iloc[0]['SaSa Net Stock']) + int(ha06_data.iloc[0]['Pending Received'])
safety_stock = int(ha06_data.iloc[0]['Safety Stock'])
effective_sold = int(ha06_data.iloc[0]['Effective Sold Qty'])

print(f"  Total available: {total_available}")
print(f"  Safety stock: {safety_stock}")
print(f"  Effective sold: {effective_sold}")
print(f"  Is stock above safety? {total_available > safety_stock}")

# Get all OMs for this article to find max sold qty
om_list = article_df[article_df['RP Type'] == 'RF']
om_data = om_list.groupby('OM')['Effective Sold Qty'].max()
ha06_om = ha06_data.iloc[0]['OM']
max_sold_for_om = om_data.get(ha06_om, 0)
print(f"  Max sold for OM {ha06_om}: {max_sold_for_om}")
print(f"  Is not highest sold? {effective_sold < max_sold_for_om}")
