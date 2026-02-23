#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Find all lines with syntax errors due to corrupted characters
"""

import ast
import sys

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Try to parse and collect all syntax errors
error_lines = []
current_line = 1

for i in range(1, len(lines) + 1):
    code_so_far = ''.join(lines[:i])
    try:
        ast.parse(code_so_far)
    except SyntaxError as e:
        if e.lineno not in error_lines:
            error_lines.append(e.lineno)
            print(f"Line {e.lineno}: {e.msg}")
            if e.text:
                print(f"  Text: {e.text[:80].strip()}")
            print()
            if len(error_lines) >= 5:  # Show first 5
                print("... and potentially more")
                break

print(f"\nTotal errors found (showing first 5): {len(error_lines)}")
