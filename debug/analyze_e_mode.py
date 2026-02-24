"""
E Mode Analysis - Check which marked stores were NOT fully transferred
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

print("=" * 80)
print("E MODE TRANSFER ANALYSIS")
print("=" * 80)
print(f"\nTotal marked stores: {len(marked_df)}")
print(f"Total marked stock: {marked_df['SaSa Net Stock'].sum()}")
print(f"Total recommendations: {len(recommendations)}\n")

# Convert recommendations to DataFrame for easier analysis
rec_df = pd.DataFrame(recommendations)

# Calculate total transferred
total_transferred = rec_df['Transfer Qty'].sum()
print(f"Total transferred: {total_transferred}")
print(f"Remaining: {marked_df['SaSa Net Stock'].sum() - total_transferred}\n")

# Analyze by Article
print("=" * 80)
print("ANALYSIS BY ARTICLE")
print("=" * 80)

articles_with_issues = []

for article in sorted(marked_df['Article'].unique()):
    article_marked = marked_df[marked_df['Article'] == article]
    article_recs = rec_df[rec_df['Article'] == article]
    
    marked_stock = article_marked['SaSa Net Stock'].sum()
    transferred = article_recs['Transfer Qty'].sum() if len(article_recs) > 0 else 0
    remaining = marked_stock - transferred
    
    # Count ND vs RF
    nd_count = len(article_marked[article_marked['RP Type'] == 'ND'])
    rf_count = len(article_marked[article_marked['RP Type'] == 'RF'])
    nd_stock = article_marked[article_marked['RP Type'] == 'ND']['SaSa Net Stock'].sum()
    rf_stock = article_marked[article_marked['RP Type'] == 'RF']['SaSa Net Stock'].sum()
    
    # Calculate RF receiving capacity
    article_data = df[df['Article'] == article]
    rf_destinations = article_data[article_data['RP Type'] == 'RF']
    
    total_capacity = 0
    for _, rf_row in rf_destinations.iterrows():
        current = rf_row['SaSa Net Stock'] + rf_row['Pending Received']
        max_cap = rf_row['Safety Stock'] * 2
        can_receive = max(0, max_cap - current)
        total_capacity += can_receive
    
    if remaining > 0:
        articles_with_issues.append({
            'Article': article,
            'Marked Stock': marked_stock,
            'ND Stock': nd_stock,
            'RF Stock': rf_stock,
            'ND Stores': nd_count,
            'RF Stores': rf_count,
            'Transferred': transferred,
            'Remaining': remaining,
            'RF Capacity': total_capacity,
            'Capacity Shortage': max(0, marked_stock - total_capacity)
        })
        
        print(f"\nArticle: {article}")
        print(f"  Marked: {nd_count} ND ({nd_stock} units) + {rf_count} RF ({rf_stock} units) = {marked_stock} units")
        print(f"  Transferred: {transferred} units")
        print(f"  REMAINING: {remaining} units ***")
        print(f"  RF Receiving Capacity: {total_capacity} units")
        if total_capacity < marked_stock:
            print(f"  ISSUE: Capacity shortage of {marked_stock - total_capacity} units!")

if articles_with_issues:
    print("\n" + "=" * 80)
    print("SUMMARY OF ISSUES")
    print("=" * 80)
    issues_df = pd.DataFrame(articles_with_issues)
    print(issues_df.to_string(index=False))
    
    print(f"\n\nTotal articles with issues: {len(articles_with_issues)}")
    print(f"Total remaining untransferred: {issues_df['Remaining'].sum()}")
    print(f"Total capacity shortage: {issues_df['Capacity Shortage'].sum()}")
else:
    print("\n" + "=" * 80)
    print("NO ISSUES FOUND - All marked stock successfully transferred!")
    print("=" * 80)
