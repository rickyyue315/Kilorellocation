# 調貨邏輯審核修正計畫（v2.24.2 基準）

來源：27 模式全面邏輯審核（business_logic / matching_engine / strategies / services / data_processor / excel_generator）。
目標：修正確定性計算錯誤，不改變正確路徑的既有結果。每項修正須附回歸測試。

## 執行守則

- 依 AGENTS.md：任何模式邏輯變更須同步 README.md、VERSION.md、config.py（VERSION）、app.py docstring、ui/tutorial.py、調貨模式詳解.txt、transfer_logic_ai_brief.md。
- 每完成一個 P 級別跑：`python -m pytest tests -q`。
- 先寫失敗測試再修（每項下方列出測試要點）。

## 待業務確認（實作前先問用戶，未確認則保持現狀並僅文件化）

1. B 特別系列接收上限語義：補到 Safety×1（現行為）還是 Safety×2（README 宣稱）？影響 P0-1 的 needed_qty 公式。
2. B2a/B3a 的 Type=T 不出貨是否也適用 ND 來源（b_special.py:26-27 現為適用）。
3. D2 接收資格斷崖：total<safety 才可收但補到 2×safety，是否擴大資格至 total<2×safety。
4. D-family「+1 避免剩 1 件」允許超 dest target 1 件嗎（matching_engine.py:73-74 順序問題）。
5. C 系列 total≤3 時 ratio cap=0 回落到完整 ceiling（小店反拿最大上限）是否本意（business_logic.py:229-233）。

## P0 — 確定性 Bug（必修）

### P0-1 B 特別系列 dest priority 3/4 永不配對
- 檔案：strategies/b_special.py（dest priority 賦值 ~90-95；rounds ~186-191）。
- 問題：rounds 只含 dest_priority 1/2；priority 3/4 接收店永遠收不到貨。Type 欄缺失或全非 T/M 時 B 特別系列零輸出。
- 修正：在 rounds 補上 dest_priority 3、4 的回合（沿用 source filter 結構：None / 'RF過剩轉出' / 'RF加強轉出'），或收斂 dest priority 為 {1,2} 靠排序鍵分層（與確認項 1 一起定案）。
- 測試：Type 欄缺失資料集必須產出建議；priority 3/4 店在來源充足時可接收。

### P0-2 F3「最高庫存優先」配對階段失效
- 檔案：strategies/f_mode.py `_sort_key`（~line 188）。
- 問題：match() 重排次鍵為 effective_sold_qty 升序，original_stock 排序失效。
- 修正：is_f3 時回傳 `(tier, -src['original_stock'], src['effective_sold_qty'])`。同時解耦 f_fulfill_small_first 對來源排序的副作用（~186-187）。
- 測試：高庫存高銷量 vs 低庫存低銷量並存 → 高庫存先出；補強 test_f3_mode.py:476 未 assert 的 `rf01_first`。

### P0-3 E2 跨 OM 漏檢 Windy→Windy
- 檔案：strategies/e2_mode.py Phase 2（~97-111）、Phase 3（~205-210）。
- 問題：validate_pair 以 cross_om=False 呼叫，Windy 限制被跳過。
- 修正：`validate_pair(..., cross_om=(source['om'] != dest['om']))` 或顯式加 `source.om=='Windy' and dest.om!='Windy' → reject`。
- 測試：鏡像 test_nd_modes 的 test_windy_restriction_in_nd2，覆蓋 Phase 2 與 Phase 3。

### P0-4 單件後處理突破接收上限
- 檔案：services/post_processing.py optimize_single_piece_transfers（rebalance ~118-127、merge ~143-155）。
- 問題：升 1→2 / merge +1 不檢查 Target Qty / needed_qty；C 系列會被 quality check 8 判失敗，F/B/E 靜默超標。
- 修正：在 build_recommendation 持久化 `Target Qty`（無上限為 None）與剩餘 needed 快照；優化前以 (Article, Receive Site) 聚合已收量，任何 +1 前檢查 `received+1 <= target`；捐 1 前檢查不使來源 dest 跌破已達成 Target。同時：允許 [1,1] 群組互併為 2；qty=2 捐出路徑限制為 qty>=3 以免製造新單件。
- 測試：Target 恰達標 + 同源 1 件 → 不超標；C 模式優化後 quality check 通過；[1,1] 合併；不產生新單件。

### P0-5 RP Type 大小寫敏感、無效值默認 RF
- 檔案：data_processor.py:285-296。
- 問題：`nd` 被矯正為 RF（破壞 ND 只出不進）；Notes 註記為死碼（Notes 欄尚未建立）。
- 修正：strip().upper() 後 isin(['ND','RF'])；無效/空白行排除並警告（不可默認 RF）；Notes 欄在 convert_data_types 開頭建立。
- 測試：`nd`/`Nd `/空白 RP Type 行為。

### P0-6 重複 (Article, Site) 未檢測會 crash
- 檔案：data_processor.py（新增檢查）；崩潰點 business_logic.py:575 `article_site_index.at`。
- 修正：preprocess 末段 `df.duplicated(['Article','Site'], keep=False)` → raise ValueError 列出前 10 組（或彙總策略，與用戶確認）。
- 測試：重複行上傳須得到明確錯誤而非 traceback。

### P0-7 F 模式同站多列 Target 重複接收 + gap-fill 缺驗證
- 檔案：strategies/f_mode.py（dests ~96-99；cap 檢查 ~234-247；gap-fill ~257-309）。
- 修正：identify_destinations 按 site 去重 Target dest；計算 transfer_qty 時預 clamp `min(qty, target - received)`；gap-fill 限定 priority==1 Target dest、加 `src.site != dest.site`、dest 不在 transfer_sites、received>=target 預檢。
- 測試：同站兩列 Target=5 → 總接收 ≤5；gap-fill 不跨 OM 填重點補0、不 source=dest。

