#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive fix for app.py encoding corruption.
The file contains UTF-8 text that was misinterpreted as Latin-1/ISO-8859-1.
"""

def detect_and_fix():
    # Read the file in binary mode to inspect raw bytes
    with open('app.py', 'rb') as f:
        raw_bytes = f.read()
    
    # Since the file reads correctly as UTF-8, but displays corrupted characters,
    # these corrupted characters are actually in the file's content.
    # We need to identify the corruption pattern.
    
    # The pattern shows UTF-8 sequences that are valid but wrong.
    # Let's fix the known corrupted strings:
    
    fixes = [
        (b'\xc3\xb0\xc5\x9c', '📊'.encode('utf-8')),  # ðŸ"Š -> 📊
        (b'\xc3\xa8\xc2\xb3\xe2\x80\xa1\xc3\xa6\xe2\x80\x93\xe2\x84\xa2\xc3\xa9\xc2\xa0', '資料查覽'.encode('utf-8')),  # è³‡ -> 資
        (b'\xc3\xa7\xc2\xb8\xc2\xbd\xc3\xa8\xc2\xa1\xc5\x93\xc3\xa6\xe2\x80\xa2\xc3\xb1', '總行數'.encode('utf-8')),  # ç¸½è¡Œæ•¸
        (b'\xc3\xa5\xe2\x80\xa2\xe2\x80\xa0\xc3\xa5\xc2\xb3\xc3\xa6\xe2\x80\xa2\xc3\xb1', '商品數'.encode('utf-8')),  # å•†å"æ•¸
        (b'\xc3\xa5\xc2\xba\xe2\x80\x9c\xc3\xa9\xe2\x80\xb9\xc2\xaaæ•¸', '店鋪數'.encode('utf-8')),  # åº—é‹ªæ•¸
    ]
    
    fixed_bytes = raw_bytes
    for corrupted, correct in fixes:
        fixed_bytes = fixed_bytes.replace(corrupted, correct)
    
    # Write back
    with open('app.py', 'wb') as f:
        f.write(fixed_bytes)
    
    print("File fixed with binary replacements")

def fix_with_text():
    """Alternative: load, fix as text, and save"""
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Build a comprehensive mapping of known corrupted terms
    replacements = {
        'ðŸ"Š': '📊',  # Chart emoji
        'è³‡æ–™é è¦½': '資料查覽',  # Data preview
        'ç¸½è¡Œæ•¸': '總行數',  # Total rows
        'å•†å"æ•¸': '商品數',  # Total articles  
        'åº—é‹ªæ•¸': '店鋪數',  # Total stores
        'æ–‡ä»¶ä¸Šå‚³èˆ‡æ•¸æ"š': '檔案上傳與數據',  # File upload
        'è³‡æ–™æ¨£æœ¬': '資料樣本',  # Data sample
        'åˆ†æžæŒ‰éˆ•å€': '分析按鈕區',  # Analysis button area
    }
    
    fixed = content
    for corrupted, correct in replacements.items():
        fixed = fixed.replace(corrupted, correct)
        print(f"Replaced: {corrupted[:20]}... -> {correct}")
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(fixed)
    
    print("\nFile fixed successfully with text replacements")

if __name__ == '__main__':
    fix_with_text()
