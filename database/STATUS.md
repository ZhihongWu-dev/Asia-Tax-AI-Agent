# Database build status

- Errors: 0
- Coverage gaps: 23
- Warnings: 134
- SQLite snapshot: database.sqlite

| Region | Category gaps | Slot gaps | Owned-pair gaps |
|---|---:|---:|---:|
| ae | 0 | 0 | 0 |
| cn | 0 | 0 | 0 |
| hk | 0 | 0 | 0 |
| id | 0 | 0 | 0 |
| in | 1 | 0 | 0 |
| jp | 0 | 0 | 0 |
| kr | 0 | 4 | 0 |
| my | 0 | 0 | 0 |
| sg | 0 | 0 | 0 |
| th | 0 | 0 | 0 |
| vn | 9 | 9 | 0 |

## Errors

none

## Gaps

gap: category in|page_treaties
gap: slot kr|company|anti_abuse without a parameter or absence record
gap: slot kr|company|outbound_wht without a parameter or absence record
gap: slot kr|individual|anti_abuse without a parameter or absence record
gap: slot kr|individual|outbound_wht without a parameter or absence record
gap: category vn|2
gap: category vn|3
gap: category vn|5
gap: category vn|6
gap: category vn|7
gap: category vn|8
gap: category vn|page_deadlines
gap: category vn|page_rates
gap: category vn|page_treaties
gap: slot vn|company|anti_abuse without a parameter or absence record
gap: slot vn|company|cfc without a parameter or absence record
gap: slot vn|company|outbound_wht without a parameter or absence record
gap: slot vn|individual|anti_abuse without a parameter or absence record
gap: slot vn|individual|cfc without a parameter or absence record
gap: slot vn|individual|final without a parameter or absence record
gap: slot vn|individual|inbound without a parameter or absence record
gap: slot vn|individual|outbound_wht without a parameter or absence record
gap: slot vn|individual|residence without a parameter or absence record

## Warnings

