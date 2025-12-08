#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
檢查Excel文件的實際欄位結構
"""

import pandas as pd

def check_excel_columns():
    """檢查Excel文件的欄位結構"""
    
    try:
        # 讀取Excel文件
        df = pd.read_excel('調貨建議_20251208.xlsx', sheet_name='調貨建議 (Transfer Recommendations)')
        
        print("Actual Excel columns:")
        for i, col in enumerate(df.columns):
            print(f"  {i+1}: {col}")
        
        print(f"\nTotal columns: {len(df.columns)}")
        print(f"Total rows: {len(df)}")
        
        # 檢查銷售數據欄位
        sales_fields = [
            'Transfer Site Last Month Sold Qty',
            'Transfer Site MTD Sold Qty',
            'Receive Site Last Month Sold Qty', 
            'Receive Site MTD Sold Qty'
        ]
        
        print("\nSales data fields check:")
        for field in sales_fields:
            if field in df.columns:
                idx = df.columns.get_loc(field) + 1
                print(f"  ✓ {field} (Column {idx})")
            else:
                print(f"  ✗ {field} - Missing")
        
        # 顯示前幾行的銷售數據
        if len(df) > 0:
            print("\nSample sales data (first 2 rows):")
            for idx in range(min(2, len(df))):
                row = df.iloc[idx]
                print(f"\nRow {idx+1}:")
                print(f"  Transfer Site: {row['Transfer Site']} → Receive Site: {row['Receive Site']}")
                print(f"  Transfer Site Last Month Sold Qty: {row.get('Transfer Site Last Month Sold Qty', 'N/A')}")
                print(f"  Transfer Site MTD Sold Qty: {row.get('Transfer Site MTD Sold Qty', 'N/A')}")
                print(f"  Receive Site Last Month Sold Qty: {row.get('Receive Site Last Month Sold Qty', 'N/A')}")
                print(f"  Receive Site MTD Sold Qty: {row.get('Receive Site MTD Sold Qty', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return False

if __name__ == "__main__":
    check_excel_columns()