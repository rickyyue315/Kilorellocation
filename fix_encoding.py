#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fix encoding issues in app.py by detecting and correcting corrupted UTF-8 sequences
"""

def fix_file():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # The corrupted sequences that need fixing
    # These are UTF-8 sequences that got misinterpreted
    fixes = [
        ('ðŸ"Š', '📊'),  # Emoji for chart/data
        ('è³‡æ–™é è¦½', '資料查覽'),  # "Data Preview"
        ('æ–‡ä»¶ä¸Šå‚³èˆ‡æ•¸æ"š', '檔案上傳與數據'),  # File upload and data
        ('4.2. è³‡æ–™é è¦½å€å¡Š', '4.2. 資料查覽模塊'),  # Data preview module
    ]
    
    fixed_content = content
    for corrupted, correct in fixes:
        fixed_content = fixed_content.replace(corrupted, correct)
    
    # Write back with explicit UTF-8 encoding
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("File fixed successfully")
    print(f"Replacements made: {len(fixes)}")

if __name__ == '__main__':
    try:
        fix_file()
    except Exception as e:
        print(f"Error: {e}")
