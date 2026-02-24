#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修復 app.py 的編碼問題
使用 ftfy 修復被錯誤解碼的 UTF-8 字符
"""

import ftfy

def fix_app_encoding():
    # 讀取原始檔案
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用 ftfy 修復編碼問題
    fixed_content = ftfy.fix_text(content)
    
    # 寫回檔案
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    # 輸出結果到檔案以便檢查
    with open('fix_result.txt', 'w', encoding='utf-8') as f:
        f.write("=== 修復前 100 字符 ===\n")
        f.write(repr(content[:100]))
        f.write("\n\n=== 修復後 100 字符 ===\n")
        f.write(repr(fixed_content[:100]))
        f.write("\n\n=== 修復後前 500 字符 ===\n")
        f.write(fixed_content[:500])
    
    print("修復完成！請查看 fix_result.txt 確認結果")

if __name__ == '__main__':
    fix_app_encoding()
