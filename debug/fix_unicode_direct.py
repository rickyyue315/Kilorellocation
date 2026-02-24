# -*- coding: utf-8 -*-
"""
使用直接字串替換修復亂碼
"""

def main():
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(script_dir, "app.py")
    
    print(f"正在修復文件: {app_file}")
    print("=" * 70)
    
    # 讀取文件
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_len = len(content)
    
    # 定義替換字典（使用直接的 Unicode 轉義）
    replacements = {
        # 系統 -> \u7cfb\u7d統71統
        '\u00e7\u00b3\u00bb\u00e7\u00b5\u00b1': '\u7cfb\u7d71',
        # 跨 -> \u8de8
        '\u00e8\u00b7\u00a8': '\u8de8',
        # 智能 -> \u667a\u80fd
        '\u00e6\u2122\u00ba\u00e8\u0192\u00bd': '\u667a\u80fd',
        # ： ->:
        '\u00ef\u00bc\u0161': '\uff1a',
        # 避免 -> \u907f\u514d
        '\u00e9\u00bf\u00e5\u2026\u00ab': '\u907f\u514d',
        # 標記商品強制 -> \u6a19\u8a18\u5546\u54c1\u5f37\u5236
        '\u00e6\u00a8\u2122\u00e8\u00a8\u2030\u00e5\u2022\u2020\u00e5\u201c\u0081\u00e5\u00bc\u00b7\u00e5\u0136\u00b6': '\u6a19\u8a18\u5546\u54c1\u5f37\u5236',
        # 接收端依遊客區 -> \u63a5\u6536\u7aef\u4f9d\u904a\u5ba2\u5340
        '\u00e6\u0160\u00a5\u00e6\u201c\u00b6\u00e7\u00ab\u00af\u00e4\u00be\u009d\u00e9\u0161\u00e5\u00ae\u00a2\u00e5\u20ac': '\u63a5\u6536\u7aef\u4f9d\u904a\u5ba2\u5340',
        # 說明 -> \u8aaa\u660e
        '\u00e8\u00aa\u00aa\u00e6\u02dc\u017e': '\u8aaa\u660e',
        # 了解各 -> \u4e86\u89e3\u5404
        '\u00e4\u00ba\u2020\u00e8\u00a7\u00a3\u00e5\u201c\u0192': '\u4e86\u89e3\u5404',
        # 特點 -> \u7279\u9ede
        '\u00e7\u2030\u00b9\u00e9\u00bb\u017e': '\u7279\u9ede',
        # ） ->\uff09
        '\u00ef\u00bc\u2030': '\uff09',
        # （ -> \uff08
        '\u00ef\u00bc\u02c6': '\uff08',
        # 特殊 -> \u7279\u6b8a
        '\u00e7\u2030\u00b9\u00e6\u00ae\u0160': '\u7279\u6b8a',
        # 的 -> \u7684
        '\u00e7\u009a\u201d': '\u7684',
        # 的 variant
        '\u00e7\u009a\u201c': '\u7684',
        # 只會處 -> \u53ea\u6703\u8655
        '\u00e5\u00aa\u0153\u00e6\u009c\u0192\u00e8\u2122': '\u53ea\u6703\u8655',
        # 僅 -> \u50c5
        '\u00e5\u0192': '\u50c5',
        # 可跨 -> \u53ef\u8de8
        '\u00e5\u00af\u00e8\u00b7\u00a8': '\u53ef\u8de8',
        # 補 -> \u88dc
        '\u00e8\u00a3\u0153': '\u88dc',
        # 顯示 -> \u986f\u793a
        '\u00e9\u00a1\u00af\u00e7\u00a4\u00ba': '\u986f\u793a',
        # 欄位 -> \u6b04\u4f4d
        '\u00e6\u00ac\u201d\u4f4d': '\u6b04\u4f4d',
        # 處理 -> \u8655\u7406
        '\u00e8\u2122\u00e7\u0020\u2020': '\u8655\u7406',
        # 必須 -> \u5fc5\u9808
        '\u00e5\u00bf\u2026\u00e9\u00a0\u2c6': '\u5fc5\u9808',
        # 臨時 -> \u81e8\u6642
        '\u00e8\u2021\u00a8\u00e6\u2122': '\u81e8\u6642',
        # 暫存 -> \u66ab\u5b58
        '\u00e6\u009a\u00ab\u00e5\u00ad\u2030': '\u66ab\u5b58',
        # 沒有 -> \u6c92\u6709
        '\u00e6\u00b2\u0019\u6709': '\u6c92\u6709',
        # 規則 -> \u898f\u5247
        '\u00e8\u00a6\u00e5\u2030': '\u898f\u5247',
        # 計算 -> \u8a08\u7b97
        '\u00e8\u00a8\u02c6\u7b97': '\u8a08\u7b97',
        # 讀取 -> \u8b80\u53d6
        '\u00e8\u00ae\u20ac\u00e5\u0160': '\u8b80\u53d6',
        # 清除 -> \u6e05\u9664
        '\u6e05\u00e2\u20ac ': '\u6e05\u9664',
        # 前 -> \u524d
        '\u00e5\u2030\u008d': '\u524d',
        # ； -> \uff1b
        '\u00ef\u00bc\u203a': '\uff1b',
    }
    
    # 應用替換
    fix_count = 0
    for wrong, correct in replacements.items():
        if wrong in content:
            count = content.count(wrong)
            content = content.replace(wrong, correct)
            fix_count += count
            # 顯示可打印的字符
            wrong_repr = wrong.encode('unicode-escape').decode('ascii')[:40]
            correct_repr = correct.encode('unicode-escape').decode('ascii')[:40]
            print(f"✓ 修復 {count} 處: {wrong_repr} -> {correct_repr}")
    
    # 寫回文件
    if fix_count > 0:
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("=" * 70)
        print(f"✅ 總共修復 {fix_count} 處亂碼！")
        print(f"文件長度: {original_len} -> {len(content)}")
        print("=" * 70)
    else:
        print("=" * 70)
        print("無需修復")
        print("=" * 70)

if __name__ == "__main__":
    main()
