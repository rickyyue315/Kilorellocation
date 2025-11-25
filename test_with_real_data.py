#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Remark column with real data from PL_reallocation_25Nov2025.XLSX
"""

import pandas as pd
from excel_generator import ExcelGenerator

# Read the real data
input_file = 'PL_reallocation_25Nov2025.XLSX'
df_input = pd.read_excel(input_file, sheet_name='Sheet1')

# Create test recommendations from real data
test_recommendations = []

# Sample a few rows to create transfer recommendations
for idx, row in df_input.head(10).iterrows():
    rec = {
        'Article': str(row.get('Article', '')),
        'Product Desc': str(row.get('Article Description', '')),
        'Transfer OM': 'OM1',
        'Transfer Site': 'Site1',
        'Receive OM': 'OM2',
        'Receive Site': 'Site2',
        'Transfer Qty': 10,
        'Original Stock': int(row.get('SaSa Net Stock', 0)),
        'After Transfer Stock': int(row.get('SaSa Net Stock', 0)) + 10,
        'Safety Stock': 5,
        'MOQ': 2,
        'Source Type': 'RF過剩轉出',
        'Destination Type': '重點補0',
        'Notes': 'Test transfer'
    }
    test_recommendations.append(rec)

# Test statistics
test_statistics = {
    'total_recommendations': len(test_recommendations),
    'total_transfer_qty': 100,
    'unique_articles': len(test_recommendations),
    'unique_oms': 2,
    'article_stats': {},
    'om_stats': {},
    'source_type_stats': {},
    'dest_type_stats': {}
}

# Generate Excel
generator = ExcelGenerator()
output_file = generator.generate_excel_file(test_recommendations, test_statistics)

# Read back and verify
df_output = pd.read_excel(output_file, sheet_name='調貨建議 (Transfer Recommendations)')

# Write results to file
with open('test_real_data_result.txt', 'w', encoding='utf-8') as f:
    f.write("Test with Real Data Results\n")
    f.write("============================\n\n")
    
    f.write("Generated Recommendations:\n")
    for idx, row in df_output.iterrows():
        f.write(f"Row {idx+1}: Article={row['Article']}, Remark={row['Remark']}\n")
    
    f.write("\n\nSummary:\n")
    has_empty = df_output['Remark'].isna().any() or (df_output['Remark'] == '').any()
    if has_empty:
        f.write("FAILED: Some Remark cells are empty\n")
    else:
        f.write("SUCCESS: All Remark cells are populated\n")
        f.write(f"Total rows: {len(df_output)}\n")
        f.write(f"Remarks populated: {len(df_output[df_output['Remark'].notna()])}\n")

print("Test completed. Results written to test_real_data_result.txt")
