#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
測試新增的銷售數據欄位功能
"""

import pandas as pd
import numpy as np
import sys
import io
from business_logic import TransferLogic
from excel_generator import ExcelGenerator
from data_processor import DataProcessor

# 設置UTF-8編碼輸出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def create_test_data():
    """創建包含銷售數據的測試數據"""
    test_data = [
        {
            'Article': '123456789012',
            'OM': 'OM001',
            'RP Type': 'ND',
            'Site': 'SITE001',
            'SaSa Net Stock': 50,
            'Pending Received': 5,
            'Safety Stock': 10,
            'Last Month Sold Qty': 25,
            'MTD Sold Qty': 15,
            'MOQ': 2,
            'Article Description': 'Test Product A'
        },
        {
            'Article': '123456789012',
            'OM': 'OM001',
            'RP Type': 'RF',
            'Site': 'SITE002',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 10,
            'Last Month Sold Qty': 30,
            'MTD Sold Qty': 20,
            'MOQ': 2,
            'Article Description': 'Test Product A'
        },
        {
            'Article': '123456789012',
            'OM': 'OM001',
            'RP Type': 'RF',
            'Site': 'SITE003',
            'SaSa Net Stock': 40,
            'Pending Received': 0,
            'Safety Stock': 10,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 8,
            'MOQ': 2,
            'Article Description': 'Test Product A'
        }
    ]
    
    return pd.DataFrame(test_data)

def process_test_data(df):
    """手動處理測試數據，模擬DataProcessor的功能"""
    processed_df = df.copy()
    
    # 確保Article欄位為12位文本格式
    processed_df['Article'] = processed_df['Article'].astype(str).str.zfill(12)
    
    # 處理商品描述欄位
    if 'Article Description' not in processed_df.columns:
        processed_df['Article Description'] = "Test Product"
    
    # 轉換數據類型
    integer_columns = [
        'SaSa Net Stock', 'Pending Received', 'Safety Stock',
        'Last Month Sold Qty', 'MTD Sold Qty', 'MOQ'
    ]
    
    for col in integer_columns:
        if col in processed_df.columns:
            processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce').fillna(0).astype(int)
    
    # 處理字符串欄位
    string_columns = ['OM', 'RP Type', 'Site']
    for col in string_columns:
        if col in processed_df.columns:
            processed_df[col] = processed_df[col].fillna("").astype(str)
    
    # 計算有效銷量
    if 'Last Month Sold Qty' in processed_df.columns and 'MTD Sold Qty' in processed_df.columns:
        processed_df['Effective Sold Qty'] = np.where(
            processed_df['Last Month Sold Qty'] > 0,
            processed_df['Last Month Sold Qty'],
            processed_df['MTD Sold Qty']
        )
    else:
        processed_df['Effective Sold Qty'] = 0
    
    return processed_df

def test_sales_data_integration():
    """測試銷售數據整合功能"""
    
    # 創建測試數據
    test_df = create_test_data()
    
    # 手動處理數據
    processed_df = process_test_data(test_df)
    
    # 初始化處理器
    transfer_logic = TransferLogic()
    excel_generator = ExcelGenerator()
    
    # 生成調貨建議
    recommendations = transfer_logic.generate_transfer_recommendations(processed_df, "保守轉貨")
    
    # 檢查建議中的銷售數據欄位
    expected_sales_fields = [
        'Transfer Site Last Month Sold Qty',
        'Transfer Site MTD Sold Qty',
        'Receive Site Last Month Sold Qty',
        'Receive Site MTD Sold Qty'
    ]
    
    # 生成Excel文件
    output_file = excel_generator.generate_excel_file(recommendations, transfer_logic.get_transfer_statistics())
    
    # 驗證Excel文件中的欄位
    df_output = pd.read_excel(output_file, sheet_name='調貨建議 (Transfer Recommendations)')
    
    # 檢查銷售數據欄位是否存在
    missing_fields = []
    for field in expected_sales_fields:
        if field not in df_output.columns:
            missing_fields.append(field)
    
    # 寫入結果到文件
    with open('test_sales_data_result.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Sales Data Column Integration Test\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Created {len(test_df)} rows of test data\n")
        f.write(f"Data preprocessing completed, {len(processed_df)} rows\n")
        f.write(f"Generated {len(recommendations)} transfer recommendations\n\n")
        
        f.write("Checking sales data fields in recommendations:\n")
        for i, rec in enumerate(recommendations):
            f.write(f"\nRecommendation {i+1}:\n")
            f.write(f"  Transfer Site: {rec['Transfer Site']}\n")
            f.write(f"  Receive Site: {rec['Receive Site']}\n")
            
            for field in expected_sales_fields:
                value = rec.get(field, 'N/A')
                f.write(f"  {field}: {value}\n")
        
        f.write(f"\nExcel file generated: {output_file}\n\n")
        
        f.write("Columns in Excel file:\n")
        for col in df_output.columns:
            f.write(f"  - {col}\n")
        
        if missing_fields:
            f.write(f"\nFAILED: Missing sales data fields: {missing_fields}\n")
            success = False
        else:
            f.write("\nSUCCESS: All sales data fields have been correctly added\n\n")
            
            # 顯示實際數據
            f.write("Actual sales data content:\n")
            for idx, row in df_output.iterrows():
                f.write(f"\nRow {idx+1}:\n")
                f.write(f"  Transfer Site Last Month Sold Qty: {row['Transfer Site Last Month Sold Qty']}\n")
                f.write(f"  Transfer Site MTD Sold Qty: {row['Transfer Site MTD Sold Qty']}\n")
                f.write(f"  Receive Site Last Month Sold Qty: {row['Receive Site Last Month Sold Qty']}\n")
                f.write(f"  Receive Site MTD Sold Qty: {row['Receive Site MTD Sold Qty']}\n")
            success = True
        
        f.write("\n" + "=" * 80 + "\n")
        if success:
            f.write("RESULT: Sales data column test PASSED\n")
        else:
            f.write("RESULT: Sales data column test FAILED\n")
        f.write("=" * 80 + "\n")
    
    return success

if __name__ == "__main__":
    success = test_sales_data_integration()
    print("Test completed. Results written to test_sales_data_result.txt")