"""
檢查所有模式下是否出現同一SKU的店舖同時做轉出與接收
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from business_logic import TransferLogic
from data_processor import DataProcessor

FILE_PATH = r"C:\Users\kf_yue\Dropbox\SASA\AI\Sep2025_App\KiLo Reallocation\PIP_JosephJoey_09Feb2026.XLSX"

MODES = [
    "保守轉貨",
    "加強轉貨",
    "附加B(特別模式)",
    "附加B2a(特別模式-T遊客鋪不出貨)",
    "附加B3(跨OM特別模式)",
    "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
    "重點補0",
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
    if not os.path.exists(FILE_PATH):
        print(f"❌ 找不到測試檔案: {FILE_PATH}")
        return

    processor = DataProcessor()
    df, info = processor.preprocess_data(FILE_PATH)

    any_violations = False
    for mode in MODES:
        violations, total = check_mode(df, mode)
        if violations:
            any_violations = True
            print(f"❌ 模式 [{mode}] 發現衝突 (建議數: {total})")
            for article, sites in violations[:10]:
                print(f"  Article {article}: 衝突店舖 {sorted(sites)}")
            if len(violations) > 10:
                print(f"  ... 另有 {len(violations) - 10} 筆衝突未顯示")
        else:
            print(f"✅ 模式 [{mode}] 無同源接收/出貨衝突 (建議數: {total})")

    if not any_violations:
        print("\n✅ 全部模式檢查完成，未發現同源接收/出貨問題")


if __name__ == "__main__":
    main()
