"""
Detailed E Mode Transfer Report - Show each marked store's transfer status
"""
import pandas as pd
from data_processor import DataProcessor
from business_logic import TransferLogic

# Read and process data
file_path = r'C:\Users\kf_yue\Dropbox\SASA\AI\Sep2025_App\KiLo Reallocation\AMU_Reallocation_29Jan2026_AI.XLSX'
processor = DataProcessor()
df, stats = processor.preprocess_data(file_path)

# Find marked records
marked_df = df[(df['ALL'].notna()) & (df['ALL'].astype(str).str.strip() != '')]

# Generate recommendations
logic = TransferLogic()
recommendations = logic.generate_transfer_recommendations(df, mode="強制轉出")

# Convert to DataFrame
rec_df = pd.DataFrame(recommendations)

print("=" * 100)
print("DETAILED TRANSFER STATUS FOR EACH MARKED STORE")
print("=" * 100)

# Group by source site
transfers_by_source = rec_df.groupby(['Transfer Site', 'Transfer OM', 'Article'])['Transfer Qty'].sum().reset_index()
transfers_by_source.columns = ['Site', 'OM', 'Article', 'Transferred']

# Create report
report_rows = []

for _, marked_row in marked_df.iterrows():
    site = marked_row['Site']
    om = marked_row['OM']
    article = marked_row['Article']
    rp_type = marked_row['RP Type']
    original_stock = marked_row['SaSa Net Stock']
    
    # Find transfers from this source
    source_transfers = transfers_by_source[
        (transfers_by_source['Site'] == site) & 
        (transfers_by_source['OM'] == om) &
        (transfers_by_source['Article'] == article)
    ]
    
    transferred = source_transfers['Transferred'].sum() if len(source_transfers) > 0 else 0
    remaining = original_stock - transferred
    
    status = "OK - FULLY TRANSFERRED" if remaining == 0 else f"ISSUE - {remaining} UNITS REMAINING"
    
    report_rows.append({
        'Article': article,
        'Site': site,
        'OM': om,
        'RP Type': rp_type,
        'Original Stock': original_stock,
        'Transferred': transferred,
        'Remaining': remaining,
        'Status': status
    })

report_df = pd.DataFrame(report_rows)

# Sort by remaining (descending) to show problems first
report_df = report_df.sort_values(['Remaining', 'Article', 'Site'], ascending=[False, True, True])

print(report_df.to_string(index=False))

# Summary
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
print(f"Total marked stores: {len(report_df)}")
print(f"Fully transferred: {len(report_df[report_df['Remaining'] == 0])}")
print(f"Partially transferred: {len(report_df[report_df['Remaining'] > 0])}")
print(f"\nTotal original stock: {report_df['Original Stock'].sum()}")
print(f"Total transferred: {report_df['Transferred'].sum()}")
print(f"Total remaining: {report_df['Remaining'].sum()}")

if report_df['Remaining'].sum() > 0:
    print("\n" + "=" * 100)
    print("STORES WITH REMAINING STOCK")
    print("=" * 100)
    remaining_df = report_df[report_df['Remaining'] > 0]
    print(remaining_df[['Article', 'Site', 'OM', 'RP Type', 'Original Stock', 'Transferred', 'Remaining']].to_string(index=False))
