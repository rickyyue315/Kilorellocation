#!/usr/bin/env python
with open('app.py', 'rb') as f:
    lines = f.readlines()

# Check the area where the for loop ends and the problematic lines start
for i in range(638, 655):
    line = lines[i]
    stripped = line.lstrip()
    leading = len(line) - len(stripped)
    
    content = stripped[:70].decode('utf-8', errors='replace')
    print(f"Line {i+1}: {leading:2d} | {content}")
