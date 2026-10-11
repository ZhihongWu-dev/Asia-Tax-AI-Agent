# 结果：模板 holding+services，主体 GROUP，事件 {'dividend': 1000.0, 'onward': 900.0, 'exit': 5000.0, 'exit_on': '2026-12-31', 'service_fee': 800.0, 'on': '2026-03-31'}

案例文件注明的假设 / 待补：
- battery: composite of holding+services from the fact packs; full facts; timing open

## 候选表（集团总税 lo / hi；主体份额；裁量数、计划项数、脆弱度）

| 候选 | lo | hi | share@lo | share@hi | 裁量 | 计划 | 脆弱 | 被支配 |
|---|---|---|---|---|---|---|---|---|
| None/SG/DEBT/False/DIRECT | 5233555.89 | 5234384.49 | 5233555.89 | 5234384.49 | 9 | 8 | 352.10 |  |
| HK/SG/DEBT/False/INDIRECT | 5233615.29 | 5234341.05 | 5233615.29 | 5234341.05 | 11 | 11 | 347.49 |  |
| None/CN/DEBT/False/DIRECT | 5233615.89 | 5234300.49 | 5233615.89 | 5234300.49 | 7 | 1 | 212.10 |  |
| HK/CN/DEBT/False/INDIRECT | 5233675.29 | 5234257.05 | 5233675.29 | 5234257.05 | 9 | 4 | 207.49 |  |
| CN/SG/EQUITY/False/DIRECT | 5233706.34 | 5234196.99 | 5233706.34 | 5234196.99 | 11 | 11 | 430.00 |  |
| CN/CN/EQUITY/False/DIRECT | 5233766.34 | 5234112.99 | 5233766.34 | 5234112.99 | 9 | 4 | 290.00 |  |
| SG/SG/DEBT/False/INDIRECT | 5233558.84 | 5234539.49 | 5233558.84 | 5234539.49 | 10 | 12 | 410.00 | 是 |
| SG/SG/DEBT/False/DIRECT | 5233561.34 | 5234572.15 | 5233561.34 | 5234572.15 | 11 | 19 | 505.16 | 是 |
| HK/SG/DEBT/False/DIRECT | 5233612.79 | 5234400.71 | 5233612.79 | 5234400.71 | 11 | 21 | 442.66 | 是 |
| SG/CN/DEBT/False/INDIRECT | 5233618.84 | 5234455.49 | 5233618.84 | 5234455.49 | 8 | 6 | 270.00 | 是 |
| SG/CN/DEBT/False/DIRECT | 5233621.34 | 5234488.15 | 5233621.34 | 5234488.15 | 9 | 13 | 365.16 | 是 |
| None/HK/DEBT/False/DIRECT | 5233667.16 | 5234364.59 | 5233667.16 | 5234364.59 | 9 | 4 | 218.81 | 是 |
| SG/HK/DEBT/False/INDIRECT | 5233670.10 | 5234519.59 | 5233670.11 | 5234519.59 | 10 | 9 | 276.78 | 是 |
| SG/HK/DEBT/False/DIRECT | 5233672.60 | 5234552.25 | 5233672.61 | 5234552.25 | 11 | 16 | 371.95 | 是 |
| HK/CN/DEBT/False/DIRECT | 5233672.79 | 5234316.71 | 5233672.79 | 5234316.71 | 9 | 14 | 302.66 | 是 |
| CN/SG/DEBT/False/DIRECT | 5233706.34 | 5234506.99 | 5233706.34 | 5234506.99 | 10 | 11 | 430.00 | 是 |
| HK/HK/DEBT/False/DIRECT | 5233724.05 | 5234380.81 | 5233724.06 | 5234380.82 | 11 | 17 | 309.44 | 是 |
| HK/HK/DEBT/False/INDIRECT | 5233726.55 | 5234321.15 | 5233726.56 | 5234321.15 | 11 | 7 | 214.26 | 是 |
| CN/SG/EQUITY/False/INDIRECT | 5233756.34 | 5234311.99 | 5233756.34 | 5234311.99 | 13 | 11 | 430.00 | 是 |
| CN/SG/DEBT/False/INDIRECT | 5233756.34 | 5234621.99 | 5233756.34 | 5234621.99 | 12 | 11 | 430.00 | 是 |
| SG/SG/EQUITY/False/INDIRECT | 5233758.84 | 5234479.49 | 5233758.84 | 5234479.49 | 12 | 14 | 390.00 | 是 |
| HK/SG/EQUITY/False/DIRECT | 5233761.34 | 5234358.65 | 5233761.34 | 5234358.65 | 13 | 26 | 535.16 | 是 |
| SG/SG/EQUITY/False/DIRECT | 5233761.34 | 5234512.15 | 5233761.34 | 5234512.15 | 13 | 22 | 485.16 | 是 |
| HK/SG/EQUITY/False/INDIRECT | 5233763.84 | 5234298.99 | 5233763.84 | 5234298.99 | 13 | 16 | 440.00 | 是 |
| CN/CN/DEBT/False/DIRECT | 5233766.34 | 5234422.99 | 5233766.34 | 5234422.99 | 8 | 4 | 290.00 | 是 |
| CN/CN/EQUITY/False/INDIRECT | 5233816.34 | 5234227.99 | 5233816.34 | 5234227.99 | 11 | 4 | 290.00 | 是 |
| CN/CN/DEBT/False/INDIRECT | 5233816.34 | 5234537.99 | 5233816.34 | 5234537.99 | 10 | 4 | 290.00 | 是 |
| CN/HK/EQUITY/False/DIRECT | 5233817.60 | 5234177.09 | 5233817.61 | 5234177.09 | 11 | 7 | 296.78 | 是 |
| CN/HK/DEBT/False/DIRECT | 5233817.60 | 5234487.09 | 5233817.61 | 5234487.09 | 10 | 7 | 296.78 | 是 |
| SG/CN/EQUITY/False/INDIRECT | 5233818.84 | 5234395.49 | 5233818.84 | 5234395.49 | 10 | 8 | 250.00 | 是 |
| HK/CN/EQUITY/False/DIRECT | 5233821.34 | 5234274.65 | 5233821.34 | 5234274.65 | 11 | 19 | 395.16 | 是 |
| SG/CN/EQUITY/False/DIRECT | 5233821.34 | 5234428.15 | 5233821.34 | 5234428.15 | 11 | 16 | 345.16 | 是 |
| HK/CN/EQUITY/False/INDIRECT | 5233823.84 | 5234214.99 | 5233823.84 | 5234214.99 | 11 | 9 | 300.00 | 是 |
| None/SG/EQUITY/False/DIRECT | 5233852.50 | 5234481.50 | 5233852.50 | 5234481.50 | 10 | 8 | 440.00 | 是 |
| CN/HK/EQUITY/False/INDIRECT | 5233867.60 | 5234292.09 | 5233867.61 | 5234292.09 | 13 | 7 | 296.78 | 是 |
| CN/HK/DEBT/False/INDIRECT | 5233867.60 | 5234602.09 | 5233867.61 | 5234602.09 | 12 | 7 | 296.78 | 是 |
| SG/HK/EQUITY/False/INDIRECT | 5233870.10 | 5234459.59 | 5233870.11 | 5234459.59 | 12 | 11 | 256.78 | 是 |
| HK/HK/EQUITY/False/DIRECT | 5233872.60 | 5234338.75 | 5233872.61 | 5234338.75 | 13 | 22 | 401.95 | 是 |
| SG/HK/EQUITY/False/DIRECT | 5233872.60 | 5234492.25 | 5233872.61 | 5234492.25 | 13 | 19 | 351.95 | 是 |
| HK/HK/EQUITY/False/INDIRECT | 5233875.10 | 5234279.09 | 5233875.11 | 5234279.09 | 13 | 12 | 306.78 | 是 |
| None/CN/EQUITY/False/DIRECT | 5233912.50 | 5234397.50 | 5233912.50 | 5234397.50 | 8 | 1 | 300.00 | 是 |
| None/HK/EQUITY/False/DIRECT | 5233963.77 | 5234461.60 | 5233963.77 | 5234461.61 | 10 | 4 | 306.78 | 是 |
| None/SG/DEBT/True/DIRECT | 10473955.80 | 10474784.29 | 10473955.80 | 10474784.29 | 9 | 9 | 351.82 | 是 |
| SG/SG/DEBT/True/INDIRECT | 10473958.84 | 10474939.49 | 10473958.84 | 10474939.49 | 10 | 13 | 410.00 | 是 |
| SG/SG/DEBT/True/DIRECT | 10473961.34 | 10474972.15 | 10473961.34 | 10474972.15 | 11 | 20 | 505.16 | 是 |
| HK/SG/DEBT/True/DIRECT | 10474012.76 | 10474800.57 | 10474012.76 | 10474800.56 | 11 | 22 | 442.46 | 是 |
| HK/SG/DEBT/True/INDIRECT | 10474015.26 | 10474740.91 | 10474015.26 | 10474740.90 | 11 | 12 | 347.30 | 是 |
| None/CN/DEBT/True/DIRECT | 10474015.80 | 10474700.29 | 10474015.80 | 10474700.29 | 7 | 1 | 211.82 | 是 |
| SG/CN/DEBT/True/INDIRECT | 10474018.84 | 10474855.49 | 10474018.84 | 10474855.49 | 8 | 7 | 270.00 | 是 |
| SG/CN/DEBT/True/DIRECT | 10474021.34 | 10474888.15 | 10474021.34 | 10474888.15 | 9 | 14 | 365.16 | 是 |
| None/HK/DEBT/True/DIRECT | 10474067.11 | 10474764.31 | 10474067.11 | 10474764.31 | 9 | 4 | 218.39 | 是 |
| SG/HK/DEBT/True/INDIRECT | 10474070.15 | 10474919.52 | 10474070.14 | 10474919.51 | 10 | 10 | 276.60 | 是 |
| SG/HK/DEBT/True/DIRECT | 10474072.65 | 10474952.18 | 10474072.64 | 10474952.17 | 11 | 17 | 371.76 | 是 |
| HK/CN/DEBT/True/DIRECT | 10474072.76 | 10474716.57 | 10474072.76 | 10474716.56 | 9 | 14 | 302.46 | 是 |
| HK/CN/DEBT/True/INDIRECT | 10474075.26 | 10474656.91 | 10474075.26 | 10474656.90 | 9 | 4 | 207.30 | 是 |
| CN/SG/EQUITY/True/DIRECT | 10474106.34 | 10474596.99 | 10474106.34 | 10474596.99 | 11 | 12 | 430.00 | 是 |
| CN/SG/DEBT/True/DIRECT | 10474106.34 | 10474906.99 | 10474106.34 | 10474906.99 | 10 | 12 | 430.00 | 是 |
| HK/HK/DEBT/True/DIRECT | 10474124.07 | 10474780.59 | 10474124.06 | 10474780.58 | 11 | 17 | 309.04 | 是 |
| HK/HK/DEBT/True/INDIRECT | 10474126.57 | 10474720.93 | 10474126.56 | 10474720.92 | 11 | 7 | 213.88 | 是 |
| CN/SG/EQUITY/True/INDIRECT | 10474156.34 | 10474711.99 | 10474156.34 | 10474711.99 | 13 | 12 | 430.00 | 是 |
| CN/SG/DEBT/True/INDIRECT | 10474156.34 | 10475021.99 | 10474156.34 | 10475021.99 | 12 | 12 | 430.00 | 是 |
| SG/SG/EQUITY/True/INDIRECT | 10474158.84 | 10474879.49 | 10474158.84 | 10474879.49 | 12 | 15 | 390.00 | 是 |
| HK/SG/EQUITY/True/DIRECT | 10474161.34 | 10474758.65 | 10474161.34 | 10474758.65 | 13 | 27 | 535.16 | 是 |
| SG/SG/EQUITY/True/DIRECT | 10474161.34 | 10474912.15 | 10474161.34 | 10474912.15 | 13 | 23 | 485.16 | 是 |
| HK/SG/EQUITY/True/INDIRECT | 10474163.84 | 10474698.99 | 10474163.84 | 10474698.99 | 13 | 17 | 440.00 | 是 |
| CN/CN/EQUITY/True/DIRECT | 10474166.34 | 10474512.99 | 10474166.34 | 10474512.99 | 9 | 4 | 290.00 | 是 |
| CN/CN/DEBT/True/DIRECT | 10474166.34 | 10474822.99 | 10474166.34 | 10474822.99 | 8 | 4 | 290.00 | 是 |
| CN/CN/EQUITY/True/INDIRECT | 10474216.34 | 10474627.99 | 10474216.34 | 10474627.99 | 11 | 4 | 290.00 | 是 |
| CN/CN/DEBT/True/INDIRECT | 10474216.34 | 10474937.99 | 10474216.34 | 10474937.99 | 10 | 4 | 290.00 | 是 |
| CN/HK/EQUITY/True/DIRECT | 10474217.65 | 10474577.02 | 10474217.64 | 10474577.01 | 11 | 7 | 296.60 | 是 |
| CN/HK/DEBT/True/DIRECT | 10474217.65 | 10474887.02 | 10474217.64 | 10474887.01 | 10 | 7 | 296.60 | 是 |
| SG/CN/EQUITY/True/INDIRECT | 10474218.84 | 10474795.49 | 10474218.84 | 10474795.49 | 10 | 9 | 250.00 | 是 |
| HK/CN/EQUITY/True/DIRECT | 10474221.34 | 10474674.65 | 10474221.34 | 10474674.65 | 11 | 19 | 395.16 | 是 |
| SG/CN/EQUITY/True/DIRECT | 10474221.34 | 10474828.15 | 10474221.34 | 10474828.15 | 11 | 17 | 345.16 | 是 |
| HK/CN/EQUITY/True/INDIRECT | 10474223.84 | 10474614.99 | 10474223.84 | 10474614.99 | 11 | 9 | 300.00 | 是 |
| None/SG/EQUITY/True/DIRECT | 10474252.50 | 10474881.50 | 10474252.50 | 10474881.50 | 10 | 9 | 440.00 | 是 |
| CN/HK/EQUITY/True/INDIRECT | 10474267.65 | 10474692.02 | 10474267.64 | 10474692.01 | 13 | 7 | 296.60 | 是 |
| CN/HK/DEBT/True/INDIRECT | 10474267.65 | 10475002.02 | 10474267.64 | 10475002.01 | 12 | 7 | 296.60 | 是 |
| SG/HK/EQUITY/True/INDIRECT | 10474270.15 | 10474859.52 | 10474270.14 | 10474859.51 | 12 | 12 | 256.60 | 是 |
| HK/HK/EQUITY/True/DIRECT | 10474272.65 | 10474738.68 | 10474272.64 | 10474738.67 | 13 | 22 | 401.76 | 是 |
| SG/HK/EQUITY/True/DIRECT | 10474272.65 | 10474892.18 | 10474272.64 | 10474892.17 | 13 | 20 | 351.76 | 是 |
| HK/HK/EQUITY/True/INDIRECT | 10474275.15 | 10474679.02 | 10474275.14 | 10474679.01 | 13 | 12 | 306.60 | 是 |
| None/CN/EQUITY/True/DIRECT | 10474312.50 | 10474797.50 | 10474312.50 | 10474797.50 | 8 | 1 | 300.00 | 是 |
| None/HK/EQUITY/True/DIRECT | 10474363.81 | 10474861.53 | 10474363.80 | 10474861.52 | 10 | 4 | 306.60 | 是 |

