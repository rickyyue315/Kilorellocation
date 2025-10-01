"""
系統測試腳本
用於驗證庫存調貨建議系統的功能
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

# 導入自定義模組
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator

def create_test_data():
    """
    創建測試數據
    
    Returns:
        測試DataFrame
    """
    # 創建測試數據
    test_data = [
        # Article 1 - OM1
        {
            'Article': '000000000001',
            'Article Description': '測試商品1',
            'OM': 'OM1',
            'RP Type': 'ND',
            'Site': 'ND_SITE1',
            'SaSa Net Stock': 20,
            'Pending Received': 0,
            'Safety Stock': 5,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 0
        },
        {
            'Article': '000000000001',
            'Article Description': '測試商品1',
            'OM': 'OM1',
            'RP Type': 'RF',
            'Site': 'RF_SITE1',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 10,
            'Last Month Sold Qty': 15,
            'MTD Sold Qty': 5
        },
        {
            'Article': '000000000001',
            'Article Description': '測試商品1',
            'OM': 'OM1',
            'RP Type': 'RF',
            'Site': 'RF_SITE2',
            'SaSa Net Stock': 5,
            'Pending Received': 0,
            'Safety Stock': 10,
            'Last Month Sold Qty': 8,
            'MTD Sold Qty': 2
        },
        {
            'Article': '000000000001',
            'Article Description': '測試商品1',
            'OM': 'OM1',
            'RP Type': 'RF',
            'Site': 'RF_SITE3',
            'SaSa Net Stock': 25,
            'Pending Received': 0,
            'Safety Stock': 10,
            'Last Month Sold Qty': 3,
            'MTD Sold Qty': 1
        },
        # Article 2 - OM1
        {
            'Article': '000000000002',
            'Article Description': '測試商品2',
            'OM': 'OM1',
            'RP Type': 'ND',
            'Site': 'ND_SITE2',
            'SaSa Net Stock': 15,
            'Pending Received': 0,
            'Safety Stock': 5,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 0
        },
        {
            'Article': '000000000002',
            'Article Description': '測試商品2',
            'OM': 'OM1',
            'RP Type': 'RF',
            'Site': 'RF_SITE4',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 8,
            'Last Month Sold Qty': 12,
            'MTD Sold Qty': 4
        },
        {
            'Article': '000000000002',
            'Article Description': '測試商品2',
            'OM': 'OM1',
            'RP Type': 'RF',
            'Site': 'RF_SITE5',
            'SaSa Net Stock': 20,
            'Pending Received': 0,
            'Safety Stock': 8,
            'Last Month Sold Qty': 2,
            'MTD Sold Qty': 1
        },
        # Article 3 - OM2
        {
            'Article': '000000000003',
            'Article Description': '測試商品3',
            'OM': 'OM2',
            'RP Type': 'ND',
            'Site': 'ND_SITE3',
            'SaSa Net Stock': 30,
            'Pending Received': 0,
            'Safety Stock': 10,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 0
        },
        {
            'Article': '000000000003',
            'Article Description': '測試商品3',
            'OM': 'OM2',
            'RP Type': 'RF',
            'Site': 'RF_SITE6',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 15,
            'Last Month Sold Qty': 20,
            'MTD Sold Qty': 8
        },
        {
            'Article': '000000000003',
            'Article Description': '測試商品3',
            'OM': 'OM2',
            'RP Type': 'RF',
            'Site': 'RF_SITE7',
            'SaSa Net Stock': 10,
            'Pending Received': 5,
            'Safety Stock': 15,
            'Last Month Sold Qty': 18,
            'MTD Sold Qty': 6
        }
    ]
    
    return pd.DataFrame(test_data)

def test_data_processor():
    """
    測試數據處理模組
    """
    print("測試數據處理模組...")
    
    # 創建測試數據
    test_df = create_test_data()
    
    # 保存測試數據為Excel文件
    test_file = "test_data.xlsx"
    test_df.to_excel(test_file, index=False)
    
    # 測試數據處理
    processor = DataProcessor()
    processed_df, stats = processor.preprocess_data(test_file)
    
    # 驗證結果
    assert len(processed_df) == len(test_df), "處理後數據行數不匹配"
    assert all(processed_df['Article'].str.len() == 12), "Article欄位不是12位"
    assert 'Effective Sold Qty' in processed_df.columns, "缺少有效銷量欄位"
    
    print("✓ 數據處理模組測試通過")
    
    # 清理測試文件
    if os.path.exists(test_file):
        os.remove(test_file)
    
    return processed_df

def test_business_logic(df):
    """
    測試業務邏輯模組
    
    Args:
        df: 處理後的DataFrame
    """
    print("測試業務邏輯模組...")
    
    # 創建業務邏輯對象
    transfer_logic = TransferLogic()
    
    # 生成調貨建議
    recommendations = transfer_logic.generate_transfer_recommendations(df)
    
    # 執行質量檢查
    quality_passed = transfer_logic.perform_quality_checks(df)
    
    # 獲取統計信息
    statistics = transfer_logic.get_transfer_statistics()
    
    # 驗證結果
    assert len(recommendations) > 0, "沒有生成調貨建議"
    assert quality_passed, "質量檢查失敗"
    assert 'total_recommendations' in statistics, "缺少總建議數統計"
    
    print("✓ 業務邏輯模組測試通過")
    print(f"  - 生成了 {len(recommendations)} 條調貨建議")
    print(f"  - 總調貨件數: {statistics.get('total_transfer_qty', 0)}")
    
    return recommendations, statistics

def test_excel_generator(recommendations, statistics):
    """
    測試Excel輸出模組
    
    Args:
        recommendations: 調貨建議列表
        statistics: 統計信息字典
    """
    print("測試Excel輸出模組...")
    
    # 創建Excel生成器
    excel_generator = ExcelGenerator()
    
    # 生成Excel文件
    output_path = excel_generator.generate_excel_file(recommendations, statistics)
    
    # 驗證文件是否存在
    assert os.path.exists(output_path), "Excel文件未生成"
    
    print("✓ Excel輸出模組測試通過")
    print(f"  - 生成文件: {output_path}")
    
    return output_path

def run_all_tests():
    """
    運行所有測試
    """
    print("開始運行系統測試...")
    print("=" * 50)
    
    try:
        # 測試數據處理模組
        processed_df = test_data_processor()
        
        # 測試業務邏輯模組
        recommendations, statistics = test_business_logic(processed_df)
        
        # 測試Excel輸出模組
        output_path = test_excel_generator(recommendations, statistics)
        
        print("=" * 50)
        print("✅ 所有測試通過！系統運行正常。")
        
        # 顯示一些示例結果
        print("\n示例調貨建議:")
        for i, rec in enumerate(recommendations[:3]):  # 只顯示前3條
            print(f"  {i+1}. 從 {rec['Transfer Site']} 調貨 {rec['Transfer Qty']} 件到 {rec['Receive Site']} (商品: {rec['Article']})")
        
        return True
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ 測試失敗: {str(e)}")
        return False

if __name__ == "__main__":
    # 運行測試
    success = run_all_tests()
    
    # 退出碼
    exit(0 if success else 1)