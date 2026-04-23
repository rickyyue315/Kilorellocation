import pandas as pd

from business_logic import TransferLogic


def _build_group_df(rows):
    return pd.DataFrame(rows)


def test_c1_rf_source_must_keep_min_two_and_avoid_single_piece_source():
    logic = TransferLogic()

    group_df = _build_group_df([
        {
            'Site': 'RF01',
            'OM': 'OM1',
            'RP Type': 'RF',
            'SaSa Net Stock': 3,
            'Pending Received': 0,
            'Safety Stock': 10,
            'Effective Sold Qty': 1,
            'Last Month Sold Qty': 1,
            'MTD Sold Qty': 0,
        },
        {
            'Site': 'RF02',
            'OM': 'OM1',
            'RP Type': 'RF',
            'SaSa Net Stock': 4,
            'Pending Received': 0,
            'Safety Stock': 10,
            'Effective Sold Qty': 1,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 1,
        },
    ])

    sources = logic.identify_sources(group_df, logic.mode_c1)
    by_site = {s['site']: s for s in sources}

    # RF01 只可轉1件，應被排除
    assert 'RF01' not in by_site

    # RF02 可轉2件，且轉後至少保留2件
    assert 'RF02' in by_site
    assert by_site['RF02']['transferable_qty'] == 2
    assert by_site['RF02']['original_stock'] - by_site['RF02']['transferable_qty'] >= 2


def test_c1_source_sorting_nd_first_then_rf_by_low_two_month_total_sales():
    logic = TransferLogic()

    group_df = _build_group_df([
        {
            'Site': 'ND01',
            'OM': 'OM1',
            'RP Type': 'ND',
            'SaSa Net Stock': 5,
            'Pending Received': 0,
            'Safety Stock': 1,
            'Effective Sold Qty': 0,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 0,
        },
        {
            'Site': 'RF_LOW',
            'OM': 'OM1',
            'RP Type': 'RF',
            'SaSa Net Stock': 6,
            'Pending Received': 0,
            'Safety Stock': 10,
            'Effective Sold Qty': 1,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 1,
        },
        {
            'Site': 'RF_HIGH',
            'OM': 'OM1',
            'RP Type': 'RF',
            'SaSa Net Stock': 6,
            'Pending Received': 0,
            'Safety Stock': 10,
            'Effective Sold Qty': 1,
            'Last Month Sold Qty': 3,
            'MTD Sold Qty': 4,
        },
    ])

    sources = logic.identify_sources(group_df, logic.mode_c1)
    ordered_sites = [s['site'] for s in sources]

    assert ordered_sites[0] == 'ND01'
    assert ordered_sites.index('RF_LOW') < ordered_sites.index('RF_HIGH')
