#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final verification of Remark column in generated Excel
"""

import pandas as pd
import glob
import sys
import io

# Set UTF-8 encoding for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Find the most recent generated Excel file
excel_files = glob.glob('調貨建議_*.xlsx')
if not excel_files:
    print("No generated Excel files found")
    exit(1)

# Get the most recent file
latest_file = max(excel_files, key=lambda x: x)

# Read the transfer recommendations sheet
df = pd.read_excel(latest_file, sheet_name='調貨建議 (Transfer Recommendations)')

# Write results to file
with open('verify_remark_result.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("REMARK COLUMN VERIFICATION\n")
    f.write("=" * 80 + "\n")
    f.write(f"File: {latest_file}\n")
    f.write(f"Total rows: {len(df)}\n")
    f.write(f"Columns: {list(df.columns)}\n\n")
    
    # Check if Remark column exists
    if 'Remark' not in df.columns:
        f.write("ERROR: Remark column not found!\n")
        exit(1)
    
    # Display sample rows with Remark
    f.write("Sample rows with Remark column:\n")
    f.write("-" * 80 + "\n")
    for idx in range(min(5, len(df))):
        article = df.iloc[idx].get('Article', 'N/A')
        remark = df.iloc[idx].get('Remark', 'N/A')
        f.write(f"Row {idx+1}: Article={article}, Remark={remark}\n")
    
    f.write("\n" + "=" * 80 + "\n")
    f.write("REMARK STATISTICS\n")
    f.write("=" * 80 + "\n")
    
    # Check for empty remarks
    empty_count = df['Remark'].isna().sum() + (df['Remark'] == '').sum()
    populated_count = len(df) - empty_count
    
    f.write(f"Total rows: {len(df)}\n")
    f.write(f"Populated remarks: {populated_count}\n")
    f.write(f"Empty remarks: {empty_count}\n")
    
    if empty_count == 0:
        f.write("\nSUCCESS: All Remark cells are populated!\n")
    else:
        f.write(f"\nFAILED: {empty_count} empty Remark cells found\n")
    
    # Show unique remarks
    f.write("\n" + "=" * 80 + "\n")
    f.write("UNIQUE REMARKS\n")
    f.write("=" * 80 + "\n")
    unique_remarks = df['Remark'].unique()
    for i, remark in enumerate(unique_remarks, 1):
        count = (df['Remark'] == remark).sum()
        f.write(f"{i}. {remark} (appears {count} times)\n")

print("Verification complete. Results written to verify_remark_result.txt")
