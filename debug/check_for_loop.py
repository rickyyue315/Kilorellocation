#!/usr/bin/env python
with open('app.py', 'rb') as f:
    lines = f.readlines()

# Check the for loop and surrounding lines
for i in range(593, min(605, len(lines))):
    line = lines[i]
    stripped = line.lstrip()
    leading = len(line) - len(stripped)
    
    content = stripped[:60].decode('utf-8', errors='replace')
    print(f"Line {i+1}: {leading:2d} chars | {content}")
