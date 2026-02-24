# -*- coding: utf-8 -*-
"""
測試 D 模式：清貨轉貨
驗證 ND 店鋪無銷售記錄時的清貨邏輯，以及避免 1 件餘貨的功能
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from business_logic import TransferLogic

def test_mode_d_clearance():
    """
    測試 D 模式的清貨轉貨邏輯
    """
    print("=" * 60)
    print("測試 D 模式：清貨轉貨")
    print("=" * 60)
    
    # 創建測試數據
    test_data = [
        # Article 1: 有 ND 店鋪無銷售記錄，需要清貨
        {
            'Article': '123456789012',
            'Article Description': '測試商品 1',
            'OM': 'OM1',
            'Site': 'ND_SITE_1',
            'RP Type': 'ND',
            'SaSa Net Stock': 5,  # 有 5 件庫存
            'Pending Received': 0,
            'Safety Stock': 2,
            'MOQ': 1,
            'Effective Sold Qty': 0,  # 無有效銷量
            'Last Month Sold Qty': 0,  # 上月銷量為 0
            'MTD Sold Qty': 0,  # MTD 銷量為 0
        },
        # Article 1: 有 RF 店鋪需要補貨
        {
            'Article': '123456789012',
            'Article Description': '測試商品 1',
            'OM': 'OM1',
            'Site': 'RF_SITE_1',
            'RP Type': 'RF',
            'SaSa Net Stock': 0,  # 無庫存
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Effective Sold Qty': 5,  # 有銷售記錄
            'Last Month Sold Qty': 3,
            'MTD Sold Qty': 2,
        },
        # Article 2: ND 店鋪有 3 件庫存，無銷售記錄
        {
            'Article': '234567890123',
            'Article Description': '測試商品 2',
            'OM': 'OM1',
            'Site': 'ND_SITE_2',
            'RP Type': 'ND',
            'SaSa Net Stock': 3,  # 有 3 件庫存
            'Pending Received': 0,
            'Safety Stock': 2,
            'MOQ': 1,
            'Effective Sold Qty': 0,  # 無有效銷量
            'Last Month Sold Qty': 0,  # 上月銷量為 0
            'MTD Sold Qty': 0,  # MTD 銷量為 0
        },
        # Article 2: RF 店鋪需要補貨
        {
            'Article': '234567890123',
            'Article Description': '測試商品 2',
            'OM': 'OM1',
            'Site': 'RF_SITE_2',
            'RP Type': 'RF',
            'SaSa Net Stock': 1,  # 只有 1 件
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Effective Sold Qty': 4,  # 有銷售記錄
            'Last Month Sold Qty': 2,
            'MTD Sold Qty': 2,
        },
        # Article 3: ND 店鋪有 1 件庫存，無銷售記錄
        {
            'Article': '345678901234',
            'Article Description': '測試商品 3',
            'OM': 'OM1',
            'Site': 'ND_SITE_3',
            'RP Type': 'ND',
            'SaSa Net Stock': 1,  # 只有 1 件
            'Pending Received': 0,
            'Safety Stock': 2,
            'MOQ': 1,
            'Effective Sold Qty': 0,  # 無有效銷量
            'Last Month Sold Qty': 0,  # 上月銷量為 0
            'MTD Sold Qty': 0,  # MTD 銷量為 0
        },
        # Article 3: RF 店鋪需要補貨
        {
            'Article': '345678901234',
            'Article Description': '測試商品 3',
            'OM': 'OM1',
            'Site': 'RF_SITE_3',
            'RP Type': 'RF',
            'SaSa Net Stock': 0,  # 無庫存
            'Pending Received': 0,
            'Safety Stock': 2,
            'MOQ': 1,
            'Effective Sold Qty': 3,  # 有銷售記錄
            'Last Month Sold Qty': 1,
            'MTD Sold Qty': 2,
        },
    ]
    
    df = pd.DataFrame(test_data)
    
    # 創建 TransferLogic 實例
    logic = TransferLogic()
    
    # 測試 D 模式
    print("\n1. 測試 D 模式：清貨轉貨")
    print("-" * 60)
    
    try:
        recommendations = logic.generate_transfer_recommendations(df, logic.mode_d)
        
        print(f"✓ 成功生成 {len(recommendations)} 條調貨建議\n")
        
        # 分析結果
        for i, rec in enumerate(recommendations, 1):
            print(f"建議 {i}:")
            print(f"  商品: {rec['Article']}")
            print(f"  轉出店鋪: {rec['Transfer Site']} (類型: {rec['Source Type']})")
            print(f"  接收店鋪: {rec['Receive Site']} (類型: {rec['Destination Type']})")
            print(f"  轉移數量: {rec['Transfer Qty']} 件")
            print(f"  原始庫存: {rec['Original Stock']} 件")
            print(f"  轉出後庫存: {rec['After Transfer Stock']} 件")
            
            # 檢查是否為 ND清貨轉出
            if rec['Source Type'] == 'ND清貨轉出':
                print(f"  ✓ 符合 D 模式：ND清貨轉出")
                
                # 檢查是否避免了 1 件餘貨
                if rec['After Transfer Stock'] == 1:
                    print(f"  ✗ 警告：轉出後剩餘 1 件，未成功避免 1 件餘貨！")
                else:
                    print(f"  ✓ 成功避免 1 件餘貨：轉出後剩餘 {rec['After Transfer Stock']} 件")
            
            print()
        
        # 統計分析
        print("=" * 60)
        print("統計分析")
        print("=" * 60)
        
        # 統計 ND清貨轉出的數量
        nd_clearance_count = sum(1 for rec in recommendations if rec['Source Type'] == 'ND清貨轉出')
        print(f"ND清貨轉出建議數量: {nd_clearance_count}")
        
        # 檢查是否有 1 件餘貨的情況
        one_piece_remaining = [rec for rec in recommendations 
                           if rec['Source Type'] == 'ND清貨轉出' and rec['After Transfer Stock'] == 1]
        if one_piece_remaining:
            print(f"✗ 發現 {len(one_piece_remaining)} 個 ND清貨轉出後剩餘 1 件的情況")
        else:
            print("✓ 所有 ND清貨轉出都成功避免了 1 件餘貨")
        
        # 執行質量檢查
        print("\n執行質量檢查...")
        quality_passed = logic.perform_quality_checks(df)
        
        if quality_passed:
            print("✓ 質量檢查通過")
        else:
            print("✗ 質量檢查失敗")
            for error in logic.quality_errors:
                print(f"  - {error}")
        
        # 獲取統計信息
        stats = logic.get_transfer_statistics()
        print("\n統計信息:")
        print(f"  總調貨建議數量: {stats['total_recommendations']}")
        print(f"  總調貨件數: {stats['total_transfer_qty']}")
        print(f"  涉及產品數量: {stats['unique_articles']}")
        print(f"  涉及OM數量: {stats['unique_oms']}")
        
        print("\n轉出類型分析:")
        for source_type, type_stats in stats['source_type_stats'].items():
            print(f"  {source_type}: {type_stats['count']} 條, {type_stats['qty']} 件")
        
        print("\n接收類型分析:")
        for dest_type, type_stats in stats['dest_type_stats'].items():
            print(f"  {dest_type}: {type_stats['count']} 條, {type_stats['qty']} 件")
        
    except Exception as e:
        print(f"✗ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)

if __name__ == "__main__":
    test_mode_d_clearance()
