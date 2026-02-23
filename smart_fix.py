#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive fix for app.py encoding issues
Uses byte-level replacement to avoid syntax errors in the fix script
"""

def fix_app_py():
    print("Reading app.py...")
    with open('app.py', 'rb') as f:
        content_bytes = f.read()
    
    # Define byte-level replacements (corrupted -> correct)
    # These use the actual UTF-8 byte sequences
    replacements_bytes = [
        # Total rows: ç¸½è¡Œæ•¸ -> 總行數
        (b'c\xc2\xa7\xc2\xbd\xc3\xa8\xc2\xa1\xc5\x93\xc3\xa6\xe2\x80\xa2\xc3\xb1', '總行數'.encode('utf-8')),
    ]
    
    # Alternative: read as UTF-8 and build string replacements from bytes
    content = content_bytes.decode('utf-8')
    
    # Count occurrences of problem strings
    problem_indicators = [
        'ç¸½è¡Œæ•¸',  # This will cause Python parser to fail, but checking the actual bytes
        'å•†å"æ•¸',
        'åº—é‹ªæ•¸',
    ]
    
    fixes_made = 0
    
    # Try fixing patterns that we know exist
    # Instead of hardcoding corrupted strings, let's detect and fix them
    
    # Method: Look for specific patterns in the lines
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines, 1):
        # Check for lines with the known problematic structure
        if 'st.metric' in line:
            # This is a metrics line that has corrupted Chinese
            # Try to fix common patterns
            
            # Pattern: å•†å"æ•¸ appears in article count line
            if 'Article' in line and 'nunique' in line:
                if 'å•†' in line:  # Check for corrupted character
                    line = line.replace('å•†å"æ•¸', '商品數')
                    fixes_made += 1
                    print(f"Fixed line {i}: Article count")
            
            # Pattern: ç¸½è¡Œæ•¸ appears in total rows line  
            if 'total_rows' in line:
                if 'ç¸' in line:  # Check for corrupted character
                    line = line.replace('ç¸½è¡Œæ•¸', '總行數')
                    fixes_made += 1
                    print(f"Fixed line {i}: Total rows")
            
            # Pattern: åº—é‹ªæ•¸ appears in store count line
            if 'Site' in line and 'nunique' in line:
                if 'åº' in line:  # Check for corrupted character
                    line = line.replace('åº—é‹ªæ•¸', '店鋪數')
                    fixes_made += 1
                    print(f"Fixed line {i}: Store count")
        
        # Fix markdown lines
        if 'st.markdown' in line:
            if 'ðŸ' in line:  # Check for corrupted emoji
                # Fix the dashboard header
                if 'è³‡æ–™é è¦½' in line:
                    line = line.replace('st.markdown("### ðŸ"Š è³‡æ–™é è¦½")', 'st.markdown("### 📊 資料查覽")')
                    fixes_made += 1
                    print(f"Fixed line {i}: Dashboard header")
                # Fix other markdown headers 
                elif 'åˆ†æž' in line:
                    line = line.replace('ðŸš€', '🚀')
                    line = line.replace('åˆ†æžèˆ‡å»ºè­°', '分析與建議')
                    fixes_made += 1
                    print(f"Fixed line {i}: Analysis header")
        
        fixed_lines.append(line)
    
    fixed_content = '\n'.join(fixed_lines)
    
    print(f"\nWriting fixed content ({fixes_made} fixes applied)...")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("Done! Verifying syntax...")
    import ast
    try:
        ast.parse(fixed_content)
        print("✓ Syntax is now valid!")
        return True
    except SyntaxError as e:
        print(f"✗ Syntax error at line {e.lineno}: {e.msg}")
        return False

if __name__ == '__main__':
    fix_app_py()
