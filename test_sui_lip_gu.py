"""
使用SUI LIP GU.xlsx測試系統功能 v1.9
測試和改善A/B模式
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

def analyze_test_data(file_path: str):
    """
    分析測試數據的基本信息
    
    Args:
        file_path: Excel文件路徑
    """
    print("分析測試數據基本信息...")
    print("=" * 50)
    
    # 讀取Excel文件
    df = pd.read_excel(file_path)
    
    # 基本統計
    print(f"總行數: {len(df)}")
    print(f"商品數量: {df['Article'].nunique()}")
    print(f"OM數量: {df['OM'].nunique()}")
    print(f"店鋪數量: {df['Site'].nunique()}")
    print(f"RP Type分佈: {df['RP Type'].value_counts().to_dict()}")
    
    # 按OM分組統計
    print("\n按OM分組統計:")
    om_stats = df.groupby('OM').agg({
        'Site': 'count',
        'SaSa Net Stock': 'sum',
        'Safety Stock': 'sum',
        'Last Month Sold Qty': 'sum',
        'MTD Sold Qty': 'sum'
    }).rename(columns={'Site': '店鋪數量'})
    print(om_stats)
    
    # 按RP Type分組統計
    print("\n按RP Type分組統計:")
    rp_stats = df.groupby('RP Type').agg({
        'Site': 'count',
        'SaSa Net Stock': 'sum',
        'Safety Stock': 'sum',
        'Last Month Sold Qty': 'sum',
        'MTD Sold Qty': 'sum'
    }).rename(columns={'Site': '店鋪數量'})
    print(rp_stats)
    
    # 庫存不足的店鋪
    print("\n庫存不足的店鋪 (SaSa Net Stock < Safety Stock):")
    insufficient_stock = df[df['SaSa Net Stock'] < df['Safety Stock']]
    print(f"數量: {len(insufficient_stock)}")
    if not insufficient_stock.empty:
        print(insufficient_stock[['Site', 'OM', 'SaSa Net Stock', 'Safety Stock']].head(10))
    
    # 無庫存的店鋪
    print("\n無庫存的店鋪 (SaSa Net Stock = 0):")
    no_stock = df[df['SaSa Net Stock'] == 0]
    print(f"數量: {len(no_stock)}")
    if not no_stock.empty:
        print(no_stock[['Site', 'OM', 'SaSa Net Stock', 'Safety Stock']].head(10))
    
    print("=" * 50)
    return df

def test_with_sui_lip_gu(file_path: str):
    """
    使用SUI LIP GU.xlsx測試系統功能
    
    Args:
        file_path: Excel文件路徑
    """
    print("開始使用SUI LIP GU.xlsx測試系統功能...")
    print("=" * 50)
    
    try:
        # 分析測試數據
        df = analyze_test_data(file_path)
        
        # 1. 數據預處理
        print("\n1. 數據預處理...")
        processor = DataProcessor()
        processed_df, processing_stats = processor.preprocess_data(file_path)
        
        print(f"   - 原始數據行數: {processing_stats['original_stats']['total_rows']}")
        print(f"   - 處理後數據行數: {processing_stats['processed_stats']['total_rows']}")
        print(f"   - 商品數量: {processed_df['Article'].nunique()}")
        print(f"   - OM數量: {processed_df['OM'].nunique()}")
        print(f"   - 店鋪數量: {processed_df['Site'].nunique()}")
        print(f"   - RP Type分佈: {processed_df['RP Type'].value_counts().to_dict()}")
        
        # 顯示數據樣本
        print("\n   數據樣本:")
        print(processed_df.head(3).to_string())
        
        # 2. 測試A模式(保守轉貨)
        print("\n2. 測試A模式(保守轉貨)...")
        transfer_logic = TransferLogic()
        recommendations_a = transfer_logic.generate_transfer_recommendations(processed_df, "保守轉貨")
        quality_passed_a = transfer_logic.perform_quality_checks(processed_df)
        statistics_a = transfer_logic.get_transfer_statistics()
        
        print(f"   - 調貨建議數量: {len(recommendations_a)}")
        print(f"   - 總調貨件數: {statistics_a.get('total_transfer_qty', 0)}")
        print(f"   - 質量檢查: {'通過' if quality_passed_a else '失敗'}")
        
        # 顯示前5條調貨建議
        if recommendations_a:
            print("\n   前5條調貨建議:")
            for i, rec in enumerate(recommendations_a[:5]):
                print(f"   {i+1}. 從 {rec['Transfer Site']} 調貨 {rec['Transfer Qty']} 件到 {rec['Receive Site']} (商品: {rec['Article']}, 轉出類型: {rec.get('Source Type', '')})")
        
        # 3. 測試B模式(加強轉貨)
        print("\n3. 測試B模式(加強轉貨)...")
        transfer_logic = TransferLogic()
        recommendations_b = transfer_logic.generate_transfer_recommendations(processed_df, "加強轉貨")
        quality_passed_b = transfer_logic.perform_quality_checks(processed_df)
        statistics_b = transfer_logic.get_transfer_statistics()
        
        print(f"   - 調貨建議數量: {len(recommendations_b)}")
        print(f"   - 總調貨件數: {statistics_b.get('total_transfer_qty', 0)}")
        print(f"   - 質量檢查: {'通過' if quality_passed_b else '失敗'}")
        
        # 顯示前5條調貨建議
        if recommendations_b:
            print("\n   前5條調貨建議:")
            for i, rec in enumerate(recommendations_b[:5]):
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
        
        # 8. 分析庫存不足的店鋪
        print("\n8. 分析庫存不足的店鋪...")
        insufficient_stock = processed_df[processed_df['SaSa Net Stock'] < processed_df['Safety Stock']]
        print(f"   - 庫存不足的店鋪數量: {len(insufficient_stock)}")
        
        # 檢查這些店鋪是否在接收列表中
        receive_sites_a = set(rec['Receive Site'] for rec in recommendations_a)
        receive_sites_b = set(rec['Receive Site'] for rec in recommendations_b)
        
        insufficient_in_receive_a = insufficient_stock[insufficient_stock['Site'].isin(receive_sites_a)]
        insufficient_in_receive_b = insufficient_stock[insufficient_stock['Site'].isin(receive_sites_b)]
        
        print(f"   - A模式中庫存不足且接收的店鋪數量: {len(insufficient_in_receive_a)}")
        print(f"   - B模式中庫存不足且接收的店鋪數量: {len(insufficient_in_receive_b)}")
        
        if not insufficient_in_receive_a.empty:
            print("   - A模式中庫存不足且接收的店鋪:")
            print(insufficient_in_receive_a[['Site', 'OM', 'SaSa Net Stock', 'Safety Stock']].head())
        
        if not insufficient_in_receive_b.empty:
            print("   - B模式中庫存不足且接收的店鋪:")
            print(insufficient_in_receive_b[['Site', 'OM', 'SaSa Net Stock', 'Safety Stock']].head())
        
        # 9. 分析轉出店鋪
        print("\n9. 分析轉出店鋪...")
        transfer_sites_a = set(rec['Transfer Site'] for rec in recommendations_a)
        transfer_sites_b = set(rec['Transfer Site'] for rec in recommendations_b)
        
        print(f"   - A模式轉出店鋪數量: {len(transfer_sites_a)}")
        print(f"   - B模式轉出店鋪數量: {len(transfer_sites_b)}")
        
        # 檢查轉出店鋪的庫存情況
        transfer_stores_a = processed_df[processed_df['Site'].isin(transfer_sites_a)]
        transfer_stores_b = processed_df[processed_df['Site'].isin(transfer_sites_b)]
        
        print(f"   - A模式轉出店鋪平均庫存: {transfer_stores_a['SaSa Net Stock'].mean():.2f}")
        print(f"   - B模式轉出店鋪平均庫存: {transfer_stores_b['SaSa Net Stock'].mean():.2f}")
        
        # 10. 分析OM調撥情況
        print("\n10. 分析OM調撥情況...")
        om_transfers_a = {}
        om_transfers_b = {}
        
        for rec in recommendations_a:
            transfer_om = rec['Transfer OM']
            receive_om = rec['Receive OM']
            if transfer_om not in om_transfers_a:
                om_transfers_a[transfer_om] = {'out': 0, 'in': 0}
            if receive_om not in om_transfers_a:
                om_transfers_a[receive_om] = {'out': 0, 'in': 0}
            om_transfers_a[transfer_om]['out'] += rec['Transfer Qty']
            om_transfers_a[receive_om]['in'] += rec['Transfer Qty']
        
        for rec in recommendations_b:
            transfer_om = rec['Transfer OM']
            receive_om = rec['Receive OM']
            if transfer_om not in om_transfers_b:
                om_transfers_b[transfer_om] = {'out': 0, 'in': 0}
            if receive_om not in om_transfers_b:
                om_transfers_b[receive_om] = {'out': 0, 'in': 0}
            om_transfers_b[transfer_om]['out'] += rec['Transfer Qty']
            om_transfers_b[receive_om]['in'] += rec['Transfer Qty']
        
        print("   - A模式OM調撥情況:")
        for om, transfers in om_transfers_a.items():
            if transfers['out'] > 0 or transfers['in'] > 0:
                print(f"     * {om}: 轉出 {transfers['out']} 件, 接收 {transfers['in']} 件")
        
        print("   - B模式OM調撥情況:")
        for om, transfers in om_transfers_b.items():
            if transfers['out'] > 0 or transfers['in'] > 0:
                print(f"     * {om}: 轉出 {transfers['out']} 件, 接收 {transfers['in']} 件")
        
        print("\n" + "=" * 50)
        print("✅ SUI LIP GU.xlsx測試完成！系統運行正常。")
        
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
    success = test_with_sui_lip_gu(test_file)
    
    # 退出碼
    exit(0 if success else 1)