#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fix all corrupted UTF-8 sequences in app.py
These appear to be UTF-8 byte sequences that are still valid UTF-8 but decode incorrectly.
"""

# Mapping of corrupted strings to their correct forms
CORRUPTION_MAP = {
    # From our analysis
    "ç¸½è¡Œæ•¸": "總行數",
    "å•†å"æ•¸": "商品數", 
    "åº—é‹ªæ•¸": "店鋪數",
    "è³‡æ–™æ¨£æœ¬": "資料樣本",
    "è¡Œï¼‰": "行）",
    "åˆ†æžæŒ‰éˆ•å€å¡Š": "分析按鈕區",
    "ðŸš€": "🚀",
    "åˆ†æžèˆ‡å»ºè­°": "分析與建議",
    "ç•¶å‰æ¨¡å¼ï¼š": "當前模式：",
    "ç¾æ¬¾è³‡æ–™äž¥åŽè²¨ï¼š": "現款資料嚴肅貨：",
    "ä¼°ç®—è½‰è¨‚æ•¸": "估算轉訂數",
    "ä¼°ç®—æ¸…è²¨è½‰è¨‚æ•¸": "估算清貨轉訂數",
    "è·‰è¡Œè½‰è¨‚": "履行轉訂",
    "å©³æœé…½ç§'æ•"": "女性商品優化",  
    # Common patterns
    'st.markdown("### ðŸ"Š è³‡æ–™é è¦½")': 'st.markdown("### 📊 資料查覽")',
}

def fix_file():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    fixed_content = content
    replacements_made = 0
    
    for corrupted, correct in CORRUPTION_MAP.items():
        if corrupted in fixed_content:
            fixed_content = fixed_content.replace(corrupted, correct)
            replacements_made += 1
            print(f"Fixed: '{corrupted[:20]}...' -> '{correct[:20]}...'")
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"\nTotal replacements: {replacements_made}")
    return replacements_made > 0

if __name__ == '__main__':
    success = fix_file()
    print("\nVerifying syntax...")
    import ast
    with open('app.py', 'r', encoding='utf-8') as f:
        code = f.read()
    try:
        ast.parse(code)
        print("✓ Syntax is now valid!")
    except SyntaxError as e:
        print(f"✗ Still has errors at line {e.lineno}: {e.msg}")