**最优候选** {'HOLD': None, 'SERVICER': 'SG', 'financing': 'DEBT', 'payment': False, 'exit_route': 'DIRECT'}（lo 5233555.89 / hi 5234384.49）；**现状** lo 5233852.50 / hi 5234481.50。

## 最优候选的税项（流 / 法域 / 税种 / 承担方 / 金额 / 依据）

下界：
- up1 · CN · income · payee · 70.00 · cn-hk.int.cap@cn, cn.wht.reduced
- up1 · CN · income · payer · -250.00 · cn.deduct.interest, cn.deduct.interest.benchmark, cn.tp.deduction_cap
- svc · CN · vat · payee · 48.00 · cn.vat.law.service
- svc · CN · vat · payer · -48.00 · cn.vat.law.input_credit
- svc · CN · income · payer · -200.00 · cn.deduct.service, cn.tp.deduction_cap
- exit · CN · income · payee · 200.00 · cn.gain.base, cn.wht.reduced
- exit · CN · stamp · payee · 2.50 · cn.stamp.seller
- exit · CN · stamp · payer · 2.50 · cn.stamp.buyer
- p2:ULT · HK · income · payee · 5233733.39 · hk.p2.base, hk.p2.topup

上界：
- up1 · CN · vat · payee · 60.00 · cn.vat.law.interest
- up1 · CN · income · payee · 100.00 · cn.wht.reduced
- up1 · HK · income · payee · 65.00 · hk.ftc.dta, hk.onshore.charge
- svc · CN · vat · payee · 48.00 · cn.vat.law.service
- svc · SG · income · payee · 36.00 · sg.ftc.dta, sg.service.base, sg.service.charge
- svc · CN · income · payee · 100.00 · cn.service.charge, cn.service.deemed_profit
- exit · CN · income · payee · 200.00 · cn.gain.base, cn.wht.reduced
- exit · HK · income · payee · 130.00 · hk.fsie.charge, hk.fsie.gain.base, hk.ftc.dta
- exit · CN · stamp · payee · 2.50 · cn.stamp.seller
- exit · CN · stamp · payer · 2.50 · cn.stamp.buyer
- p2:ULT · HK · income · payee · 5233642.99 · hk.p2.base, hk.p2.topup

