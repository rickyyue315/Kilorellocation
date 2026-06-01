"""
AI 报表增强模拟测试 -- 展示 LLM 增强注解的真实样貌

[注意] 仅供示范用，不修改任何系统程式码。
目的是具体展示[报表增强]这个 AI 场景的输出品质，验证是否值得引入。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from business_logic import TransferLogic


# -- 工具函数 ------------------------------------------------------------------

def build_df(rows):
    """建立测试用 DataFrame，补齐必要栏位"""
    df = pd.DataFrame(rows)
    for col in ['Pending Received', 'Safety Stock', 'MOQ', 'Effective Sold Qty']:
        if col not in df.columns:
            df[col] = 0
    for col in ['Article Description', 'ALL', 'Target', 'Type']:
        if col not in df.columns:
            df[col] = ''
    df['Effective Sold Qty'] = df.apply(
        lambda r: max(r['Last Month Sold Qty'], r['MTD Sold Qty']),
        axis=1
    )
    return df


def simulate_ai_enhanced_note(rec: dict, mode: str) -> str:
    """
    模拟 LLM 对一笔调货建议生成的增强注解。
    内容是根据实际调货数据、常见 LLM 输出风格，合理模拟的结果，
    并非真实 API 呼叫。
    """
    article = rec['Article']
    src = rec['Transfer Site']
    dst = rec['Receive Site']
    qty = rec['Transfer Qty']

    # -- 模拟不同情境的 AI 注解 --
    scenarios = {
        f"{article}_{src}_{dst}": (
            f"[AI分析] {dst} 库存不足(现有 {rec.get('Receive Original Stock', 0)} 件)，"
            f"由库存较充裕的 {src} 调拨 {qty} 件以满足其销售需求。"
            f"建议后续追踪 {dst} 的库存周转情况，避免再次缺货。"
        ),
    }

    # 预设 AI 注解(没被特定情境匹配到的用这个)
    default = (
        f"[AI分析] {src} -> {dst} 调拨 {qty} 件，"
        f"基于模式[{mode}]的库存优化策略。"
        f"建议营运团队关注此 SKU 在 {dst} 的销售表现。"
    )

    return scenarios.get(f"{article}_{src}_{dst}", default)


def print_separator(title: str):
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_comparison(rec, ai_note):
    print(f"  商品: {rec['Article']} | {rec.get('Article Description', '')}")
    print(f"  {rec['Transfer Site']} ({rec['Transfer OM']}) -> {rec['Receive Site']} ({rec['Receive OM']})")
    print(f"  调拨数量: {rec['Transfer Qty']}")
    print(f"  +-- 现有注解 -----------------------------------------------------")
    print(f"  | {rec['Notes']}")
    print(f"  +-- AI 增强注解 --------------------------------------------------")
    print(f"  | {ai_note}")
    print(f"  +---------------------------------------------------------------")
    print()


# =============================================================================
#  场景一：保守转货模式 (A mode)
#  情境：一批 RF 店铺，部分库存过剩，部分缺货
# =============================================================================

def run_scenario_a():
    print_separator("场景一：保守转货模式 (A Mode)")
    print("  情境：RF 店铺间库存重新分配，保护安全库存")
    print("  测试商品：同 OM 下，部分店铺库存过剩，部分库存不足")

    df = build_df([
        {'Article': '109249904001', 'OM': 'Ivy', 'Site': 'IV001', 'RP Type': 'RF',
         'SaSa Net Stock': 20, 'Safety Stock': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2, 'MOQ': 1},
        {'Article': '109249904001', 'OM': 'Ivy', 'Site': 'IV002', 'RP Type': 'RF',
         'SaSa Net Stock': 2, 'Safety Stock': 5, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 3, 'MOQ': 1},
        {'Article': '109249904001', 'OM': 'Ivy', 'Site': 'IV003', 'RP Type': 'RF',
         'SaSa Net Stock': 0, 'Safety Stock': 4, 'Last Month Sold Qty': 2, 'MTD Sold Qty': 1, 'MOQ': 1},
    ])

    logic = TransferLogic()
    recs = logic.generate_transfer_recommendations(df, "保守轉貨")

    print(f"\n  [结果] 产生了 {len(recs)} 笔调货建议")
    print()

    for r in recs:
        ai_note = simulate_ai_enhanced_note(r, "保守轉貨")
        print_comparison(r, ai_note)


# =============================================================================
#  场景二：重点补0模式 (C mode)
#  情境：部分店铺库存 = 0，从 ND 店铺紧急补货
# =============================================================================

def run_scenario_c():
    print_separator("场景二：重点补0模式 (C Mode)")
    print("  情境：零库存店铺优先补货，ND 店铺作为货源")
    print("  测试商品：同 OM 下，2 间 RF 库存 0，ND 店铺供货")

    df = build_df([
        {'Article': '109249904002', 'OM': 'Ivy', 'Site': 'IV_ND1', 'RP Type': 'ND',
         'SaSa Net Stock': 15, 'Safety Stock': 0, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'MOQ': 1},
        {'Article': '109249904002', 'OM': 'Ivy', 'Site': 'IV010', 'RP Type': 'RF',
         'SaSa Net Stock': 0, 'Safety Stock': 5, 'Last Month Sold Qty': 5, 'MTD Sold Qty': 2, 'MOQ': 1},
        {'Article': '109249904002', 'OM': 'Ivy', 'Site': 'IV011', 'RP Type': 'RF',
         'SaSa Net Stock': 0, 'Safety Stock': 3, 'Last Month Sold Qty': 1, 'MTD Sold Qty': 1, 'MOQ': 1},
        {'Article': '109249904002', 'OM': 'Ivy', 'Site': 'IV012', 'RP Type': 'RF',
         'SaSa Net Stock': 8, 'Safety Stock': 4, 'Last Month Sold Qty': 2, 'MTD Sold Qty': 1, 'MOQ': 1},
    ])

    logic = TransferLogic()
    recs = logic.generate_transfer_recommendations(df, "重點補0")

    print(f"\n  [结果] 产生了 {len(recs)} 笔调货建议")
    print()

    for r in recs:
        ai_note = simulate_ai_enhanced_note(r, "重點補0")
        print_comparison(r, ai_note)


# =============================================================================
#  场景三：强制转出模式 (E1 mode)
#  情境：特定门市被标记 ALL，强制将库存转出
# =============================================================================

def run_scenario_e():
    print_separator("场景三：强制转出模式 (E1 Mode)")
    print("  情境：部分店铺被标记 ALL，强制将库存转出给其他 RF")
    print("  测试商品：1 间 ND 被标 ALL 需全数转出，2 间 RF 库存不足")

    df = build_df([
        {'Article': '109249904003', 'OM': 'Ivy', 'Site': 'IV020', 'RP Type': 'ND',
         'SaSa Net Stock': 12, 'Safety Stock': 0, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0,
         'MOQ': 1, 'ALL': '*'},
        {'Article': '109249904003', 'OM': 'Ivy', 'Site': 'IV021', 'RP Type': 'RF',
         'SaSa Net Stock': 1, 'Safety Stock': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2, 'MOQ': 1},
        {'Article': '109249904003', 'OM': 'Ivy', 'Site': 'IV022', 'RP Type': 'RF',
         'SaSa Net Stock': 0, 'Safety Stock': 4, 'Last Month Sold Qty': 2, 'MTD Sold Qty': 1, 'MOQ': 1},
    ])

    logic = TransferLogic()
    recs = logic.generate_transfer_recommendations(df, "強制轉出")

    print(f"\n  [结果] 产生了 {len(recs)} 笔调货建议")
    print()

    for r in recs:
        ai_note = simulate_ai_enhanced_note(r, "強制轉出")
        print_comparison(r, ai_note)


# =============================================================================
#  场景四：ND1 模式 (ND 店铺互转)
#  情境：ND 店铺之间互相调拨库存
# =============================================================================

def run_scenario_nd():
    print_separator("场景四：ND1 模式 (ND 店铺互转)")
    print("  情境：低销量 ND 店铺转出给高销量 ND 店铺")
    print("  测试商品：同 OM 下，2 间 ND 互转")

    df = build_df([
        {'Article': '109249904004', 'OM': 'Ivy', 'Site': 'IV_ND_LOW', 'RP Type': 'ND',
         'SaSa Net Stock': 10, 'Safety Stock': 0, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'MOQ': 1},
        {'Article': '109249904004', 'OM': 'Ivy', 'Site': 'IV_ND_HIGH', 'RP Type': 'ND',
         'SaSa Net Stock': 5, 'Safety Stock': 0, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2, 'MOQ': 1},
    ])

    logic = TransferLogic()
    recs = logic.generate_transfer_recommendations(df, "ND同OM轉貨")

    print(f"\n  [结果] 产生了 {len(recs)} 笔调货建议")
    print()

    for r in recs:
        ai_note = simulate_ai_enhanced_note(r, "ND1")
        print_comparison(r, ai_note)


# =============================================================================
#  场景五：精简SKU(同OM)模式
#  情境：大量 RF 店铺库存过剩，需将多余库存集中或退回
# =============================================================================

def run_scenario_simplified():
    print_separator("场景五：精简SKU(同OM)模式")
    print("  情境：整合多余库存，RF 只保留限量库存")
    print("  测试商品：同 OM 下多间 RF，部分库存超过上限")

    df = build_df([
        {'Article': '109249904005', 'OM': 'Ivy', 'Site': 'IV030', 'RP Type': 'RF',
         'SaSa Net Stock': 15, 'Safety Stock': 3, 'Last Month Sold Qty': 2, 'MTD Sold Qty': 1, 'MOQ': 1},
        {'Article': '109249904005', 'OM': 'Ivy', 'Site': 'IV031', 'RP Type': 'RF',
         'SaSa Net Stock': 12, 'Safety Stock': 2, 'Last Month Sold Qty': 1, 'MTD Sold Qty': 0, 'MOQ': 1},
        {'Article': '109249904005', 'OM': 'Ivy', 'Site': 'IV032', 'RP Type': 'RF',
         'SaSa Net Stock': 3, 'Safety Stock': 4, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2, 'MOQ': 1},
    ])

    logic = TransferLogic()
    recs = logic.generate_transfer_recommendations(df, "精簡SKU(限同OM)")

    print(f"\n  [结果] 产生了 {len(recs)} 笔调货建议")
    print()

    for r in recs:
        ai_note = simulate_ai_enhanced_note(r, "精簡SKU(同OM)")
        print_comparison(r, ai_note)


# =============================================================================
#  综合对比总结
# =============================================================================

def print_summary():
    print_separator("AI 增强注解 vs 现有注解 -- 对比总结")
    print("""
  +--------------------------------------------------------------------+
  |                        对 比 分 析                                  |
  +-----------------------------+--------------------------------------+
  | 现有注解 (notes.py)         | AI 增强注解 (模拟)                   |
  +-----------------------------+--------------------------------------+
  | 结构化，每段资讯明确标记     | 自然语言段落，资讯松散               |
  | 包含精确数值计算             | 仅重复既有数值，无新增洞察           |
  | (剩余库存、缺口、累计接收)  |                                       |
  | 标示业务规则(模式、类型)    | 泛泛建议[追踪销售][关注表现]         |
  | 无冗言                       | 大量填充词(建议、基于、关注)         |
  | 100% 确定性                 | 可能产生幻觉或无关内容               |
  | 零开销、零延迟              | API 成本 + 3-10秒延迟               |
  +-----------------------------+--------------------------------------+
  | 结论：AI 注解提供了[更多文字]而非[更多资讯]。                       |
  |       对库存调度操作没有增加任何实际价值。                          |
  +--------------------------------------------------------------------+
    """)


# =============================================================================
#  主程式
# =============================================================================

if __name__ == "__main__":
    print()
    print("  +============================================================+")
    print("  |  AI 报表增强模拟测试                                        |")
    print("  |  展示 LLM 增强注解的实际输出与现有注解对比                  |")
    print("  +============================================================+")
    print("  [注意] 此测试为独立示范，不修改任何系统程式码")
    print()

    run_scenario_a()
    run_scenario_c()
    run_scenario_e()
    run_scenario_nd()
    run_scenario_simplified()
    print_summary()
