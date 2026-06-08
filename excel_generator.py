"""
Excel輸出模組 v2.16.0
生成調貨建議和統計摘要的Excel文件
支持二十五模式系統：A(保守轉貨)/B(加強轉貨)/B2(附加B特別模式)/B2a(附加B2a特別模式)/B2L(附加B2L特別模式)/B2La(附加B2La特別模式)/B3(附加B跨OM特別模式)/B3a(附加B3a跨OM特別模式)/B3L(附加B3L跨OM特別模式)/B3La(附加B3La跨OM特別模式)/C(重點補0)/C1(重點補0-只補0/1)/C2(附加C跨OM重點補0)/D(清貨轉貨)/D2(清貨轉貨ND限定)/E1(強制轉出)/E1b(強制轉出優先類型接收)/E2(強制轉出跨OM)/F(目標優化)/F2(F指定模式)/ND1(ND同OM轉貨)/ND2(ND混合OM轉貨)/精簡SKU(限同OM)/精簡SKU(跨OM)/精簡SKU(退D001)
增加詳細Notes分類資訊
"""

import io
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import xlsxwriter
from typing import Dict, List, Optional
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExcelGenerator:
    """Excel輸出類 v2.10.0"""
    
    def __init__(self):
        self.output_filename = ""
    
    def generate_filename(self) -> str:
        """
        生成輸出文件名
        
        Returns:
            格式化的文件名
        """
        current_datetime = datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y%m%d_%H%M%S")
        filename = f"調貨建議_{current_datetime}.xlsx"
        self.output_filename = filename
        return filename
    
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
    
    def create_transfer_recommendations_sheet(self, writer, recommendations: List[Dict], mode: str = None):
        """
        創建調貨建議工作表
        
        Args:
            writer: ExcelWriter對象
            recommendations: 調貨建議列表
        """
        logger.info("創建調貨建議工作表")
        
        # 準備數據
        show_d001_col = mode == "精簡SKU(退D001)" if mode else False
        df_data = []
        for rec in recommendations:
            # 生成Remark
            source_type = rec.get('Source Type', '')
            dest_type = rec.get('Destination Type') or rec.get('Receive Type', '')
            remark = self._generate_remark(source_type, dest_type) if source_type and dest_type else ''
            
            row_data = {
                'Brand': rec.get('Product Hierarchy') or rec.get('Brand') or rec.get('品牌', ''),
                'Article': rec['Article'],
                'Product Desc': rec['Product Desc'],
                'Transfer OM': rec['Transfer OM'],
                'Transfer Site': rec['Transfer Site'],
                'Receive OM': rec['Receive OM'],
                'Receive Site': rec['Receive Site'],
                'Transfer Qty': rec['Transfer Qty'],
                'Transfer Original Stock': rec['Original Stock'],
                'Transfer After Transfer Stock': rec['After Transfer Stock'],
                'Transfer Safety Stock': rec['Safety Stock'],
                'Transfer MOQ': rec['MOQ'],
                'Remark': remark,
                'Notes': rec.get('Notes', ''),
                'AI Risk': rec.get('AI Risk', ''),
                'AI Needs Review': rec.get('AI Needs Review', ''),
                # 新增銷售數據欄位
                'Transfer Site Last Month Sold Qty': rec.get('Transfer Site Last Month Sold Qty', 0),
                'Transfer Site MTD Sold Qty': rec.get('Transfer Site MTD Sold Qty', 0),
                'Receive Site Last Month Sold Qty': rec.get('Receive Site Last Month Sold Qty', 0),
                'Receive Site MTD Sold Qty': rec.get('Receive Site MTD Sold Qty', 0),
                # 新增Receive Original Stock欄位
                'Receive Original Stock': rec.get('Receive Original Stock', 0)
            }
            if show_d001_col:
                row_data['D001 Receive Qty'] = rec['Transfer Qty']
            df_data.append(row_data)
        
        # 創建DataFrame
        df = pd.DataFrame(df_data)
        
        # 寫入Excel
        df.to_excel(writer, sheet_name='調貨建議 (Transfer Recommendations)', index=False)
        
        # 獲取工作簿和工作表對象
        workbook = writer.book
        worksheet = writer.sheets['調貨建議 (Transfer Recommendations)']
        
        # 設置列寬（優化為適中寬度）
        worksheet.set_column('A:A', 14)  # Brand
        worksheet.set_column('B:B', 12)  # Article
        worksheet.set_column('C:C', 25)  # Product Desc
        worksheet.set_column('D:D', 12)  # Transfer OM
        worksheet.set_column('E:E', 12)  # Transfer Site
        worksheet.set_column('F:F', 12)  # Receive OM
        worksheet.set_column('G:G', 12)  # Receive Site
        worksheet.set_column('H:H', 10)  # Transfer Qty
        worksheet.set_column('I:I', 18)  # Transfer Original Stock
        worksheet.set_column('J:J', 20)  # Transfer After Transfer Stock
        worksheet.set_column('K:K', 18)  # Transfer Safety Stock
        worksheet.set_column('L:L', 12)  # Transfer MOQ
        worksheet.set_column('M:M', 25)  # Remark - 簡潔的轉出→接收映射
        worksheet.set_column('N:N', 75)  # Notes - 600像素約等於75字符
        worksheet.set_column('O:O', 10)  # AI Risk
        worksheet.set_column('P:P', 12)  # AI Needs Review
        worksheet.set_column('Q:Q', 18)  # Transfer Site Last Month Sold Qty
        worksheet.set_column('R:R', 15)  # Transfer Site MTD Sold Qty
        worksheet.set_column('S:S', 18)  # Receive Site Last Month Sold Qty
        worksheet.set_column('T:T', 15)  # Receive Site MTD Sold Qty
        worksheet.set_column('U:U', 15)  # Receive Original Stock
        if show_d001_col:
            worksheet.set_column('V:V', 18)  # D001 Receive Qty

        # 添加標題格式
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1,
            'font_name': 'Arial',
            'font_size': 10
        })

        # 應用標題格式
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # 添加數據格式
        data_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'top',
            'font_name': 'Arial',
            'font_size': 10
        })

        # Notes欄位的特殊格式（換行和自動高度）
        notes_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'top',
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'left'
        })

        # 應用數據格式（使用列格式避免逐格寫入，提高效能）
        worksheet.set_column('A:M', None, data_format)
        worksheet.set_column('N:N', 75, notes_format)
        worksheet.set_column('O:P', None, data_format)
        worksheet.set_column('Q:U', None, data_format)
        if show_d001_col:
            worksheet.set_column('V:V', None, data_format)

        # 設置標題行高度與預設行高（避免逐行設定）
        worksheet.set_row(0, 40)
        worksheet.set_default_row(22)
    
    def create_summary_dashboard_sheet(self, writer, statistics: Dict):
        """
        創建統計摘要工作表
        
        Args:
            writer: ExcelWriter對象
            statistics: 統計信息字典
        """
        logger.info("創建統計摘要工作表")
        
        workbook = writer.book
        worksheet = workbook.add_worksheet('統計摘要 (Summary Dashboard)')
        
        # 設置格式
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Arial'
        })
        
        kpi_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Arial'
        })
        
        kpi_value_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#D7E4BC',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Arial'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BC',
            'border': 1,
            'font_name': 'Arial',
            'font_size': 10
        })
        
        data_format = workbook.add_format({
            'border': 1,
            'font_name': 'Arial',
            'font_size': 10
        })
        
        # 標題
        worksheet.merge_range('A1:B1', '調貨建議統計摘要', title_format)
        
        # KPI橫幅
        worksheet.write('A3', '總調貨建議行數', kpi_format)
        worksheet.write('B3', statistics.get('total_recommendations', 0), kpi_value_format)
        
        worksheet.write('A4', '總調貨件數', kpi_format)
        worksheet.write('B4', statistics.get('total_transfer_qty', 0), kpi_value_format)
        
        worksheet.write('A5', '涉及產品數量', kpi_format)
        worksheet.write('B5', statistics.get('unique_articles', 0), kpi_value_format)
        
        worksheet.write('A6', '涉及OM數量', kpi_format)
        worksheet.write('B6', statistics.get('unique_oms', 0), kpi_value_format)
        
        # 按Article統計
        row = 8
        worksheet.write(f'A{row}', 'Brand', header_format)
        worksheet.write(f'B{row}', '按Article統計', header_format)
        worksheet.write(f'C{row}', 'Product Desc', header_format)
        worksheet.write(f'D{row}', '總調貨件數', header_format)
        worksheet.write(f'E{row}', '調貨行數', header_format)
        worksheet.write(f'F{row}', '涉及OM數量', header_format)
        
        article_stats = statistics.get('article_stats', {})
        for article, stats in article_stats.items():
            row += 1
            worksheet.write(f'A{row}', stats.get('brand', ''), data_format)
            worksheet.write(f'B{row}', article, data_format)
            worksheet.write(f'C{row}', stats.get('product_desc', ''), data_format)
            worksheet.write(f'D{row}', stats['total_qty'], data_format)
            worksheet.write(f'E{row}', stats['count'], data_format)
            worksheet.write(f'F{row}', stats['om_count'], data_format)
        
        # 空白行
        row += 2
        
        # 按OM統計
        worksheet.write(f'A{row}', '按OM統計', header_format)
        worksheet.write(f'B{row}', '轉出件數', header_format)
        worksheet.write(f'C{row}', '接收件數', header_format)
        worksheet.write(f'D{row}', '調貨行數', header_format)
        worksheet.write(f'E{row}', '涉及Article數量', header_format)
        
        om_stats = statistics.get('om_stats', {})
        for om, stats in om_stats.items():
            row += 1
            worksheet.write(f'A{row}', om, data_format)
            worksheet.write(f'B{row}', stats.get('transfer_qty', stats.get('total_qty', 0)), data_format)
            worksheet.write(f'C{row}', stats.get('receive_qty', 0), data_format)
            worksheet.write(f'D{row}', stats['count'], data_format)
            worksheet.write(f'E{row}', stats['article_count'], data_format)
        
        # 空白行
        row += 2
        
        # 轉出類型分析
        worksheet.write(f'A{row}', '轉出類型分析', header_format)
        worksheet.write(f'B{row}', '建議行數', header_format)
        worksheet.write(f'C{row}', '總件數', header_format)
        
        source_type_stats = statistics.get('source_type_stats', {})
        for source_type, stats in source_type_stats.items():
            row += 1
            worksheet.write(f'A{row}', source_type, data_format)
            worksheet.write(f'B{row}', stats['count'], data_format)
            worksheet.write(f'C{row}', stats['qty'], data_format)
        
        # 空白行
        row += 2
        
        # 接收類型分析
        worksheet.write(f'A{row}', '接收類型分析', header_format)
        worksheet.write(f'B{row}', '建議行數', header_format)
        worksheet.write(f'C{row}', '總件數', header_format)
        
        dest_type_stats = statistics.get('dest_type_stats', {})
        for dest_type, stats in dest_type_stats.items():
            row += 1
            worksheet.write(f'A{row}', dest_type, data_format)
            worksheet.write(f'B{row}', stats['count'], data_format)
            worksheet.write(f'C{row}', stats['qty'], data_format)
        
        # 設置列寬（優化為適中寬度）
        worksheet.set_column('A:A', 18)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 12)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 12)
        
        # 設置行高
        worksheet.set_row(0, 25)  # 標題行
        worksheet.set_row(2, 20)  # KPI標題行
        worksheet.set_row(3, 20)  # KPI值行
        worksheet.set_row(4, 20)  # KPI值行
        worksheet.set_row(5, 20)  # KPI值行
        worksheet.set_row(6, 20)  # KPI值行
    
    def generate_excel_file(self, recommendations: List[Dict], statistics: Dict,
                           output_path: Optional[str] = None,
                           mode: str = None,
                           ai_summary: Optional[str] = None) -> bytes:
        """
        生成完整的Excel文件，返回 bytes（記憶體操作，無磁碟 I/O）
        
        Args:
            recommendations: 調貨建議列表
            statistics: 統計信息字典
            output_path: 保留參數（已棄用，不再使用）
            mode: 調貨模式名稱
            ai_summary: optional AI executive summary text
        
        Returns:
            Excel 文件的 bytes 內容
        """
        logger.info("開始生成Excel文件（BytesIO模式）")
        
        self.generate_filename()

        
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            self.create_transfer_recommendations_sheet(writer, recommendations, mode)
            self.create_summary_dashboard_sheet(writer, statistics)
            if ai_summary:
                self.create_smart_summary_sheet(writer, ai_summary)

        logger.info("Excel文件生成完成（BytesIO）")
        return buf.getvalue()

    def create_smart_summary_sheet(self, writer, ai_summary: str):
        workbook = writer.book
        worksheet = workbook.add_worksheet('智能摘要')

        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'left',
            'valign': 'vcenter', 'font_name': 'Arial',
        })
        label_fmt = workbook.add_format({
            'bold': True, 'font_size': 10, 'font_name': 'Arial',
        })
        text_fmt = workbook.add_format({
            'font_size': 10, 'text_wrap': True, 'valign': 'top',
            'font_name': 'Arial',
        })
        footer_fmt = workbook.add_format({
            'italic': True, 'font_size': 9, 'color': '#888888',
            'font_name': 'Arial',
        })

        row = 0
        worksheet.write(row, 0, '智能摘要', title_fmt)
        row += 2

        gen_time = datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M:%S")
        worksheet.write(row, 0, '生成時間', label_fmt)
        worksheet.write(row, 1, gen_time, text_fmt)
        row += 2

        worksheet.write(row, 0, '摘要', label_fmt)
        worksheet.write(row, 1, ai_summary, text_fmt)
        row += 2

        worksheet.write(row, 0, '此摘要由 AI 基於聚合統計數據生成，並不包含銷量庫存數據，摘要僅供參考，不能取代系統規則及人手覆核。', footer_fmt)

        worksheet.set_column('A:A', 14)
        worksheet.set_column('B:B', 80)