## 待定事实（按丢失代价排序）
- 250.00  ('cn.deduct.interest.benchmark', 'up1')  flow.benchmark_rate, flow.interest_rate
- 56.44  ('cn.vat.law.interest', 'up1')  flow.unified_borrowing_relending
- 0.00  ('cn.vat.law.price_includes_vat', 'up1')  flow.price_includes_vat
- 0.00  ('sg.service.base', 'svc')  flow.profit_margin
- 0.00  ('data.p2_tcsh', 'SG')  group.p2_cbcr_pbt_sg, group.p2_cbcr_revenue_sg, group.p2_cbcr_simplified_taxes_sg, group.p2_qualified_cbcr_sg, group.p2_tcsh_history_sg
- 0.00  ('data.p2_dm', 'SG')  group.p2_dm_avg_income_eur_sg, group.p2_dm_avg_revenue_eur_sg

## 待定条件：计划项与裁量项（按代价排序）
- 200.00  ('cn.deduct.service', 'svc')  payer.reasonable_service_fee
- 80.00  ('cn.wht.service_as_royalty', 'svc')  payee.service_fee_is_royalty_for_know_how
- 60.00  ('cn-sg.pe.no_pe@cn', 'svc')  payee.fixed_place_in_cn:is_false, payee.residence_cert:is_true
- 60.00  ('cn-sg.ppt@cn', 'svc')  payee.ppt
- 48.00  ('cn.vat.law.input_credit', 'svc')  flow.input_vat_documents_kept:is_true
- 4.60  ('hk.onshore.charge', 'up1')  payee.income_sourced_in_hk
- 4.60  ('hk.fsie.substance.interest', 'up1')  payee.adequate_substance
- 1.45  ('cn-hk.int.cap@cn', 'up1')  payee.no_adverse_bo_factors
- 1.45  ('cn-hk.ppt@cn', 'up1')  payee.ppt
- 0.00  ('sg.service.charge', 'svc')  flow.receipt_kind:is_in
- 0.00  ('sg.fsie.charge', 'svc')  flow.receipt_kind:is_in
- 0.00  ('hk.fsie.substance.share_transfer', 'exit')  payee.adequate_substance
- 0.00  ('hk.fsie.participation.share_transfer', 'exit')  payee.no_main_purpose_of_tax_benefit
- 0.00  ('sg.ftc.pooling', 'svc')  payee.ftc_pooling_election:is_true
- 0.00  ('data.p2_tcsh_elected_sg', 'SG')  group.p2_tcsh_elected_sg:elect
- 0.00  ('data.p2_tcsh_elected_cn', 'CN')  group.p2_tcsh_elected_cn:elect

