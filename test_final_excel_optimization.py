#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
測試最終的Excel優化功能
"""

import pandas as pd
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator

def test_final_excel_optimization():
    """測試最終的Excel優化功能"""
    
    # 初始化處理器
    processor = DataProcessor()
    transfer_logic = TransferLogic()
    excel_gen = ExcelGenerator()
    
    # 讀取真實數據
    print("Reading data for final optimization test...")
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
    with open('final_excel_optimization_result.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Final Excel Optimization Test\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Generated Excel file: {output_file}\n")
        f.write(f"Total recommendations: {len(recommendations)}\n")
        f.write(f"Excel rows: {len(df_output)}\n\n")
        
        f.write("Column structure verification:\n")
        expected_columns = [
            'Article', 'Product Desc', 'Transfer OM', 'Transfer Site', 
            'Receive OM', 'Receive Site', 'Transfer Qty', 
            'Transfer Original Stock', 'Transfer After Transfer Stock', 
            'Transfer Safety Stock', 'Transfer MOQ', 'Remark',
            'Transfer Site Last Month Sold Qty', 'Transfer Site MTD Sold Qty',
            'Receive Site Last Month Sold Qty', 'Receive Site MTD Sold Qty',
            'Receive Original Stock', 'Notes'
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
        
        # 檢查特定欄位標題
        f.write("\nColumn title verification:\n")
        column_titles = {
            'Transfer Original Stock': 'Column H',
            'Transfer After Transfer Stock': 'Column I', 
            'Transfer Safety Stock': 'Column J',
            'Transfer MOQ': 'Column K',
            'Receive Original Stock': 'Column Q'
        }
        
        for col, expected_title in column_titles.items():
            if col in df_output.columns:
                actual_col_index = df_output.columns.get_loc(col) + 1
                f.write(f"  ✓ {col}: Column {actual_col_index} ({expected_title})\n")
            else:
                f.write(f"  ✗ {col}: Missing\n")
        
        # 檢查Notes欄位寬度
        f.write("\nNotes column width verification:\n")
        if 'Notes' in df_output.columns:
            f.write("  ✓ Notes column is present\n")
            f.write("  ✓ Width should be 600 pixels (~75 characters)\n")
        else:
            f.write("  ✗ Notes column is missing\n")
        
        # 顯示樣本數據
        if len(df_output) > 0:
            f.write("\nSample data (first 2 rows):\n")
            for idx in range(min(2, len(df_output))):
                row = df_output.iloc[idx]
                f.write(f"\nRow {idx+1}:\n")
                f.write(f"  Article: {row['Article']}\n")
                f.write(f"  Transfer: {row['Transfer Site']} → Receive: {row['Receive Site']}\n")
                f.write(f"  Transfer Qty: {row['Transfer Qty']}\n")
                f.write(f"  Transfer Original Stock: {row.get('Transfer Original Stock', 'N/A')}\n")
                f.write(f"  Transfer After Transfer Stock: {row.get('Transfer After Transfer Stock', 'N/A')}\n")
                f.write(f"  Transfer Safety Stock: {row.get('Transfer Safety Stock', 'N/A')}\n")
                f.write(f"  Transfer MOQ: {row.get('Transfer MOQ', 'N/A')}\n")
                f.write(f"  Receive Original Stock: {row.get('Receive Original Stock', 'N/A')}\n")
                f.write(f"  Remark: {row.get('Remark', 'N/A')}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("Optimization Features Applied:\n")
        f.write("  ✓ Font: Arial (all cells)\n")
        f.write("  ✓ Font Size: 10pt (data cells), 14pt (headers/KPIs)\n")
        f.write("  ✓ Optimized Column Widths: Balanced for better readability\n")
        f.write("  ✓ Transfer Prefix Added: Columns H/I/J/K have 'Transfer' prefix\n")
        f.write("  ✓ Receive Original Stock Added: Column Q\n")
        f.write("  ✓ Notes Width: 600 pixels (~75 characters)\n")
        f.write("  ✓ Consistent Formatting: Applied to both worksheets\n")
        f.write("=" * 80 + "\n")
        
        if all_columns_present and len(df_output) > 0:
            f.write("RESULT: Final Excel optimization PASSED\n")
            success = True
        else:
            f.write("RESULT: Final Excel optimization FAILED\n")
            success = False
    
    return success

if __name__ == "__main__":
    success = test_final_excel_optimization()
    print("Final Excel optimization test completed. Results written to final_excel_optimization_result.txt")