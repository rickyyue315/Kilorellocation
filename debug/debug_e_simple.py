"""
Simplified E-mode debug - output to file
"""
import pandas as pd
import sys
import io

# Set UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data_processor import DataProcessor
from business_logic import TransferLogic

# Read file
file_path = r'C:\Users\kf_yue\Dropbox\SASA\AI\Sep2025_App\KiLo Reallocation\AMU_Reallocation_29Jan2026_AI.XLSX'

processor = DataProcessor()
df, stats = processor.preprocess_data(file_path)

# Find marked records
marked_df = df[(df['ALL'].notna()) & (df['ALL'].astype(str).str.strip() != '')]

print(f"Total records: {len(df)}")
print(f"Marked ALL records: {len(marked_df)}")

# Initialize business logic
logic = TransferLogic()

# Execute E mode transfer recommendations
print("\n=== Executing E mode ===")
recommendations = logic.generate_transfer_recommendations(df, mode="強制轉出")

print(f"Total recommendations: {len(recommendations)}")

# Save to file for analysis
output_file = "e_mode_debug_results.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(f"Total records: {len(df)}\n")
    f.write(f"Marked ALL records: {len(marked_df)}\n\n")
    
    f.write("=== Marked stores ===\n")
    marked_summary = marked_df.groupby(['Article', 'RP Type']).agg({
        'SaSa Net Stock': 'sum',
        'Site': 'count'
    }).reset_index()
    marked_summary.columns = ['Article', 'RP Type', 'Total Stock', 'Store Count']
    f.write(marked_summary.to_string())
    f.write("\n\n")
    
    f.write(f"=== Recommendations ({len(recommendations)}) ===\n")
    if len(recommendations) > 0:
        if isinstance(recommendations, list):
            rec_df = pd.DataFrame(recommendations)
        else:
            rec_df = recommendations
        
        # Summary by article
        if 'Article' in rec_df.columns and 'Quantity' in rec_df.columns:
            rec_summary = rec_df.groupby('Article')['Quantity'].agg(['count', 'sum']).reset_index()
            rec_summary.columns = ['Article', 'Recommendation Count', 'Total Transferred']
            f.write(rec_summary.to_string())
            f.write("\n\n")
        
        # Detailed recommendations
        f.write("=== Detailed Recommendations ===\n")
        cols_to_show = []
        for col in ['Article', 'From Site', 'To Site', 'Quantity', 'From OM', 'To OM', 'Source Type', 'Destination Type']:
            if col in rec_df.columns:
                cols_to_show.append(col)
        
        if cols_to_show:
            f.write(rec_df[cols_to_show].to_string())
        else:
            f.write(rec_df.to_string())
    
    f.write("\n\n=== Analysis by Article ===\n")
    for article in sorted(marked_df['Article'].unique()):
        f.write(f"\n--- Article: {article} ---\n")
        
        article_marked = marked_df[marked_df['Article'] == article]
        f.write(f"Marked stores: {len(article_marked)}\n")
        f.write(f"Total marked stock: {article_marked['SaSa Net Stock'].sum()}\n")
        
        # RP Type breakdown
        rp_breakdown = article_marked.groupby('RP Type')['SaSa Net Stock'].sum()
        for rp_type, stock in rp_breakdown.items():
            f.write(f"  {rp_type}: {stock} units\n")
        
        # Find RF stores for this article
        article_data = df[df['Article'] == article]
        rf_stores = article_data[article_data['RP Type'] == 'RF']
        
        f.write(f"\nRF stores (all): {len(rf_stores)}\n")
        
        total_capacity = 0
        for _, rf_row in rf_stores.iterrows():
            current = rf_row['SaSa Net Stock'] + rf_row['Pending Received']
            max_cap = rf_row['Safety Stock'] * 2
            can_receive = max(0, max_cap - current)
            total_capacity += can_receive
            if can_receive > 0:
                f.write(f"  {rf_row['Site']} (OM: {rf_row['OM']}): +{can_receive} units (current: {current}, max: {max_cap})\n")
        
        f.write(f"\nTotal receive capacity: {total_capacity}\n")
        f.write(f"Transfer demand: {article_marked['SaSa Net Stock'].sum()}\n")
        
        if total_capacity < article_marked['SaSa Net Stock'].sum():
            shortage = article_marked['SaSa Net Stock'].sum() - total_capacity
            f.write(f"*** ISSUE: Insufficient capacity! Short by {shortage} units ***\n")
        
        # Check recommendations
        if isinstance(recommendations, list):
            article_recs = [r for r in recommendations if str(r.get('Article', '')).zfill(12) == article]
        else:
            article_recs = recommendations[recommendations['Article'] == article] if len(recommendations) > 0 else []
        
        if len(article_recs) > 0:
            if isinstance(article_recs, list):
                total_transferred = sum(r['Quantity'] for r in article_recs)
            else:
                total_transferred = article_recs['Quantity'].sum()
            
            f.write(f"\nRecommendations: {len(article_recs)}\n")
            f.write(f"Actual transferred: {total_transferred}\n")
            
            remaining = article_marked['SaSa Net Stock'].sum() - total_transferred
            if remaining > 0:
                f.write(f"*** WARNING: {remaining} units NOT transferred! ***\n")
        else:
            f.write(f"\n*** WARNING: NO recommendations for this article! ***\n")

print(f"\nResults saved to: {output_file}")
