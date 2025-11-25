#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify Remark column fix
"""

from excel_generator import ExcelGenerator
import pandas as pd

# Create test data with Destination Type
test_recommendations = [
    {
        'Article': 'ART001',
        'Product Desc': 'Product 1',
        'Transfer OM': 'OM1',
        'Transfer Site': 'Site1',
        'Receive OM': 'OM2',
        'Receive Site': 'Site2',
        'Transfer Qty': 100,
        'Original Stock': 500,
        'After Transfer Stock': 600,
        'Safety Stock': 50,
        'MOQ': 10,
        'Source Type': 'RF over',
        'Destination Type': 'Priority 0',
        'Notes': 'Test note 1'
    },
    {
        'Article': 'ART002',
        'Product Desc': 'Product 2',
        'Transfer OM': 'OM1',
        'Transfer Site': 'Site1',
        'Receive OM': 'OM3',
        'Receive Site': 'Site3',
        'Transfer Qty': 50,
        'Original Stock': 200,
        'After Transfer Stock': 250,
        'Safety Stock': 30,
        'MOQ': 5,
        'Source Type': 'ND Transfer',
        'Destination Type': 'Priority 0',
        'Notes': 'Test note 2'
    }
]

# Test statistics
test_statistics = {
    'total_recommendations': 2,
    'total_transfer_qty': 150,
    'unique_articles': 2,
    'unique_oms': 3,
    'article_stats': {},
    'om_stats': {},
    'source_type_stats': {},
    'dest_type_stats': {}
}

# Generate Excel
generator = ExcelGenerator()
output_file = generator.generate_excel_file(test_recommendations, test_statistics)

# Read back and verify
df = pd.read_excel(output_file, sheet_name='調貨建議 (Transfer Recommendations)')

# Write results to file
with open('verify_result.txt', 'w', encoding='utf-8') as f:
    f.write("Verification Results\n")
    f.write("====================\n\n")
    
    f.write("Data:\n")
    for idx, row in df.iterrows():
        f.write(f"Row {idx+1}: Article={row['Article']}, Remark={row['Remark']}\n")
    
    f.write("\n\nSummary:\n")
    has_empty = df['Remark'].isna().any() or (df['Remark'] == '').any()
    if has_empty:
        f.write("FAILED: Some Remark cells are empty\n")
    else:
        f.write("SUCCESS: All Remark cells are populated\n")
        f.write(f"Total rows: {len(df)}\n")
        f.write(f"Remarks populated: {len(df[df['Remark'].notna()])}\n")

print("Results written to verify_result.txt")
