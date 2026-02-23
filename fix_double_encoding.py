# -*- coding: utf-8 -*-
"""
強力修復 app.py 中的UTF-8雙重編碼問題
"""

def fix_double_encoding(text):
    """修復UTF-8雙重編碼問題"""
    try:
        # 嘗試將文本當作 latin-1 編碼，然後解碼為 UTF-8
        # 這能修復常見的UTF-8雙重編碼問題
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        # 如果失敗，返回原文本
        return text

def process_file(filepath):
    """處理文件"""
    print(f"正在處理文件: {filepath}")
    print("=" * 70)
    
    # 讀取文件
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"已讀取 {len(lines)} 行")
    except Exception as e:
        print(f"讀取失敗: {e}")
        return False
    
    # 處理每一行
    fixed_lines = []
    fix_count = 0
    
    for i, line in enumerate(lines, 1):
        fixed_line = fix_double_encoding(line)
        if fixed_line != line:
            fix_count += 1
            # 顯示前10個修改
            if fix_count <= 10:
                print(f"第 {i} 行:")
                print(f"  原文: {line.strip()[:80]}")
                print(f"  修正: {fixed_line.strip()[:80]}")
        fixed_lines.append(fixed_line)
    
    if fix_count > 10:
        print(f"... 還有 {fix_count - 10} 行被修改（未顯示）")
    
    print(f"\n總共修復 {fix_count} 行")
    
    # 寫回文件
    if fix_count > 0:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(fixed_lines)
            print(f"已成功寫入文件")
            return True
        except Exception as e:
            print(f"寫入失敗: {e}")
            return False
    else:
        print("無需修復")
        return True

if __name__ == "__main__":
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(script_dir, "app.py")
    
    if process_file(app_file):
        print("\n" + "=" * 70)
        print("✅ 修復完成！")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ 修復失敗！")
        print("=" * 70)
