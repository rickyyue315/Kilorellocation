#!/usr/bin/env python
# Check for indentation issues

with open('app.py', 'rb') as f:
    lines = f.readlines()

# Check lines around 645
for i in range(642, min(652, len(lines))):
    line = lines[i]
    # Count leading whitespace  
    stripped = line.lstrip()
    leading = len(line) - len(stripped)
    
    # Check for tabs vs spaces
    leading_ws = line[:leading]
    has_tabs = b'\t' in leading_ws
    has_spaces = len(leading_ws.replace(b'\t', b'')) > 0
    
    content = stripped[:60].decode('utf-8', errors='replace')
    print(f"Line {i+1}: {leading} chars, Tabs={has_tabs}, Content: {content}")
    if has_tabs and has_spaces:
        print(f"  WARNING: MIXED TABS AND SPACES!")