param jp.inbound.individual.foreign_income_taxable: quote differs only by whitespace
param jp.inbound.company.foreign_income_taxable: quote differs only by whitespace
param cn-hk.outbound_wht.dividend_rate_reduced: quote differs only by whitespace
param cn-hk.anti_abuse.ppt_applies: quote differs only by whitespace
param cn-in.outbound_wht.dividend_rate: quote differs only by whitespace
param cn-id.outbound_wht.dividend_rate: quote differs only by whitespace
param cn-id.anti_abuse.ppt_applies: quote differs only by whitespace
param cn-jp.outbound_wht.dividend_rate: quote differs only by whitespace
param cn-jp.anti_abuse.ppt_applies: quote differs only by whitespace
param cn-my.outbound_wht.dividend_rate: quote differs only by whitespace
param cn-my.anti_abuse.ppt_applies: quote differs only by whitespace
param cn-vn.outbound_wht.dividend_rate: quote differs only by whitespace
param cn-vn.anti_abuse.ppt_applies: quote differs only by whitespace
param cn-kr.outbound_wht.dividend_rate_reduced: quote differs only by whitespace
param cn-kr.outbound_wht.holding_pct_min: quote differs only by whitespace
param cn-kr.anti_abuse.ppt_applies: quote differs only by whitespace
param cn-sg.outbound_wht.dividend_rate_reduced: quote differs only by whitespace
param cn-sg.outbound_wht.holding_pct_min: quote differs only by whitespace
param cn-sg.anti_abuse.ppt_applies: quote differs only by whitespace
param cn-th.outbound_wht.dividend_rate_reduced: quote differs only by whitespace
param cn-th.outbound_wht.holding_pct_min: quote differs only by whitespace
param cn-th.anti_abuse.ppt_applies: quote differs only by whitespace
param cn-in.anti_abuse.ppt_applies: quote differs only by whitespace
param hk-id.outbound_wht.dividend_rate_reduced: quote differs only by whitespace
param hk-id.outbound_wht.holding_pct_min: quote differs only by whitespace
param hk-id.anti_abuse.ppt_applies: quote differs only by whitespace
param hk-in.outbound_wht.dividend_rate: quote differs only by whitespace
param hk-in.anti_abuse.ppt_applies: quote differs only by whitespace
param hk-jp.outbound_wht.dividend_rate_reduced: quote differs only by whitespace
param hk-jp.outbound_wht.holding_pct_min: quote differs only by whitespace
param hk-jp.outbound_wht.holding_months_min: quote differs only by whitespace
param hk-jp.anti_abuse.ppt_applies: quote differs only by whitespace
param hk-kr.outbound_wht.dividend_rate_reduced: quote differs only by whitespace
param hk-kr.outbound_wht.holding_pct_min: quote differs only by whitespace
param hk-kr.anti_abuse.ppt_applies: quote differs only by whitespace
param hk-my.outbound_wht.dividend_rate_reduced: quote differs only by whitespace
param hk-my.outbound_wht.holding_pct_min: quote differs only by whitespace
param hk-my.outbound_wht.dividend_rate_other: quote differs only by whitespace
param hk-my.anti_abuse.ppt_applies: quote differs only by whitespace
param hk-th.outbound_wht.dividend_rate: quote differs only by whitespace
param hk-th.anti_abuse.ppt_applies: quote differs only by whitespace
param hk-vn.anti_abuse.ppt_applies: quote differs only by whitespace
param sg-th.outbound_wht.dividend_rate: quote differs only by whitespace
param sg-th.anti_abuse.ppt_applies: quote differs only by whitespace
param sg-vn.outbound_wht.dividend_rate_reduced: quote differs only by whitespace
param sg-vn.outbound_wht.holding_pct_min: quote differs only by whitespace
param sg-vn.outbound_wht.dividend_rate_mid: quote differs only by whitespace
param sg-vn.outbound_wht.holding_pct_min.mid: quote differs only by whitespace
param sg-vn.anti_abuse.ppt_applies: quote differs only by whitespace
param sg.final.cit_rate: quote differs only by whitespace
param sg.inbound.ftc_method: quote differs only by whitespace
param sg.residence.residence_days_min: quote differs only by whitespace
param my.inbound.foreign_income_taxable: quote differs only by whitespace
param my.inbound.ftc_method: quote differs only by whitespace
param th.outbound_wht.dividend_wht_rate: quote differs only by whitespace
param id.final.cit_rate: quote differs only by whitespace
param id.inbound.foreign_dividend_exempt_if_invested: quote differs only by whitespace
param th.anti_abuse.transfer_pricing_market_price_adjustment: quote differs only by whitespace
param in.residence.company_poem: quote differs only by whitespace
param in.anti_abuse.gaar_chapter_applies: quote differs only by whitespace
param in.final.company_default_cit_rate: quote differs only by whitespace
param in.outbound_wht.nonresident_payment_tds_required: quote differs only by whitespace
param jp.final.individual_top_rate: quote differs only by whitespace
param jp.outbound_wht.nonresident_payment_withholding: quote differs only by whitespace
param ae.inbound.individual_uae_business_foreign_income: quote differs only by whitespace
param ae.residence.individual_uae_business: quote differs only by whitespace
param ae-cn.anti_abuse.ppt_applies: quote differs only by whitespace
param ae-hk.outbound_wht.interest_rate: quote differs only by whitespace
param ae-hk.outbound_wht.royalty_rate: quote differs only by whitespace
param ae-hk.anti_abuse.ppt_applies: quote differs only by whitespace
param ae-jp.anti_abuse.ppt_applies: quote differs only by whitespace
param ae-sg.outbound_wht.dividend_rate: quote differs only by whitespace
param ae-sg.outbound_wht.interest_rate: quote differs only by whitespace
param ae-sg.outbound_wht.royalty_rate: quote differs only by whitespace
param ae-sg.anti_abuse.ppt_applies: quote differs only by whitespace
param ae-th.outbound_wht.dividend_rate: quote differs only by whitespace
param in-th.outbound_wht.dividend_rate: quote differs only by whitespace
param in-jp.outbound_wht.dividend_rate: quote differs only by whitespace
param in-jp.anti_abuse.ppt_applies: quote differs only by whitespace
param in-sg.outbound_wht.holding_pct_min: quote differs only by whitespace
param in-sg.outbound_wht.dividend_rate_reduced: quote differs only by whitespace
param in-sg.anti_abuse.ppt_applies: quote differs only by whitespace
param ae-th.outbound_wht.interest_rate_financial_institution: quote differs only by whitespace
param ae-th.outbound_wht.interest_rate_other: quote differs only by whitespace
param ae-th.outbound_wht.royalty_rate: quote differs only by whitespace
param ae-vn.outbound_wht.dividend_rate_parent: quote differs only by whitespace
param ae-vn.outbound_wht.dividend_rate_other: quote differs only by whitespace
param ae-vn.outbound_wht.dividend_rate_government: quote differs only by whitespace
param ae-vn.outbound_wht.interest_rate: quote differs only by whitespace
param ae-vn.outbound_wht.royalty_rate: quote differs only by whitespace
param my.final.cit_rate: quote differs only by whitespace
param my.residence.company_management_control: quote differs only by whitespace
param my.residence.individual_days_threshold: quote differs only by whitespace
param my.final.individual_top_rate: quote differs only by whitespace
param my.outbound_wht.interest_royalty_withholding: quote differs only by whitespace
param my.anti_abuse.gaar_adjustment_power: quote differs only by whitespace
param id.residence.individual_days_threshold: quote differs only by whitespace
param id.residence.company_domicile: quote differs only by whitespace
param id.final.individual_top_rate: quote differs only by whitespace
param id.cfc.overseas_dividend_receipt_time: quote differs only by whitespace
param id.anti_abuse.substance_over_form: quote differs only by whitespace
param ae-my.outbound_wht.dividend_rate: quote differs only by whitespace
param ae-my.outbound_wht.interest_rate: quote differs only by whitespace
param ae-my.outbound_wht.interest_rate_government: quote differs only by whitespace
param ae-my.outbound_wht.royalty_rate: quote differs only by whitespace
param id-in.outbound_wht.dividend_rate: quote differs only by whitespace
param id-in.outbound_wht.interest_rate: quote differs only by whitespace
param id-in.outbound_wht.interest_rate_government: quote differs only by whitespace
param id-in.outbound_wht.royalty_rate: quote differs only by whitespace
param id-in.anti_abuse.ppt_applies: quote differs only by whitespace
param id-jp.outbound_wht.dividend_rate_parent: quote differs only by whitespace
param id-jp.outbound_wht.holding_pct_min: quote differs only by whitespace
param id-jp.outbound_wht.holding_months_min: quote differs only by whitespace
param id-jp.outbound_wht.interest_rate: quote differs only by whitespace
param id-jp.outbound_wht.royalty_rate: quote differs only by whitespace
param id-jp.anti_abuse.ppt_applies: quote differs only by whitespace
param id-kr.outbound_wht.dividend_rate_parent: quote differs only by whitespace
param id-kr.outbound_wht.holding_pct_min: quote differs only by whitespace
param id-kr.outbound_wht.interest_rate: quote differs only by whitespace
param id-kr.outbound_wht.interest_rate_government: quote differs only by whitespace
param id-kr.outbound_wht.royalty_rate: quote differs only by whitespace
param id-kr.anti_abuse.ppt_applies: quote differs only by whitespace
param id-my.outbound_wht.dividend_rate: quote differs only by whitespace
param id-my.outbound_wht.interest_rate: quote differs only by whitespace
param id-my.outbound_wht.interest_rate_government: quote differs only by whitespace
param id-my.anti_abuse.ppt_applies: quote differs only by whitespace
param id-vn.outbound_wht.dividend_rate: quote differs only by whitespace
param id-vn.outbound_wht.royalty_rate: quote differs only by whitespace
param kr.cfc.controlled_foreign_company_reporting_required: quote differs only by whitespace
decision my.absent.3: quote differs only by whitespace
decision my.absent.cfc: quote differs only by whitespace
decision th.absent.individual.anti_abuse: quote differs only by whitespace
decision in.absent.3: quote differs only by whitespace
decision in.absent.cfc: quote differs only by whitespace