## P1 — 高風險 / 輸出正確性

### P1-1 最終 Notes 重建欄位錯置（影響所有模式輸出備註）
- 檔案：services/post_processing.py refresh_recommendation_fields（46-68）、services/recommendation_factory.py、services/notes.py。
- 修正：build 時持久化 Source Safety Stock / Receive Safety Stock / Receive Pending / transferable_qty / needed_qty 快照；refresh 讀回；`Target Qty` 缺失用 None 而非 0（消除全員「已達接收上限」誤標）。

### P1-2 Prioritizer 全部 🔴
- 檔案：services/prioritizer.py:21 `src_pri <= 2` 永真（所有來源 priority ∈ {1,2}）。
- 修正：改 `<= 1` 或以 source_type/qty 重新定義層級（與用戶確認分級規則）；更新 README 優先級說明。

### P1-3 D-family +1 在 clamp 後執行可超 target
- 檔案：services/matching_engine.py:71-74。
- 修正（若確認項 4 為不允許）：`_adjust_d_family_remainder` 後再套一次 `_clamp_target_qty`，超標時改為接受剩 1 件。

### P1-4 C1 needed bump 超 target（threshold>1 時）
- 檔案：strategies/c1_mode.py:27-29。
- 修正：`target - total < 2` 時跳過該 dest，而非灌大 needed_qty。

### P1-5 C2 行為與 C 分裂
- 檔案：strategies/c2_mode.py:28（預封鎖所有候選源）、:91-104（繞過 compute_transfer_qty 產生 1 件調貨）。
- 修正：transfer_sites 改為實際轉出後才加入；transfer_qty 改呼叫 compute_transfer_qty。

### P1-6 資料清洗洞
- data_processor.py：負 SaSa Net Stock / Pending Received 清為 0 並註記、套 OUTLIER_CAP；Article 改 regex `^\d{1,12}$` 驗證（拒 NaN/超長/浮點殘留，勿 zfill+截尾合併 SKU）；coerce 為 0 的非數值計數納入 processed_stats；Target/Type 大小寫欄名正規化比照 ALL 防覆寫（160-181）；calamine fallback 前 seek(0)。

### P1-7 精簡SKU / ND 修正
- simplified_sku.py:154、simplified_sku_return_d001.py:58：`int(supply_source)` 改 pd.to_numeric coerce（防 ValueError 中止）。
- source_dest_factory.safe_get_last2m：缺欄回退改 上月+MTD，觸發時警告；`Last 2 Month Sold Qty` 加入 config 清洗清單。
- simplified_sku match 排序改 `(priority, -qty)`（ND 優先，避免 ND 被迫退 D001）— 與用戶確認。
- nd_mode.py:52-58：ND1/ND2 緊急缺貨改用 total_available（含 Pending）判斷與計需求。
- 精簡SKU(退D001)：registry 補 dest_method 空實作，免白算 _dests_general。

### P1-8 Excel / 統計
- statistics.py:111 vs 128：Target達成分析 key 統一 .strip().upper()；:165 排序鍵改 `(gap <= 0, -gap)`；達成件數 KPI 每列封頂 min(actual, target)。
- excel_generator.py:109-129 vs 166-171：set_column 寬度被格式呼叫重置 → 寬度+format 合併設定。
- excel_generator.py:361：F 模式 gate 改用 mode code/registry flag。
- requirements.txt 補 tzdata。

### P1-9 測試過期
- tests/test_mode_registry.py:136/146/155 assert 26 → 27；test_nd_modes.py make_df 的 Effective Sold Qty 改為 上月+MTD。

## P2 — 一致性 / 效能 / 清理（不改結果）

1. 合併 can_transfer 與 predicates.validate_pair 為單一參數化驗證函式（根除漂移）。
2. Site/OM 比較統一入口 .strip().upper() 正規化（Windy 檢查、同站檢查現大小寫敏感）。
3. Total Available 在 data_processor 物化一次；max_receive_qty 統一「剩餘可收量」語義。
4. post_processing D-family 豁免集合改用 registry get_mode_families()。
5. 效能：identify 以 itertuples 取代 iterrows；E2 Phase 3 per-OM max 預計算；compute_target_fulfillment_stats 先過濾 Target>0；移除 post_processing.py:166 重複 refresh、business_logic.py:500 整表 copy、死碼 handle_missing_values。
6. 死碼清理：e2_mode.py:134-135 無效 continue、d_mode enable_2site_limit 死參數（matching_engine.py:222 改用 D2_MAX_RECEIVE_SITES_PER_SOURCE）、f_mode sort_order/receive_sites 未用、simplified_sku_return_d001 重複 import、get_codes_needing_column 改名或回傳 code。
7. quality_checks 強化：跨 OM（Windy/HD）後驗、B/E/F target cap 通用檢查、缺鍵防 KeyError、重複索引降級處理、F 模式 ND skip 僅限 Target dest。
8. E 模式接收店排除 ALL 標記行。

## 驗證

- 全套：`python -m pytest tests -q`。
- 重點回歸：tests/test_b2_b3_source_receive_site_limit.py、test_f3_mode.py、test_nd_modes.py、test_modes_simple.py + 本計畫新增測試。
- 覆蓋缺口補測：ND3、精簡SKU 三變體、D2 優化版（200%/2店上限）、E2 跨 OM Windy。
- 完成後依 AGENTS.md 同步 7 份文件並 bump VERSION。
