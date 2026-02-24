#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 檢查第503行的具體字符
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    line = lines[502]
    print('Line 503 content:')
    print(repr(line))
    print()
    print('Looking for U+00B3 (superscript 3):')
    if '\u00b3' in line:
        print('FOUND U+00B3 at position:', line.index('\u00b3'))
    else:
        print('U+00B3 not found in this line')
    
    # Check all characters
    print('\nCharacters in line:')
    for i, char in enumerate(line[:50]):  # First 50 chars
        if ord(char) < 32:
            print(f'  [{i:2d}] [CTRL U+{ord(char):04X}]')
        else:
            print(f'  [{i:2d}] {repr(char)} U+{ord(char):04X}')
