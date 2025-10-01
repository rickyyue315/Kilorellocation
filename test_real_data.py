"""
使用真實數據測試系統功能 v1.8
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
        
        # 2. 測試A模式(保守轉貨) + C模式(按OM調配)
        print("\n2. 測試A模式(保守轉貨) + C模式(按OM調配)...")
        transfer_logic = TransferLogic()
        recommendations_ac = transfer_logic.generate_transfer_recommendations(df, "保守轉貨", "按OM調配")
        quality_passed_ac = transfer_logic.perform_quality_checks(df)
        statistics_ac = transfer_logic.get_transfer_statistics()
        
        print(f"   - 調貨建議數量: {len(recommendations_ac)}")
        print(f"   - 總調貨件數: {statistics_ac.get('total_transfer_qty', 0)}")
        print(f"   - 質量檢查: {'通過' if quality_passed_ac else '失敗'}")
        
        # 顯示前3條調貨建議
        if recommendations_ac:
            print("\n   前3條調貨建議:")
            for i, rec in enumerate(recommendations_ac[:3]):
                print(f"   {i+1}. 從 {rec['Transfer Site']} 調貨 {rec['Transfer Qty']} 件到 {rec['Receive Site']} (商品: {rec['Article']})")
        
        # 3. 測試B模式(加強轉貨) + D模式(按港澳調配)
        print("\n3. 測試B模式(加強轉貨) + D模式(按港澳調配)...")
        transfer_logic = TransferLogic()
        recommendations_bd = transfer_logic.generate_transfer_recommendations(df, "加強轉貨", "按港澳調配")
        quality_passed_bd = transfer_logic.perform_quality_checks(df)
        statistics_bd = transfer_logic.get_transfer_statistics()
        
        print(f"   - 調貨建議數量: {len(recommendations_bd)}")
        print(f"   - 總調貨件數: {statistics_bd.get('total_transfer_qty', 0)}")
        print(f"   - 質量檢查: {'通過' if quality_passed_bd else '失敗'}")
        
        # 顯示前3條調貨建議
        if recommendations_bd:
            print("\n   前3條調貨建議:")
            for i, rec in enumerate(recommendations_bd[:3]):
                print(f"   {i+1}. 從 {rec['Transfer Site']} 調貨 {rec['Transfer Qty']} 件到 {rec['Receive Site']} (商品: {rec['Article']})")
        
        # 4. 生成Excel文件
        print("\n4. 生成Excel文件...")
        excel_generator = ExcelGenerator()
        
        # 生成A+C模式Excel文件
        excel_path_ac = excel_generator.generate_excel_file(recommendations_ac, statistics_ac)
        print(f"   - A+C模式Excel文件: {excel_path_ac}")
        
        # 生成B+D模式Excel文件
        excel_path_bd = excel_generator.generate_excel_file(recommendations_bd, statistics_bd)
        print(f"   - B+D模式Excel文件: {excel_path_bd}")
        
        # 5. 比較不同模式的結果
        print("\n5. 比較不同模式的結果...")
        print(f"   - A+C模式調貨建議數量: {len(recommendations_ac)}")
        print(f"   - B+D模式調貨建議數量: {len(recommendations_bd)}")
        print(f"   - A+C模式總調貨件數: {statistics_ac.get('total_transfer_qty', 0)}")
        print(f"   - B+D模式總調貨件數: {statistics_bd.get('total_transfer_qty', 0)}")
        
        # 6. 統計分析
        print("\n6. 統計分析 (A+C模式)...")
        source_type_stats = statistics_ac.get('source_type_stats', {})
        dest_type_stats = statistics_ac.get('dest_type_stats', {})
        
        print("   - 轉出類型分析:")
        for source_type, stats in source_type_stats.items():
            print(f"     * {source_type}: {stats['count']} 條建議, {stats['qty']} 件")
        
        print("   - 接收類型分析:")
        for dest_type, stats in dest_type_stats.items():
            print(f"     * {dest_type}: {stats['count']} 條建議, {stats['qty']} 件")
        
        print("\n6. 統計分析 (B+D模式)...")
        source_type_stats = statistics_bd.get('source_type_stats', {})
        dest_type_stats = statistics_bd.get('dest_type_stats', {})
        
        print("   - 轉出類型分析:")
        for source_type, stats in source_type_stats.items():
            print(f"     * {source_type}: {stats['count']} 條建議, {stats['qty']} 件")
        
        print("   - 接收類型分析:")
        for dest_type, stats in dest_type_stats.items():
            print(f"     * {dest_type}: {stats['count']} 條建議, {stats['qty']} 件")
        
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