"""
簡化版測試腳本：檢查所有模式下是否出現同源店舖同時接收和轉出的情況
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from business_logic import TransferLogic
from data_processor import DataProcessor

# 使用相對路徑或默認測試數據
FILE_PATH = "PIP_JosephJoey_09Feb2026.XLSX"

if not os.path.exists(FILE_PATH):
    print(f"警告: 找不到測試檔案: {FILE_PATH}")
    print("使用模擬數據進行測試...")
    
    # 創建模擬數據
    import pandas as pd
    
    # 模擬一些可能導致同源問題的數據
    data = {
        'Article': ['109249904001'] * 6 + ['109249904002'] * 6,
        'OM': ['OM1'] * 6 + ['OM2'] * 6,
        'Site': ['HB25', 'HC25', 'HC63', 'HB10', 'HA02', 'HA06'] +
                ['HB25', 'HC25', 'HC63', 'HB10', 'HA02', 'HA06'],
        'RP Type': ['RF', 'RF', 'RF', 'RF', 'ND', 'RF'],
        'SaSa Net Stock': [5, 3, 0, 10, 8, 2],
        'Pending Received': [0, 0, 0, 0, 0, 0],
        'Safety Stock': [3, 5, 4, 5, 2, 3],
        'Last Month Sold Qty': [1, 1, 3, 5, 2, 1],
        'MTD Sold Qty': [0, 1, 2, 3, 1, 0],
        'MOQ': [1, 1, 1, 1, 1, 1],
        'Article Description': ['Test Product A'] * 6 + ['Test Product B'] * 6,
        'Type': ['L', 'L', 'R', 'R', 'M', 'T'],  # 用於B2/B3模式
    }
    df = pd.DataFrame(data)
else:
    processor = DataProcessor()
    df, info = processor.preprocess_data(FILE_PATH)

MODES = [
    "保守轉貨",
    "加強轉貨", 
    "附加B(特別模式)",
    "附加B3(跨OM特別模式)",
    "重點補0",
    "附加C2(跨OM重點補0)",
    "清貨轉貨",
    "強制轉出",
    "目標優化",
]

def check_mode(df, mode):
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, mode)

    article_sources = defaultdict(set)
    article_dests = defaultdict(set)

    for rec in recommendations:
        article = rec["Article"]
        article_sources[article].add(rec["Transfer Site"])
        article_dests[article].add(rec["Receive Site"])

    violations = []
    for article in article_sources:
        overlap = article_sources[article] & article_dests[article]
        if overlap:
            violations.append((article, overlap))

    return violations, len(recommendations)

def main():
    any_violations = False
    for mode in MODES:
        violations, total = check_mode(df, mode)
        if violations:
            any_violations = True
            print(f"模式 [{mode}] 發現衝突 (建議數: {total})")
            for article, sites in violations[:10]:
                print(f"  Article {article}: 衝突店舖 {sorted(sites)}")
            if len(violations) > 10:
                print(f"  ... 另有 {len(violations) - 10} 筆衝突未顯示")
        else:
            print(f"模式 [{mode}] 無同源接收/出貨衝突 (建議數: {total})")

    if not any_violations:
        print("\n全部模式檢查完成，未發現同源接收/出貨問題")

if __name__ == "__main__":
    main()