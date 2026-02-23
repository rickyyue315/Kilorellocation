#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fix all corrupted UTF-8 sequences in app.py using direct replacements
"""

def fix_file():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Use list of tuples with raw hex to avoid syntax errors in this script
    # Format: (corrupted_pattern, correct_replacement)
    replacements = [
        # Pattern 1: ç¸½è¡Œæ•¸ -> 總行數
        ("ç¸½è¡Œæ•¸", "總行數"),
        # Pattern 2: å•†å"æ•¸ -> 商品數  
        ("å•†å"æ•¸", "商品數"),
        # Pattern 3: åº—é‹ªæ•¸ -> 店鋪數
        ("åº—é‹ªæ•¸", "店鋪數"),
        # Pattern 4: è³‡æ–™æ¨£æœ¬ -> 資料樣本
        ("è³‡æ–™æ¨£æœ¬", "資料樣本"),
        # Pattern 5: The dashboard/analysis section header
        ('st.markdown("### ðŸ"Š è³‡æ–™é è¦½")', 'st.markdown("### 📊 資料查覽")'),
    ]
    
    fixed_content = content
    count = 0
    for corrupted, correct in replacements:
        if corrupted in fixed_content:
            fixed_content = fixed_content.replace(corrupted, correct)
            count += 1
            print(f"Fixed: '{corrupted}' -> '{correct}'")
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"\nTotal replacements: {count}")

if __name__ == '__main__':
    fix_file()
