# 銷售數據欄位實現總結

## 任務完成 ✓

成功在調貨建議Excel輸出中新增了四個銷售數據欄位，顯示出貨店舖及收貨店舖的過去銷售數量。

## 新增欄位

### 1. Transfer Site Last Month Sold Qty
- **描述**: 出貨店舖上月銷售量
- **位置**: Excel中的M欄
- **列寬**: 25字符

### 2. Transfer Site MTD Sold Qty  
- **描述**: 出貨店舖當月累計銷售量
- **位置**: Excel中的N欄
- **列寬**: 20字符

### 3. Receive Site Last Month Sold Qty
- **描述**: 收貨店舖上月銷售量
- **位置**: Excel中的O欄
- **列寬**: 25字符

### 4. Receive Site MTD Sold Qty
- **描述**: 收貨店舖當月累計銷售量
- **位置**: Excel中的P欄
- **列寬**: 20字符

## 實現詳情

### 修改的文件

#### 1. [`business_logic.py`](business_logic.py)

**主要修改**:
- **第44-56行**: 在ND類型轉出來源中添加銷售數據
  ```python
  'last_month_sold_qty': int(row['Last Month Sold Qty']),
  'mtd_sold_qty': int(row['MTD Sold Qty'])
  ```

- **第158-170行**: 在RF類型轉出來源中添加銷售數據
  ```python
  'last_month_sold_qty': int(row['Last Month Sold Qty']),
  'mtd_sold_qty': int(row['MTD Sold Qty'])
  ```

- **第204-220行**: 在重點補0接收目標中添加銷售數據
  ```python
  'last_month_sold_qty': int(row['Last Month Sold Qty']),
  'mtd_sold_qty': int(row['MTD Sold Qty'])
  ```

- **第228-244行**: 在緊急缺貨補貨接收目標中添加銷售數據
  ```python
  'last_month_sold_qty': int(row['Last Month Sold Qty']),
  'mtd_sold_qty': int(row['MTD Sold Qty'])
  ```

- **第251-267行**: 在潛在缺貨補貨接收目標中添加銷售數據
  ```python
  'last_month_sold_qty': int(row['Last Month Sold Qty']),
  'mtd_sold_qty': int(row['MTD Sold Qty'])
  ```

- **第433-440行**: 在調貨建議中添加銷售數據欄位
  ```python
  'Transfer Site Last Month Sold Qty': source.get('last_month_sold_qty', 0),
  'Transfer Site MTD Sold Qty': source.get('mtd_sold_qty', 0),
  'Receive Site Last Month Sold Qty': dest.get('last_month_sold_qty', 0),
  'Receive Site MTD Sold Qty': dest.get('mtd_sold_qty', 0)
  ```

#### 2. [`excel_generator.py`](excel_generator.py)

**主要修改**:
- **第82-86行**: 在DataFrame中添加四個銷售數據欄位
  ```python
  'Transfer Site Last Month Sold Qty': rec.get('Transfer Site Last Month Sold Qty', 0),
  'Transfer Site MTD Sold Qty': rec.get('Transfer Site MTD Sold Qty', 0),
  'Receive Site Last Month Sold Qty': rec.get('Receive Site Last Month Sold Qty', 0),
  'Receive Site MTD Sold Qty': rec.get('Receive Site MTD Sold Qty', 0)
  ```

- **第112-116行**: 設置新增欄位的列寬
  ```python
  worksheet.set_column('M:M', 25)  # Transfer Site Last Month Sold Qty
  worksheet.set_column('N:N', 20)  # Transfer Site MTD Sold Qty
  worksheet.set_column('O:O', 25)  # Receive Site Last Month Sold Qty
  worksheet.set_column('P:P', 20)  # Receive Site MTD Sold Qty
  worksheet.set_column('Q:Q', 60)  # Notes - 增加寬度以顯示詳細分類信息
  ```

- **第150行**: 更新Notes欄位索引（從12改為16）
  ```python
  if col_num == 16:  # Notes欄位 (第Q列，索引為16)
  ```

## Excel輸出結構

更新後的Excel工作表包含以下欄位（按順序）：

1. Article (A欄)
2. Product Desc (B欄)
3. Transfer OM (C欄)
4. Transfer Site (D欄)
5. Receive OM (E欄)
6. Receive Site (F欄)
7. Transfer Qty (G欄)
8. Original Stock (H欄)
9. After Transfer Stock (I欄)
10. Safety Stock (J欄)
11. MOQ (K欄)
12. Remark (L欄)
13. **Transfer Site Last Month Sold Qty** (M欄) ← 新增
14. **Transfer Site MTD Sold Qty** (N欄) ← 新增
15. **Receive Site Last Month Sold Qty** (O欄) ← 新增
16. **Receive Site MTD Sold Qty** (P欄) ← 新增
17. Notes (Q欄)

## 測試驗證

### 測試1: 模擬數據測試
- **文件**: [`test_sales_data_columns.py`](test_sales_data_columns.py)
- **結果**: ✓ 通過
- **驗證**: 所有四個銷售數據欄位正確添加並包含預期數據

### 測試2: 真實數據測試
- **文件**: [`verify_real_data_sales.py`](verify_real_data_sales.py)
- **數據源**: `PL_reallocation_25Nov2025.XLSX` (747行)
- **結果**: ✓ 通過
- **生成調貨建議**: 110條
- **驗證**: 所有四個銷售數據欄位存在且包含實際銷售數據

### 測試結果樣本
```
Row 1:
  Transfer Site Last Month Sold Qty: 4
  Transfer Site MTD Sold Qty: 0
  Receive Site Last Month Sold Qty: 8
  Receive Site MTD Sold Qty: 0
```

## 數據流程

1. **數據輸入**: 原始Excel包含 `Last Month Sold Qty` 和 `MTD Sold Qty` 欄位
2. **數據處理**: [`DataProcessor`](data_processor.py) 處理並驗證銷售數據
3. **業務邏輯**: [`TransferLogic`](business_logic.py) 在識別轉出/接收店舖時提取銷售數據
4. **調貨匹配**: 在生成調貨建議時將銷售數據從源店舖和目標店舖傳遞到建議中
5. **Excel輸出**: [`ExcelGenerator`](excel_generator.py) 將銷售數據欄位添加到最終Excel輸出

## 使用說明

新增的銷售數據欄位會自動在生成調貨建議時填充，無需額外配置。用戶可以：

1. 查看出貨店舖的歷史銷售表現（上月和當月）
2. 查看接收店舖的歷史銷售表現（上月和當月）
3. 基於銷售數據做出更明智的調貨決策
4. 分析銷售趨勢與庫存調配的關係

## 兼容性

- ✓ 向後兼容：現有功能保持不變
- ✓ 數據完整性：缺失銷售數據時自動設為0
- ✓ 格式一致性：遵循現有的Excel格式和樣式
- ✓ 性能影響：最小化，僅增加四個數值欄位的處理

## 總結

成功實現了用戶要求的功能，在調貨建議Excel中新增了四個銷售數據欄位，提供了出貨店舖和收貨店舖的完整銷售歷史信息，支援更精準的庫存調配決策。