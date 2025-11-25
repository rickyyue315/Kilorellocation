#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify Remark column fix
"""

from excel_generator import ExcelGenerator
import pandas as pd
import sys

# Create test data with Destination Type
test_recommendations = [
    {
        'Article': 'ART001',
        'Product Desc': 'Product 1',
        'Transfer OM': 'OM1',
        'Transfer Site': 'Site1',
        'Receive OM': 'OM2',
        'Receive Site': 'Site2',
        'Transfer Qty': 100,
        'Original Stock': 500,
        'After Transfer Stock': 600,
        'Safety Stock': 50,
        'MOQ': 10,
        'Source Type': 'RF over',
        'Destination Type': 'Priority 0',
        'Notes': 'Test note 1'
    },
    {
        'Article': 'ART002',
        'Product Desc': 'Product 2',
        'Transfer OM': 'OM1',
        'Transfer Site': 'Site1',
        'Receive OM': 'OM3',
        'Receive Site': 'Site3',
        'Transfer Qty': 50,
        'Original Stock': 200,
        'After Transfer Stock': 250,
        'Safety Stock': 30,
        'MOQ': 5,
        'Source Type': 'ND Transfer',
        'Destination Type': 'Priority 0',
        'Notes': 'Test note 2'
    },
    {
        'Article': 'ART003',
        'Product Desc': 'Product 3',
        'Transfer OM': 'OM2',
        'Transfer Site': 'Site2',
        'Receive OM': 'OM4',
        'Receive Site': 'Site4',
        'Transfer Qty': 75,
        'Original Stock': 300,
        'After Transfer Stock': 375,
        'Safety Stock': 40,
        'MOQ': 8,
        'Source Type': 'RF over',
        'Destination Type': 'Emergency Stock',
        'Notes': 'Test note 3'
    }
]

# Test statistics
test_statistics = {
    'total_recommendations': 3,
    'total_transfer_qty': 225,
    'unique_articles': 3,
    'unique_oms': 4,
    'article_stats': {},
    'om_stats': {},
    'source_type_stats': {},
    'dest_type_stats': {}
}

# Generate Excel
generator = ExcelGenerator()
output_file = generator.generate_excel_file(test_recommendations, test_statistics)

# Read back and verify
df = pd.read_excel(output_file, sheet_name='調貨建議 (Transfer Recommendations)')

# Check if remarks are populated
has_empty = df['Remark'].isna().any() or (df['Remark'] == '').any()

if has_empty:
    sys.exit(1)
else:
    sys.exit(0)
