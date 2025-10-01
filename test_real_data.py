"""
使用真實數據測試系統功能 v1.9
簡化為雙模式系統：A(保守轉貨)/B(加強轉貨)
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# 導入自定義模組
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_with_real_data(file_path: str):
    """
    使用真實數據測試系統功能
    
    Args:
        file_path: Excel文件路徑
    """
    print("開始使用真實數據測試系統功能...")
    print("=" * 50)
    
    try:
        # 1. 數據預處理
        print("1. 數據預處理...")
        processor = DataProcessor()
        df, processing_stats = processor.preprocess_data(file_path)
        
        print(f"   - 原始數據行數: {processing_stats['original_stats']['total_rows']}")
        print(f"   - 處理後數據行數: {processing_stats['processed_stats']['total_rows']}")
        print(f"   - 商品數量: {df['Article'].nunique()}")
        print(f"   - OM數量: {df['OM'].nunique()}")
        print(f"   - 店鋪數量: {df['Site'].nunique()}")
        print(f"   - RP Type分佈: {df['RP Type'].value_counts().to_dict()}")
        
        # 顯示數據樣本
        print("\n   數據樣本:")
        print(df.head(3).to_string())
        
        # 2. 測試A模式(保守轉貨)
        print("\n2. 測試A模式(保守轉貨)...")
        transfer_logic = TransferLogic()
        recommendations_a = transfer_logic.generate_transfer_recommendations(df, "保守轉貨")
        quality_passed_a = transfer_logic.perform_quality_checks(df)
        statistics_a = transfer_logic.get_transfer_statistics()
        
        print(f"   - 調貨建議數量: {len(recommendations_a)}")
        print(f"   - 總調貨件數: {statistics_a.get('total_transfer_qty', 0)}")
        print(f"   - 質量檢查: {'通過' if quality_passed_a else '失敗'}")
        
        # 顯示前3條調貨建議
        if recommendations_a:
            print("\n   前3條調貨建議:")
            for i, rec in enumerate(recommendations_a[:3]):
                print(f"   {i+1}. 從 {rec['Transfer Site']} 調貨 {rec['Transfer Qty']} 件到 {rec['Receive Site']} (商品: {rec['Article']}, 轉出類型: {rec.get('Source Type', '')})")
        
        # 3. 測試B模式(加強轉貨)
        print("\n3. 測試B模式(加強轉貨)...")
        transfer_logic = TransferLogic()
        recommendations_b = transfer_logic.generate_transfer_recommendations(df, "加強轉貨")
        quality_passed_b = transfer_logic.perform_quality_checks(df)
        statistics_b = transfer_logic.get_transfer_statistics()
        
        print(f"   - 調貨建議數量: {len(recommendations_b)}")
        print(f"   - 總調貨件數: {statistics_b.get('total_transfer_qty', 0)}")
        print(f"   - 質量檢查: {'通過' if quality_passed_b else '失敗'}")
        
        # 顯示前3條調貨建議
        if recommendations_b:
            print("\n   前3條調貨建議:")
            for i, rec in enumerate(recommendations_b[:3]):
                print(f"   {i+1}. 從 {rec['Transfer Site']} 調貨 {rec['Transfer Qty']} 件到 {rec['Receive Site']} (商品: {rec['Article']}, 轉出類型: {rec.get('Source Type', '')})")
        
        # 4. 生成Excel文件
        print("\n4. 生成Excel文件...")
        excel_generator = ExcelGenerator()
        
        # 生成A模式Excel文件
        excel_path_a = excel_generator.generate_excel_file(recommendations_a, statistics_a)
        print(f"   - A模式Excel文件: {excel_path_a}")
        
        # 生成B模式Excel文件
        excel_path_b = excel_generator.generate_excel_file(recommendations_b, statistics_b)
        print(f"   - B模式Excel文件: {excel_path_b}")
        
        # 5. 比較不同模式的結果
        print("\n5. 比較不同模式的結果...")
        print(f"   - A模式調貨建議數量: {len(recommendations_a)}")
        print(f"   - B模式調貨建議數量: {len(recommendations_b)}")
        print(f"   - A模式總調貨件數: {statistics_a.get('total_transfer_qty', 0)}")
        print(f"   - B模式總調貨件數: {statistics_b.get('total_transfer_qty', 0)}")
        
        # 6. 統計分析
        print("\n6. 統計分析 (A模式)...")
        source_type_stats = statistics_a.get('source_type_stats', {})
        dest_type_stats = statistics_a.get('dest_type_stats', {})
        
        print("   - 轉出類型分析:")
        for source_type, stats in source_type_stats.items():
            print(f"     * {source_type}: {stats['count']} 條建議, {stats['qty']} 件")
        
        print("   - 接收類型分析:")
        for dest_type, stats in dest_type_stats.items():
            print(f"     * {dest_type}: {stats['count']} 條建議, {stats['qty']} 件")
        
        print("\n6. 統計分析 (B模式)...")
        source_type_stats = statistics_b.get('source_type_stats', {})
        dest_type_stats = statistics_b.get('dest_type_stats', {})
        
        print("   - 轉出類型分析:")
        for source_type, stats in source_type_stats.items():
            print(f"     * {source_type}: {stats['count']} 條建議, {stats['qty']} 件")
        
        print("   - 接收類型分析:")
        for dest_type, stats in dest_type_stats.items():
            print(f"     * {dest_type}: {stats['count']} 條建議, {stats['qty']} 件")
        
        # 7. 轉出類型詳細分析
        print("\n7. 轉出類型詳細分析...")
        print("   - A模式轉出類型:")
        for rec in recommendations_a[:5]:  # 顯示前5條
            print(f"     * {rec['Transfer Site']} -> {rec['Receive Site']}: {rec['Source Type']}, 庫存變化: {rec['Original Stock']} -> {rec['After Transfer Stock']}, 安全庫存: {rec['Safety Stock']}")
        
        print("   - B模式轉出類型:")
        for rec in recommendations_b[:5]:  # 顯示前5條
            print(f"     * {rec['Transfer Site']} -> {rec['Receive Site']}: {rec['Source Type']}, 庫存變化: {rec['Original Stock']} -> {rec['After Transfer Stock']}, 安全庫存: {rec['Safety Stock']}")
        
        print("\n" + "=" * 50)
        print("✅ 真實數據測試完成！系統運行正常。")
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 測試文件路徑
    test_file = "SUI LIP GU.xlsx"
    
    # 檢查文件是否存在
    if not os.path.exists(test_file):
        print(f"錯誤: 測試文件 {test_file} 不存在")
        exit(1)
    
    # 運行測試
    success = test_with_real_data(test_file)
    
    # 退出碼
    exit(0 if success else 1)