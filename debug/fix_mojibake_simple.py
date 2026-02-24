# -*- coding: utf-8 -*-
"""
使用原始字符串替換修復亂碼
"""

import re

def main():
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(script_dir, "app.py")
    
    print(f"正在修復文件: {app_file}")
    print("=" * 70)
    
    # 以二進制方式讀取
    with open(app_file, 'rb') as f:
        content_bytes = f.read()
    
    # 轉換為文本
    content = content_bytes.decode('utf-8', errors='replace')
    original_content = content
    
    # 使用直接的亂碼字符串替換（從文件中複製的真實亂碼）
    # 這些是從 grep 結果中看到的實際亂碼
    replacements = [
        ('ç³»çµ±', '系統'),
        ('è·¨', '跨'),
        ('æ™ºèƒ½', '智能'),
        ('ï¼š', '：'),
        ('é¿å…', '避免'),
        ('æ¨™è¨˜å•†å"å¼·åˆ¶', '標記商品強制'),
        ('æŽ¥æ"¶ç«¯ä¾éŠå®¢å€', '接收端依遊客區'),
        ('éŠå®¢å€', '遊客區'),
        ('èªªæ˜Ž', '說明'),
        ('äº†è§£å"', '了解各'),
        ('ç‰¹é»ž', '特點'),
        ('ï¼‰', '）'),
        ('ï¼ˆ', '（'),
        ('ç‰¹æ®Š', '特殊'),
        ('çš"', '的'),
        ('å¼·åˆ¶', '強制'),
        ('åªæœƒè™•', '只會處'),
        ('åƒ…', '僅'),
        ('å¯è·¨', '可跨'),
        ('è£œ', '補'),
        ('é¡¯ç¤º', '顯示'),
        ('æ¬"位', '欄位'),
        ('è™•理', '處理'),
        ('å¿…須', '必須'),
        ('è‡¨æ™'', '臨時'),
        ('æš«å­˜', '暫存'),
        ('æ²'有', '沒有'),
        ('è¦å‰‡', '規則'),
        ('è¦å‰‡', '規則'),  # variant
        ('資¨ˆ算', '計算'),
        ('資®€å–', '讀取'),
        ('清†', '清除'),
        ('å‰', '前'),
        ('ï¼›', '；'),
    ]
    
    # 應用替換
    fix_count = 0
    for wrong, correct in replacements:
        if wrong in content:
            count = content.count(wrong)
            content = content.replace(wrong, correct)
            fix_count += count
            print(f"✓ 修復 '{wrong}' -> '{correct}' ({count} 處)")
    
    # 寫回文件
    if content != original_content:
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("=" * 70)
        print(f"✅ 總共修復 {fix_count} 處亂碼！")
        print("=" * 70)
        return True
    else:
        print("=" * 70)
        print("無需修復（或全部已修復）")
        print("=" * 70)
        return False

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
