import pandas as pd

df = pd.read_excel('調貨建議_20251209.xlsx', sheet_name='調貨建議 (Transfer Recommendations)')
print('Actual Excel columns:')
for i, col in enumerate(df.columns):
    print(f'{i+1}: {col}')