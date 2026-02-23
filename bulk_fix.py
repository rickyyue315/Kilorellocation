#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Aggressive fix: Replace all known corrupted UTF-8 sequences
This reads the file as text and applies systematic replacements
"""

import re

def main():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Dictionary of corrupted patterns to their correct versions
    # Based on manual inspection of the file
    patterns = [
        # Corrupted markdown/UI elements
        ('ðŸ"Š è³‡æ–™é è¦½', '📊 資料查覽'),
        ('ðŸ"‹ èª¿è²¨å»ºè­°æ¸…å–®', '📋 調貨建議清單'),
        ('ðŸ"Š è©³ç´°', '📊 詳細'),  # For statistics  
        ('åˆ†æžæŒ‰éˆ•', '分析按鈕'),
        ('ðŸš€', '🚀'),
        
        # Common Chinese corruptions
        ('ç•¶å‰', '當前'),
        ('æ¨¡å¼', '模式'),
        ('æ€»', '總'),
        ('ç¨™', '線'),
        ('ä¼°', '估'),
        ('ç®—', '算'),
        ('è½‰', '轉'),
        ('è¨‚', '訂'),
        ('è²¡', '貨'),
        ('ç‰©', '物'),
        ('é‹ª', '幫'),
        ('æ‰¿', '承'),
        ('èª¿', '調'),
        ('è²¨', '貨'),
        ('å»ºè­°', '建議'),
        ('ç¤ºæ•¸', '示數'),
        ('æ¸…å–®', '清單'),
        
        # Markdown special cases
        ('st.markdown("**è³‡æ–™æ¨£æœ¬', 'st.markdown("**資料樣本'),
        ('st.success("æ–‡ä»¶ä¸Šå‚³', 'st.success("檔案上傳'),
        ('èš²å‰ 10 è¡Œ', '前 10 行'),
        
        # Comments  
        ('# æ¸…ç', '# 清'),
        ('# è', '# 資'),
        ('# åˆ†', '# 分'),
    ]
    
    fixed_content = content
    fixes_count = 0
    
    for corrupted, correct in patterns:
        if corrupted in fixed_content:
            fixed_content = fixed_content.replace(corrupted, correct)
            fixes_count += 1
            print(f"✓ Fixed: '{corrupted}' -> '{correct}'")
    
    # Write back
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"\nApplied {fixes_count} fixes")
    
    # Verify syntax
    import ast
    try:
        ast.parse(fixed_content)
        print("✓ Syntax check PASSED!")
        return True
    except SyntaxError as e:
        print(f"✗ Syntax error at line {e.lineno}: {e.msg}")
        if e.text:
            print(f"  Text: {e.text[:80]}")
        return False

if __name__ == '__main__':
    main()
