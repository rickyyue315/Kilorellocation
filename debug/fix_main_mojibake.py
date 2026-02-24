#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

filepath = "app.py"

print(f"讀取文件: {filepath}")
with open(filepath, 'rb') as f:
    data = f.read()

original_size = len(data)

# 確認存在的亂碼
print(f"\n發現亂碼:")
print(f"  系統: {data.count(b'\\xc3\\xa7\\xc2\\xb3\\xc2\\xbb\\xc3\\xa7\\xc2\\xb5\\xc2\\xb1')} 處")
print(f"  跨: {data.count(b'\\xc3\\xa8\\xc2\\xb7\\xc2\\xa8')} 處")
print(f"  智能: {data.count(b'\\xc3\\xa6\\xe2\\x84\\xa2\\xc2\\xba\\xc3\\xa8\\xc6\\x92\\xc2\\xbd')} 處")

# 關鍵替換
data = data.replace(b'\\xc3\\xa7\\xc2\\xb3\\xc2\\xbb\\xc3\\xa7\\xc2\\xb5\\xc2\\xb1', '系統'.encode('utf-8'))
data = data.replace(b'\\xc3\\xa8\\xc2\\xb7\\xc2\\xa8', '跨'.encode('utf-8'))
data = data.replace(b'\\xc3\\xa6\\xe2\\x84\\xa2\\xc2\\xba\\xc3\\xa8\\xc6\\x92\\xc2\\xbd', '智能'.encode('utf-8'))
data = data.replace(b'\\xc3\\xaf\\xc2\\xbc\\xc5\\xa1', '：'.encode('utf-8'))
data = data.replace(b'\\xc3\\xa9\\xc2\\xbf\\xc2\\xa5\\xc3\\xa5\\xe2\\x80\\xa6\\xc2\\xab', '避免'.encode('utf-8'))

# 寫回文件
with open(filepath, 'wb') as f:
    f.write(data)

print(f"\修復後文件大小: {len(data)} 字節 (原大小: {original_size})")
print("主要亂碼已修復！")
