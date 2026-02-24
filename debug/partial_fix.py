#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive encoding fix for app.py
The file contains UTF-8 text but with corrupted Chinese characters
This script identifies and fixes all corrupted strings
"""

import re

def fix_corrupted_file():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # These are known UTF-8 sequences that got corrupted
    # Pattern: when UTF-8 bytes are misinterpreted
    
    # Common corrupted patterns and their corrections
    corruption_fixes = []
    
    # Scan for lines with problematic characters
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        fixed_line = line
        
        # Fix markdown lines with corrupted emojis and text
        if 'st.markdown' in line and ('#' in line or '**' in line):
            # Check if line contains extended ASCII characters that suggest corruption
            if any(ord(c) > 127 for c in line):
                # Try to identify and fix specific patterns
                
                # Pattern 1: Dashboard header line 503
                if '資料查覽' in line or ('è' in line and '‡' in line and '™' in line):
                    if 'ðŸ"Š' in line or 'ðŸ' in line:
                        fixed_line = line.replace('ðŸ"Š', '📊')
                        if 'è³‡æ–™é è¦½' in fixed_line:
                            fixed_line = fixed_line.replace('è³‡æ–™é è¦½', '資料查覽')
                
                # Pattern 2: Report header  
                if 'èª¿è²¨' in line or ('調' in line or '建' in line):
                    if 'ðŸ"‹' in line:
                        fixed_line = fixed_line.replace('ðŸ"‹', '📋')
                    if 'èª¿è²¨å»ºè­°' in line:
                        fixed_line = fixed_line.replace('èª¿è²¨å»ºè­°', '調貨建議')
                        
                # Pattern 3: Other markdown patterns
                fixed_line = fixed_line.replace('ðŸš€', '🚀')
                fixed_line = fixed_line.replace('å¼·åˆ¶', '強制')
                fixed_line = fixed_line.replace('è½‰å‡º', '轉出')
        
        # Fix other string literals
        if 'st.' in line and '"' in line:
            # Try to fix any remaining corruption
            # Replacement dictionary for common corrupted sequences
            replacements = {
                'ç•¶å‰': '當前',
                'æ¨¡å¼': '模式',
                'è²¡å¿°': '財務',  
                'éžç¾æ¬¾': '非現款',
                'è²¨ç‰©': '貨物',
            }
            
            for corrupted, correct in replacements.items():
                if corrupted in fixed_line:
                    fixed_line = fixed_line.replace(corrupted, correct)
        
        fixed_lines.append(fixed_line)
    
    fixed_content = '\n'.join(fixed_lines)
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("Partial fix applied")
    print("\nNow checking syntax...")
    
    import ast
    try:
        ast.parse(fixed_content)
        print("✓ Syntax is valid!")
        return True
    except SyntaxError as e:
        print(f"✗ Error at line {e.lineno}: {e.msg}")
        if e.text:
            print(f"  {e.text[:60]}")
        return False

if __name__ == '__main__':
    fix_corrupted_file()
