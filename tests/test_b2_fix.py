"""
測試 B2 模式修正：驗證接收店舖在同一SKU下不會同時作為轉出店舖
針對 Article 109249904001 的場景：HC25 不應同時是接收方和轉出方
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from business_logic import TransferLogic
from data_processor import DataProcessor

def test_b2_no_dual_role():
    """測試 B2 模式下同一 SKU 不會出現接收店同時做轉出"""
    
    logic = TransferLogic()
    
    # 讀取實際的檔案（使用相對路徑或環境變數）
    import os
    file_path = os.getenv('TEST_DATA_PATH', os.path.join(os.path.dirname(__file__), '..', 'data', 'PIP_JosephJoey_09Feb2026.XLSX'))
    
    if not os.path.exists(file_path):
        print(f"[WARN] 測試檔案不存在: {file_path}")
        print("改用模擬數據進行測試...")
        test_with_mock_data()
        return
    
    processor = DataProcessor()
    df, info = processor.preprocess_data(file_path)
    
    mode = "附加B(特別模式)"
    recommendations = logic.generate_transfer_recommendations(df, mode)
    
    # 檢查每個 Article 是否有店舖同時做轉出和接收
    from collections import defaultdict
    article_sources = defaultdict(set)
    article_dests = defaultdict(set)
    
    for rec in recommendations:
        article = rec['Article']
        article_sources[article].add(rec['Transfer Site'])
        article_dests[article].add(rec['Receive Site'])
    
    violations = []
    for article in article_sources:
        overlap = article_sources[article] & article_dests[article]
        if overlap:
            violations.append((article, overlap))
    
    if violations:
        print("[FAIL] 仍有衝突：")
        for article, sites in violations:
            print(f"  Article {article}: 衝突店舖 {sites}")
            for rec in recommendations:
                if rec['Article'] == article and (rec['Transfer Site'] in sites or rec['Receive Site'] in sites):
                    print(f"    {rec['Transfer Site']} -> {rec['Receive Site']} (Qty: {rec['Transfer Qty']}, "
                          f"Source: {rec['Source Type']}, Dest: {rec['Destination Type']})")
    else:
        print("[PASS] 所有 Article 中沒有店舖同時做轉出和接收")
    
    target_article = '109249904001'
    article_recs = [r for r in recommendations if r['Article'] == target_article]
    if article_recs:
        print(f"\n[INFO] Article {target_article} 的調貨建議：")
        for rec in article_recs:
            print(f"  {rec['Transfer Site']} ({rec['Source Type']}) -> "
                  f"{rec['Receive Site']} ({rec['Destination Type']}), Qty: {rec['Transfer Qty']}")
    
    print(f"\n[SUMMARY] 總計建議數: {len(recommendations)}")


def test_with_mock_data():
    """使用模擬數據測試 B2 模式"""
    
    logic = TransferLogic()
    
    # 模擬 HC25 同時符合 source (Local/Type=L) 和 destination (缺貨) 條件的場景
    data = {
        'Article': ['109249904001'] * 4,
        'OM': ['OM1'] * 4,
        'Site': ['HB25', 'HC25', 'HC63', 'HB10'],
        'RP Type': ['RF', 'RF', 'RF', 'RF'],
        'SaSa Net Stock': [5, 3, 0, 10],
        'Pending Received': [0, 0, 0, 0],
        'Safety Stock': [3, 5, 4, 5],
        'Last Month Sold Qty': [1, 1, 3, 5],
        'MTD Sold Qty': [0, 1, 2, 3],
        'MOQ': [1, 1, 1, 1],
        'Effective Sold Qty': [1, 2, 5, 8],
        'Article Description': ['Test Product'] * 4,
        'Type': ['L', 'L', 'R', 'R'],
    }
    df = pd.DataFrame(data)
    
    mode = "附加B(特別模式)"
    recommendations = logic.generate_transfer_recommendations(df, mode)
    
    # 檢查衝突
    sources_set = set(r['Transfer Site'] for r in recommendations)
    dests_set = set(r['Receive Site'] for r in recommendations)
    overlap = sources_set & dests_set
    
    if overlap:
        print(f"[FAIL] 模擬測試失敗：衝突店舖 {overlap}")
        for rec in recommendations:
            print(f"  {rec['Transfer Site']} ({rec['Source Type']}) -> "
                  f"{rec['Receive Site']} ({rec['Destination Type']}), Qty: {rec['Transfer Qty']}")
    else:
        print("[PASS] 模擬測試通過：沒有店舖同時做轉出和接收")
        for rec in recommendations:
            print(f"  {rec['Transfer Site']} ({rec['Source Type']}) -> "
                  f"{rec['Receive Site']} ({rec['Destination Type']}), Qty: {rec['Transfer Qty']}")


if __name__ == '__main__':
    test_b2_no_dual_role()
