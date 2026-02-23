#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用字節模式替換修復亂碼
"""

import os

def main():
    filepath = "app.py"
    
    print(f"讀取文件: {filepath}")
    with open(filepath, 'rb') as f:
        data = f.read()
    
    original_size = len(data)
    
    # 定義字節級別的替換規則
    byte_replacements = [
        # 系統
        (b'\xc3\xa7\xc2\xb3\xc2\xbb\xc3\xa7\xc2\xb5\xc2\xb1', '\u7cfb\u7d71'.encode('utf-8')),
        # 跨
        (b'\xc3\xa8\xc2\xb7\xc2\xa8', '\u8de8'.encode('utf-8')),
        # 智能
        (b'\xc3\xa6\xe2\x84\xa2\xc2\xba\xc3\xa8\xc6\x92\xc2\xbd', '\u667a\u80fd'.encode('utf-8')),
        # ：
        (b'\xc3\xaf\xc2\xbc\xc5\xa1', '\uff1a'.encode('utf-8')),
        # 避免
        (b'\xc3\xa9\xc2\xbf\xc2\xa5\xc3\xa5\xe2\x80\xa6\xc2\xab', '\u907f\u514d'.encode('utf-8')),
        # 標記商品強制
        (b'\xc3\xa6\xc2\xa8\xe2\x84\xa2\xc3\xa8\xc2\xa8\xe2\x80\xb0\xc3\xa5\xe2\x80\xa2\xe2\x80\xa0\xc3\xa5\xe2\x80\x9c\xc5\x81\xc3\xa5\xc2\xbc\xc2\xb7\xc3\xa5\xc5\xb6\xc2\xb6', '\u6a19\u8a18\u5546\u54c1\u5f37\u5236'.encode('utf-8')),
        # 接收端依遊客區
        (b'\xc3\xa6\xc5\xa0\xc2\xa5\xc3\xa6\xe2\x80\x9c\xc2\xb6\xc3\xa7\xc2\xab\xc2\xaf\xc3\xa4\xc2\xbe\xc5\x93\xc3\xa9\xc5\xa1\xc3\xa5\xc2\xae\xc2\xa2\xc3\xa5\xe2\x82\xac', '\u63a5\u6536\u7aef\u4f9d\u904a\u5ba2\u5340'.encode('utf-8')),
        # 說明
        (b'\xc3\xa8\xc2\xaa\xc2\xaa\xc3\xa6\xcb\x9c\xc5\xbe', '\u8aaa\u660e'.encode('utf-8')),
        # 了解各
        (b'\xc3\xa4\xc2\xba\xe2\x80\xa0\xc3\xa8\xc2\xa7\xa3\xc3\xa5\xe2\x80\x9c\xc6\x92', '\u4e86\u89e3\u5404'.encode('utf-8')),
        # 特點
        (b'\xc3\xa7\xe2\x80\xb0\xc2\xb9\xc3\xa9\xc2\xbb\xc5\xbe', '\u7279\u9ede'.encode('utf-8')),
        # 特殊
        (b'\xc3\xa7\xe2\x80\xb0\xc2\xb9\xc3\xa6\xc2\xae\xc5\xa0', '\u7279\u6b8a'.encode('utf-8')),
       # ）
        (b'\xc3\xaf\xc2\xbc\xe2\x80\xb0', '\uff09'.encode('utf-8')),
        # （
        (b'\xc3\xaf\xc2\xbc\xcb\x86', '\uff08'.encode('utf-8')),
        # 的
        (b'\xc3\xa7\xc5\xa1\xe2\x80\x9d', '\u7684'.encode('utf-8')),
        # 的 (variant)
        (b'\xc3\xa7\xc5\xa1\xe2\x80\x9c', '\u7684'.encode('utf-8')),
        # 只會處
        (b'\xc3\xa5\xc2\xaa\xc5\x93\xc3\xa6\xc5\x93\xc6\x92\xc3\xa8\xe2\x84\xa2', '\u53ea\u6703\u8655'.encode('utf-8')),
        # 僅
        (b'\xc3\xa5\xc6\x92', '\u50c5'.encode('utf-8')),
        # 可跨
        (b'\xc3\xa5\xc2\xaf\xc3\xa8\xc2\xb7\xc2\xa8', '\u53ef\u8de8'.encode('utf-8')),
        # 補
        (b'\xc3\xa8\xc2\xa3\xc5\x93', '\u88dc'.encode('utf-8')),
        # 顯示
        (b'\xc3\xa9\xc2\xa1\xc2\xaf\xc3\xa7\xc2\xa4\xc2\xba', '\u986f\u793a'.encode('utf-8')),
        # 欄位
        (b'\xc3\xa6\xc2\xac\xe2\x80\x9d\xc4\xbd', '\u6b04\u4f4d'.encode('utf-8')),
        # 處理
        (b'\xc3\xa8\xe2\x84\xa2\xc3\xa7\xc5\xa0 \xe2\x80\xa0', '\u8655\u7406'.encode('utf-8')),
        # 必須
        (b'\xc3\xa5\xc2\xbf\xe2\x80\xa6\xc3\xa9\xc2\xa0\xc2\xb6', '\u5fc5\u9808'.encode('utf-8')),
        # 臨時
        (b'\xc3\xa8\xe2\x80\xa1\xc2\xa8\xc3\xa6\xe2\x84\xa2', '\u81e8\u6642'.encode('utf-8')),
        # 暫存
        (b'\xc3\xa6\xc5\x93\xc2\xab\xc3\xa5\xc2\xad\xe2\x80\xb0', '\u66ab\u5b58'.encode('utf-8')),
        # 沒有
        (b'\xc3\xa6\xc2\xb2\xc5\x0099\xc3', '\u6c92\u6709'.encode('utf-8')),
        # 規則
        (b'\xc3\xa8\xc2\xa6\xc3\xa5\xe2\x80\xb0', '\u898f\u5247'.encode('utf-8')),
        # 計算
        (b'\xc3\xa8\xc2\xa8\xcb\x86\xc2\xb算', '\u8a08\u7b97'.encode('utf-8')),
        # 讀取
        (b'\xc3\xa8\xc2\xae\xe2\x82\xac\xc3\xa5\xc5\xa0', '\u8b80\u53d6'.encode('utf-8')),
        # 清除
        (b'\xe6\xb8\x85\xe2\x80\xa0 ', '\u6e05\u9664'.encode('utf-8')),
        # 前
        (b'\xc3\xa5\xe2\x80\xb0\xc2\x8d', '\u524d'.encode('utf-8')),
        # ；
        (b'\xc3\xaf\xc2\xbc\xe2\x80\xba', '\uff1b'.encode('utf-8')),
    ]
    
    # 應用替換
    fix_count = 0
    for wrong_bytes, correct_bytes in byte_replacements:
        count = data.count(wrong_bytes)
        if count > 0:
            data = data.replace(wrong_bytes, correct_bytes)
            fix_count += count
            print(f"修復 {count} 處: {wrong_bytes[:20]}... -> {correct_bytes.decode('utf-8')}")
    
    # 寫回文件
    if len(data) != original_size or fix_count > 0:
        with open(filepath, 'wb') as f:
            f.write(data)
        print(f"\n總共修復了 {fix_count} 處亂碼")
        print(f"文件大小: {original_size} -> {len(data)} 字節")
        print("修復完成！")
    else:
        print("沒有發現需要修復的亂碼")

if __name__ == "__main__":
    main()
