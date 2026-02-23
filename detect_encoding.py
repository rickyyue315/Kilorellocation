#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 嘗試找出原始編碼
with open('app.py', 'rb') as f:
    raw_bytes = f.read()

# 檢查第503行的原始字節
content_str = raw_bytes.decode('utf-8')
lines = content_str.split('\n')
line_503 = lines[502]

print("Line 503 as hex:")
line_bytes = line_503.encode('utf-8')
print(' '.join(f'{b:02X}' for b in line_bytes[:50]))
print()

# 嘗試各種編碼組合
print("Trying different interpretations:")

# 如果原始是UTF-8，但被當作Latin-1讀取
try:
    mangled = line_503.encode('latin-1', errors='ignore')
    restored = mangled.decode('utf-8', errors='ignore')
    print("Latin-1->UTF-8:", repr(restored))
except Exception as e:
    print("Latin-1 failed:", e)

# 如果原始是UTF-8字節，但被當作cp1252讀取
try:
    mangled = line_503.encode('cp1252', errors='ignore')
    restored = mangled.decode('utf-8', errors='ignore')
    print("cp1252->UTF-8:", repr(restored))
except Exception as e:
    print("cp1252 failed:", e)
