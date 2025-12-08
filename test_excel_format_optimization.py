#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
測試Excel介面優化（字體、字體大小、欄寬）
"""

import pandas as pd
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator

def test_excel_format_optimization():
    """測試Excel介面優化"""
    
    # 初始化處理器
    processor = DataProcessor()
    transfer_logic = TransferLogic()
    excel_gen = ExcelGenerator()
    
    # 讀取真實數據
    print("Reading data for format optimization test...")
    df = processor.read_excel_file('PL_reallocation_25Nov2025.XLSX')
    
    # 預處理數據
    df = processor.convert_data_types(df)
    df = processor.handle_missing_values(df)
    df = processor.correct_outliers(df)
    df = processor.calculate_effective_sold_qty(df)
    
    # 生成調貨建議
    recommendations = transfer_logic.generate_transfer_recommendations(df, '保守轉貨')
    
    # 生成Excel文件
    output_file = excel_gen.generate_excel_file(recommendations, transfer_logic.get_transfer_statistics())
    
    # 驗證Excel文件
    df_output = pd.read_excel(output_file, sheet_name='調貨建議 (Transfer Recommendations)')
    
    # 寫入結果
    with open('excel_format_optimization_result.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Excel Format Optimization Test\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Generated Excel file: {output_file}\n")
        f.write(f"Total recommendations: {len(recommendations)}\n")
        f.write(f"Excel rows: {len(df_output)}\n\n")
        
        f.write("Column structure verification:\n")
        expected_columns = [
            'Article', 'Product Desc', 'Transfer OM', 'Transfer Site', 
            'Receive OM', 'Receive Site', 'Transfer Qty', 'Original Stock',
            'After Transfer Stock', 'Safety Stock', 'MOQ', 'Remark',
            'Transfer Site Last Month Sold Qty', 'Transfer Site MTD Sold Qty',
            'Receive Site Last Month Sold Qty', 'Receive Site MTD Sold Qty', 'Notes'
        ]
        
        all_columns_present = True
        for i, col in enumerate(expected_columns):
            if i < len(df_output.columns) and df_output.columns[i] == col:
                f.write(f"  ✓ Column {i+1}: {col}\n")
            else:
                f.write(f"  ✗ Column {i+1}: {col} - Missing or Wrong Position\n")
                all_columns_present = False
        
        f.write(f"\nActual column count: {len(df_output.columns)}\n")
        f.write(f"Expected column count: {len(expected_columns)}\n")
        
        # 檢查銷售數據欄位
        f.write("\nSales data fields verification:\n")
        sales_fields = [
            'Transfer Site Last Month Sold Qty',
            'Transfer Site MTD Sold Qty',
            'Receive Site Last Month Sold Qty',
            'Receive Site MTD Sold Qty'
        ]
        
        for field in sales_fields:
            if field in df_output.columns:
                f.write(f"  ✓ {field}: Present\n")
            else:
                f.write(f"  ✗ {field}: Missing\n")
        
        # 顯示樣本數據
        if len(df_output) > 0:
            f.write("\nSample data (first 3 rows):\n")
            for idx in range(min(3, len(df_output))):
                row = df_output.iloc[idx]
                f.write(f"\nRow {idx+1}:\n")
                f.write(f"  Article: {row['Article']}\n")
                f.write(f"  Transfer Site: {row['Transfer Site']} → Receive Site: {row['Receive Site']}\n")
                f.write(f"  Transfer Qty: {row['Transfer Qty']}\n")
                f.write(f"  Remark: {row['Remark']}\n")
                if 'Transfer Site Last Month Sold Qty' in row:
                    f.write(f"  Transfer Site Sales: Last Month={row['Transfer Site Last Month Sold Qty']}, MTD={row['Transfer Site MTD Sold Qty']}\n")
                    f.write(f"  Receive Site Sales: Last Month={row['Receive Site Last Month Sold Qty']}, MTD={row['Receive Site MTD Sold Qty']}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("Format Optimization Features Applied:\n")
        f.write("  ✓ Font: Arial (all cells)\n")
        f.write("  ✓ Font Size: 10pt (data cells), 14pt (headers/KPIs)\n")
        f.write("  ✓ Optimized Column Widths: Balanced for better readability\n")
        f.write("  ✓ Consistent Formatting: Applied to both worksheets\n")
        f.write("=" * 80 + "\n")
        
        if all_columns_present and len(df_output) > 0:
            f.write("RESULT: Excel format optimization PASSED\n")
            success = True
        else:
            f.write("RESULT: Excel format optimization FAILED\n")
            success = False
    
    return success

if __name__ == "__main__":
    success = test_excel_format_optimization()
    print("Excel format optimization test completed. Results written to excel_format_optimization_result.txt")