"""
使用 ftfy 庫徹底修復 app.py 中的所有UTF-8亂碼
"""

import ftfy

def fix_file_with_ftfy(filepath):
    """使用 ftfy 修復文件中的所有編碼問題"""
    
    print(f"正在使用 ftfy 修復文件: {filepath}")
    print("=" * 60)
    
    # 讀取文件
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        print(f"✓ 成功讀取文件 ({len(content)} 字元)")
    except Exception as e:
        print(f"✗ 讀取文件失敗: {e}")
        return False
    
    # 使用 ftfy 修復文本
    try:
        fixed_content = ftfy.fix_text(content)
        
        # 統計修改
        if fixed_content != content:
            changes = sum(1 for c1, c2 in zip(content, fixed_content) if c1 != c2)
            if changes > 0:
                print(f"✓ 修復了 {changes} 個字元")
            else:
                # 長度變化
                if len(fixed_content) != len(content):
                    print(f"✓ 文本長度變化: {len(content)} -> {len(fixed_content)}")
                else:
                    print("✓ 文本已完成修復")
        else:
            print("✓ 文件無需修復（已經是正確編碼）")
        
        # 寫回文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"✓ 成功寫入修復後的文件")
        
        return True
        
    except Exception as e:
        print(f"✗ 修復過程失敗: {e}")
        return False

if __name__ == "__main__":
    import os
    
    # 獲取當前腳本所在目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(script_dir, "app.py")
    
    if fix_file_with_ftfy(app_file):
        print("\n" + "=" * 60)
        print("✅ 修復完成！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ 修復失敗！")
        print("=" * 60)
