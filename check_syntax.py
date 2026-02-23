#!/usr/bin/env python
# Quick syntax check
import ast
import sys

try:
    with open('app.py', 'r', encoding='utf-8') as f:
        code = f.read()
    ast.parse(code)
    print('✓ No syntax errors')
    sys.exit(0)
except SyntaxError as e:
    print(f'✗ Syntax error at line {e.lineno}: {e.msg}')
    sys.exit(1)
