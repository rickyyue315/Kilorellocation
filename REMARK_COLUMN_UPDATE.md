# 調貨建議 Excel 新增 Remark 欄位

## 更新摘要

已成功在調貨建議 Excel 輸出中新增 **Remark** 欄位，用於簡潔顯示轉出分類到接收分類的映射關係。

## 修改內容

### 文件修改：[`excel_generator.py`](excel_generator.py)

#### 1. 新增 `_generate_remark()` 方法 (第 37-48 行)
```python
def _generate_remark(self, source_type: str, dest_type: str) -> str:
    """
    生成簡潔的Remark，顯示轉出分類到接收分類的映射
    
    Args:
        source_type: 轉出分類 (e.g., 'ND轉出', 'RF過剩轉出', 'RF加強轉出')
        dest_type: 接收分類 (e.g., '重點補0', '緊急缺貨補貨', '潛在缺貨補貨')
        
    Returns:
        簡潔的Remark字符串
    """
    return f"{source_type} → {dest_type}"
```

#### 2. 修改 `create_transfer_recommendations_sheet()` 方法
- **第 63-66 行**：在數據準備階段生成 Remark
  ```python
  # 生成Remark
  source_type = rec.get('Source Type', '')
  dest_type = rec.get('Receive Type', '')
  remark = self._generate_remark(source_type, dest_type) if source_type and dest_type else ''
  ```

- **第 80 行**：將 Remark 添加到 DataFrame
  ```python
  'Remark': remark,
  ```

- **第 106 行**：設置 Remark 欄位寬度為 35
  ```python
  worksheet.set_column('L:L', 35)  # Remark - 簡潔的轉出→接收映射
  ```

- **第 141 行**：更新 Notes 欄位索引從 11 改為 12（因為新增了 Remark 欄）
  ```python
  if col_num == 12:  # Notes欄位 (第M列，索引為12)
  ```

## Remark 格式示例

根據您的需求，Remark 欄位將顯示以下映射關係：

| 轉出分類 | 接收分類 | Remark |
|---------|---------|--------|
| RF過剩轉出 | 重點補0 | RF過剩轉出 → 重點補0 |
| RF過剩轉出 | 緊急缺貨補貨 | RF過剩轉出 → 緊急缺貨補貨 |
| ND轉出 | 重點補0 | ND轉出 → 重點補0 |
| RF加強轉出 | 潛在缺貨補貨 | RF加強轉出 → 潛在缺貨補貨 |

## Excel 輸出欄位順序

調貨建議工作表現在包含以下欄位（按順序）：

1. Article
2. Product Desc
3. Transfer OM
4. Transfer Site
5. Receive OM
6. Receive Site
7. Transfer Qty
8. Original Stock
9. After Transfer Stock
10. Safety Stock
11. MOQ
12. **Remark** ← 新增欄位
13. Notes

## 特點

✅ **簡潔易讀**：使用箭頭符號 (→) 清晰表示轉出到接收的流向
✅ **自動生成**：無需手動輸入，系統自動根據轉出和接收分類生成
✅ **適當寬度**：Remark 欄寬度設置為 35，足以顯示完整的映射信息
✅ **與 Notes 協調**：Remark 提供簡潔概覽，Notes 提供詳細分析

## 測試結果

已驗證 Remark 生成功能正常運作，所有映射關係均正確生成。

## 使用方式

無需任何額外操作。當系統生成調貨建議 Excel 文件時，Remark 欄位將自動填充相應的轉出→接收映射信息。
