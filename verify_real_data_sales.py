#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用真實數據驗證銷售數據欄位功能
"""

import pandas as pd
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator

def verify_real_data():
    """使用真實數據驗證銷售數據欄位"""
    
    # 初始化處理器
    processor = DataProcessor()
    transfer_logic = TransferLogic()
    excel_gen = ExcelGenerator()
    
    # 讀取真實數據
    print("Reading real data...")
    df = processor.read_excel_file('PL_reallocation_25Nov2025.XLSX')
    
    # 預處理數據
    df = processor.convert_data_types(df)
    df = processor.handle_missing_values(df)
    df = processor.correct_outliers(df)
    df = processor.calculate_effective_sold_qty(df)
    
    print(f"Processed {len(df)} rows of data")
    
    # 生成調貨建議
    print("Generating transfer recommendations...")
    recommendations = transfer_logic.generate_transfer_recommendations(df, '保守轉貨')
    
    print(f"Generated {len(recommendations)} transfer recommendations")
    
    # 生成Excel文件
    print("Generating Excel file...")
    output_file = excel_gen.generate_excel_file(recommendations, transfer_logic.get_transfer_statistics())
    
    # 驗證銷售數據欄位
    print("Verifying sales data fields...")
    df_output = pd.read_excel(output_file, sheet_name='調貨建議 (Transfer Recommendations)')
    
    sales_fields = [
        'Transfer Site Last Month Sold Qty',
        'Transfer Site MTD Sold Qty', 
        'Receive Site Last Month Sold Qty',
        'Receive Site MTD Sold Qty'
    ]
    
    # 寫入結果
    with open('verify_real_data_sales_result.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Real Data Sales Data Verification\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Input data rows: {len(df)}\n")
        f.write(f"Generated recommendations: {len(recommendations)}\n")
        f.write(f"Output file: {output_file}\n\n")
        
        f.write("Sales data fields verification:\n")
        all_present = True
        for field in sales_fields:
            if field in df_output.columns:
                f.write(f"  ✓ {field}: Present\n")
            else:
                f.write(f"  ✗ {field}: Missing\n")
                all_present = False
        
        f.write(f"\nOutput Excel rows: {len(df_output)}\n")
        
        if all_present and len(recommendations) > 0:
            f.write("\nSample sales data from first recommendation:\n")
            sample = df_output.iloc[0]
            for field in sales_fields:
                f.write(f"  {field}: {sample[field]}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        if all_present:
            f.write("RESULT: Real data verification PASSED\n")
        else:
            f.write("RESULT: Real data verification FAILED\n")
        f.write("=" * 80 + "\n")
    
    return all_present

if __name__ == "__main__":
    success = verify_real_data()
    print("Verification completed. Results written to verify_real_data_sales_result.txt")