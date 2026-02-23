"""修復 app.py 中的縮進問題"""

# 讀取文件
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 從第 597 行(index 596)開始到第 645 行(index 644)，將 24 個空格改為 20 個空格
for i in range(596, 645):
    if i < len(lines):
        if lines[i].startswith('                        '):  # 24 spaces
            lines[i] = '                    ' + lines[i][24:]  # Replace with 20 spaces

# 寫回文件
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("縮進修復完成！")
