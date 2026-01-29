"""
Debug E mode force transfer issue
"""
import pandas as pd
import sys
import io

# Set UTF-8 encoding for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from data_processor import DataProcessor
from business_logic import TransferLogic

# Read file
file_path = r'C:\Users\kf_yue\Dropbox\SASA\AI\Sep2025_App\KiLo Reallocation\AMU_Reallocation_29Jan2026_AI.XLSX'

processor = DataProcessor()
df, stats = processor.preprocess_data(file_path)

print(f"總記錄數: {len(df)}")
print(f"\n標記為ALL的記錄數: {len(df[(df['ALL'].notna()) & (df['ALL'].astype(str).str.strip() != '')])}")

# 查看標記了ALL的店舖
marked_df = df[(df['ALL'].notna()) & (df['ALL'].astype(str).str.strip() != '')]
print("\n=== 標記為ALL的店舖 ===")
print(marked_df[['Article', 'Site', 'OM', 'RP Type', 'SaSa Net Stock', 'Safety Stock']].to_string())

# 初始化業務邏輯
logic = TransferLogic()

# 執行E模式調貨建議
print("\n\n=== 開始執行E模式調貨建議 ===")
recommendations_df = logic.generate_transfer_recommendations(df, mode="強制轉出")

print(f"\nTotal recommendations: {len(recommendations_df)}")

if len(recommendations_df) > 0:
    print("\n=== Transfer Recommendations ===")
    if isinstance(recommendations_df, list):
        # If it's a list of dicts, convert to DataFrame
        recommendations_df = pd.DataFrame(recommendations_df)
    
    display_cols = []
    for col in ['Article', 'From Site', 'To Site', 'Quantity', 'From OM', 'To OM', 'Source Type', 'Destination Type']:
        if col in recommendations_df.columns:
            display_cols.append(col)
    
    if display_cols:
        print(recommendations_df[display_cols].to_string())
    else:
        print(recommendations_df.to_string())
else:
    print("\nNo recommendations generated!")

# Analyze transfer/receive status for each Article
print("\n\n=== Detailed Analysis ===")
for article in marked_df['Article'].unique():
    print(f"\n--- Article: {article} ---")
    
    article_data = df[df['Article'] == article]
    marked_for_article = marked_df[marked_df['Article'] == article]
    
    print(f"Marked sources count: {len(marked_for_article)}")
    print(f"Total marked stock: {marked_for_article['SaSa Net Stock'].sum()}")
    
    # Find possible RF receiving stores
    rf_stores = article_data[article_data['RP Type'] == 'RF']
    print(f"\nRF stores count: {len(rf_stores)}")
    
    if len(rf_stores) > 0:
        # Calculate receiving capacity (Safety Stock * 2 - current stock)
        total_receive_capacity = 0
        for _, rf_row in rf_stores.iterrows():
            current_stock = rf_row['SaSa Net Stock'] + rf_row['Pending Received']
            max_capacity = rf_row['Safety Stock'] * 2
            can_receive = max(0, max_capacity - current_stock)
            total_receive_capacity += can_receive
            if can_receive > 0:
                print(f"  {rf_row['Site']} (OM: {rf_row['OM']}): Can receive {can_receive} (Current: {current_stock}, Max: {max_capacity})")
        
        print(f"\nTotal receive capacity: {total_receive_capacity}")
        print(f"Transfer demand: {marked_for_article['SaSa Net Stock'].sum()}")
        
        if total_receive_capacity < marked_for_article['SaSa Net Stock'].sum():
            shortage = marked_for_article['SaSa Net Stock'].sum() - total_receive_capacity
            print(f"ISSUE: Insufficient capacity! Short by {shortage} units")
    else:
        print("ISSUE: No RF stores available to receive!")
    
    # Check recommendations for this article
    if isinstance(recommendations_df, list):
        article_recommendations = [r for r in recommendations_df if r.get('Article') == article]
        article_recommendations = pd.DataFrame(article_recommendations) if article_recommendations else pd.DataFrame()
    else:
        article_recommendations = recommendations_df[recommendations_df['Article'] == article] if len(recommendations_df) > 0 else pd.DataFrame()
    
    print(f"\nRecommendations for this article: {len(article_recommendations)}")
    if len(article_recommendations) > 0:
        actual_transferred = article_recommendations['Quantity'].sum()
        remaining = marked_for_article['SaSa Net Stock'].sum() - actual_transferred
        print(f"Actual transferred: {actual_transferred}")
        print(f"Remaining untransferred: {remaining}")
        if remaining > 0:
            print(f"WARNING: {remaining} units could not be transferred!")
