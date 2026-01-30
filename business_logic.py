"""
業務邏輯模組 v2.1.1
實現調貨規則、源/目的地識別和匹配算法
支持六模式系統：A(保守轉貨)/B(加強轉貨)/C(重點補0)/D(清貨轉貨)/E(強制轉出)/F(目標優化)
優化接收條件和避免同一SKU的轉出店鋪同時接收
基於累計接收數量判斷是否達到最低保障標準的機制
強化ND店鋪限制：所有模式下ND店鋪只能轉出，不能接收
D模式特殊規則：ND清貨轉出避免1件餘貨
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransferLogic:
    """調貨業務邏輯類 v2.1.1"""
    
    def __init__(self):
        self.transfer_recommendations = []
        self.quality_check_passed = True
        self.quality_errors = []
        self.mode_a = "保守轉貨"  # A模式
        self.mode_b = "加強轉貨"  # B模式
        self.mode_c = "重點補0"  # C模式
        self.mode_d = "清貨轉貨"  # D模式
        self.mode_e = "強制轉出"  # E模式
        self.mode_f = "目標優化"  # F模式
    
    def identify_sources(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        """
        識別轉出候選店鋪

        Args:
            group_df: 按Article和OM分組的DataFrame
            mode: 轉貨模式（保守轉貨、加強轉貨、重點補0、清貨轉貨、強制轉出或目標優化）

        Returns:
            轉出候選店鋪列表
        """
        sources: List[Dict] = []

        # F模式特殊處理：Target優先接收，轉出可全數釋放
        if mode == self.mode_f:
            # ND類型：全數轉出
            nd_sources = group_df[group_df['RP Type'] == 'ND']
            for _, row in nd_sources.iterrows():
                net_stock = int(row['SaSa Net Stock'])
                if net_stock > 0:
                    sources.append({
                        'site': row['Site'],
                        'om': row['OM'],
                        'rp_type': row['RP Type'],
                        'transferable_qty': net_stock,
                        'priority': 1,
                        'original_stock': net_stock,
                        'effective_sold_qty': int(row['Effective Sold Qty']),
                        'source_type': 'F模式ND轉出',
                        'last_month_sold_qty': int(row['Last Month Sold Qty']),
                        'mtd_sold_qty': int(row['MTD Sold Qty'])
                    })

            # RF類型：可忽視最小庫存要求，但保護最高銷量店鋪
            rf_sources = group_df[group_df['RP Type'] == 'RF']
            max_sold_qty = rf_sources['Effective Sold Qty'].max() if not rf_sources.empty else 0

            for _, row in rf_sources.iterrows():
                net_stock = int(row['SaSa Net Stock'])
                effective_sold = int(row['Effective Sold Qty'])

                if net_stock <= 0:
                    continue
                if effective_sold >= max_sold_qty:
                    continue

                sources.append({
                    'site': row['Site'],
                    'om': row['OM'],
                    'rp_type': row['RP Type'],
                    'transferable_qty': net_stock,
                    'priority': 2,
                    'original_stock': net_stock,
                    'effective_sold_qty': effective_sold,
                    'source_type': 'F模式RF轉出',
                    'last_month_sold_qty': int(row['Last Month Sold Qty']),
                    'mtd_sold_qty': int(row['MTD Sold Qty'])
                })

            # 按優先級 + 銷售量升序排序（銷售最多排最後）
            sources.sort(key=lambda x: (x['priority'], x.get('effective_sold_qty', 0)))
            return sources

        # E模式特殊處理：檢查是否有被標記為*ALL*的行
        if mode == self.mode_e:
            # 檢查是否存在'ALL'欄位，以及是否有任何行被標記
            if 'ALL' in group_df.columns:
                all_marked = group_df[
                    (group_df['ALL'].notna()) & 
                    (group_df['ALL'].astype(str).str.strip() != '')
                ]
                
                # E模式：只有被標記為*ALL*的行才會轉出，所有庫存全數轉出
                for _, row in all_marked.iterrows():
                    net_stock = int(row['SaSa Net Stock'])
                    if net_stock > 0:  # 只考慮有庫存的店鋪
                        sources.append({
                            'site': row['Site'],
                            'om': row['OM'],
                            'rp_type': row['RP Type'],
                            'transferable_qty': net_stock,  # 全數轉出
                            'priority': 1,  # E模式：優先級最高
                            'original_stock': net_stock,
                            'effective_sold_qty': int(row['Effective Sold Qty']),
                            'source_type': 'E模式強制轉出',
                            'last_month_sold_qty': int(row['Last Month Sold Qty']),
                            'mtd_sold_qty': int(row['MTD Sold Qty']),
                            'is_e_mode': True  # 標記為E模式
                        })
                
                # 按優先級排序
                sources.sort(key=lambda x: x['priority'])
                return sources  # E模式只處理標記的行，不處理其他邏輯
        
        # 優先級1：ND類型轉出（所有模式一致，E模式除外）
        nd_sources = group_df[group_df['RP Type'] == 'ND']
        for _, row in nd_sources.iterrows():
            if row['SaSa Net Stock'] > 0:  # 只考慮有庫存的店鋪
                # D模式特殊處理：檢查是否為清貨對象（銷量為0）
                last_month_sold = int(row['Last Month Sold Qty'])
                mtd_sold = int(row['MTD Sold Qty'])
                
                if mode == self.mode_d and last_month_sold == 0 and mtd_sold == 0:
                    # D模式：清貨轉貨，針對無銷售記錄的ND店鋪
                    source_type = 'ND清貨轉出'
                else:
                    # 其他模式：正常ND轉出
                    source_type = 'ND轉出'
                
                sources.append({
                    'site': row['Site'],
                    'om': row['OM'],
                    'rp_type': row['RP Type'],
                    'transferable_qty': int(row['SaSa Net Stock']),
                    'priority': 1,
                    'original_stock': int(row['SaSa Net Stock']),
                    'effective_sold_qty': int(row['Effective Sold Qty']),
                    'source_type': source_type,
                    # 添加銷售數據
                    'last_month_sold_qty': last_month_sold,
                    'mtd_sold_qty': mtd_sold
                })

        # 優先級2：RF類型轉出
        rf_sources = group_df[group_df['RP Type'] == 'RF']

        # 找出該Article+OM組合中的最高有效銷量（用於避免從最高動銷店轉出）
        max_sold_qty = rf_sources['Effective Sold Qty'].max() if not rf_sources.empty else 0

        for _, row in rf_sources.iterrows():
            total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
            safety_stock = int(row['Safety Stock'])
            effective_sold = int(row['Effective Sold Qty'])

            # 條件1：(庫存+在途) > Safety Stock
            is_stock_above_safety = total_available > safety_stock

            # 條件2：不是最高銷量店鋪（保護最高動銷店）
            is_not_highest_sold = effective_sold < max_sold_qty

            # 不符合前置條件則略過
            if not (is_stock_above_safety and is_not_highest_sold):
                continue

            # 根據模式計算可轉出數量（已明確階梯：A < C < B）
            if mode == self.mode_a:
                # A模式(保守轉貨)
                # 僅動用明顯過剩庫存，嚴格不跌破 Safety Stock
                base_transferable = total_available - safety_stock
                if base_transferable <= 0:
                    continue

                # 上限：20% total_available，至少 2 件
                upper_limit = max(int(total_available * 0.2), 2)

                actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
                if actual_transferable <= 0:
                    continue

                remaining_stock = int(row['SaSa Net Stock']) - actual_transferable

                # 僅當仍維持 >= Safety Stock 才允許轉出
                if remaining_stock >= safety_stock:
                    source_type = 'RF過剩轉出'
                else:
                    continue

            elif mode == self.mode_c:
                # C模式(重點補0)
                # 中等強度，小量精準支援 0 / 低庫存店，不做大規模抽貨。
                base_transferable = total_available - safety_stock
                if base_transferable <= 0:
                    continue

                # 上限設計：
                # - 比例：最多 30% total_available
                # - 件數：最多 3 件
                # - 並允許至少 1 件（支援補0微調貨）
                ratio_cap = int(total_available * 0.3)
                abs_cap = 3
                # 有效上限不能為負
                capped_ratio = max(ratio_cap, 0)
                raw_upper = min(capped_ratio, abs_cap) if capped_ratio > 0 else abs_cap
                upper_limit = max(1, raw_upper)

                actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
                if actual_transferable <= 0:
                    continue

                remaining_stock = int(row['SaSa Net Stock']) - actual_transferable

                # 類型標記：
                # - 若仍 >= Safety → RF過剩轉出（風險低）
                # - 若略低於 Safety → RF加強轉出（為重點補0作有限犧牲）
                if remaining_stock >= safety_stock:
                    source_type = 'RF過剩轉出'
                else:
                    source_type = 'RF加強轉出'

            else:
                # B模式(加強轉貨)
                # 最 aggressive：最大釋放，多於 C 模式，並可在可控範圍下下探 Safety。
                base_transferable = total_available - safety_stock
                if base_transferable <= 0:
                    continue

                # 上限：最多 50% total_available，至少 2 件
                upper_limit = max(int(total_available * 0.5), 2)

                actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
                if actual_transferable <= 0:
                    continue

                remaining_stock = int(row['SaSa Net Stock']) - actual_transferable

                # 類型標記：
                # - 若仍 >= Safety → RF過剩轉出
                # - 若 < Safety → RF加強轉出（接受更強調撥出）
                if remaining_stock >= safety_stock:
                    source_type = 'RF過剩轉出'
                else:
                    source_type = 'RF加強轉出'

            # 加入可轉出來源（所有模式共用）
            if actual_transferable > 0:
                sources.append({
                    'site': row['Site'],
                    'om': row['OM'],
                    'rp_type': row['RP Type'],
                    'transferable_qty': int(actual_transferable),
                    'priority': 2,
                    'original_stock': int(row['SaSa Net Stock']),
                    'effective_sold_qty': effective_sold,
                    'source_type': source_type,
                    # 添加銷售數據
                    'last_month_sold_qty': int(row['Last Month Sold Qty']),
                    'mtd_sold_qty': int(row['MTD Sold Qty'])
                })

        # 按優先級排序（ND優先，RF其次）
        sources.sort(key=lambda x: x['priority'])

        return sources
    
    def identify_destinations(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        """
        識別接收候選店鋪
        
        Args:
            group_df: 按Article和OM分組的DataFrame
            mode: 轉貨模式（保守轉貨、加強轉貨、重點補0、清貨轉貨、強制轉出或目標優化）
            
        Returns:
            接收候選店鋪列表
        """
        destinations = []
        
        # 只考慮RF類型店鋪，明確排除ND類型店鋪（ND店鋪在所有模式下都只能轉出，不能接收）
        rf_destinations = group_df[(group_df['RP Type'] == 'RF') & (group_df['RP Type'] != 'ND')]

        # F模式特殊處理：Target數字優先接收，其餘店鋪按C模式補0
        if mode == self.mode_f:
            if 'Target' in rf_destinations.columns:
                target_series = pd.to_numeric(rf_destinations['Target'], errors='coerce')
            else:
                target_series = pd.Series(np.nan, index=rf_destinations.index)

            for idx, row in rf_destinations.iterrows():
                total_available = row['SaSa Net Stock'] + row['Pending Received']
                target_value = target_series.loc[idx]

                # Target數字：優先接收目標
                if pd.notna(target_value) and target_value > 0:
                    target_qty = int(target_value)
                    if total_available < target_qty:
                        needed_qty = target_qty - total_available
                        destinations.append({
                            'site': row['Site'],
                            'om': row['OM'],
                            'rp_type': row['RP Type'],
                            'needed_qty': needed_qty,
                            'priority': 1,
                            'current_stock': row['SaSa Net Stock'],
                            'pending_received': row['Pending Received'],
                            'safety_stock': row['Safety Stock'],
                            'moq': row['MOQ'],
                            'effective_sold_qty': row['Effective Sold Qty'],
                            'dest_type': 'F模式目標接收',
                            'target_qty': target_qty,
                            'received_qty': 0,
                            'last_month_sold_qty': int(row['Last Month Sold Qty']),
                            'mtd_sold_qty': int(row['MTD Sold Qty'])
                        })
                    continue

                # 未標Target的店鋪，按C模式重點補0
                if total_available <= 1:
                    target_qty = max(int(row['Safety Stock'] * 0.5), 3)
                    needed_qty = target_qty - total_available
                    if needed_qty > 0:
                        destinations.append({
                            'site': row['Site'],
                            'om': row['OM'],
                            'rp_type': row['RP Type'],
                            'needed_qty': needed_qty,
                            'priority': 2,
                            'current_stock': row['SaSa Net Stock'],
                            'pending_received': row['Pending Received'],
                            'safety_stock': row['Safety Stock'],
                            'moq': row['MOQ'],
                            'effective_sold_qty': row['Effective Sold Qty'],
                            'dest_type': '重點補0',
                            'target_qty': target_qty,
                            'received_qty': 0,
                            'last_month_sold_qty': int(row['Last Month Sold Qty']),
                            'mtd_sold_qty': int(row['MTD Sold Qty'])
                        })

            destinations.sort(key=lambda x: x['priority'])
            return destinations
        
        # E模式特殊處理：所有RF店鋪都可以接收，上限為Safety Stock的2倍
        if mode == self.mode_e:
            for _, row in rf_destinations.iterrows():
                total_available = row['SaSa Net Stock'] + row['Pending Received']
                safety_stock = int(row['Safety Stock'])
                
                # E模式：接收上限為Safety Stock的2倍
                max_can_receive = safety_stock * 2
                
                # 如果目前庫存低於接收上限，則允許接收
                if total_available < max_can_receive:
                    needed_qty = max_can_receive - total_available
                    
                    destinations.append({
                        'site': row['Site'],
                        'om': row['OM'],
                        'rp_type': row['RP Type'],
                        'needed_qty': needed_qty,
                        'priority': 1,  # E模式所有RF店鋪同優先級
                        'current_stock': row['SaSa Net Stock'],
                        'pending_received': row['Pending Received'],
                        'safety_stock': safety_stock,
                        'moq': row['MOQ'],
                        'effective_sold_qty': row['Effective Sold Qty'],
                        'dest_type': 'E模式接收',
                        'target_qty': max_can_receive,  # 目標為Safety Stock的2倍
                        'received_qty': 0,  # 初始化累計接收數量
                        'last_month_sold_qty': int(row['Last Month Sold Qty']),
                        'mtd_sold_qty': int(row['MTD Sold Qty']),
                        'max_receive_qty': max_can_receive  # 記錄最大接收限制
                    })
            
            # 按優先級排序
            destinations.sort(key=lambda x: x['priority'])
            return destinations
        
        # 找出該Article+OM組合中的最高有效銷量
        max_sold_qty = rf_destinations['Effective Sold Qty'].max() if not rf_destinations.empty else 0
        
        for _, row in rf_destinations.iterrows():
            total_available = row['SaSa Net Stock'] + row['Pending Received']
            
            # C模式特殊處理：針對(SaSa Net Stock+Pending Received)<=1的店鋪
            if mode == self.mode_c and total_available <= 1:
                # 計算需要補充的數量：根據Safety Stock的50%和3件的最高值來確定補充數量
                target_qty = max(int(row['Safety Stock'] * 0.5), 3)
                needed_qty = target_qty - total_available
                
                if needed_qty > 0:
                    destinations.append({
                        'site': row['Site'],
                        'om': row['OM'],
                        'rp_type': row['RP Type'],
                        'needed_qty': needed_qty,
                        'priority': 1,  # C模式中優先級最高
                        'current_stock': row['SaSa Net Stock'],
                        'pending_received': row['Pending Received'],
                        'safety_stock': row['Safety Stock'],
                        'moq': row['MOQ'],
                        'effective_sold_qty': row['Effective Sold Qty'],
                        'dest_type': '重點補0',
                        'target_qty': target_qty,  # 添加目標數量信息
                        'received_qty': 0,  # 初始化累計接收數量
                        # 添加銷售數據
                        'last_month_sold_qty': int(row['Last Month Sold Qty']),
                        'mtd_sold_qty': int(row['MTD Sold Qty'])
                    })
                continue
            
            # A和B模式的常規處理
            # 優先級1：緊急缺貨補貨
            is_no_stock = row['SaSa Net Stock'] == 0
            has_sales_history = row['Effective Sold Qty'] > 0
            
            if is_no_stock and has_sales_history:
                needed_qty = row['Safety Stock']
                destinations.append({
                    'site': row['Site'],
                    'om': row['OM'],
                    'rp_type': row['RP Type'],
                    'needed_qty': needed_qty,
                    'priority': 1,
                    'current_stock': row['SaSa Net Stock'],
                    'pending_received': row['Pending Received'],
                    'safety_stock': row['Safety Stock'],
                    'moq': row['MOQ'],
                    'effective_sold_qty': row['Effective Sold Qty'],
                    'dest_type': '緊急缺貨補貨',
                    'target_qty': needed_qty,  # 添加目標數量信息
                    'received_qty': 0,  # 初始化累計接收數量
                    # 添加銷售數據
                    'last_month_sold_qty': int(row['Last Month Sold Qty']),
                    'mtd_sold_qty': int(row['MTD Sold Qty'])
                })
                continue
            
            # 優先級2：潛在缺貨補貨
            is_insufficient_stock = total_available < row['Safety Stock']
            is_highest_sold = row['Effective Sold Qty'] == max_sold_qty
            
            if is_insufficient_stock and is_highest_sold:
                needed_qty = row['Safety Stock'] - total_available
                destinations.append({
                    'site': row['Site'],
                    'om': row['OM'],
                    'rp_type': row['RP Type'],
                    'needed_qty': needed_qty,
                    'priority': 2,
                    'current_stock': row['SaSa Net Stock'],
                    'pending_received': row['Pending Received'],
                    'safety_stock': row['Safety Stock'],
                    'moq': row['MOQ'],
                    'effective_sold_qty': row['Effective Sold Qty'],
                    'dest_type': '潛在缺貨補貨',
                    'target_qty': row['Safety Stock'],  # 添加目標數量信息
                    'received_qty': 0,  # 初始化累計接收數量
                    # 添加銷售數據
                    'last_month_sold_qty': int(row['Last Month Sold Qty']),
                    'mtd_sold_qty': int(row['MTD Sold Qty'])
                })
        
        # 按優先級排序
        destinations.sort(key=lambda x: x['priority'])
        
        return destinations
    
    def match_transfers(self, article: str, om: str, sources: List[Dict], 
                       destinations: List[Dict], product_desc: str, mode: str) -> List[Dict]:
        """
        執行轉出與接收的匹配
        
        Args:
            article: 商品編號
            om: OM編號
            sources: 轉出候選店鋪列表
            destinations: 接收候選店鋪列表
            product_desc: 商品描述
            mode: 轉貨模式
            
        Returns:
            匹配成功的調貨建議列表
        """
        recommendations = []
        
        # E模式特殊處理：優先級和OM匹配邏輯
        if mode == self.mode_e:
            return self._match_transfers_e_mode(sources, destinations, article, om, product_desc, group_df)

        # F模式特殊處理：Target優先接收 + 跨OM匹配
        if mode == self.mode_f:
            return self._match_transfers_f_mode(sources, destinations, article, product_desc)
        
        # 複製源和目的地列表，避免修改原始數據
        temp_sources = [s.copy() for s in sources]
        temp_destinations = [d.copy() for d in destinations]
        
        # 記錄已經作為轉出店鋪的站點，避免它們同時作為接收店鋪
        transfer_sites = set()
        
        # 記錄接收店鋪的累計接收數量
        received_qty_by_site = {}
        
        # 按優先級順序進行匹配
        # 1. ND轉出 -> 緊急缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 1, 1, transfer_sites, received_qty_by_site, mode)
        
        # 2. ND轉出 -> 潛在缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 1, 2, transfer_sites, received_qty_by_site, mode)
        
        # 3. RF過剩轉出 -> 緊急缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF過剩轉出')
        
        # 4. RF過剩轉出 -> 潛在缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 2, 2, transfer_sites, received_qty_by_site, mode, 'RF過剩轉出')
        
        # 5. RF加強轉出 -> 緊急缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF加強轉出')
        
        # 6. RF加強轉出 -> 潛在缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 2, 2, transfer_sites, received_qty_by_site, mode, 'RF加強轉出')
        
        # 7. C模式特殊處理：RF轉出 -> 重點補0
        if mode == self.mode_c:
            self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                                   article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, None, '重點補0')
        
        return recommendations

    def _match_transfers_f_mode(self, sources: List[Dict], destinations: List[Dict],
                               article: str, product_desc: str) -> List[Dict]:
        """
        F模式特殊匹配邏輯：
        1. Target數字優先接收
        2. 允許跨OM配對
        3. HD店鋪不能轉到HA/HB/HC
        4. 嚴格避免同一SKU的轉出店鋪同時接收
        5. 總轉移量不超過總需求量
        """
        recommendations = []

        temp_sources = [s.copy() for s in sources]
        temp_destinations = [d.copy() for d in destinations]

        # 先將所有source sites加入transfer_sites，避免同時接收
        transfer_sites = set([s['site'] for s in temp_sources if s['transferable_qty'] > 0])

        # 接收店鋪累計接收數量
        received_qty_by_site = {}

        total_needed = sum([int(d.get('needed_qty', 0)) for d in temp_destinations])
        remaining_demand = total_needed

        for source in temp_sources:
            if source['transferable_qty'] <= 0 or remaining_demand <= 0:
                continue

            for dest in temp_destinations:
                if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0 or remaining_demand <= 0:
                    continue

                if source['site'] == dest['site']:
                    continue
                if dest['site'] in transfer_sites:
                    continue
                if dest.get('rp_type') == 'ND':
                    continue

                # HD限制檢查：HD店鋪不能轉去HA/HB/HC店鋪
                source_site = source['site']
                is_source_hd = source_site.upper().startswith('HD') if isinstance(source_site, str) else False
                if is_source_hd:
                    dest_site_upper = dest['site'].upper() if isinstance(dest['site'], str) else ''
                    if dest_site_upper.startswith(('HA', 'HB', 'HC')):
                        continue

                transfer_qty = min(source['transferable_qty'], dest['needed_qty'], remaining_demand)
                if transfer_qty <= 0:
                    continue

                receive_site_key = f"{dest['site']}_{article}"
                current_received_qty = received_qty_by_site.get(receive_site_key, 0)

                recommendation = {
                    'Article': article,
                    'Product Desc': product_desc,
                    'Transfer OM': source['om'],
                    'Transfer Site': source['site'],
                    'Receive OM': dest['om'],
                    'Receive Site': dest['site'],
                    'Transfer Qty': transfer_qty,
                    'Original Stock': source['original_stock'],
                    'After Transfer Stock': source['original_stock'] - transfer_qty,
                    'Safety Stock': 0,
                    'MOQ': 0,
                    'Source Priority': source['priority'],
                    'Destination Priority': dest['priority'],
                    'Source Type': source['source_type'],
                    'Destination Type': dest['dest_type'],
                    'Notes': self._create_recommendation_note(source, dest, current_received_qty, transfer_qty, self.mode_f),
                    'Transfer Site Last Month Sold Qty': source.get('last_month_sold_qty', 0),
                    'Transfer Site MTD Sold Qty': source.get('mtd_sold_qty', 0),
                    'Receive Site Last Month Sold Qty': dest.get('last_month_sold_qty', 0),
                    'Receive Site MTD Sold Qty': dest.get('mtd_sold_qty', 0),
                    'Receive Original Stock': dest.get('current_stock', 0)
                }

                if 'target_qty' in dest:
                    recommendation['Target Qty'] = dest['target_qty']

                recommendation['Cumulative Received Qty'] = current_received_qty + transfer_qty

                recommendations.append(recommendation)

                received_qty_by_site[receive_site_key] = current_received_qty + transfer_qty

                source['transferable_qty'] -= transfer_qty
                dest['needed_qty'] -= transfer_qty
                remaining_demand -= transfer_qty

                if dest.get('target_qty') is not None and received_qty_by_site[receive_site_key] >= dest['target_qty']:
                    dest['needed_qty'] = 0

        return recommendations
    
    def _match_transfers_e_mode(self, sources: List[Dict], destinations: List[Dict], 
                               article: str, om: str, product_desc: str, 
                               group_df: pd.DataFrame) -> List[Dict]:
        """
        E模式特殊匹配邏輯：
        1. 優先同OM配對
        2. 當該OM所有接收店鋪都無能力接收時，放寬跨OM店鋪接收
        3. 但HD店鋪絕對不能轉去HA/HB/HC的店鋪
        4. 當其他OM未有店舖涉及強制轉出時，可按照C模式照常做重點補0
        5. 嚴格避免同一SKU的轉出店舖同時接收
        
        Args:
            sources: 轉出候選店鋪列表（E模式已標記*ALL*）
            destinations: 接收候選店鋪列表
            article: 商品編號
            om: OM編號
            product_desc: 商品描述
            group_df: 該Article的完整數據DataFrame（用於Phase 3邏輯）
            
        Returns:
            匹配成功的調貨建議列表
        """
        recommendations = []
        
        # 複製源和目的地列表
        temp_sources = [s.copy() for s in sources]
        temp_destinations = [d.copy() for d in destinations]
        
        # 記錄已經作為轉出店鋪的站點
        # 關鍵：先將所有E模式source sites添加到transfer_sites，防止它們同時作為接收方
        transfer_sites = set([s['site'] for s in temp_sources if s['transferable_qty'] > 0])
        
        # 記錄接收店鋪的累計接收數量
        received_qty_by_site = {}
        
        # 記錄E模式強制轉出的來源OM（用於判斷是否切換到C模式）
        e_mode_source_oms = set([s['om'] for s in temp_sources])
        
        # Phase 1: 優先同OM配對
        for source in temp_sources:
            if source['transferable_qty'] <= 0:
                continue
            
            # 找出同OM的接收店鋪
            same_om_dests = [d for d in temp_destinations 
                           if d['om'] == source['om'] and d['needed_qty'] > 0]
            
            # 優先匹配同OM的目標
            for dest in same_om_dests:
                if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0:
                    continue
                
                # 基本檢查
                if source['site'] == dest['site']:
                    continue
                if dest['site'] in transfer_sites:
                    continue
                if dest.get('rp_type') == 'ND':
                    continue
                
                # HD限制檢查：HD店鋪不能轉去HA/HB/HC店鋪
                source_site = source['site']
                is_source_hd = source_site.upper().startswith('HD') if isinstance(source_site, str) else False
                if is_source_hd:
                    dest_site_upper = dest['site'].upper() if isinstance(dest['site'], str) else ''
                    if dest_site_upper.startswith(('HA', 'HB', 'HC')):
                        continue  # 跳過不允許的目標
                
                # 執行轉移
                transfer_qty = min(source['transferable_qty'], dest['needed_qty'])
                
                recommendation = {
                    'Article': article,
                    'Product Desc': product_desc,
                    'Transfer OM': source['om'],
                    'Transfer Site': source['site'],
                    'Receive OM': dest['om'],
                    'Receive Site': dest['site'],
                    'Transfer Qty': transfer_qty,
                    'Original Stock': source['original_stock'],
                    'After Transfer Stock': source['original_stock'] - transfer_qty,
                    'Safety Stock': 0,
                    'MOQ': 0,
                    'Source Priority': source['priority'],
                    'Destination Priority': dest['priority'],
                    'Source Type': source['source_type'],
                    'Destination Type': dest['dest_type'],
                    'Notes': f'E模式強制轉出 - 同OM配對',
                    'Transfer Site Last Month Sold Qty': source.get('last_month_sold_qty', 0),
                    'Transfer Site MTD Sold Qty': source.get('mtd_sold_qty', 0),
                    'Receive Site Last Month Sold Qty': dest.get('last_month_sold_qty', 0),
                    'Receive Site MTD Sold Qty': dest.get('mtd_sold_qty', 0),
                    'Receive Original Stock': dest.get('current_stock', 0)
                }
                
                if 'target_qty' in dest:
                    recommendation['Target Qty'] = dest['target_qty']
                
                recommendations.append(recommendation)
                
                # 更新庫存
                source['transferable_qty'] -= transfer_qty
                dest['needed_qty'] -= transfer_qty
        
        # Phase 2: 當同OM無法完全接收時，跨OM配對（但HD店鋪不能轉去HA/HB/HC）
        for source in temp_sources:
            if source['transferable_qty'] <= 0:
                continue
            
            # 找出可用的跨OM接收店鋪
            source_om = source['om']
            source_site = source['site']
            
            # 檢查轉出店鋪的Site是否以HD開頭（限制規則）
            is_source_hd = source_site.upper().startswith('HD') if isinstance(source_site, str) else False
            
            for dest in temp_destinations:
                if dest['needed_qty'] <= 0:
                    continue
                
                # 跳過同OM的目標（已在Phase 1處理）
                if dest['om'] == source_om:
                    continue
                
                # 基本檢查
                if source['site'] == dest['site']:
                    continue
                if dest['site'] in transfer_sites:
                    continue
                if dest.get('rp_type') == 'ND':
                    continue
                
                # HD限制檢查：HD店鋪不能轉去HA/HB/HC店鋪
                if is_source_hd:
                    dest_site_upper = dest['site'].upper() if isinstance(dest['site'], str) else ''
                    if dest_site_upper.startswith(('HA', 'HB', 'HC')):
                        continue  # 跳過不允許的目標
                
                # 執行轉移
                transfer_qty = min(source['transferable_qty'], dest['needed_qty'])
                
                recommendation = {
                    'Article': article,
                    'Product Desc': product_desc,
                    'Transfer OM': source['om'],
                    'Transfer Site': source['site'],
                    'Receive OM': dest['om'],
                    'Receive Site': dest['site'],
                    'Transfer Qty': transfer_qty,
                    'Original Stock': source['original_stock'],
                    'After Transfer Stock': source['original_stock'] - transfer_qty,
                    'Safety Stock': 0,
                    'MOQ': 0,
                    'Source Priority': source['priority'],
                    'Destination Priority': dest['priority'],
                    'Source Type': source['source_type'],
                    'Destination Type': dest['dest_type'],
                    'Notes': f'E模式強制轉出 - 跨OM配對',
                    'Transfer Site Last Month Sold Qty': source.get('last_month_sold_qty', 0),
                    'Transfer Site MTD Sold Qty': source.get('mtd_sold_qty', 0),
                    'Receive Site Last Month Sold Qty': dest.get('last_month_sold_qty', 0),
                    'Receive Site MTD Sold Qty': dest.get('mtd_sold_qty', 0),
                    'Receive Original Stock': dest.get('current_stock', 0)
                }
                
                if 'target_qty' in dest:
                    recommendation['Target Qty'] = dest['target_qty']
                
                recommendations.append(recommendation)
                
                # 更新庫存
                source['transferable_qty'] -= transfer_qty
                dest['needed_qty'] -= transfer_qty
                
                # 如果源已耗盡，跳出
                if source['transferable_qty'] <= 0:
                    break
        
        # Phase 3: C模式回退邏輯 - 當其他OM未有店舖涉及強制轉出時，可按照C模式照常做重點補0
        
        # 關鍵：收集所有非E模式OM的接收目標sites（無論其needed_qty當前狀態）
        # 這些sites不應該再成為C模式的sources，因為它們已經被分配為接收方
        non_e_mode_receiving_sites = set([d['site'] for d in temp_destinations 
                                          if d['om'] not in e_mode_source_oms])
        
        # 篩選非E模式OM的未滿足接收需求
        unfulfilled_dests = [d for d in temp_destinations 
                            if d['needed_qty'] > 0 
                            and d['om'] not in e_mode_source_oms
                            and d['site'] not in transfer_sites]
        
        if unfulfilled_dests:
            # 識別非E模式OM的RF過剩店舖，用於C模式轉出
            c_mode_sources = []
            
            for _, row in group_df[(group_df['RP Type'] == 'RF')].iterrows():
                # 跳過E模式OM的店舖
                if row['OM'] in e_mode_source_oms:
                    continue
                
                # 跳過已經作為轉出店舖的（關鍵：避免轉出店舖同時接收）
                if row['Site'] in transfer_sites:
                    continue
                
                # 關鍵：不能同時作為接收目標的sites
                if row['Site'] in non_e_mode_receiving_sites:
                    continue
                
                total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
                safety_stock = int(row['Safety Stock'])
                effective_sold = int(row['Effective Sold Qty'])
                
                # 找出該OM的最高銷量（保護最高動銷店）
                om_rf_stores = group_df[(group_df['RP Type'] == 'RF') & (group_df['OM'] == row['OM'])]
                max_sold_qty = om_rf_stores['Effective Sold Qty'].max() if not om_rf_stores.empty else 0
                
                # C模式條件：庫存高於安全庫存，且不是最高銷量店
                is_stock_above_safety = total_available > safety_stock
                is_not_highest_sold = effective_sold < max_sold_qty
                
                if is_stock_above_safety and is_not_highest_sold:
                    base_transferable = total_available - safety_stock
                    if base_transferable <= 0:
                        continue
                    
                    # C模式上限：30% total_available，最多3件，至少1件
                    ratio_cap = int(total_available * 0.3)
                    abs_cap = 3
                    capped_ratio = max(ratio_cap, 0)
                    raw_upper = min(capped_ratio, abs_cap) if capped_ratio > 0 else abs_cap
                    upper_limit = max(1, raw_upper)
                    
                    actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
                    
                    if actual_transferable > 0:
                        remaining_stock = int(row['SaSa Net Stock']) - actual_transferable
                        
                        # 判斷類型
                        if remaining_stock >= safety_stock:
                            source_type = 'RF過剩轉出(C模式回退)'
                        else:
                            source_type = 'RF加強轉出(C模式回退)'
                        
                        c_mode_sources.append({
                            'site': row['Site'],
                            'om': row['OM'],
                            'rp_type': row['RP Type'],
                            'transferable_qty': actual_transferable,
                            'priority': 2,
                            'original_stock': int(row['SaSa Net Stock']),
                            'effective_sold_qty': effective_sold,
                            'source_type': source_type,
                            'last_month_sold_qty': int(row['Last Month Sold Qty']),
                            'mtd_sold_qty': int(row['MTD Sold Qty'])
                        })
            
            # 執行C模式匹配
            for source in c_mode_sources:
                if source['transferable_qty'] <= 0:
                    continue
                
                # 標記為轉出店舖
                transfer_sites.add(source['site'])
                
                for dest in unfulfilled_dests:
                    if dest['needed_qty'] <= 0:
                        continue
                    
                    # 避免同一店舖自我調貨
                    if source['site'] == dest['site']:
                        continue
                    
                    # 關鍵：嚴格避免轉出店舖同時作為接收店舖
                    if dest['site'] in transfer_sites:
                        continue
                    
                    # 確保接收店舖不是ND類型
                    if dest.get('rp_type') == 'ND':
                        continue
                    
                    # HD限制檢查：HD店鋪不能轉去HA/HB/HC店鋪
                    source_site = source['site']
                    is_source_hd = source_site.upper().startswith('HD') if isinstance(source_site, str) else False
                    if is_source_hd:
                        dest_site_upper = dest['site'].upper() if isinstance(dest['site'], str) else ''
                        if dest_site_upper.startswith(('HA', 'HB', 'HC')):
                            continue  # 跳過不允許的目標
                    
                    # 檢查累計接收數量，避免過量接收
                    receive_site_key = f"{dest['site']}_{article}"
                    current_received = received_qty_by_site.get(receive_site_key, 0)
                    
                    # 對於E模式接收店舖，檢查是否已達到上限（2倍安全庫存）
                    if dest.get('dest_type') == 'E模式接收':
                        max_receive = dest.get('max_receive_qty', dest.get('target_qty', float('inf')))
                        if current_received >= max_receive:
                            continue  # 已達上限，跳過
                        # 計算剩餘可接收量
                        remaining_capacity = max_receive - current_received
                        transfer_qty = min(source['transferable_qty'], dest['needed_qty'], remaining_capacity)
                    else:
                        transfer_qty = min(source['transferable_qty'], dest['needed_qty'])
                    
                    if transfer_qty <= 0:
                        continue
                    
                    # 創建建議
                    recommendation = {
                        'Article': article,
                        'Product Desc': product_desc,
                        'Transfer OM': source['om'],
                        'Transfer Site': source['site'],
                        'Receive OM': dest['om'],
                        'Receive Site': dest['site'],
                        'Transfer Qty': transfer_qty,
                        'Original Stock': source['original_stock'],
                        'After Transfer Stock': source['original_stock'] - transfer_qty,
                        'Safety Stock': 0,
                        'MOQ': 0,
                        'Source Priority': source['priority'],
                        'Destination Priority': dest['priority'],
                        'Source Type': source['source_type'],
                        'Destination Type': dest['dest_type'],
                        'Notes': f'E模式Phase3 - C模式回退（非E模式OM的重點補0）',
                        'Transfer Site Last Month Sold Qty': source.get('last_month_sold_qty', 0),
                        'Transfer Site MTD Sold Qty': source.get('mtd_sold_qty', 0),
                        'Receive Site Last Month Sold Qty': dest.get('last_month_sold_qty', 0),
                        'Receive Site MTD Sold Qty': dest.get('mtd_sold_qty', 0),
                        'Receive Original Stock': dest.get('current_stock', 0)
                    }
                    
                    if 'target_qty' in dest:
                        recommendation['Target Qty'] = dest['target_qty']
                    
                    recommendations.append(recommendation)
                    
                    # 更新數量
                    source['transferable_qty'] -= transfer_qty
                    dest['needed_qty'] -= transfer_qty
                    received_qty_by_site[receive_site_key] = current_received + transfer_qty
                    
                    if source['transferable_qty'] <= 0:
                        break
        
        return recommendations
    
    def _match_by_priority(self, sources: List[Dict], destinations: List[Dict], 
                          recommendations: List[Dict], article: str, group_id: str, 
                          product_desc: str, source_priority: int, dest_priority: int,
                          transfer_sites: set, received_qty_by_site: Dict,
                          mode: str,
                          source_type_filter: Optional[str] = None,
                          dest_type_filter: Optional[str] = None):
        """
        按指定優先級進行匹配
        
        Args:
            sources: 轉出候選店鋪列表
            destinations: 接收候選店鋪列表
            recommendations: 調貨建議列表
            article: 商品編號
            group_id: 分組ID（OM）
            product_desc: 商品描述
            source_priority: 轉出優先級
            dest_priority: 接收優先級
            transfer_sites: 已經作為轉出店鋪的站點集合
            received_qty_by_site: 接收店鋪的累計接收數量字典
            source_type_filter: 轉出類型過濾器（可選）
            dest_type_filter: 接收類型過濾器（可選）
        """
        # 篩選指定優先級的源和目的地
        filtered_sources = [s for s in sources if s['priority'] == source_priority and s['transferable_qty'] > 0]
        
        # 如果指定了轉出類型過濾器，則按類型篩選
        if source_type_filter:
            filtered_sources = [s for s in filtered_sources if s['source_type'] == source_type_filter]
        
        filtered_destinations = [d for d in destinations if d['priority'] == dest_priority and d['needed_qty'] > 0]
        
        # 如果指定了接收類型過濾器，則按類型篩選
        if dest_type_filter:
            filtered_destinations = [d for d in filtered_destinations if d['dest_type'] == dest_type_filter]
        
        # 執行匹配
        for source in filtered_sources:
            # 將當前轉出店鋪添加到轉出店鋪集合
            transfer_sites.add(source['site'])
            
            for dest in filtered_destinations:
                if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0:
                    continue
                
                # 避免同一店鋪自我調貨
                if source['site'] == dest['site']:
                    continue
                
                # 避免轉出店鋪同時作為接收店鋪
                if dest['site'] in transfer_sites:
                    continue
                
                # 防禦性檢查：確保接收店鋪不是ND類型（ND店鋪在所有模式下都只能轉出，不能接收）
                if dest.get('rp_type') == 'ND':
                    continue
                
                # 檢查接收店鋪是否已達到目標數量
                receive_site_key = f"{dest['site']}_{article}"
                current_received_qty = received_qty_by_site.get(receive_site_key, 0)
                
                # 對於C模式(重點補0)，檢查累計接收數量是否達到目標
                if dest['dest_type'] == '重點補0':
                    # 如果累計接收數量已達到目標數量，跳過此接收店鋪
                    if current_received_qty >= dest['target_qty']:
                        continue
                
                # 確定轉移數量
                # 對於C模式(重點補0)，考慮累計接收數量
                if dest['dest_type'] == '重點補0':
                    # 計算還需要接收的數量
                    remaining_needed = dest['target_qty'] - current_received_qty
                    transfer_qty = min(source['transferable_qty'], dest['needed_qty'], remaining_needed)
                else:
                    # A、B和D模式，使用原始邏輯
                    transfer_qty = min(source['transferable_qty'], dest['needed_qty'])
                
                # --- 數量調整邏輯 (D模式放寬限制以避免1件餘貨) ---
                
                # 1. D模式特殊處理：避免ND轉出後剩餘1件 (涵蓋ND清貨轉出和一般ND轉出)
                if mode == self.mode_d and source['rp_type'] == 'ND':
                    remaining_after_transfer = source['original_stock'] - transfer_qty
                    if remaining_after_transfer == 1:
                        # 嘗試多轉1件，使剩餘為0件 (放寬接收店鋪的 needed_qty 限制)
                        if source['transferable_qty'] >= transfer_qty + 1:
                            transfer_qty += 1
                        # 如果無法多轉1件，則少轉1件，使剩餘為2件
                        elif transfer_qty > 1:
                            transfer_qty -= 1
                
                # 2. 調貨數量優化：如果只有1件，嘗試調高到2件 (避免小額調撥)
                if transfer_qty == 1 and source['transferable_qty'] >= 2:
                    # 檢查是否為允許優化的類型
                    if source['source_type'] in ['ND轉出', 'ND清貨轉出', 'RF加強轉出']:
                        potential_qty = 2
                        remaining_after_opt = source['original_stock'] - potential_qty
                        
                        # 在模式D下，ND店鋪要特別避免優化後留下1件餘貨
                        if mode == self.mode_d and source['rp_type'] == 'ND' and remaining_after_opt == 1:
                            if source['transferable_qty'] >= 3:
                                transfer_qty = 3
                            else:
                                # 如果不能調到3，則保持1件 (避免1件餘貨優先於避免小額調撥)
                                pass
                        else:
                            # 其他情況正常優化到2件
                            transfer_qty = 2
                
                # 創建調貨建議
                recommendation = {
                    'Article': article,
                    'Product Desc': product_desc,
                    'Transfer OM': source['om'],
                    'Transfer Site': source['site'],
                    'Receive OM': dest['om'],
                    'Receive Site': dest['site'],
                    'Transfer Qty': transfer_qty,
                    'Original Stock': source['original_stock'],
                    'After Transfer Stock': source['original_stock'] - transfer_qty,
                    'Safety Stock': 0,  # 需要從原始數據獲取
                    'MOQ': 0,  # 需要從原始數據獲取
                    'Source Priority': source['priority'],
                    'Destination Priority': dest['priority'],
                    'Source Type': source['source_type'],
                    'Destination Type': dest['dest_type'],
                    'Notes': self._create_recommendation_note(source, dest, current_received_qty, transfer_qty, mode),
                    # 新增銷售數據欄位
                    'Transfer Site Last Month Sold Qty': source.get('last_month_sold_qty', 0),
                    'Transfer Site MTD Sold Qty': source.get('mtd_sold_qty', 0),
                    'Receive Site Last Month Sold Qty': dest.get('last_month_sold_qty', 0),
                    'Receive Site MTD Sold Qty': dest.get('mtd_sold_qty', 0),
                    # 新增Receive Original Stock欄位
                    'Receive Original Stock': dest.get('current_stock', 0)
                }
                
                # 添加目標數量信息（如果有）
                if 'target_qty' in dest:
                    recommendation['Target Qty'] = dest['target_qty']
                
                # 添加累計接收數量信息
                recommendation['Cumulative Received Qty'] = current_received_qty + transfer_qty
                
                recommendations.append(recommendation)
                
                # 更新接收店鋪的累計接收數量
                received_qty_by_site[receive_site_key] = current_received_qty + transfer_qty
                
                # 更新剩餘可轉出數量和需求數量
                source['transferable_qty'] -= transfer_qty
                dest['needed_qty'] -= transfer_qty
                
                # 對於C模式(重點補0)，如果累計接收數量已達到目標，將需求設為0
                if dest['dest_type'] == '重點補0' and received_qty_by_site[receive_site_key] >= dest['target_qty']:
                    dest['needed_qty'] = 0
    
    def generate_transfer_recommendations(self, df: pd.DataFrame, mode: str) -> List[Dict]:
        """
        生成所有調貨建議
        
        Args:
            df: 預處理後的DataFrame
            mode: A模式(保守轉貨)、B模式(加強轉貨)、C模式(重點補0)、D模式(清貨轉貨)、E模式(強制轉出)或F模式(目標優化)
            
        Returns:
            調貨建議列表
        """
        logger.info(f"開始生成調貨建議 - {mode}")
        
        # 驗證模式
        if mode not in [self.mode_a, self.mode_b, self.mode_c, self.mode_d, self.mode_e, self.mode_f]:
            raise ValueError(f"無效的轉貨模式: {mode}")
        
        # 根據模式選擇分組方式
        if mode in [self.mode_e, self.mode_f]:
            # E/F模式支持跨OM配對，因此僅按Article分組
            grouped = df.groupby(['Article'])
        else:
            # 其他模式按Article和OM分組
            grouped = df.groupby(['Article', 'OM'])
        
        all_recommendations = []
        
        # 記錄所有已經作為轉出店鋪的站點，避免它們同時作為接收店鋪
        global_transfer_sites = set()
        
        # 記錄所有接收店鋪的累計接收數量
        global_received_qty_by_site = {}
        
        for group_keys, group_df in grouped:
            # 獲取商品描述
            product_desc = group_df['Article Description'].iloc[0] if 'Article Description' in group_df.columns else ""
            
            # 識別轉出候選店鋪
            sources = self.identify_sources(group_df, mode)
            
            # 識別接收候選店鋪
            destinations = self.identify_destinations(group_df, mode)
            
            # E/F模式特殊處理：從destinations中過濾掉同時作為轉出源的店鋪
            if mode in [self.mode_e, self.mode_f]:
                source_sites = set([s['site'] for s in sources])
                destinations = [d for d in destinations if d['site'] not in source_sites]
            
            # 執行匹配
            if mode in [self.mode_e, self.mode_f]:
                article = group_keys[0] if isinstance(group_keys, (list, tuple)) else group_keys
                om = "Multiple" # E/F模式下OM由source/dest決定
            else:
                article, om = group_keys
            
            # E模式需要傳入group_df以支持Phase 3邏輯
            if mode == self.mode_e:
                recommendations = self._match_transfers_e_mode(sources, destinations, article, om, product_desc, group_df)
            elif mode == self.mode_f:
                recommendations = self._match_transfers_f_mode(sources, destinations, article, product_desc)
            else:
                recommendations = self.match_transfers(article, om, sources, destinations, product_desc, mode)
            
            # 更新全局轉出店鋪集合
            for rec in recommendations:
                global_transfer_sites.add(rec['Transfer Site'])
                
                # 更新全局累計接收數量
                receive_site_key = f"{rec['Receive Site']}_{rec['Article']}"
                current_received_qty = global_received_qty_by_site.get(receive_site_key, 0)
                global_received_qty_by_site[receive_site_key] = current_received_qty + rec['Transfer Qty']
            
            # 更新安全庫存和MOQ信息
            for rec in recommendations:
                # 從原始數據中獲取安全庫存和MOQ
                source_data = df[(df['Article'] == rec['Article']) & (df['Site'] == rec['Transfer Site'])]
                if not source_data.empty:
                    rec['Safety Stock'] = source_data['Safety Stock'].iloc[0]
                    rec['MOQ'] = source_data['MOQ'].iloc[0]
            
            all_recommendations.extend(recommendations)
        
        logger.info(f"共生成 {len(all_recommendations)} 條調貨建議")
        
        self.transfer_recommendations = all_recommendations
        return all_recommendations
    
    def perform_quality_checks(self, df: pd.DataFrame) -> bool:
        """
        執行質量檢查
        
        Args:
            df: 原始數據DataFrame
            
        Returns:
            質量檢查是否通過
        """
        logger.info("開始執行質量檢查")
        
        self.quality_errors = []
        self.quality_check_passed = True
        
        # 檢查1：轉出與接收的Article必須完全一致
        for rec in self.transfer_recommendations:
            if 'Article' not in rec:
                self.quality_errors.append(f"調貨建議中缺少Article欄位: {rec}")
                self.quality_check_passed = False
        
        # 檢查2：Transfer Qty必須為正整數
        for rec in self.transfer_recommendations:
            if not isinstance(rec['Transfer Qty'], int) or rec['Transfer Qty'] <= 0:
                self.quality_errors.append(f"轉移數量必須為正整數: {rec}")
                self.quality_check_passed = False
        
        # 檢查3：Transfer Qty不得超過轉出店鋪的原始SaSa Net Stock
        for rec in self.transfer_recommendations:
            transfer_site = rec['Transfer Site']
            article = rec['Article']
            
            # 查找轉出店鋪的原始庫存
            source_data = df[(df['Article'] == article) & (df['Site'] == transfer_site)]
            if not source_data.empty:
                original_stock = source_data['SaSa Net Stock'].iloc[0]
                if rec['Transfer Qty'] > original_stock:
                    self.quality_errors.append(f"轉移數量超過原始庫存: {rec}")
                    self.quality_check_passed = False
        
        # 檢查4：Transfer Site和Receive Site不能相同
        for rec in self.transfer_recommendations:
            if rec['Transfer Site'] == rec['Receive Site']:
                self.quality_errors.append(f"轉出店鋪和接收店鋪不能相同: {rec}")
                self.quality_check_passed = False
        
        # 檢查5：最終輸出的Article欄位必須是12位文本格式
        for rec in self.transfer_recommendations:
            if not isinstance(rec['Article'], str) or len(rec['Article']) != 12:
                self.quality_errors.append(f"Article欄位必須是12位文本格式: {rec}")
                self.quality_check_passed = False
        
        # 檢查6：同一SKU的轉出店鋪不能同時作為接收店鋪
        transfer_sites_by_article = {}
        receive_sites_by_article = {}
        
        for rec in self.transfer_recommendations:
            article = rec['Article']
            
            # 記錄轉出店鋪
            if article not in transfer_sites_by_article:
                transfer_sites_by_article[article] = set()
            transfer_sites_by_article[article].add(rec['Transfer Site'])
            
            # 記錄接收店鋪
            if article not in receive_sites_by_article:
                receive_sites_by_article[article] = set()
            receive_sites_by_article[article].add(rec['Receive Site'])
        
        # 檢查是否有重疊
        for article in transfer_sites_by_article:
            if article in receive_sites_by_article:
                overlap = transfer_sites_by_article[article] & receive_sites_by_article[article]
                if overlap:
                    self.quality_errors.append(f"同一SKU {article} 的轉出店鋪同時作為接收店鋪: {overlap}")
                    self.quality_check_passed = False
        
        # 檢查7：接收店鋪不能是ND類型（ND店鋪在所有模式下都只能轉出，不能接收）
        for rec in self.transfer_recommendations:
            receive_site = rec['Receive Site']
            article = rec['Article']
            receive_data = df[(df['Article'] == article) & (df['Site'] == receive_site)]
            if not receive_data.empty:
                rp_type = receive_data['RP Type'].iloc[0]
                if rp_type == 'ND':
                    self.quality_errors.append(f"ND店鋪不能作為接收店鋪 - Site: {receive_site}, Article: {article}")
                    self.quality_check_passed = False
        
        # 檢查8：對於C模式(重點補0)，檢查接收店鋪的累計接收數量是否超過目標數量
        receive_site_stats = {}
        for rec in self.transfer_recommendations:
            if rec.get('Destination Type') == '重點補0':
                key = (rec['Article'], rec['Receive Site'])
                if key not in receive_site_stats:
                    receive_site_stats[key] = {
                        'target_qty': rec.get('Target Qty', 0),
                        'total_received': 0
                    }
                receive_site_stats[key]['total_received'] += rec['Transfer Qty']
        
        # 檢查是否有超過目標數量的情況
        for key, stats in receive_site_stats.items():
            article, site = key
            if stats['total_received'] > stats['target_qty']:
                self.quality_errors.append(f"同一SKU {article} 的接收店鋪 {site} 累計接收數量超過目標數量: {stats['total_received']} > {stats['target_qty']}")
                self.quality_check_passed = False
        
        if self.quality_check_passed:
            logger.info("質量檢查通過")
        else:
            logger.error(f"質量檢查失敗，發現 {len(self.quality_errors)} 個錯誤")
            for error in self.quality_errors:
                logger.error(error)
        
        return self.quality_check_passed
    
    def get_transfer_statistics(self) -> Dict:
        """
        獲取調貨統計信息
        
        Returns:
            統計信息字典
        """
        if not self.transfer_recommendations:
            return {}
        
        # 總調貨建議數量
        total_recommendations = len(self.transfer_recommendations)
        
        # 總調貨件數
        total_transfer_qty = sum(rec['Transfer Qty'] for rec in self.transfer_recommendations)
        
        # 涉及產品數量
        unique_articles = len(set(rec['Article'] for rec in self.transfer_recommendations))
        
        # 涉及OM數量
        unique_oms = len(set(rec['Transfer OM'] for rec in self.transfer_recommendations))
        
        # 按Article統計
        article_stats = {}
        for rec in self.transfer_recommendations:
            article = rec['Article']
            if article not in article_stats:
                article_stats[article] = {
                    'total_qty': 0,
                    'count': 0,
                    'oms': set()
                }
            article_stats[article]['total_qty'] += rec['Transfer Qty']
            article_stats[article]['count'] += 1
            article_stats[article]['oms'].add(rec['Transfer OM'])
        
        # 轉換set為count
        for article in article_stats:
            article_stats[article]['om_count'] = len(article_stats[article]['oms'])
        
        # 按OM統計
        om_stats = {}
        for rec in self.transfer_recommendations:
            om = rec['Transfer OM']
            if om not in om_stats:
                om_stats[om] = {
                    'total_qty': 0,
                    'count': 0,
                    'articles': set()
                }
            om_stats[om]['total_qty'] += rec['Transfer Qty']
            om_stats[om]['count'] += 1
            om_stats[om]['articles'].add(rec['Article'])
        
        # 轉換set為count
        for om in om_stats:
            om_stats[om]['article_count'] = len(om_stats[om]['articles'])
        
        # 轉出類型分析
        source_type_stats = {}
        for rec in self.transfer_recommendations:
            source_type = rec.get('Source Type', 'Unknown')
            if source_type not in source_type_stats:
                source_type_stats[source_type] = {'count': 0, 'qty': 0}
            source_type_stats[source_type]['count'] += 1
            source_type_stats[source_type]['qty'] += rec['Transfer Qty']
        
        # 接收類型分析
        dest_type_stats = {}
        for rec in self.transfer_recommendations:
            dest_type = rec.get('Destination Type', 'Unknown')
            if dest_type not in dest_type_stats:
                dest_type_stats[dest_type] = {'count': 0, 'qty': 0}
            dest_type_stats[dest_type]['count'] += 1
            dest_type_stats[dest_type]['qty'] += rec['Transfer Qty']
        
        return {
            'total_recommendations': total_recommendations,
            'total_transfer_qty': total_transfer_qty,
            'unique_articles': unique_articles,
            'unique_oms': unique_oms,
            'article_stats': article_stats,
            'om_stats': om_stats,
            'source_type_stats': source_type_stats,
            'dest_type_stats': dest_type_stats
        }
    def _create_recommendation_note(self, source: Dict, dest: Dict, current_received_qty: int, transfer_qty: int, mode: str) -> str:
        """
        創建調貨建議的Notes欄位內容
        
        Args:
            source: 轉出店鋪信息
            dest: 接收店鋪信息
            current_received_qty: 當前累計接收數量
            transfer_qty: 本次轉移數量
            mode: 轉貨模式
            
        Returns:
            詳細的Notes欄位內容
        """
        notes_parts = []
        
        # 1. 轉出店鋪分類
        notes_parts.append(f"【轉出分類: {source['source_type']}】")
        
        # 2. 接收店鋪分類
        notes_parts.append(f"【接收分類: {dest['dest_type']}】")
        
        # 3. 優先級信息
        if source['priority'] == 1:
            priority_desc = "ND轉出(最高優先級)"
        else:
            priority_desc = "RF轉出"
        notes_parts.append(f"【轉出優先級: {priority_desc}】")
        
        if dest['priority'] == 1:
            priority_desc = "接收(最高優先級)"
        else:
            priority_desc = "接收(一般優先級)"
        notes_parts.append(f"【接收優先級: {priority_desc}】")
        
        # 4. 庫存狀況分析
        if source['source_type'] == 'ND轉出' and mode != self.mode_d:
            notes_parts.append("【轉出分析: ND類型店鋪，無庫存限制，可全數轉出】")
        elif source['source_type'] == 'F模式ND轉出':
            notes_parts.append("【轉出分析: F模式ND類型店鋪，無庫存限制，全數轉出】")
        elif source['rp_type'] == 'ND' and mode == self.mode_d:
            remaining_after_transfer = source['original_stock'] - transfer_qty
            notes_parts.append(f"【轉出分析: ND店鋪清貨(模式D)，轉出後剩餘庫存({remaining_after_transfer})件，已優化避免1件餘貨】")
        elif source['source_type'] == 'F模式RF轉出':
            remaining_after_transfer = source['original_stock'] - transfer_qty
            notes_parts.append(f"【轉出分析: F模式RF轉出，可忽視最小庫存要求，轉出後剩餘庫存({remaining_after_transfer})件】")
        elif source['source_type'] == 'RF過剩轉出':
            remaining_after_transfer = source['original_stock'] - transfer_qty
            notes_parts.append(f"【轉出分析: RF過剩轉出，轉出後剩餘庫存({remaining_after_transfer})仍高於安全庫存({source.get('safety_stock', 'N/A')})】")
        elif source['source_type'] == 'RF加強轉出':
            remaining_after_transfer = source['original_stock'] - transfer_qty
            notes_parts.append(f"【轉出分析: RF加強轉出，轉出後剩餘庫存({remaining_after_transfer})可能低於安全庫存({source.get('safety_stock', 'N/A')})】")
        
        # 5. 接收需求分析
        if dest['dest_type'] == 'F模式目標接收':
            target_qty = dest.get('target_qty', 0)
            notes_parts.append(f"【接收分析: F模式目標接收，目標數量{target_qty}件，累計已接收{current_received_qty + transfer_qty}件】")
        elif dest['dest_type'] == '重點補0':
            if 'target_qty' in dest:
                notes_parts.append(f"【接收分析: 重點補0，目標數量{dest['target_qty']}件，累計已接收{current_received_qty + transfer_qty}件，缺口{abs((current_received_qty + transfer_qty) - dest['target_qty'])}件】")
            else:
                notes_parts.append("【接收分析: 重點補0，針對低庫存店鋪補貨】")
        elif dest['dest_type'] == '緊急缺貨補貨':
            notes_parts.append("【接收分析: 緊急缺貨補貨，該店鋪零庫存但有銷售記錄】")
        elif dest['dest_type'] == '潛在缺貨補貨':
            current_stock = dest.get('current_stock', 0)
            pending = dest.get('pending_received', 0)
            safety_stock = dest.get('safety_stock', 0)
            total_available = current_stock + pending
            shortage = safety_stock - total_available
            notes_parts.append(f"【接收分析: 潛在缺貨補貨，庫存不足{shortage}件，補充至安全庫存{safety_stock}件】")
        
        # 6. 轉移數量說明
        if transfer_qty == 2 and source.get('original_stock', 0) == 1:
            notes_parts.append("【數量說明: 已優化至2件，最小轉移單位】")
        elif transfer_qty == 1:
            notes_parts.append("【數量說明: 最小轉移單位1件】")
        else:
            notes_parts.append(f"【數量說明: 轉移{transfer_qty}件】")
        
        # 7. 轉移後狀況
        remaining_stock = source['original_stock'] - transfer_qty
        notes_parts.append(f"【轉移後狀況: 轉出店鋪剩餘庫存{remaining_stock}件，接收店鋪累計接收{current_received_qty + transfer_qty}件】")
        
        # 8. 特殊標記
        if source['source_type'] in ['RF加強轉出']:
            notes_parts.append("【特殊標記: 加強轉出類型，需注意轉出後庫存狀況】")
        if dest['dest_type'] == '重點補0':
            notes_parts.append("【特殊標記: 重點補0類型，確保最低保障標準】")
        
        return " | ".join(notes_parts)