## 规则会读但案例未给的字段（53）
- exit  flow.acquirer_chargeable_in_hk
- exit  flow.assessment_notice_on
- exit  flow.clawback_event_within_2y
- exit  flow.cn_cost_basis
- exit  flow.determination_on
- exit  flow.first_notification_on
- exit  flow.foreign_tax_rate
- exit  flow.payable_on
- exit  flow.remitted_on
- exit  flow.reorg_acquired_ratio
- exit  flow.reorg_buyer_resident_in_cn
- exit  flow.reorg_commitment_3y
- exit  flow.reorg_control_ratio
- exit  flow.reorg_equity_payment_share
- exit  flow.reorg_filed
- exit  flow.reorg_operations_unchanged_12m
- exit  flow.reorg_same_residence
- exit  flow.reorg_shares_kept_12m
- exit  flow.shares_cancelled
- exit  flow.tax_paid_on
- exit  flow.tax_paid_or_secured
- svc  flow.arms_length_max
- svc  flow.assessment_notice_on
- svc  flow.first_notification_on
- svc  flow.foreign_tax_rate
- svc  flow.input_vat_documents_kept
- svc  flow.payable_on
- svc  flow.pboc_benchmark_rate
- svc  flow.profit_margin
- svc  flow.receipt_kind
- svc  flow.remitted_on
- svc  flow.tax_paid_on
- svc  flow.tax_paid_or_secured
- svc  flow.tp_adjustment_paid_on
- svc  flow.tp_adjustment_tax
- svc  payee.fixed_place_in_cn
- svc  payee.residence_cert
- up1  flow.arms_length_max
- up1  flow.assessment_notice_on
- up1  flow.benchmark_rate
- up1  flow.determination_on
- up1  flow.first_notification_on
- up1  flow.foreign_tax_rate
- up1  flow.interest_rate
- up1  flow.payable_on
- up1  flow.pboc_benchmark_rate
- up1  flow.price_includes_vat
- up1  flow.remitted_on
- up1  flow.tax_paid_on
- up1  flow.tax_paid_or_secured
- up1  flow.tp_adjustment_paid_on
- up1  flow.tp_adjustment_tax
- up1  flow.unified_borrowing_relending
