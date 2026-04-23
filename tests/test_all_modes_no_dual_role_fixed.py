"""
æª¢æŸ¥æ‰€æœ‰æ¨¡å¼ä¸‹æ˜¯å¦å‡ºç¾åŒä¸€SKUçš„åº—èˆ–åŒæ™‚åšè½‰å‡ºèˆ‡æŽ¥æ”¶
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from business_logic import TransferLogic
from data_processor import DataProcessor

FILE_PATH = r"C:\Users\kf_yue\Dropbox\SASA\AI\Sep2025_App\KiLo Reallocation\PIP_JosephJoey_09Feb2026.XLSX"

MODES = [
    "ä¿å®ˆè½‰è²¨",
    "åŠ å¼·è½‰è²¨",
    "é™„åŠ B(ç‰¹åˆ¥æ¨¡å¼)",
    "é™„åŠ B2a(ç‰¹åˆ¥æ¨¡å¼-TéŠå®¢é‹ªä¸å‡ºè²¨)",
    "é™„åŠ B3(è·¨OMç‰¹åˆ¥æ¨¡å¼)",
    "é™„åŠ B3a(è·¨OMç‰¹åˆ¥æ¨¡å¼-TéŠå®¢é‹ªä¸å‡ºè²¨)",
    "é‡é»žè£œ0",
    "é‡é»žè£œ0-åªè£œ0/1",
    "æ¸…è²¨è½‰è²¨",
    "æ¸…è²¨è½‰è²¨(NDé™å®š)",
    "å¼·åˆ¶è½‰å‡º",
    "ç›®æ¨™å„ªåŒ–",
    "FæŒ‡å®šæ¨¡å¼",
]


def check_mode(df, mode):
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, mode)

    article_sources = defaultdict(set)
    article_dests = defaultdict(set)

    for rec in recommendations:
]
]
]

]
    for article in article_sources:
]
        if overlap:
            violations.append((article, overlap))

    return violations, len(recommendations)


def main():
    if not os.path.exists(FILE_PATH):
        print(f"âŒ æ‰¾ä¸åˆ°æ¸¬è©¦æª”æ¡ˆ: {FILE_PATH}")
        return

    processor = DataProcessor()
    df, info = processor.preprocess_data(FILE_PATH)

    any_violations = False
    for mode in MODES:
        violations, total = check_mode(df, mode)
        if violations:
            any_violations = True
]
]
                print(f"  Article {article}: è¡çªåº—èˆ– {sorted(sites)}")
            if len(violations) > 10:
                print(f"  ... å¦æœ‰ {len(violations) - 10} ç­†è¡çªæœªé¡¯ç¤º")
        else:
]

    if not any_violations:
        print("\nâœ… å…¨éƒ¨æ¨¡å¼æª¢æŸ¥å®Œæˆï¼Œæœªç™¼ç¾åŒæºæŽ¥æ”¶/å‡ºè²¨å•é¡Œ")


if __name__ == "__main__":
    main()
