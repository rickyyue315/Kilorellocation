"""
徹底修復 app.py 中的所有中文亂碼
"""

import re

# 定義所有需要修復的亂碼對照表
mojibake_fixes = [
    ("支持十一模式ç³»çµ±", "支持十一模式系統"),
    ("附加Bè·¨OM特別模式", "附加B跨OM特別模式"),
    ("附加Cè·¨OM重點補0", "附加C跨OM重點補0"),
    ("æ™ºèƒ½", "智能"),
    ("è·¨OM", "跨OM"),
    ("ï¼š", "："),
    ("é¿å…", "避免"),
    ("æ¨™è¨˜å•†å"å¼·åˆ¶", "標記商品強制"),
    ("æŽ¥æ"¶ç«¯ä¾éŠå®¢å€", "接收端依遊客區"),
    ("éŠå®¢å€", "遊客區"),
    ("è¦å‰‡", "規則"),
    ("èªªæ˜Ž", "說明"),
    ("ï¼‰", "）"),
    ("ï¼ˆ", "（"),
    ("ç‰¹æ®Š", "特殊"),
    ("çš"", "的"),
    ("å¼·åˆ¶", "強制"),
    ("åªæœƒè™•", "只會處"),
    ("åƒ…", "僅"),
    ("å¯è·¨", "可跨"),
    ("è£œ0", "補0"),
    ("é¡¯ç¤º", "顯示"),
    ("æ¬"位", "欄位"),
    ("è™•理", "處理"),
    ("å¿…須", "必須"),
    ("è‡¨æ™'", "臨時"),
    ("æš«å­˜", "暫存"),
    ("æ²'有", "沒有"),
    ("è¦å‰‡", "規則"),
    ("資¨­ç½®æ—¥èªŒ", "配置日誌"),
    ("資¨ˆ算", "計算"),
    ("資®€å–", "讀取"),
    ("清†", "清除"),
]

def fix_mojibake_in_file(filepath):
    """修復文件中的所有亂碼"""
    
    # 讀取文件（使用 UTF-8 編碼）
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"讀取文件失敗: {e}")
        return False
    
    original_content = content
    fix_count = 0
    
    # 逐個應用修復
    for wrong, correct in mojibake_fixes:
        if wrong in content:
            count = content.count(wrong)
            content = content.replace(wrong, correct)
            fix_count += count
            print(f"修復 '{wrong}' -> '{correct}' ({count} 處)")
    
    # 如果有修改，寫回文件
    if content != original_content:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"\n✅ 成功修復 {fix_count} 處亂碼！")
            return True
        except Exception as e:
            print(f"寫入文件失敗: {e}")
            return False
    else:
        print("沒有發現需要修復的亂碼。")
        return True

if __name__ == "__main__":
    import os
    
    # 獲取當前腳本所在目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(script_dir, "app.py")
    
    print(f"正在修復文件: {app_file}")
    print("=" * 60)
    
    if fix_mojibake_in_file(app_file):
        print("\n修復完成！")
    else:
        print("\n修復失敗！")
