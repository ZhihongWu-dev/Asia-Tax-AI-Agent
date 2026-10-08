"""Write official/params.csv. Every row was read from the clause text; `quote` must occur verbatim in the clause."""
import csv
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(r"C:/Coding/Projects/TUM/project_study_self/official")
FIELDS = ["param_id", "scope", "income", "topic", "name", "value", "unit", "cite_id",
          "effective_from", "effective_to", "quote", "status", "cross_check", "note"]
R = []
XC_HK = "hk.ird.dta-rates#all 内地一行：股息 5/10，利息 7，特许权使用费 5/7，一致"
XC_2008 = "；cn.sta.2008-112 附件：香港、新加坡列在“5%（直接拥有支付股息公司至少25%股份情况下）”，低于25%为10%，一致；cn.gsf.2010-75#10 第二款解释：至少25%资本 5%，其他 10%，一致（仅中新）"
XC_HK = XC_HK + XC_2008.split("；cn.gsf")[0]


def p(pid, scope, income, topic, name, value, unit, cite, eff, quote, note="", to="", xc=""):
    R.append(dict(param_id=pid, scope=scope, income=income, topic=topic, name=name, value=value, unit=unit,
                  cite_id=cite, effective_from=eff, effective_to=to, quote=quote, status="extracted",
                  cross_check=xc, note=note))


HK, SG = "pair(CN,HK)", "pair(CN,SG)"
A, AS = "treaty.cn-hk.2006.zh", "treaty.cn-sg.2007.zh"
n26 = "内地适用起始日由《安排》第26条推得，生效日 2006-12-08 见 cn.sta.treaty-list 与 hk.ird.dta-mainland"

# ---- Mainland - Hong Kong
p("cn-hk.div.cap_qualified", HK, "DIVIDEND", "rate", "cap_qualified", 5, "%", A + "#10.2", "2007-01-01",
  "如果受益所有人是直接拥有支付股息公司至少25%资本的公司，为股息总额的5%", n26, xc=XC_HK)
p("cn-hk.div.ratio_min", HK, "DIVIDEND", "condition", "direct_ratio_min", 25, "%", A + "#10.2", "2007-01-01",
  "直接拥有支付股息公司至少25%资本的公司", n26)
p("cn-hk.div.cap_other", HK, "DIVIDEND", "rate", "cap_other", 10, "%", A + "#10.2", "2007-01-01",
  "在其它情况下，为股息总额的10%", n26, xc=XC_HK)
p("cn-hk.int.cap", HK, "INTEREST", "rate", "cap", 7, "%", A + "#11.2", "2007-01-01",
  "则所征税款不应超过利息总额的7%", n26, xc=XC_HK)
p("cn-hk.roy.cap", HK, "ROYALTY", "rate", "cap", 7, "%", A + "#12.2", "2007-01-01",
  "则所征税款不应超过特许权使用费总额的7%", n26, xc=XC_HK)
p("cn-hk.roy.cap_aircraft_ship_lease", HK, "ROYALTY", "rate", "cap_aircraft_ship_lease", 5, "%",
  "treaty.cn-hk.2006.p4.zh#2", "2015-12-29",
  "对飞机和船舶租赁业务支付的特许权使用费，所征税款不应超过特许权使用费总额的5%",
  "生效与适用日期见 cn.sta.2016-12", xc="hk.ird.dta-rates.notes#all：自 29.12.2015 起 5%，一致")
p("cn-hk.gain.immovable_ratio_over", HK, "SHARE_TRANSFER", "condition", "immovable_value_ratio_over", 50, "%",
  "treaty.cn-hk.2006.p5.zh#4", "2020-01-01",
  "超过50%的价值直接或间接来自于第六条所定义的位于另一方的不动产", "第五议定书替换第13条第4款；生效与适用日期见 cn.sta.2019-51")
p("cn-hk.gain.immovable_lookback", HK, "SHARE_TRANSFER", "condition", "immovable_lookback", 3, "years",
  "treaty.cn-hk.2006.p5.zh#4", "2020-01-01", "在转让行为前三年内的任一时间")
p("cn-hk.gain.share_ratio_min", HK, "SHARE_TRANSFER", "condition", "participation_ratio_min", 25, "%",
  "treaty.cn-hk.2006.p2.zh#5", "2008-06-11", "曾经直接或间接参与该公司至少百分之二十五的资", "第二议定书替换第13条第5款")
p("cn-hk.gain.share_lookback", HK, "SHARE_TRANSFER", "condition", "participation_lookback", 12, "months",
  "treaty.cn-hk.2006.p2.zh#5", "2008-06-11", "如果该收益人在转让行为前的十二个月内")
p("cn-hk.gain.listed_shares_residence_only", HK, "SHARE_TRANSFER", "condition", "listed_shares_residence_only",
  1, "bool", "treaty.cn-hk.2006.p4.zh#3", "2015-12-29",
  "一方居民转让在被认可的证券交易所上市的另一方居民公司股票取得的收益，应仅在转让者为其居民的一方征税",
  "限于在同一证券交易所买入并卖出")
p("cn-hk.ppt", HK, "ALL", "anti_abuse", "principal_purpose_test", 1, "bool", "treaty.cn-hk.2006.p5.zh#6",
  "2020-01-01", "主要目的之一是获得该优惠，则不得就相关所得给予该优惠", "需裁量，对应 U(DISCRETION)")
p("cn-hk.map.limit", HK, "ALL", "limit", "map_years", 3, "years", A + "#23.1", "2007-01-01", "三年内提出")

# ---- China - Singapore
n28 = "生效与适用日期见 cn.gsf.2007-116"
p("cn-sg.div.cap_qualified", SG, "DIVIDEND", "rate", "cap_qualified", 5, "%", AS + "#10.2", "2008-01-01",
  "不应超过股息总额的百分之五", n28, xc=XC_2008.lstrip("；"))
p("cn-sg.div.ratio_min", SG, "DIVIDEND", "condition", "direct_ratio_min", 25, "%", AS + "#10.2", "2008-01-01",
  "直接拥有支付股息公司至少百分之二十五资本", "受益所有人须为公司，合伙企业除外")
p("cn-sg.div.cap_other", SG, "DIVIDEND", "rate", "cap_other", 10, "%", AS + "#10.2", "2008-01-01",
  "在其他情况下，不应超过股息总额的百分之十", xc=XC_2008.lstrip("；"))
p("cn-sg.int.cap_bank", SG, "INTEREST", "rate", "cap_bank_or_financial_institution", 7, "%", AS + "#11.2",
  "2008-01-01", "在该项利息是由银行或金融机构取得的情况下，不应超过利息总额的百分之七")
p("cn-sg.int.cap_other", SG, "INTEREST", "rate", "cap_other", 10, "%", AS + "#11.2", "2008-01-01",
  "在其他情况下，不应超过利息总额的百分之十")
p("cn-sg.roy.cap", SG, "ROYALTY", "rate", "cap", 10, "%", AS + "#12.2", "2008-01-01",
  "则所征税款不应超过特许权使用费总额的百分之十")
p("cn-sg.roy.equipment_base", SG, "ROYALTY", "rate", "equipment_tax_base_share", 60, "%", AS + "#protocol",
  "2008-01-01", "按支付特许权使用费总额的百分之六十确定税基", "仅限使用工业、商业、科学设备的特许权使用费")
p("cn-sg.gain.immovable_ratio_over", SG, "SHARE_TRANSFER", "condition", "immovable_value_ratio_over", 50, "%",
  AS + "#13.4", "2008-01-01", "如果股份价值的百分之五十以上直接或间接由位于缔约国另一方的不动产构成")
p("cn-sg.gain.share_ratio_min", SG, "SHARE_TRANSFER", "condition", "participation_ratio_min", 25, "%",
  AS + "#13.5", "2008-01-01", "该公司或其他法人至少百分之二十五的资本")
p("cn-sg.gain.share_lookback", SG, "SHARE_TRANSFER", "condition", "participation_lookback", 12, "months",
  AS + "#13.5", "2008-01-01", "如果该收益人在转让行为前的十二个月内")
p("cn-sg.map.limit", SG, "ALL", "limit", "map_years", 3, "years", AS + "#24.1", "2008-01-01", "三年内提出")
p("cn-sg.mli.in_operation", SG, "ALL", "procedure", "mli_modifications_in_operation", 1, "bool",
  "treaty.cn-sg.mli#p1", "2022-09-01", "comes into operation on 1 September 2022",
  "多边公约对中新协定的修改；具体条款在该命令附表，尚未逐条取参数")
p("cn-sg.ppt", SG, "ALL", "anti_abuse", "principal_purpose_test", 1, "bool", "treaty.cn-sg.2007.mli.zh#27", "2023-01-01",
  "可以合理地认定就某项所得获取本协定某项优惠是直接或间接 产生该优惠的安排或交易的主要目的之一，则不应对该项所得给 予该优惠",
  "公约第七条第一款经整合文本替代协定第十条第六款、第十一条第八款、第十二条第七款；综合判断，对应一个 U(DISCRETION)；生效日按 superseded.csv 的 2023-01-01（预提税自公约对双方生效后下一公历年 1 月 1 日）")

# ---- Hong Kong - Singapore
p("hk-sg.no_comprehensive_dta", "pair(HK,SG)", "ALL", "condition", "comprehensive_dta", 0, "bool",
  "treaty.hk-sg.2003#1", "", "", "只有航运与航空收入的有限协定；香港全面协定清单中没有新加坡，见 hk.ird.dta-list")

# ---- Mainland domestic
p("cn.div.holding_months_min", "CN", "DIVIDEND", "condition", "holding_months_min", 12, "months",
  "cn.gsh.2009-81#i3", "", "在取得股息前连续12个月以内任何时候均符合税收协定规定的比例")
p("cn.bo.onpay_ratio", "CN", "ALL", "anti_abuse", "onpay_ratio_adverse_from", 50, "%", "cn.sta.2018-09#i2", "2018-04-01",
  "申请人有义务在收到所得的12个月内将所得的50%以上支付给第三国（地区）居民", "不利因素之一，综合分析，需裁量")
p("cn.bo.onpay_window", "CN", "ALL", "anti_abuse", "onpay_window", 12, "months", "cn.sta.2018-09#i2", "2018-04-01",
  "在收到所得的12个月内")
p("cn.bo.safe_harbour", "CN", "DIVIDEND", "condition", "safe_harbour_holders",
  "government;listed_company;individual;wholly_owned_by_these", "enum", "cn.sta.2018-09#i4", "2018-04-01",
  "可不根据本公告第二条规定的因素进行综合分析，直接判定申请人具有“受益所有人”身份", "仅适用于股息")
p("cn.treaty.claim_proc", "CN", "ALL", "procedure", "claim_proc", "SELF_ASSESS", "enum", "cn.sta.2019-35#3", "2020-01-01",
  "自行判断、申报享受、相关资料留存备查")
p("cn.treaty.refund_route", "CN", "ALL", "procedure", "refund_of_overpaid_tax", 1, "bool", "cn.sta.2019-35#10", "2020-01-01",
  "可在税收征管法规定期限内自行或通过扣缴义务人向主管税务机关要求退还多缴税款", "期限本身见税收征管法，待入库后补参数")
p("cn.treaty.refund_check_days", "CN", "ALL", "limit", "refund_verification_days", 30, "days",
  "cn.sta.2019-35#10", "2020-01-01", "30日内查实")

p("cn.eit.rate_nonresident_statutory", "CN", "ALL", "rate", "statutory_rate_non_resident", 20, "%", "cn.law.eit#4",
  "2008-01-01", "非居民企业取得本法第三条第三款规定的所得，适用税率为20％", "法定税率；实际按实施条例减按征收")
p("cn.wht.rate", "CN", "ALL", "rate", "withholding_rate_non_resident", 10, "%", "cn.reg.eit#91", "2008-01-01",
  "减按10%的税率征收企业所得税", "国内法预提税率，与协定上限取低")
p("cn.wht.base_gross", "CN", "DIVIDEND", "condition", "tax_base_is_gross", 1, "bool", "cn.law.eit#19", "2008-01-01",
  "股息、红利等权益性投资收益和利息、租金、特许权使用费所得，以收入全额为应纳税所得额", "同样适用于利息与特许权使用费")
p("cn.wht.base_gain", "CN", "SHARE_TRANSFER", "condition", "tax_base_is_gain", 1, "bool", "cn.law.eit#19",
  "2008-01-01", "转让财产所得，以收入全额减除财产净值后的余额为应纳税所得额")
p("cn.wht.at_source", "CN", "ALL", "procedure", "withheld_by_payer", 1, "bool", "cn.law.eit#37", "2008-01-01",
  "实行源泉扣缴，以支付人为扣缴义务人")
p("cn.wht.remit_days", "CN", "ALL", "limit", "withholding_remit_days", 7, "days", "cn.sta.2017-37#i7", "2017-12-01",
  "扣缴义务人应当自扣缴义务发生之日起7日内向扣缴义务人所在地主管税务机关申报和解缴代扣税款")
p("cn.refund.limit_years", "CN", "ALL", "limit", "refund_claim_years", 3, "years", "cn.law.tca#51", "",
  "纳税人自结算缴纳税款之日起三年内发现的，可以向税务机关要求退还多缴的税款", "ex_post 的时效")
p("cn.ftc.carryforward_years", "CN", "ALL", "limit", "credit_carryforward_years", 5, "years", "cn.law.eit#23",
  "2008-01-01", "超过抵免限额的部分，可以在以后五个年度内")
p("cn.ftc.indirect_ratio_min", "CN", "DIVIDEND", "condition", "indirect_credit_ratio_min", 20, "%",
  "cn.reg.eit#80", "2008-01-01", "直接控制，是指居民企业直接持有外国企业20%以上股份")
p("cn.ftc.indirect_tiers", "CN", "DIVIDEND", "condition", "indirect_credit_tiers", 5, "tiers", "cn.cs.2017-84#i2",
  "2017-01-01", "五层外国企业")
p("cn.ftc.method_lock_years", "CN", "ALL", "limit", "credit_method_lock_years", 5, "years", "cn.cs.2017-84#i1",
  "2017-01-01", "上述方式一经选择，5年内不得改变", "分国不分项或不分国不分项")
p("cn.indirect.value_ratio", "CN", "SHARE_TRANSFER", "anti_abuse", "deemed_no_purpose_value_ratio", 75, "%",
  "cn.sta.2015-07#i4", "2015-02-03", "境外企业股权75%以上价值直接或间接来自于中国应税财产", "四项须同时符合")
p("cn.indirect.asset_or_income_ratio", "CN", "SHARE_TRANSFER", "anti_abuse", "deemed_no_purpose_asset_or_income_ratio",
  90, "%", "cn.sta.2015-07#i4", "2015-02-03", "境外企业资产总额（不含现金）的90%以上直接或间接由在中国境内的投资构成")
p("cn.indirect.listed_safe_harbour", "CN", "SHARE_TRANSFER", "condition", "listed_market_trade_excluded", 1, "bool",
  "cn.sta.2015-07#i5", "2015-02-03", "非居民企业在公开市场买入并卖出同一上市境外企业股权取得间接转让中国应税财产所得")
p("cn.indirect.reorg_ratio", "CN", "SHARE_TRANSFER", "condition", "intragroup_reorg_ratio_min", 80, "%",
  "cn.sta.2015-07#i6", "2015-02-03", "股权转让方直接或间接拥有股权受让方80%以上的股权", "不动产占比过半时为 100%")

# ---- Hong Kong domestic
p("hk.profits.rate_corp", "HK", "ALL", "rate", "profits_tax_rate_corporation", 16.5, "%", "hk.cap112.en#sch8B",
  "2018-04-01", "at the rate of 16.5% on any part of section 14 assessable profits over $2,000,000")
p("hk.profits.rate_corp_first_tier", "HK", "ALL", "rate", "profits_tax_rate_first_2m", 8.25, "%",
  "hk.cap112.en#sch8B", "2018-04-01", "at the rate of 8.25% on section 14 assessable profits up to $2,000,000")
p("hk.royalty.deemed_profit", "HK", "ROYALTY", "rate", "deemed_assessable_profit_share", 30, "%",
  "hk.cap112.en#s21A", "2003-04-01", "for any sum received by or accrued to the person on or after 1 April 2003, 30%")
p("hk.royalty.deemed_profit_associate", "HK", "ROYALTY", "rate", "deemed_assessable_profit_share_associate", 100,
  "%", "hk.cap112.en#s21A", "", "100% of the sum in the case of a sum derived from an associate")
p("hk.fsie.participation_ratio_min", "HK", "DIVIDEND", "condition", "participation_ratio_min", 5, "%",
  "hk.cap112.en#s15M", "", "has continuously held not less than 5% of equity interests in the investee entity",
  "也适用于股权处置收益")
p("hk.fsie.participation_months_min", "HK", "DIVIDEND", "condition", "participation_months_min", 12, "months",
  "hk.cap112.en#s15M", "", "for a period of not less than 12 months immediately before")
p("hk.fsie.reference_rate", "HK", "DIVIDEND", "condition", "subject_to_tax_reference_rate", 15, "%",
  "hk.cap112.en#s15N", "", "the reference rate is 15%")

# ---- Singapore domestic
S43 = "sg.ita1947.full#s43"
p("sg.corp.rate", "SG", "ALL", "rate", "corporate_income_tax_rate", 17, "%", S43, "",
  "every company or body of persons, tax at the rate of 17% on every dollar of the chargeable income thereof")
p("sg.wht.interest", "SG", "INTEREST", "rate", "withholding_rate_non_resident", 15, "%", S43, "",
  "tax at the rate of 15% is to be levied and paid on the gross amount of", "第43条第3款，所得类别见第12条第6款等")
p("sg.wht.royalty", "SG", "ROYALTY", "rate", "withholding_rate_non_resident", 10, "%", S43, "",
  "tax at the rate of 10% is to be levied and paid on the gross amount of any income referred to in section 12(7)(a) and (b)",
  "第43条第3A款")
p("sg.fsie.headline_rate_min", "SG", "DIVIDEND", "condition", "foreign_headline_rate_min", 15, "%",
  "sg.ita1947.full#s13", "", "is not less than 15%", "第13条第9款的条件之一；另需已在来源地征税")
p("sg.wht.filing_due", "SG", "INTEREST", "limit", "withholding_filing_due",
  "15th day of the second month following payment", "text", "sg.ita1947.full#s45", "",
  "by the 15th day of the second month following the month in which the interest from which the tax is to be deducted is paid")

# ---- Hong Kong and Singapore domestic conditions (read from the statutes; expired regimes are not kept)
# ==== Hong Kong / Singapore domestic statute parameters (generated; every quote checked against clauses.csv)
# ==== BLOCK 1: core rows
# ---- Hong Kong: Inland Revenue Ordinance (hk.cap112.en)
# s14 charge
p("hk.profits.charge_scope", "HK", "ALL", "condition", "charge_requires_hk_business_and_hk_source_profits", 1, "bool", "hk.cap112.en#s14", "", "on every person carrying on a trade, profession or business in Hong Kong in respect of his assessable profits arising in or derived from Hong Kong", "利得税须同时满足在香港经营业务及利润于香港产生或得自香港")
p("hk.gain.capital_asset_excluded", "HK", "SHARE_TRANSFER", "condition", "capital_asset_sale_profits_excluded", 1, "bool", "hk.cap112.en#s14", "", "(excluding profits arising from the sale of capital assets)", "条文未给出资本性质的判断标准，需个案判断")
# s15(1)(b), (ba), s20B, s21A royalties
p("hk.royalty.deemed_use_in_hk", "HK", "ROYALTY", "condition", "deemed_hk_receipt_ip_used_in_hk", 1, "bool", "hk.cap112.en#s15", "", "received by or accrued to a person for the use, or the right to the use, in Hong Kong of any patent, design, trade mark, copyright material", "第15(1)(b)条；限于本部未另行征税的款项")
p("hk.royalty.deemed_use_outside_hk_deductible", "HK", "ROYALTY", "condition", "deemed_hk_receipt_ip_used_outside_hk_if_deductible_in_hk", 1, "bool", "hk.cap112.en#s15", "2004-06-25", "which are deductible in ascertaining the assessable profits of a person under this Part", "第15(1)(ba)条：在香港以外使用知识产权的款项，仅当可在香港利得税下扣除时才视为香港收入；起始日取同条编辑附注")
p("hk.royalty.payer_chargeable", "HK", "ROYALTY", "procedure", "non_resident_chargeable_in_name_of_hk_payer", 1, "bool", "hk.cap112.en#s20B", "", "is chargeable to tax in respect of the sums described in subsection (1) in the name of any person in Hong Kong who paid or credited those sums", "适用于第15(1)(a)、(b)、(ba)、(bb)条的款项；税款可向该香港付款人追讨")
p("hk.royalty.payer_must_deduct", "HK", "ROYALTY", "procedure", "payer_must_deduct_tax_at_payment", 1, "bool", "hk.cap112.en#s20B", "", "he shall, at the time he makes the payment or credit, deduct from those sums so much thereof as is sufficient to produce the amount of such tax", "条文未规定固定预扣率，扣除额为足以缴付该税款的数额")
p("hk.royalty.associate_carve_out", "HK", "ROYALTY", "condition", "associate_100pct_not_applied_if_ip_never_owned_by_hk_business", 1, "bool", "hk.cap112.en#s21A", "", "no person carrying on a trade, profession or business in Hong Kong has at any time wholly or partly owned the property in respect of which the sum is paid", "须税务局局长信纳；此时来自相联者的款项仍按 30% 计算")
# s15(1)(f), s26A interest
p("hk.interest.deemed_corporation", "HK", "INTEREST", "condition", "deemed_hk_receipt_corporation_interest_derived_from_hk", 1, "bool", "hk.cap112.en#s15", "", "sums received by or accrued to a corporation carrying on a trade, profession or business in Hong Kong by way of interest derived from Hong Kong", "第15(1)(f)条；法团须在香港经营业务且利息得自香港")
p("hk.interest.exempt_instruments", "HK", "INTEREST", "condition", "interest_on_specified_instruments_excluded_from_profits", 1, "bool", "hk.cap112.en#s26A", "", "shall not be included in the profits of any corporation or other person chargeable to tax under this Part", "第26A(1)条列举储税券、政府债券、外汇基金债务票据、港元多边机构债务票据、长期债务票据的利息；2011-03-25 起发行的长期债务票据由发行人的相联者收取时不适用（第1B款）")
# Division 3A foreign-sourced income (ss 15H-15OC)
p("hk.fsie.covered_income", "HK", "ALL", "condition", "specified_foreign_sourced_income_types", "interest;dividend;disposal_gain;ip_income", "enum", "hk.cap112.en#s15H", "", "means any interest, dividend, disposal gain or IP income arising in or derived from a territory outside Hong Kong", "受规管财务实体、享受优惠税率或免税的实体及买卖商的相关收入被排除在外")
p("hk.fsie.mne_entity_only", "HK", "ALL", "condition", "recipient_is_mne_entity_carrying_on_business_in_hk", 1, "bool", "hk.cap112.en#s15I", "", "is received in Hong Kong by an MNE entity carrying on a trade, profession or business in Hong Kong", "跨国企业集团指至少有一个实体或常设机构不在最终母实体所在司法管辖区的集团（第15H条）")
p("hk.fsie.received_in_hk_trigger", "HK", "ALL", "condition", "taxed_in_year_received_in_hk", 1, "bool", "hk.cap112.en#s15I", "", "is to be regarded as a receipt arising in or derived from Hong Kong for the basis period of the year of assessment during which the income is received in Hong Kong", "未在香港收取则第15I(1)条不触发")
p("hk.fsie.gain_not_capital", "HK", "SHARE_TRANSFER", "condition", "foreign_gain_not_treated_as_capital", 1, "bool", "hk.cap112.en#s15I", "", "is to be regarded as not arising from the sale of capital assets even if it so arises", "属第15I(1)条范围的指明外地收入不能援引第14条的资本资产排除")
p("hk.fsie.substance_exception_income", "HK", "ALL", "condition", "economic_substance_exception_income_types", "interest;dividend;non_ip_disposal_gain", "enum", "hk.cap112.en#s15K", "", "the income is interest, a dividend or a non-IP disposal gain", "满足第15K(2)条经济实质要求时第15I(1)条不适用；知识产权收入及其处置收益不适用此例外")
p("hk.fsie.substance_pure_holding", "HK", "ALL", "condition", "pure_equity_holding_entity_adequate_people_and_premises", 1, "bool", "hk.cap112.en#s15K", "", "in the Commissioner’s opinion, the entity has adequate human resources and premises for carrying out the specified economic activities", "纯股权持有实体另须遵守公司注册及存档规定，并在香港进行或安排进行持有及管理股权的活动；需裁量")
p("hk.fsie.participation_subject_to_tax", "HK", "DIVIDEND", "condition", "participation_exemption_requires_qualifying_similar_tax", 1, "bool", "hk.cap112.en#s15N", "", "the income is subject to a qualifying similar tax in a territory outside Hong Kong", "股息也可由其基础利润或有关下游收入已受合资格类似税项规限来满足；同样适用于股权处置收益")
p("hk.fsie.participation_anti_hybrid", "HK", "DIVIDEND", "anti_abuse", "participation_exemption_denied_if_dividend_deductible_abroad", 1, "bool", "hk.cap112.en#s15N", "", "section 15M does not apply if, and to the extent that, the income is allowable for deduction when computing the amount of the tax", "指股息在境外就基础利润计税时可获扣除的情形")
p("hk.fsie.participation_main_purpose", "HK", "DIVIDEND", "anti_abuse", "participation_exemption_main_purpose_test", 1, "bool", "hk.cap112.en#s15N", "", "the main purpose, or one of the main purposes, of the entity in entering into the arrangement was to obtain a tax benefit", "须税务局局长信纳，需裁量")
p("hk.fsie.intragroup_assoc_ratio_min", "HK", "SHARE_TRANSFER", "condition", "intragroup_transfer_relief_associating_interest_min", 75, "%", "hk.cap112.en#s15OC", "", "entity A has at least 75% of direct or indirect beneficial interest in, or in relation to, entity B", "第15OA条集团内部转让宽免的相联门槛，也可按表决权计算；买卖双方出售时均须应课利得税")
p("hk.fsie.intragroup_clawback_years", "HK", "SHARE_TRANSFER", "limit", "intragroup_transfer_relief_clawback_years", 2, "years", "hk.cap112.en#s15OB", "", "within 2 years after the subject sale", "期内任一方不再应课利得税或双方不再相联，则宽免终止")
# s50, s50AAA double taxation relief
p("hk.ftc.credit_limit", "HK", "ALL", "limit", "treaty_credit_limit", "hk_tax_on_same_income_at_average_rate", "enum", "hk.cap112.en#s50", "", "The credit shall not exceed the amount which would be produced by computing the amount of the income in accordance with the provisions of this Ordinance and then charging it to tax at a rate", "税率为抵免前应课税款除以总收入")
p("hk.ftc.unilateral_no_dta", "HK", "ALL", "condition", "unilateral_credit_if_no_dta", 1, "bool", "hk.cap112.en#s50AAA", "", "no double taxation arrangements have been made with the government of a territory outside Hong Kong", "已有安排但未纳入豁免条文或抵免条文时同样适用；可抵免的收入范围见附表54")
# Schedule 17K onshore equity disposal gains
p("hk.onshore_gain.ratio_min", "HK", "SHARE_TRANSFER", "condition", "qualifying_equity_interest_min", 15, "%", "hk.cap112.en#sch17K", "2024-01-01", "entitle the holder of the interests to at least a 15% share in the profits, capital or reserves of the investee entity", "附表17K；可与密切相关实体持有的权益合并计算；仅适用于于香港产生或得自香港的处置收益")
p("hk.onshore_gain.holding_months_min", "HK", "SHARE_TRANSFER", "condition", "holding_months_min", 24, "months", "hk.cap112.en#sch17K", "2024-01-01", "means the continuous period of 24 months immediately before the date of the disposal", "须在整个参考期间持有")
p("hk.onshore_gain.election_required", "HK", "SHARE_TRANSFER", "procedure", "written_election_required", 1, "bool", "hk.cap112.en#sch17K", "2024-01-01", "Subsection (1) does not apply to an investor entity unless it elects in writing that the subsection applies to it", "未作书面选择则不适用附表17K第5(1)条")
# ---- Singapore: Income Tax Act 1947 (sg.ita1947.full)
# s10 charge
p("sg.charge.basis", "SG", "ALL", "condition", "income_chargeable_bases", "accruing_in_or_derived_from_sg;received_in_sg_from_outside", "enum", "sg.ita1947.full#s10", "", "upon the income of any person accruing in or derived from Singapore or received in Singapore from outside Singapore", "第10(1)款")
p("sg.foreign_income.remittance_is_receipt", "SG", "ALL", "condition", "foreign_income_remitted_counts_as_received_in_sg", 1, "bool", "sg.ita1947.full#s10", "", "any amount from any income derived from outside Singapore which is remitted to, transmitted or brought into, Singapore", "第10(25)款；用于偿还新加坡业务债务或购买动产并带入新加坡亦视为在新加坡收取")
# s12(6), (7) deemed source
p("sg.source.interest_borne_by_sg", "SG", "INTEREST", "condition", "deemed_sg_source_if_borne_by_sg_resident_or_pe", 1, "bool", "sg.ita1947.full#s12", "", "borne, directly or indirectly, by a person resident in Singapore or a permanent establishment in Singapore except in respect of any business carried on outside Singapore", "第12(6)款；可在新加坡来源所得中扣除者亦视为来源于新加坡；经境外常设机构经营的业务及境外不动产除外")
p("sg.source.royalty_borne_by_sg", "SG", "ROYALTY", "condition", "deemed_sg_source_if_borne_by_sg_resident_or_pe", 1, "bool", "sg.ita1947.full#s12", "", "which is borne, directly or indirectly, by a person resident in Singapore or a permanent establishment in Singapore", "第12(7)款；可在新加坡来源所得中扣除者亦视为来源于新加坡；经境外常设机构在境外经营的业务除外")
# s43(3) conditions of the 15% rate
p("sg.wht.interest_non_resident", "SG", "INTEREST", "condition", "recipient_not_resident_in_sg", 1, "bool", "sg.ita1947.full#s43", "1996-02-28", "accruing in or derived from Singapore on or after 28 February 1996 by a person not resident in Singapore", "第43(3)款")
p("sg.wht.interest_not_sg_trade", "SG", "INTEREST", "condition", "not_derived_from_trade_carried_on_in_sg", 1, "bool", "sg.ita1947.full#s43", "1996-02-28", "which is not derived by the person from any trade, business, profession or vocation carried on or exercised by the person in Singapore", "第43(3)款；不满足时不适用 15% 税率")
p("sg.wht.interest_not_sg_pe", "SG", "INTEREST", "condition", "not_effectively_connected_with_sg_pe", 1, "bool", "sg.ita1947.full#s43", "1996-02-28", "which is not effectively connected with any permanent establishment in Singapore of the person", "第43(3)款；不满足时不适用 15% 税率")
# s45 withholding
p("sg.wht.payer_duty", "SG", "INTEREST", "procedure", "payer_must_withhold_if_payee_not_known_resident", 1, "bool", "sg.ita1947.full#s45", "", "Where a person is liable to pay to another person not known to the firstmentioned person to be resident in Singapore any interest which is chargeable to tax under this Act, the firstmentioned person must", "须扣税并立即通知及向税务局缴付所扣税款")
p("sg.wht.rate_fallback", "SG", "INTEREST", "rate", "withholding_rate_non_individual_when_s43_3_3a_not_applicable", 17, "%", "sg.ita1947.full#s45", "", "where the person to be paid is any other person, at the rate of 17%", "收款人非个人且不适用第43(3)或(3A)款时的扣缴率；依第45A条同样适用于第12(6)、(7)款所得")
p("sg.wht.late_penalty", "SG", "INTEREST", "procedure", "late_payment_penalty", 5, "%", "sg.ita1947.full#s45", "", "a sum equal to 5% of such amount of tax is payable", "逾期未向税务局缴付所扣税款的罚款")
p("sg.wht.late_penalty_monthly", "SG", "INTEREST", "procedure", "late_payment_additional_penalty_per_month", 1, "%", "sg.ita1947.full#s45", "", "an additional penalty of 1% of such amount of tax is payable for each completed month that the tax remains unpaid", "期限后 30 日内仍未缴付时按完整月份加收")
p("sg.wht.late_penalty_monthly_cap", "SG", "INTEREST", "limit", "late_payment_additional_penalty_cap", 15, "%", "sg.ita1947.full#s45", "", "the total additional penalty under this paragraph must not exceed 15% of the amount of tax outstanding", "追加罚款的上限")
# s13(8), (9) foreign-sourced dividends
p("sg.fsie.subject_to_tax", "SG", "DIVIDEND", "condition", "foreign_income_subject_to_tax_in_source_territory", 1, "bool", "sg.ita1947.full#s13", "", "the income is subject to tax of a similar character to income tax (by whatever name called)", "第13(9)(a)款；股息可计入派息公司就其利润已缴的税款（第10款），部长可个案豁免此条件（第9B款）")
p("sg.fsie.beneficial", "SG", "DIVIDEND", "condition", "comptroller_satisfied_exemption_beneficial", 1, "bool", "sg.ita1947.full#s13", "", "the Comptroller is satisfied that the tax exemption would be beneficial to the person resident in Singapore", "第13(9)(c)款，需裁量")
# s10L gains from the sale of foreign assets
p("sg.s10l.relevant_group_entity", "SG", "SHARE_TRANSFER", "condition", "seller_is_entity_of_relevant_group", 1, "bool", "sg.ita1947.full#s10L", "2024-01-01", "gains from the sale or disposal by an entity (called in this section the seller entity) of a relevant group of any movable or immovable property situated outside Singapore", "相关集团指集团实体并非全部在同一司法管辖区设立，或任一实体在多于一个司法管辖区设有营业地点")
p("sg.s10l.received_in_sg_trigger", "SG", "SHARE_TRANSFER", "condition", "gain_taxed_when_received_in_sg", 1, "bool", "sg.ita1947.full#s10L", "2024-01-01", "that are received in Singapore from outside Singapore, are treated as income chargeable to tax under section 10(1)", "按第10(1)(g)款课税；仅适用于本不属第10(1)条应税所得或本可免税的收益（第2款）")
p("sg.s10l.excluded_entity", "SG", "SHARE_TRANSFER", "condition", "economic_substance_carve_out", 1, "bool", "sg.ita1947.full#s10L", "2024-01-01", "carried out by an entity that is an excluded entity in the basis period in which the sale or disposal occurred", "仅限非知识产权的境外资产；除外实体须在新加坡管理和执行业务并具备足够经济实质")
# s13W disposal of shares
p("sg.s13w.ratio_min", "SG", "SHARE_TRANSFER", "condition", "shareholding_ratio_min", 20, "%", "sg.ita1947.full#s13W", "2026-01-01", "legally and beneficially owned at least 20% of the ordinary shares in investee company B1", "第13W(1A)款；亦可按普通股与优先股实缴股本价值合计至少 20% 满足；该款未设终止日期")
p("sg.s13w.holding_months_min", "SG", "SHARE_TRANSFER", "condition", "holding_months_min", 24, "months", "sg.ita1947.full#s13W", "2026-01-01", "at all times during a continuous period of at least 24 months ending on the date immediately before the date of disposal of such shares", "第13W(1A)款")
# s50, s50A, s50C foreign tax credit
p("sg.ftc.credit_limit", "SG", "ALL", "limit", "treaty_credit_limit", "sg_tax_on_same_income_at_average_rate", "enum", "sg.ita1947.full#s50", "", "The credit must not exceed the amount which would be produced by computing the amount of the income in accordance with the provisions of this Act and then charging it to income tax at a rate", "税率为抵免前应课所得税除以应评税收入")
p("sg.ftc.unilateral", "SG", "ALL", "condition", "unilateral_credit_if_no_treaty", 1, "bool", "sg.ita1947.full#s50A", "", "Even if there are no arrangements in force under section 49 with the government of any territory outside Singapore, tax credit under section 50 must, subject to this section, be given to any person resident in Singapore", "涵盖股息、第10L条收益等；利息与特许权使用费限于非由新加坡居民或常设机构负担且不可在新加坡扣除者")
p("sg.ftc.pooling_foreign_tax_paid", "SG", "ALL", "condition", "pooling_requires_foreign_tax_paid", 1, "bool", "sg.ita1947.full#s50C", "", "income tax (by whatever name called) or qualified domestic minimum top\u2011up tax (but disregarding any excluded top\u2011up tax), has been paid on the income", "汇集抵免条件之一（第50C(2)(a)款）")
p("sg.ftc.pooling_headline_rate_min", "SG", "ALL", "condition", "pooling_foreign_headline_rate_min", 15, "%", "sg.ita1947.full#s50C", "", "carried on by a company in that territory at that time, is not less than 15%", "汇集抵免条件之一：收取时来源地最高公司税率不低于 15%")
#
# ==== BLOCK 2: supplementary rows (finer conditions of the same provisions; drop this block if a smaller set is wanted)
# ---- Hong Kong
p("hk.royalty.deemed_film_use_in_hk", "HK", "ROYALTY", "condition", "deemed_hk_receipt_film_or_recording_used_in_hk", 1, "bool", "hk.cap112.en#s15", "", "received by or accrued to a person from the exhibition or use in Hong Kong of cinematograph or television film or tape, any sound recording", "第15(1)(a)条；限于本部未另行征税的款项")
p("hk.interest.deemed_financial_institution", "HK", "INTEREST", "condition", "deemed_hk_receipt_financial_institution_hk_business", 1, "bool", "hk.cap112.en#s15", "", "received by or accrued to a financial institution by way of interest which arises through or from the carrying on by the financial institution of its business in Hong Kong", "第15(1)(i)条；即使有关资金在香港以外提供")
p("hk.interest.deemed_intragroup_financing", "HK", "INTEREST", "condition", "deemed_hk_receipt_intragroup_financing_business_in_hk", 1, "bool", "hk.cap112.en#s15", "", "by way of interest that arises through or from the carrying on in Hong Kong by the corporation of its intra-group financing business", "第15(1)(ia)条；适用于金融机构以外的法团，即使有关资金在香港以外提供")
p("hk.fsie.remittance_is_receipt", "HK", "ALL", "condition", "sum_remitted_counts_as_received_in_hk", 1, "bool", "hk.cap112.en#s15H", "", "the sum is remitted to, or is transmitted or brought into, Hong Kong", "第15H(5)条；用于偿还在港业务债务或购买动产并带入香港亦视为在香港收取")
p("hk.fsie.commencement", "HK", "ALL", "condition", "regime_applies_to_income_accrued_and_received_from", 1, "bool", "hk.cap112.en#sch55", "2023-01-01", "apply in relation to specified foreign-sourced income accrued and received on or after 1 January 2023", "附表55过渡条文；2023年修订扩大的处置收益范围适用于 2024-01-01 起累算并收取的收入（附表56）")
p("hk.fsie.substance_non_pure_holding", "HK", "ALL", "condition", "non_pure_equity_holding_entity_adequate_operating_expenditure_in_hk", 1, "bool", "hk.cap112.en#s15K", "", "the total amount of operating expenditure incurred in Hong Kong for carrying out the specified economic activities is adequate in the Commissioner’s opinion", "非纯股权持有实体另须在香港有足够数目的合资格雇员进行指明经济活动；需裁量")
p("hk.fsie.participation_headline_rate_basis", "HK", "DIVIDEND", "condition", "reference_rate_compared_with_highest_applicable_rate", 1, "bool", "hk.cap112.en#s15N", "", "the highest applicable rate, of a similar tax in that territory is equal to or higher than the reference rate", "比较的是境外类似税项的适用税率（多于一个时取最高者），非实际税负")
p("hk.fsie.intragroup_relief", "HK", "SHARE_TRANSFER", "condition", "intragroup_transfer_at_no_gain_no_loss", 1, "bool", "hk.cap112.en#s15OA", "", "the selling entity is to be regarded as having sold the subject property for a consideration of such amount as would secure that neither a gain nor a loss would accrue to the selling entity", "第15OA(3)条；买卖双方须相联且出售时均应课利得税")
p("hk.fsie.ip_nexus_exception", "HK", "ROYALTY", "condition", "qualifying_ip_income_excepted_portion_by_nexus", 1, "bool", "hk.cap112.en#s15L", "", "section 15I(1) does not operate in relation to the excepted portion of the income ascertained under Part 2 of Schedule 17FC", "仅限合资格知识产权收入，例外部分按附表17FC计算")
p("hk.ftc.unilateral_fsie_only", "HK", "ALL", "condition", "unilateral_credit_only_for_income_charged_under_s15I", 1, "bool", "hk.cap112.en#sch54", "2023-01-01", "the following condition is specified for the income: the income is chargeable to profits tax because of section 15I(1)", "单边抵免只适用于因第15I(1)条而应课税的指明外地收入；股权以外的处置收益自 2024-01-01 起累算并收取者适用")
p("hk.ftc.underlying_ratio_min", "HK", "DIVIDEND", "condition", "underlying_tax_credit_adequate_interest_min", 10, "%", "hk.cap112.en#s50AAAC", "", "person A has at least 10% of direct or indirect beneficial interest in, or in relation to, person B", "股息基础利润已缴税款获抵免所需的足够权益，也可按表决权计算")
# ---- Singapore
p("sg.source.interest_loan_funds_used_in_sg", "SG", "INTEREST", "condition", "deemed_sg_source_if_loan_funds_used_in_sg", 1, "bool", "sg.ita1947.full#s12", "", "any income derived from loans where the funds provided by such loans are brought into or used in Singapore", "第12(6)(b)款")
p("sg.wht.royalty_non_resident", "SG", "ROYALTY", "condition", "recipient_not_resident_in_sg", 1, "bool", "sg.ita1947.full#s43", "2005-01-01", "accruing in or derived from Singapore on or after 1 January 2005 by a person not resident in Singapore", "第43(3A)款")
p("sg.wht.royalty_not_sg_trade", "SG", "ROYALTY", "condition", "not_derived_from_trade_carried_on_in_sg", 1, "bool", "sg.ita1947.full#s43", "2005-01-01", "which is not derived by the person from any trade, business, profession or vocation carried on or exercised by the person in Singapore", "第43(3A)款含相同措辞；不满足时不适用 10% 税率")
p("sg.wht.royalty_not_sg_pe", "SG", "ROYALTY", "condition", "not_effectively_connected_with_sg_pe", 1, "bool", "sg.ita1947.full#s43", "2005-01-01", "which is not effectively connected with any permanent establishment in Singapore of the person", "第43(3A)款含相同措辞；不满足时不适用 10% 税率")
p("sg.wht.duty_extends_to_royalty", "SG", "ROYALTY", "procedure", "withholding_duty_applies_to_s12_6_7_income", 1, "bool", "sg.ita1947.full#s45A", "", "Section 45(1) to (8) applies in relation to the payment of any income referred to in section 12(6) or (7)", "第45条的扣缴、申报期限及罚款规定同样适用于第12(6)、(7)款所得")
p("sg.fsie.recipient", "SG", "DIVIDEND", "condition", "recipient_resident_non_individual", 1, "bool", "sg.ita1947.full#s13", "2003-06-01", "on or after 1 June 2003 by any person, not being an individual, resident in Singapore", "第13(8)(d)款；须为在新加坡收取的境外股息")
p("sg.fsie.ministerial_order", "SG", "ALL", "condition", "exemption_or_concessionary_rate_by_ministerial_order", 1, "bool", "sg.ita1947.full#s13", "", "the income received by a person resident in Singapore from such source in any country outside Singapore as may be specified in the order", "第13(12)款；部长可通过命令全部或部分免税或适用优惠税率，须有具体命令")
p("sg.s10l.substance_pure_holding", "SG", "SHARE_TRANSFER", "condition", "pure_equity_holding_entity_adequate_people_and_premises_in_sg", 1, "bool", "sg.ita1947.full#s10L", "2024-01-01", "the entity has adequate human resources and premises in Singapore to carry out the operations of the entity", "纯股权持有实体另须依法定期提交报表，且业务在新加坡管理和执行")
p("sg.s10l.substance_non_pure_holding", "SG", "SHARE_TRANSFER", "condition", "non_pure_equity_holding_entity_adequate_economic_substance_in_sg", 1, "bool", "sg.ita1947.full#s10L", "2024-01-01", "the entity has adequate economic substance in Singapore, taking into account the following considerations", "另须业务在新加坡管理和执行；考虑雇员人数、资历经验、业务支出及关键决策是否在新加坡作出")
p("sg.s10l.share_situs", "SG", "SHARE_TRANSFER", "condition", "company_share_situs", "place_of_incorporation", "enum", "sg.ita1947.full#s10L", "2024-01-01", "any shares in or securities issued by a company, or any right or interest in such shares or securities, are situated where the company is incorporated", "用于判断是否属境外资产；登记股份以登记册所在地为准（第15款(i)项）")
p("sg.ftc.underlying_ratio_min", "SG", "DIVIDEND", "condition", "underlying_tax_credit_shareholding_min", 25, "%", "sg.ita1947.full#s50A", "", "owns not less than 25% of the total number of issued shares of the company paying the dividend", "达到该比例时抵免须计入派息公司就其利润已缴的税款；部长可个案豁免此比例要求")
p("sg.ftc.pooling_election", "SG", "ALL", "procedure", "pooling_by_election", 1, "bool", "sg.ita1947.full#s50C", "", "the person may elect to be given a pooled credit for that year of assessment in lieu of any 2 or more of those credits", "自 2012 课税年度起")
p("sg.ftc.pooling_sg_tax_not_nil", "SG", "ALL", "condition", "pooling_requires_sg_tax_payable_on_income", 1, "bool", "sg.ita1947.full#s50C", "", "the income tax payable under this Act on the income for the year of assessment (before allowance of any credit under this Part) is not nil", "汇集抵免条件之一（第50C(2)(c)款）")

# ---- exposed by the S45 calculator labels (labels/sg_s45_labels.csv)
p("sg.wht.late_penalty_monthly_starts_after_days", "SG", "INTEREST", "limit", "additional_penalty_starts_after_days", 30, "days",
  "sg.ita1947.full#s45", "", "within 30 days after the time specified in paragraph (a), an additional penalty of 1%",
  "每月 1% 的附加罚款在到期日后 30 天仍未缴时才开始按整月计")
p("sg.dtr.cor_due", "SG", "ALL", "limit", "certificate_of_residence_due", "31 Mar of the following year", "text",
  "sg.iras.wht.dta-relief#h3", "", "The due date is 31 Mar of the following year if the claim is for a period in the current calendar year",
  "主张协定减免须在次年 3 月 31 日前提交对方居民证明")

p("sg.time.excluded_days", "SG", "ALL", "limit", "excluded_days", "sunday;public_holiday", "enum", "sg.ia1965.full#s50", "",
  "if the last day of the period is a Sunday or a public holiday (which days are called in this section excluded days) the period includes the next following day not being an excluded day",
  "期限最后一天是周日或公众假期时顺延到下一个非排除日；周六不在其列")
p("sg.time.act_on_excluded_day", "SG", "ALL", "limit", "act_due_on_excluded_day_moves_to_next_day", 1, "bool", "sg.ia1965.full#s50", "",
  "if that day happens to be an excluded day, the act or proceeding is considered as done or taken in due time if it is done or taken on the next day afterwards, not being an excluded day",
  "规定在某日办理的事项，该日为排除日的，次一非排除日办理视为按期")
p("sg.holiday.sunday_substitute", "SG", "ALL", "limit", "holiday_on_sunday_next_day_is_holiday", 1, "bool", "sg.ha1998.full#s4", "",
  "if any day specified in the Schedule falls on a Sunday, the day next following not being itself a public holiday is declared a public holiday in Singapore",
  "法定假日逢周日，次日为公众假期")
p("sg.wht.movable_property_rent", "SG", "ROYALTY", "rate", "withholding_rate_non_resident_movable_property_rent", 15, "%",
  "sg.ita1947.full#s43", "", "tax at the rate of 15% is to be levied and paid on the gross amount of — ( a ) any income referred to in section 12(6); and ( b ) any income referred to in section 12(7)( a ), ( b ) and ( d )",
  "第43条第3款：第12条第7款(d)项的动产租金按 15%；(a)(b)项的特许权使用费另由第3A款降为 10%")
p("cn-sg.int.government_exempt", SG, "INTEREST", "condition", "exempt_if_beneficial_owner_is_listed_government_body", 1, "bool",
  "treaty.cn-sg.2007.p2.zh#2.1", "2010-01-01", "从缔约国一方取得的利息应在该国免税，如果受益所有人是",
  "第二议定书替换后的第11条第3款；限列名的政府、央行及政府全资机构")
p("cn-sg.int.government_exempt_condition", SG, "INTEREST", "condition", "wholly_government_owned_and_non_commercial", 1, "bool",
  "treaty.cn-sg.2007.p2.zh#2.1", "2010-01-01", "应为中国政府完全拥有并且不从事商业活动",
  "列名机构还须由政府完全拥有且不从事商业活动")

p("cn-sg.roy.includes_equipment", SG, "ROYALTY", "condition", "royalties_include_equipment_use", 1, "bool", AS + "#12.3",
  "2008-01-01", "也包括使用或有权使用工业、商业、科学设备", "协定对特许权使用费的定义包含设备使用费")
p("cn-sg.roy.equipment_rent_is_royalty", SG, "ROYALTY", "condition", "equipment_rent_is_royalty", 1, "bool",
  "cn.gsf.2010-75#12.3", "", "特许权使用费也包括使用或有权使用工业、商业、科学设备取得的所得，即设备租金",
  "税务总局条文解释；融资租赁中被认定为利息的部分、不动产使用费除外")

p("sg.wht.comptroller_may_allow_other_period", "SG", "ALL", "procedure", "comptroller_may_allow_other_period", 1, "bool",
  "sg.ita1947.full#s45", "", "allow any person or class of persons to give notice of the deduction of tax and make payment of the amount so deducted within such other period and subject to such conditions as the Comptroller may determine",
  "第45条第2款(a)项：税务长可准许某人或某类人在其他期限内申报并缴纳。税务局实务上的到期日晚于法定日期时，法律上的授权在此")
p("sg.wht.penalty_runs_from_allowed_date", "SG", "ALL", "procedure", "penalty_date_is_15th_or_date_allowed", 1, "bool",
  "sg.ita1947.full#s45", "", "or such other date as may be allowed under subsection (2)(a), a sum equal to 5% of such amount of tax is payable",
  "第45条第4款(a)项：罚款以 15 日或税务长准许的其他日期为界")

p("sg.dtr.cor_due_prior_years", "SG", "ALL", "limit", "certificate_of_residence_due_prior_years", "3 months from WHT submission", "text",
  "sg.iras.wht.dta-relief#h3", "", "Within 3 months from the date of WHT submission if the claim is for preceding calendar years",
  "付款所属年度早于申报年度时，居民证明须在申报后 3 个月内提交")

p("cn-hk.cor.covers_following_years", HK, "ALL", "procedure", "hk_certificate_covers_following_calendar_years", 2, "years",
  "cn.sta.2016-35#all", "2016-04-15", "可用作证明该香港居民在该公历年度及其后连续两个公历年度的香港居民身份",
  "香港税务局就某公历年度出具的居民身份证明书，在内地可用于该年度及其后连续两个公历年度；情况变化后不再适用")
p("cn-hk.cor.void_after_change", HK, "ALL", "procedure", "hk_certificate_void_after_change_of_circumstances", 1, "bool",
  "cn.sta.2016-35#all", "2016-04-15", "不再符合享受《安排》待遇条件，则原适用于该公历年度的居民身份证明书不能用作证明其在情况发生变化后的香港居民身份",
  "居民情况变化后，原证明书不能再证明变化后的居民身份")

# ---- Mainland: when the withholding obligation arises, and the exchange rate it fixes
p("cn.wht.obligation_date", "CN", "ALL", "procedure", "withholding_obligation_date", "actual payment or date payable", "text",
  "cn.sta.2017-37#i4", "2017-12-01", "扣缴义务发生之日为相关款项实际支付或者到期应支付之日",
  "扣缴义务在实际支付或到期应支付之日发生；到期应支付指按权责发生制应计入成本费用的应付款（cn.reg.eit#105）")
p("cn.wht.obligation_date_dividend", "CN", "DIVIDEND", "procedure", "withholding_obligation_date_dividend", "actual payment", "text",
  "cn.sta.2017-37#i7", "2017-12-01", "相关应纳税款扣缴义务发生之日为股息、红利等权益性投资收益实际支付之日",
  "股息以实际支付日为扣缴义务发生日，不看到期应付")
p("cn.wht.fx_rule", "CN", "ALL", "procedure", "fx_conversion_rule", "CNY central parity on the obligation date", "text",
  "cn.sta.2017-37#i4", "2017-12-01", "应当按照扣缴义务发生之日人民币汇率中间价折合成人民币",
  "外币计价的款项按扣缴义务发生之日的人民币汇率中间价折算；中间价由中国外汇交易中心公布，见 tools/fx_cny.py")

# ---- Mainland: profits reinvested by the foreign investor, withholding deferred (财税〔2018〕102号, 公告2018年第53号)
D = "cn.cs.2018-102"
p("cn.reinvest.deferral", "CN", "DIVIDEND", "condition", "reinvestment_defers_withholding", 1, "bool", D + "#i1", "2018-01-01",
  "用于境内直接投资暂不征收预提所得税政策的适用范围，由外商投资鼓励类项目扩大至所有非禁止外商投资的项目和领域",
  "境外投资者以分得利润在境内直接投资，暂不征收预提所得税；范围为所有非禁止外商投资的项目和领域")
p("cn.reinvest.forms", "CN", "DIVIDEND", "condition", "qualifying_investment_forms", "capital_increase;new_entity;unrelated_acquisition", "text",
  D + "#i2", "2018-01-01", "1.新增或转增中国境内居民企业实收资本或者资本公积； 2.在中国境内投资新建居民企业； 3.从非关联方收购中国境内居民企业股权",
  "三种直接投资形式；补缴已认缴注册资本也属新增实收资本（cn.sta.2018-53#i1）")
p("cn.reinvest.excludes_listed_shares", "CN", "DIVIDEND", "condition", "listed_shares_excluded_unless_strategic", 1, "bool", D + "#i2", "2018-01-01",
  "不包括新增、转增、收购上市公司股份（符合条件的战略投资除外）", "上市公司股份不算，战略投资除外")
p("cn.reinvest.profit_is_distributed_retained_earnings", "CN", "DIVIDEND", "condition", "profit_is_actually_distributed_retained_earnings", 1, "bool",
  D + "#i2", "2018-01-01", "境外投资者分得的利润属于中国境内居民企业向投资者实际分配已经实现的留存收益而形成的股息、红利等权益性投资收益",
  "须是实际分配的已实现留存收益")
p("cn.reinvest.direct_payment", "CN", "DIVIDEND", "condition", "funds_move_directly_to_investee", 1, "bool", D + "#i2", "2018-01-01",
  "相关款项从利润分配企业的账户直接转入被投资企业或股权转让方账户，在直接投资前不得在境内外其他账户周转",
  "资金须从利润分配企业账户直接转入被投资企业或转让方账户；经人民币再投资专用存款账户当日划转视为直接（cn.sta.2018-53#i2）")
p("cn.reinvest.retroactive_claim_years", "CN", "DIVIDEND", "limit", "retroactive_claim_years", 3, "years", D + "#i5", "2018-01-01",
  "可在实际缴纳相关税款之日起三年内申请追补享受该政策，退还已缴纳的税款", "未享受的可在缴税之日起三年内追补并退税")
p("cn.reinvest.recapture_days", "CN", "DIVIDEND", "limit", "recapture_filing_days_after_withdrawal", 7, "days", D + "#i6", "2018-01-01",
  "在实际收取相应款项后7日内，按规定程序向税务部门申报补缴递延的税款", "收回投资后 7 日内补缴递延税款")
p("cn.reinvest.special_reorg_continues", "CN", "DIVIDEND", "condition", "special_reorganisation_keeps_deferral", 1, "bool", D + "#i7", "2018-01-01",
  "被投资企业发生重组符合特殊性重组条件，并实际按照特殊性重组进行税务处理的，可继续享受暂不征收预提所得税政策待遇", "特殊性重组不触发补缴")
p("cn.reinvest.late_from_payment_date", "CN", "DIVIDEND", "procedure", "late_payment_runs_from_profit_payment", 1, "bool", D + "#i4", "2018-01-01",
  "税款延迟缴纳期限自相关利润支付之日起计算", "后续核实不符合条件的，滞纳期自利润支付之日起算")
p("cn.reinvest.treaty_at_payment_time", "CN", "DIVIDEND", "procedure", "recapture_uses_treaty_in_force_at_payment", 1, "bool",
  "cn.sta.2018-53#i3", "2018-01-01", "仅可适用相关利润支付时有效的税收协定", "补缴时可享协定待遇，但以利润支付时有效的协定为准")
p("cn.reinvest.fifo_disposal", "CN", "DIVIDEND", "procedure", "deferred_tranche_disposed_first", 1, "bool", "cn.sta.2018-53#i11", "2018-01-01",
  "视为先行处置已享受暂不征税政策的投资", "部分处置时视为先处置已递延的部分")
p("cn.reinvest.payer_filing_days", "CN", "DIVIDEND", "limit", "payer_filing_days_after_payment", 7, "days", "cn.sta.2018-53#i6", "2018-01-01",
  "应在实际支付利润之日起7日内，向主管税务机关提交以下资料", "利润分配企业在支付后 7 日内报送扣缴报告表与信息报告表")

# ---- Mainland: reinvestment tax credit 2025-2028 (财政部 税务总局 商务部公告2025年第2号, 公告2025年第18号)
C = "cn.cs.2025-02"
p("cn.reinvest.credit_rate", "CN", "DIVIDEND", "rate", "reinvestment_credit_rate", 10, "%", C + "#i1", "2025-01-01",
  "可按照投资额的10%抵免境外投资者当年的应纳税额，当年不足抵免的准予向以后结转",
  "再投资额的 10% 抵免当年应纳税额，不足结转；2028-12-31 后余额可继续抵至零（#i10）", to="2028-12-31")
p("cn.reinvest.credit_rate_treaty_lower", "CN", "DIVIDEND", "rate", "credit_rate_follows_lower_treaty_rate", 1, "bool", C + "#i1", "2025-01-01",
  "税收协定中关于股息、红利等权益性投资收益适用税率低于10%的，按照协定税率执行",
  "协定股息税率低于 10% 时按协定税率计算抵免额（内地香港合格股息 5%）；比例一经选定不得再改（cn.sta.2025-18#i4）", to="2028-12-31")
p("cn.reinvest.credit_min_holding_months", "CN", "DIVIDEND", "condition", "credit_min_holding_months", 60, "months", C + "#i2", "2025-01-01",
  "境外投资者境内再投资需连续持有至少5年（60个月）以上", "连续持有满 60 个月；起算月为《利润再投资情况表》的再投资时间当月（cn.sta.2025-18#i2）", to="2028-12-31")
p("cn.reinvest.credit_encouraged_industry", "CN", "DIVIDEND", "condition", "investee_in_encouraged_catalogue", 1, "bool", C + "#i2", "2025-01-01",
  "被投资企业从事的产业属于《鼓励外商投资产业目录》所列的全国鼓励外商投资产业目录", "被投资企业须属全国鼓励外商投资产业目录", to="2028-12-31")
p("cn.reinvest.credit_against", "CN", "DIVIDEND", "condition", "credit_offsets_later_income_from_same_payer", 1, "bool", C + "#i3", "2025-01-01",
  "境外投资者从利润分配企业自利润分配再投资之日以后取得的企业所得税法第三条第三款规定的股息红利、利息、特许权使用费等所得应缴纳的企业所得税",
  "抵免只能冲抵再投资之日后从同一利润分配企业取得的股息、利息、特许权使用费等的税额；多个分配企业分别归集（cn.sta.2025-18#i5）", to="2028-12-31")
p("cn.reinvest.credit_recapture_days", "CN", "DIVIDEND", "limit", "credit_recapture_filing_days", 7, "days", C + "#i5", "2025-01-01",
  "应在收回投资后7日内向利润分配企业所在地税务机关申报补缴递延的税款", "收回投资后 7 日内补缴递延税款，结转余额可抵", to="2028-12-31")
p("cn.reinvest.credit_early_withdrawal_reduces", "CN", "DIVIDEND", "condition", "withdrawal_before_60_months_reduces_credit", 1, "bool", C + "#i5", "2025-01-01",
  "还应按比例减少境外投资者可享受的税收抵免额度", "不满 60 个月收回的，按比例减少抵免额度，已超用部分 7 日内补缴", to="2028-12-31")
p("cn.reinvest.credit_fx", "CN", "DIVIDEND", "procedure", "credit_fx_rule", "CNY central parity on the payment date", "text",
  "cn.sta.2025-18#i6", "2025-01-01", "按实际支付相关款项之日的汇率中间价折合成人民币", "外币再投资按实际支付日中间价折算", to="2028-12-31")
p("cn.reinvest.credit_holding_stop", "CN", "DIVIDEND", "procedure", "holding_stops_at_registration_change_month", 1, "bool",
  "cn.sta.2025-18#i3", "2025-01-01", "以被投资企业完成股权变更或注销登记手续当月，确认停止计算其持有该再投资被收回部分的时间",
  "持有期止于股权变更或注销登记当月；更早取得对价的以取得当月为准", to="2028-12-31")

# ---- added 2026-10-07 for the CN rule spec
p("cn.bo.via_100pct_owner", "CN", "DIVIDEND", "condition", "beneficial_owner_via_100pct_owner", 1, "bool",
  "cn.sta.2018-09#i3", "2018-04-01", "直接或间接持有申请人100%股份的人符合“受益所有人”条件",
  "申请人不合格但 100% 持有人合格且为同一居民国居民或中间层均合格时，视为受益所有人；仅股息")
p("cn.gaar", "CN", "ALL", "anti_abuse", "general_anti_avoidance", 1, "bool", "cn.law.eit#47", "2008-01-01",
  "企业实施其他不具有合理商业目的的安排而减少其应纳税收入或者所得额的，税务机关有权按照合理方法调整",
  "不具有合理商业目的指以减少、免除或者推迟缴纳税款为主要目的（实施条例第120条）；综合判断，对应 U(DISCRETION)")
p("cn.tca.late_surcharge_daily", "CN", "ALL", "procedure", "late_payment_surcharge_per_day", 0.05, "%", "cn.law.tca#32", "",
  "从滞纳税款之日起，按日加收滞纳税款万分之五的滞纳金", "扣缴义务人逾期解缴：每日万分之五")
p("cn-sg.int.government_exempt_condition_sg", SG, "INTEREST", "condition", "sg_bodies_statutory_or_wholly_government_owned_and_non_commercial", 1, "bool",
  "treaty.cn-sg.2007.p2.zh#2.1", "2010-01-01", "应依照新加坡议会法案规定设立或完全由新加坡政府拥有，并且不从事商业活动",
  "新加坡一侧列名机构（金管局、政府投资公司、法定机构）的附加条件；内地来源利息付给新加坡政府机构时适用")
p("cn-hk.int.government_exempt", HK, "INTEREST", "condition", "exempt_if_received_by_other_side_government_or_agreed_body", 1, "bool",
  "treaty.cn-hk.2006.zh#11.3", "2007-01-01", "发生于一方而为另一方政府或由双方主管当局认同的机构取得的利息，应在该一方免税",
  "政府或双方主管当局认同的机构取得的利息免税")

# ---- added 2026-10-07 for the HK rule spec
p("hk.fsie.receipt_kinds", "HK", "ALL", "condition", "received_in_hk_kinds", "REMITTED;DEBT_SETTLED;MOVABLE_PROPERTY", "enum",
  "hk.cap112.en#s15H", "2023-01-01", "the sum is remitted to, or is transmitted or brought into, Hong Kong; (b) the sum is used to satisfy any debt incurred in respect of a trade, profession or business carried on in Hong Kong; or (c) the sum is used to buy movable property",
  "第15H(5)条“收到于香港”的三种情形，对应字典 receipt_kind 的枚举值")
p("hk.fsie.nexus_uplift", "HK", "ROYALTY", "rate", "rd_fraction_uplift", 130, "%", "hk.cap112.en#sch17FC", "2024-01-01",
  "F = QE × 130% QE + NE", "关联比例 F = QE×130%/(QE+NE)，上限 100%（附表 17FC 第 3 条）")
p("hk.fsie.nexus_cap", "HK", "ROYALTY", "limit", "rd_fraction_cap", 100, "%", "hk.cap112.en#sch17FC", "2024-01-01",
  "ascertained in accordance with subsection (1) is more than 100%", "F 超过 100% 时取 100%")
p("hk.fsie.participation_resident_or_pe", "HK", "DIVIDEND", "condition", "participation_entity_resident_or_pe", 1, "bool",
  "hk.cap112.en#s15M", "2023-01-01", "a Hong Kong resident person; or (ii) a non-Hong Kong resident person who has a permanent establishment in Hong Kong",
  "参与豁免只给香港居民人士或在港有常设机构的非居民")
p("hk.onshore_gain.trading_stock_disregarded", "HK", "SHARE_TRANSFER", "condition", "trading_stock_periods_disregarded", 1, "bool",
  "hk.cap112.en#sch17K", "2024-01-01", "regarded as trading stock for any period are to be disregarded for the purposes of sections 5 and 6 of this Schedule",
  "被视为营业存货的期间不计入持股期与 15% 测试")

# ---- added 2026-10-07 for the receiving-side rules (step 4)
p("sg.fsie.receipt_kinds", "SG", "ALL", "condition", "received_in_sg_kinds", "REMITTED;DEBT_SETTLED;MOVABLE_PROPERTY", "enum",
  "sg.ita1947.full#s10", "", "any amount from any income derived from outside Singapore which is remitted to, transmitted or brought into, Singapore; ( b ) any amount from any income derived from outside Singapore which is applied in or towards satisfaction of any debt incurred in respect of a trade or business carried on in Singapore; and ( c ) any amount from any income derived from outside Singapore which is applied to purchase any movable property which is brought into Singapore",
  "第10(25)条“收到于新加坡”的三种情形，与香港 s15H(5) 同构")
p("sg.ftc.unilateral_income", "SG", "ALL", "condition", "unilateral_credit_income_kinds", "dividend;royalty;interest;s10l_gain;other_income_nature", "enum",
  "sg.ita1947.full#s50A", "", "( c ) any dividend derived from that territory",
  "第50A(1)条单边抵免覆盖股息、特许权（非新加坡居民负担）、利息（同）、10L 收益及其他所得；对港澳等无协定来源")

# ---- added 2026-10-07: the payer's deduction (what makes debt vs equity and IP location comparable)
p("cn.eit.rate", "CN", "ALL", "rate", "corporate_income_tax_rate", 25, "%", "cn.law.eit#4", "2008-01-01",
  "企业所得税的税率为25％", "居民企业法定税率")
p("cn.deduct.general", "CN", "ALL", "condition", "reasonable_expense_deductible", 1, "bool", "cn.law.eit#8", "2008-01-01",
  "企业实际发生的与取得收入有关的、合理的支出，包括成本、费用、税金、损失和其他支出，准予在计算应纳税所得额时扣除",
  "合理性是综合判断，对应 U(DISCRETION)")
p("cn.thincap.disallow", "CN", "INTEREST", "anti_abuse", "excess_related_party_interest_not_deductible", 1, "bool", "cn.law.eit#46", "2008-01-01",
  "企业从其关联方接受的债权性投资与权益性投资的比例超过规定标准而发生的利息支出，不得在计算应纳税所得额时扣除", "资本弱化")
p("cn.thincap.ratio_other", "CN", "INTEREST", "condition", "related_debt_equity_ratio_other_enterprises", 2, "ratio", "cn.cs.2008-121#i1", "2008-01-01",
  "其他企业，为2：1", "非金融企业关联方债资比例上限 2:1")
p("cn.thincap.ratio_financial", "CN", "INTEREST", "condition", "related_debt_equity_ratio_financial_enterprises", 5, "ratio", "cn.cs.2008-121#i1", "2008-01-01",
  "金融企业，为5：1", "金融企业 5:1")
p("cn.thincap.arms_length_exception", "CN", "INTEREST", "condition", "excess_interest_deductible_if_arms_length", 1, "bool", "cn.cs.2008-121#i2", "2008-01-01",
  "证明相关交易活动符合独立交易原则的；或者该企业的实际税负不高于境内关联方的，其实际支付给境内关联方的利息支出，在计算应纳税所得额时准予扣除",
  "超比例利息在证明独立交易原则时仍可扣除；综合判断")
p("hk.deduct.general", "HK", "ALL", "condition", "outgoings_in_production_of_profits_deductible", 1, "bool", "hk.cap112.en#s16", "",
  "there shall be deducted all outgoings and expenses to the extent to which they are incurred during the basis period for that year of assessment by such person in the production of profits",
  "第16(1)条一般扣除")
p("sg.deduct.general", "SG", "ALL", "condition", "outgoings_wholly_exclusively_in_production_deductible", 1, "bool", "sg.ita1947.full#s14", "",
  "there are to be deducted all outgoings and expenses wholly and exclusively incurred during that period by that person in the production of the income",
  "第14(1)条一般扣除")

# ---- added 2026-10-07: Mainland deadline roll-over, MAP acceptance, intragroup clawback
p("cn.time.holiday_roll", "CN", "ALL", "limit", "last_day_on_public_holiday_rolls", 1, "bool", "cn.reg.tca#109", "2016-02-06",
  "期限的最后一日是法定休假日的，以休假日期满的次日为期限的最后一日", "实施细则第109条：最后一日逢法定休假日顺延至休假期满次日")
p("cn.time.long_holiday_days", "CN", "ALL", "limit", "consecutive_holiday_days_extend_by_count", 3, "days", "cn.reg.tca#109", "2016-02-06",
  "在期限内有连续３日以上法定休假日的，按休假日天数顺延", "期限内含连续 3 日以上法定休假日的，按天数顺延")
p("cn.map.actions", "CN", "ALL", "procedure", "map_requires_action_of_other_authority", "assessment;denial;adjustment", "enum", "cn.sta.2013-56#7", "2013-11-01",
  "缔约对方所采取的措施，已经或将会导致不符合税收协定所规定的征税行为", "相互协商以对方税务机关的措施为对象")
p("cn.map.no_reacceptance_after", "CN", "ALL", "procedure", "no_reacceptance_after_withdrawal_or_refusal", "withdrawn;result_refused", "enum", "cn.sta.2013-56#19", "2013-11-01",
  "申请人撤回申请或者拒绝接受缔约双方主管当局达成一致的相互协商结果的，税务机关不再受理基于同一事实和理由的申请", "撤回或拒绝结果后不再受理同一事实的申请")

# ---- added 2026-10-07: domestic remedies (objection, appeal, administrative review)
p("hk.objection.months", "HK", "ALL", "limit", "objection_months_after_notice_of_assessment", 1, "months", "hk.cap112.en#s64", "",
  "received by the Commissioner within 1 month after the date of the notice of assessment", "第64(1)条：评税通知后 1 个月内书面反对")
p("hk.appeal.months", "HK", "ALL", "limit", "appeal_months_after_determination", 1, "months", "hk.cap112.en#s66", "",
  "1 month after the transmission to him under section 64(4) of the Commissioner’s written determination", "第66(1)条：局长裁定送达后 1 个月内上诉税务上诉委员会")
p("sg.objection.months_company", "SG", "ALL", "limit", "objection_months_company", 2, "months", "sg.ita1947.full#s76", "2014-01-01",
  "if the person is a company and the notice of assessment is served on the person on or after 1 January 2014, 2 months", "第76(3)(a)条：公司自评税通知送达起 2 个月内反对")
p("cn.review.pay_first", "CN", "ALL", "procedure", "pay_or_secure_before_review", 1, "bool", "cn.law.tca#88", "",
  "必须先依照税务机关的纳税决定缴纳或者解缴税款及滞纳金或者提供相应的担保，然后可以依法申请行政复议", "纳税争议：复议前置，先缴税或担保")
p("cn.review.days", "CN", "ALL", "limit", "review_days_after_knowing", 60, "days", "cn.law.ar#20", "2024-01-01",
  "可以自知道或者应当知道该行政行为之日起六十日内提出行政复议申请", "行政复议法第20条：知道之日起 60 日")

# ---- added 2026-10-07 (场景.md): explicit no-charge cites
p("hk.nocharge.scope", "HK", "ALL", "condition", "profits_tax_only_on_hk_business_profits", 1, "bool", "hk.cap112.en#s14", "",
  "on every person carrying on a trade, profession or business in Hong Kong in respect of his assessable profits arising in or derived from Hong Kong",
  "第14条：利得税只及于在港经营者的香港来源利润；香港无股息、利息预提税，非居民所得不课")
p("sg.nocharge.dividend", "SG", "DIVIDEND", "condition", "one_tier_dividends_exempt", 1, "bool", "sg.ita1947.full#s13", "2008-01-01",
  "any dividends paid on or after 1 January 2008 by any company resident in Singapore", "第13(1)(za)条：单一公司税制下新加坡公司股息免税")
# ---- CN residence side: worldwide income, foreign tax credit
p("cn.ftc.credit", "CN", "ALL", "condition", "foreign_tax_creditable", 1, "bool", "cn.law.eit#23", "2008-01-01",
  "企业取得的下列所得已在境外缴纳的所得税税额，可以从其当期应纳税额中抵免，抵免限额为该项所得依照本法规定计算的应纳税额",
  "第23条：直接抵免，限额为该所得按本法计算的应纳税额；超限额五年结转（cn.ftc.carryforward_years）")
p("cn.ftc.indirect", "CN", "DIVIDEND", "condition", "underlying_tax_creditable_if_controlled", 1, "bool", "cn.law.eit#24", "2008-01-01",
  "外国企业在境外实际缴纳的所得税税额中属于该项所得负担的部分，可以作为该居民企业的可抵免境外所得税税额",
  "第24条：间接抵免，限直接或间接控制（20% 以上，第80条）的外国企业，层级见 cn.ftc.indirect_tiers")
p("cn.ftc.limit_per_country", "CN", "ALL", "condition", "credit_limit_per_country", 1, "bool", "cn.reg.eit#78", "2008-01-01",
  "该抵免限额应当分国(地区)不分项计算", "第78条：分国不分项；2017-84 允许选择不分国，一经选择 5 年不变")
p("cn.ftc.income_recognition_dividend", "CN", "DIVIDEND", "procedure", "foreign_dividend_recognised_on_resolution", 1, "bool", "cn.cs.2009-125#i3", "2010-01-01",
  "来源于境外的股息、红利等权益性投资收益，应按被投资方作出利润分配决定的日期确认收入实现", "境外股息按分配决议日确认")
# ---- services and permanent establishment
p("cn-sg.pe.service_months", SG, "SERVICE_FEE", "condition", "service_pe_months_in_12", 6, "months", "treaty.cn-sg.2007.p2.zh#1", "2008-01-01",
  "取消第三款第（二）项中“六个月”的规定", "协定第5(3)(二)款原门槛，以替换它的第二议定书为证；库内整合文本的该项已按 superseded.csv 剔除", to="2009-12-31")
p("cn.service.deemed_profit_design_min", "CN", "SERVICE_FEE", "rate", "deemed_profit_rate_engineering_design_consulting_min", 15, "%", "cn.gsf.2010-19#5", "2010-02-20",
  "从事承包工程作业、设计和咨询劳务的，利润率为15%-30%", "核定利润率区间下端")
p("cn.service.deemed_profit_design_max", "CN", "SERVICE_FEE", "rate", "deemed_profit_rate_engineering_design_consulting_max", 30, "%", "cn.gsf.2010-19#5", "2010-02-20",
  "从事承包工程作业、设计和咨询劳务的，利润率为15%-30%", "核定利润率区间上端")
p("cn.service.establishment", "CN", "SERVICE_FEE", "condition", "service_place_is_establishment", 1, "bool", "cn.reg.eit#5", "2008-01-01",
  "提供劳务的场所", "实施条例第五条：机构、场所包括提供劳务的场所")
p("cn.eit.resident_worldwide", "CN", "ALL", "condition", "resident_taxed_on_worldwide_income", 1, "bool", "cn.law.eit#3", "2008-01-01",
  "居民企业应当就其来源于中国境内、境外的所得缴纳企业所得税", "居民侧征税权")
p("cn.eit.asset_net_value_deductible", "CN", "SHARE_TRANSFER", "condition", "asset_net_value_deductible_on_transfer", 1, "bool", "cn.law.eit#16", "2008-01-01",
  "企业转让资产，该项资产的净值，准予在计算应纳税所得额时扣除", "居民转让股权：所得 = 收入 − 净值")
p("cn.ftc.indirect_formula", "CN", "DIVIDEND", "condition", "underlying_tax_attributable_formula", 1, "bool", "cn.cs.2009-125#i5", "2010-01-01",
  "本层企业所纳税额属于由一家上一层企业负担的税额＝（本层企业就利润和投资收益所实际缴纳的税额+符合本通知规定的由本层企业间接负担的税额）×本层企业向一家上一层企业分配的股息（红利）÷本层企业所得税后利润额",
  "间接负担税额的逐层公式；字段 underlying_tax_share 按此式给出（占股息的百分比）")
p("cn.ftc.gross_up", "CN", "DIVIDEND", "condition", "foreign_dividend_grossed_up_by_direct_and_underlying_tax", 1, "bool", "cn.sta.2010-01.a01#16", "2010-01-01",
  "该境外股息、红利所得应为境外股息、红利税后净所得与就该项所得直接缴纳和间接负担的税额之和",
  "操作指南第4点：间接抵免时股息按直接缴纳与间接负担的税额还原；流金额已是扣缴前的毛额，引擎只再加间接负担部分")
# ---- 范围.md 1: the entity's own rate exists in each law (the rate the case states is the fact; these are the provenance)
p("cn.eit.rate_entity", "CN", "ALL", "condition", "entity_specific_rate_exists", 1, "bool", "cn.law.eit#28", "2008-01-01",
  "国家需要重点扶持的高新技术企业，减按15％的税率征收企业所得税", "实体适用税率为事实字段 cit_rate；此行为其存在的出处（高新 15%，小微 20%）")
p("hk.profits.rate_entity", "HK", "ALL", "condition", "entity_specific_rate_exists", 1, "bool", "hk.cap112.en#sch8B", "2018-04-01",
  "at the rate of 8.25% on section 14 assessable profits up to $2,000,000", "两级制：首 200 万港元 8.25%，其余 16.5%；实体边际税率为事实字段 cit_rate")
p("sg.corp.rate_entity", "SG", "ALL", "condition", "entity_specific_rate_exists", 1, "bool", "sg.ita1947.full#s43", "2020-01-01",
  "for every dollar of the first $10,000 of the chargeable income, only 25% is chargeable with tax", "s43(6B) 部分免税：首 1 万新元 75% 免、次 19 万 50% 免；实体边际税率为事实字段 cit_rate")
# ---- 范围.md 3: interest deduction conditions
p("cn.deduct.interest_benchmark", "CN", "INTEREST", "condition", "interest_deductible_up_to_financial_enterprise_rate", 1, "bool", "cn.reg.eit#38", "2008-01-01",
  "非金融企业向非金融企业借款的利息支出，不超过按照金融企业同期同类贷款利率计算的数额的部分", "第三十八条(二)；(一) 向金融企业借款全额扣除")
p("hk.deduct.interest_cond_fi", "HK", "INTEREST", "condition", "interest_deductible_if_lender_is_financial_institution", 1, "bool", "hk.cap112.en#s16", "",
  "the money has been borrowed from a financial institution or an overseas financial institution", "s16(2)(d)")
p("hk.deduct.interest_cond_lender_taxable", "HK", "INTEREST", "condition", "interest_deductible_if_taxable_in_lenders_hands", 1, "bool", "hk.cap112.en#s16", "",
  "the money has been borrowed from a person other than a financial institution or an overseas financial institution and the sums payable by way of interest are chargeable to tax under this Ordinance", "s16(2)(c)")
p("sg.deduct.interest_capital_employed", "SG", "INTEREST", "condition", "interest_deductible_if_capital_employed_in_acquiring_income", 1, "bool", "sg.ita1947.full#s14", "",
  "such sum is payable on capital employed in acquiring the income", "s14(1)(a)：借款用于取得免税股息的不得扣除")
# ---- 范围.md 4: arm's length as a cap on the deduction when the taxpayer's own range is stated
p("cn.tp.adjust_to_median", "CN", "ALL", "condition", "tp_adjustment_to_interquartile_median", 1, "bool", "cn.gsf.2009-02#41", "2008-01-01",
  "企业利润水平低于可比企业利润率区间中位值的，原则上应按照不低于中位值进行调整", "四分位法；区间上限之上的支付不得扣除")
p("hk.tp.arms_length", "HK", "ALL", "condition", "arms_length_principle_between_associated_persons", 1, "bool", "hk.cap112.en#s50AAF", "2018-07-13",
  "Arm’s length principle for provision between associated persons", "s50AAF Rule 1")
p("sg.tp.arms_length", "SG", "ALL", "condition", "related_party_transactions_at_arms_length", 1, "bool", "sg.ita1947.full#s34D", "",
  "Transactions not at arm’s length", "s34D(1A)")
# ---- 范围.md 2: stamp duty on share transfers
p("cn.stamp.equity_rate", "CN", "SHARE_TRANSFER", "rate", "stamp_duty_equity_transfer_instrument_rate", 0.05, "%", "cn.law.stamp.flk#20", "2022-07-01",
  "价款的万分之五", "印花税税目税率表：产权转移书据—股权转让书据（不包括应缴纳证券交易印花税的）；国家法律法规数据库 PDF；法规库附件为图片版 .ppt，cn.law.stamp.sh 为政府网站转载本")
p("cn.stamp.taxpayer_each_party", "CN", "SHARE_TRANSFER", "condition", "each_party_writing_the_instrument_is_taxpayer", 1, "bool", "cn.law.stamp.flk#1", "2022-07-01",
  "应当依照本法规定缴纳印花税", "第一条：书立应税凭证的单位和个人为纳税人，产权转移书据由双方书立，各自纳税")
p("hk.stamp.stock_rate", "HK", "SHARE_TRANSFER", "rate", "stamp_duty_contract_note_rate", 0.1, "%", "hk.cap117.en#sch1", "2023-11-17",
  "0.1% of the amount of the consideration or of its value at the date on which the contract note falls to be executed", "First Schedule head 2(1)(A)；买卖双方各一张成交单据，各 0.1%")
p("hk.stamp.contract_note_each_party", "HK", "SHARE_TRANSFER", "condition", "contract_note_by_each_party", 1, "bool", "hk.cap117.en#s19", "",
  "any person who effects any sale or purchase of Hong Kong stock as principal or agent shall", "s19(1)：出售方与购买方各自制作并加盖印花")
# ---- 范围.md 4: documentation clocks, adjustment interest, surcharge
p("cn.tp.local_file_other_threshold", "CN", "ALL", "condition", "local_file_threshold_other_related_dealings", 40000000, "CNY", "cn.sta.2016-42#i13", "2016-01-01",
  "其他关联交易金额合计超过4000万元", "有形资产 2 亿、金融资产 1 亿、无形资产 1 亿为另三档，模型只定价利息/特许权/服务费，取“其他”档")
p("cn.tp.local_file_due", "CN", "ALL", "procedure", "local_file_due_date", "next_year_june_30", "text", "cn.sta.2016-42#i19", "2016-01-01",
  "本地文档和特殊事项文档应当在关联交易发生年度次年6月30日之前准备完毕", "")
p("cn.tp.interest_spread", "CN", "ALL", "rate", "special_adjustment_interest_spread_over_benchmark", 5, "%", "cn.sta.2017-06#44", "2017-05-01",
  "加5个百分点计算，并按照一年365天折算日利息率", "百分点；按 365 天折算日息")
p("cn.tp.interest_from", "CN", "ALL", "procedure", "special_adjustment_interest_runs_from", "next_year_june_1", "text", "cn.sta.2017-06#44", "2017-05-01",
  "自税款所属纳税年度的次年6月1日起至缴纳或者补缴税款之日止计算加收利息", "")
p("cn.tp.interest_base_only_with_docs", "CN", "ALL", "condition", "benchmark_only_if_documentation_provided", 1, "bool", "cn.sta.2017-06#44", "2017-05-01",
  "可以只按照基准利率加收利息", "第四十四条第二款(三)")
p("hk.tp.local_file_months", "HK", "ALL", "limit", "master_and_local_file_within_months_after_period", 9, "months", "hk.cap112.en#s58C", "2018-07-13",
  "prepare, within 9 months after the end of each accounting period of the entity, a file in respect of the accounting period (local file)", "")
p("hk.tp.threshold_revenue", "HK", "ALL", "condition", "small_entity_revenue_threshold", 400000000, "HKD", "hk.cap112.en#sch17I", "2018-07-13",
  "total amount of revenue $400 million", "Sch 17I s4(a)；任两项不超过即免")
p("hk.tp.threshold_assets", "HK", "ALL", "condition", "small_entity_assets_threshold", 300000000, "HKD", "hk.cap112.en#sch17I", "2018-07-13",
  "total value of assets $300 million", "Sch 17I s4(b)")
p("hk.tp.threshold_employees", "HK", "ALL", "condition", "small_entity_employees_threshold", 100, "persons", "hk.cap112.en#sch17I", "2018-07-13",
  "average number of employees 100", "Sch 17I s4(c)")
p("sg.tp.documentation_revenue_min", "SG", "ALL", "condition", "tp_documentation_gross_revenue_threshold", 10000000, "SGD", "sg.ita1947.full#s34F", "2019-01-01",
  "if the gross revenue of the company, firm or trust derived from its trade or business for the basis period concerned is more than $10 million", "s34F(2)(a)")
p("sg.tp.documentation_due", "SG", "ALL", "procedure", "tp_documentation_due", "return_due_30_nov", "text", "sg.ita1947.full#s34F", "2019-01-01",
  "must be prepared no later than the time for the making of the return", "s34F(5)(a)；法条本身不定日期（s62 以公告定），申报期限由案例作为事实 return_due_on 给出")
p("sg.corp.return_due", "SG", "ALL", "procedure", "corporate_return_filing_due", "30 Nov", "text", "sg.iras.formc#h2", "",
  "must be filed by 30 Nov every year", "税务局页面（实务，B 级）：Form C-S / Form C 每年 11 月 30 日前申报；法条本身以公告定期限（s62）")
p("sg.tp.surcharge_rate", "SG", "ALL", "rate", "tp_adjustment_surcharge", 5, "%", "sg.ita1947.full#s34E", "2019-01-01",
  "a surcharge equal to 5% of the amount of the increase or reduction", "s34E(1)")
# ---- 范围.md 5: controlled foreign companies
p("cn.cfc.definition", "CN", "ALL", "condition", "cfc_undistributed_profit_included", 1, "bool", "cn.law.eit#45", "2008-01-01",
  "并非由于合理的经营需要而对利润不作分配或者减少分配的，上述利润中应归属于该居民企业的部分，应当计入该居民企业的当期收入", "")
p("cn.cfc.control_single_min", "CN", "ALL", "condition", "cfc_control_single_holder_min", 10, "%", "cn.reg.eit#117", "2008-01-01",
  "直接或者间接单一持有外国企业10%以上有表决权股份", "")
p("cn.cfc.control_joint_min", "CN", "ALL", "condition", "cfc_control_joint_min", 50, "%", "cn.reg.eit#117", "2008-01-01",
  "共同持有该外国企业50%以上股份", "")
p("cn.cfc.chain_over_50_counts_100", "CN", "ALL", "condition", "cfc_chain_tier_over_50_counts_100", 1, "bool", "cn.gsf.2009-02#77", "2008-01-01",
  "中间层持有股份超过50%的，按100%计算", "")
p("cn.cfc.low_tax_ratio", "CN", "ALL", "condition", "cfc_low_tax_share_of_statutory_rate", 50, "%", "cn.reg.eit#118", "2008-01-01",
  "低于企业所得税法第四条第一款规定税率的50%", "即实际税负 < 12.5%；字段 cfc_tax_burden_ratio 为实际税负占法定税率的百分比")
p("cn.cfc.exempt_whitelist", "CN", "ALL", "condition", "cfc_exempt_if_in_designated_non_low_tax_jurisdiction", 1, "bool", "cn.gsf.2009-02#84", "2008-01-01",
  "设立在国家税务总局指定的非低税率国家（地区）", "")
p("cn.cfc.whitelist", "CN", "ALL", "condition", "cfc_designated_non_low_tax_jurisdictions", "US;GB;FR;DE;JP;IT;CA;AU;IN;ZA;NZ;NO", "enum", "cn.gsh.2009-37#all", "2009-01-21",
  "美国、英国、法国、德国、日本、意大利、加拿大、澳大利亚、印度、南非、新西兰和挪威", "香港、新加坡不在名单内")
p("cn.cfc.exempt_active", "CN", "ALL", "condition", "cfc_exempt_if_mainly_active_income", 1, "bool", "cn.gsf.2009-02#84", "2008-01-01",
  "主要取得积极经营活动所得", "裁量")
p("cn.cfc.exempt_profit_max", "CN", "ALL", "condition", "cfc_exempt_if_annual_profit_below", 5000000, "CNY", "cn.gsf.2009-02#84", "2008-01-01",
  "年度利润总额低于500万元人民币", "")
p("cn.cfc.credit", "CN", "ALL", "condition", "cfc_inclusion_foreign_tax_creditable", 1, "bool", "cn.gsf.2009-02#82", "2008-01-01",
  "计入中国居民企业股东当期所得已在境外缴纳的企业所得税税款，可按照所得税法或税收协定的有关规定抵免", "")
# ---- 范围.md 7: Mainland VAT on cross-border services and IP
p("cn.vat.withholding_agent", "CN", "ALL", "condition", "purchaser_withholds_vat_for_nonresident", 1, "bool", "cn.cs.2016-36.a01#6", "2016-05-01",
  "在境内发生应税行为，在境内未设有经营机构的，以购买方为增值税扣缴义务人", "第六条")
p("cn.vat.offshore_service_excluded", "CN", "ALL", "condition", "services_wholly_abroad_not_domestic", 1, "bool", "cn.cs.2016-36.a01#13", "2016-05-01",
  "境外单位或者个人向境内单位或者个人销售完全在境外发生的服务", "第十三条(一)；(二) 完全在境外使用的无形资产")
p("cn.vat.rate_services", "CN", "ALL", "rate", "vat_rate_services_and_ip", 6, "%", "cn.cs.2016-36.a01#15", "2016-05-01",
  "税率为6％", "服务、无形资产")
p("cn.vat.withholding_formula", "CN", "ALL", "condition", "withheld_vat_price_divided_by_one_plus_rate", 1, "bool", "cn.cs.2016-36.a01#20", "2016-05-01",
  "应扣缴税额=购买方支付的价款÷（1+税率）×税率", "价款含税")
p("cn.vat.rate_tangible_lease_2016", "CN", "ROYALTY", "rate", "vat_rate_tangible_movable_lease", 17, "%", "cn.cs.2016-36.a01#15", "2016-05-01",
  "提供有形动产租赁服务，税率为17%", "历史税率；2018-05-01 起 16%，2019-04-01 起 13%", to="2018-04-30")
p("cn.vat.rate_tangible_lease_2018", "CN", "ROYALTY", "rate", "vat_rate_tangible_movable_lease", 16, "%", "cn.cs.2018-32#i1", "2018-05-01",
  "原适用17%和11%税率的，税率分别调整为16%、10%", "历史税率", to="2019-03-31")
p("cn.vat.rate_tangible_lease", "CN", "ROYALTY", "rate", "vat_rate_tangible_movable_lease", 13, "%", "cn.cs.2019-39#i1", "2019-04-01",
  "原适用16%税率的，税率调整为13%", "有形动产租赁（设备、飞机、船舶租金）现行税率")
p("cn.vat.input_credit", "CN", "ALL", "condition", "withheld_vat_creditable_as_input", 1, "bool", "cn.cs.2016-36.a01#25", "2016-05-01",
  "从境外单位或者个人购进服务、无形资产或者不动产，自税务机关或者扣缴义务人取得的解缴税款的完税凭证上注明的增值税额", "一般纳税人")
# ---- 范围.md 6: residence by place of effective management
p("cn.residence.pem_criteria", "CN", "ALL", "basis", "foreign_incorporated_cn_controlled_company_resident_if_four_criteria", 1, "bool", "cn.gsf.2009-82#i2", "2008-01-01",
  "境外中资企业同时符合以下条件的，根据企业所得税法第二条第二款和实施条例第四条的规定，应判定其为实际管理机构在中国境内的居民企业", "四项标准为事实字段；认定由税务机关确认（裁量）；引擎按图变体取界")
p("cn.residence.substance_over_form", "CN", "ALL", "basis", "effective_management_substance_over_form", 1, "bool", "cn.gsf.2009-82#i3", "2008-01-01",
  "对于实际管理机构的判断，应当遵循实质重于形式的原则", "")
p("cn.residence.application", "CN", "ALL", "basis", "resident_determination_by_application_to_investor_authority", 1, "bool", "cn.sta.2014-09#i1", "2014-01-29",
  "须向其中国境内主要投资者登记注册地主管税务机关提出居民企业认定申请", "公告2014年第9号第一条")
# ---- 范围.md 9: Pillar Two (Hong Kong ordinance; Singapore's Act when the library has its text)
p("p2.revenue_threshold", "HK", "ALL", "condition", "globe_revenue_threshold", 750000000, "EUR", "hk.ord.2025-21#p42", "2025-01-01",
  "annual revenue of EUR 750 million or more in the consolidated financial statements of the ultimate parent entity", "GloBE Art 1.1.1，两个以上前四个财年")
p("p2.minimum_rate", "HK", "ALL", "rate", "globe_minimum_rate", 15, "%", "hk.ord.2025-21#p147", "2025-01-01",
  "Minimum rate (最低稅率) means fifteen percent (15%)", "GloBE Art 10.1")
p("p2.sbie_payroll_rate", "HK", "ALL", "rate", "sbie_payroll_carve_out_rate", 5, "%", "hk.ord.2025-21#p86", "2025-01-01",
  "The payroll carve-out for a constituent entity located in a jurisdiction is equal to 5% of its eligible payroll costs", "GloBE Art 5.3.3；过渡期按 p2.sbie_payroll_transition")
p("p2.sbie_tangible_rate", "HK", "ALL", "rate", "sbie_tangible_asset_carve_out_rate", 5, "%", "hk.ord.2025-21#p87", "2025-01-01",
  "The tangible asset carve-out for a constituent entity located in a jurisdiction is equal to 5% of the carrying value of eligible tangible assets located in such jurisdiction", "GloBE Art 5.3.4")
p("p2.sbie_payroll_transition", "HK", "ALL", "procedure", "sbie_payroll_rate_by_fiscal_year", "2023:10;2024:9.8;2025:9.6;2026:9.4;2027:9.2;2028:9.0;2029:8.2;2030:7.4;2031:6.6;2032:5.8", "text", "hk.ord.2025-21#p120", "2025-01-01",
  "Fiscal Year Beginning In Article 5.3.3 Rate 2023 10% 2024 9.8% 2025 9.6% 2026 9.4% 2027 9.2% 2028 9.0% 2029 8.2% 2030 7.4% 2031 6.6% 2032 5.8%", "GloBE Art 9.2.1")
p("p2.sbie_tangible_transition", "HK", "ALL", "procedure", "sbie_tangible_rate_by_fiscal_year", "2023:8.0;2024:7.8;2025:7.6;2026:7.4;2027:7.2;2028:7.0;2029:6.6;2030:6.2;2031:5.8;2032:5.4", "text", "hk.ord.2025-21#p121", "2025-01-01",
  "Article 5.3.4 Rate 2023 8.0% 2024 7.8% 2025 7.6% 2026 7.4% 2027 7.2% 2028 7.0% 2029 6.6% 2030 6.2% 2031 5.8% 2032 5.4%", "GloBE Art 9.2.2")
p("hk.p2.hkmtt", "HK", "ALL", "condition", "hong_kong_minimum_top_up_tax_charged", 1, "bool", "hk.ord.2025-21#p21", "2025-01-01",
  "Schedule 62 has effect for charging a domestic minimum top-up tax within the meaning of the OECD GloBE model rules, to be called the Hong Kong minimum top-up tax or HKMTT", "s26AE(4)")
# ---- Singapore stamp duty, GST reverse charge, Pillar Two (范围.md 2, 7, 9)
p("sg.stamp.share_rate", "SG", "SHARE_TRANSFER", "rate", "stamp_duty_transfer_of_shares_rate", 0.2, "%", "sg.sda1929.sch1#sch1", "2014-02-22",
  "if executed on or after 22 February 2014 0.2% of the amount of the consideration", "First Schedule Article 3(c)(ii)")
p("sg.stamp.transferee_pays", "SG", "SHARE_TRANSFER", "condition", "stamp_duty_on_conveyance_paid_by_transferee", 1, "bool", "sg.sda1929.sch3#sch3", "",
  "The grantee, transferee or lessee", "Third Schedule Article 2(a)：买方缴纳")
p("sg.gst.reverse_charge", "SG", "ALL", "condition", "reverse_charge_on_imported_services_if_not_fully_recoverable", 1, "bool", "sg.gsta1993.s14#s14", "2020-01-01",
  "the recipient is not entitled to credit for the full amount of the recipient’s input tax under sections 19 and 20", "s14(1)：进口服务由不能全额抵扣进项税的收受方自行计税")
p("sg.gst.rate", "SG", "ALL", "rate", "gst_rate", 9, "%", "sg.gsta1993.s16#s16", "2024-01-01",
  "9% from and including 1 January 2024", "s16(cb)")
p("sg.p2.revenue_threshold", "SG", "ALL", "condition", "globe_revenue_threshold", 750000000, "EUR", "sg.memta2024.s8#s8", "2025-01-01",
  "A is EUR 750 million or its equivalent in other currency", "s8(2)：按财年月数折算；两个以上前四个财年")
p("sg.p2.minimum_rate", "SG", "ALL", "rate", "globe_minimum_rate", 15, "%", "sg.memta2024.s7#s7", "2025-01-01",
  "The minimum rate is 15%.", "s7")
p("sg.p2.dtt", "SG", "ALL", "condition", "domestic_top_up_tax_payable", 1, "bool", "sg.memta2024.s28#s28", "2025-01-01",
  "DTT is payable in respect of an MNE group for a financial year where", "s28(1)：国内补足税")
p("sg.p2.sbie_payroll_rate", "SG", "ALL", "rate", "sbie_payroll_carve_out_rate", 5, "%", "sg.memta2024.sch2#sch2", "2025-01-01",
  '( j ) for a financial year beginning in 2032, 5.8%; and ( k ) for a financial year beginning after 2032, 5.0%', "s18(2) 与附表二第 1 段 (k)：2032 年以后")
p("sg.p2.sbie_tangible_rate", "SG", "ALL", "rate", "sbie_tangible_asset_carve_out_rate", 5, "%", "sg.memta2024.sch2#sch2", "2025-01-01",
  '( j ) for a financial year beginning in 2032, 5.4%; and ( k ) for a financial year beginning after 2032, 5.0%', "s18(3) 与附表二第 2 段 (k)：2032 年以后")
p("sg.p2.sbie_payroll_transition", "SG", "ALL", "procedure", "sbie_payroll_rate_by_fiscal_year", '2023:10.0;2024:9.8;2025:9.6;2026:9.4;2027:9.2;2028:9.0;2029:8.2;2030:7.4;2031:6.6;2032:5.8', "text", "sg.memta2024.sch2#sch2", "2025-01-01",
  'In section 18(2), the applicable percentage is — ( a ) for a financial year beginning in 2023, 10.0%; ( b ) for a financial year beginning in 2024, 9.8%; ( c ) for a financial year beginning in 2025, 9.6%; ( d ) for a financial year beginning in 2026, 9.4%; ( e ) for a financial year beginning in 2027, 9.2%; ( f ) for a financial year beginning in 2028, 9.0%; ( g ) for a financial year beginning in 2029, 8.2%; ( h ) for a financial year beginning in 2030, 7.4%; ( i ) for a financial year beginning in 2031, 6.6%; ( j ) for a financial year beginning in 2032, 5.8%; and ( k ) for a financial year beginning after 2032, 5.0%', "附表二第 1 段：按财年起始年")
p("sg.p2.sbie_tangible_transition", "SG", "ALL", "procedure", "sbie_tangible_rate_by_fiscal_year", '2023:8.0;2024:7.8;2025:7.6;2026:7.4;2027:7.2;2028:7.0;2029:6.6;2030:6.2;2031:5.8;2032:5.4', "text", "sg.memta2024.sch2#sch2", "2025-01-01",
  'In section 18(3), the applicable percentage is — ( a ) for a financial year beginning in 2023, 8.0%; ( b ) for a financial year beginning in 2024, 7.8%; ( c ) for a financial year beginning in 2025, 7.6%; ( d ) for a financial year beginning in 2026, 7.4%; ( e ) for a financial year beginning in 2027, 7.2%; ( f ) for a financial year beginning in 2028, 7.0%; ( g ) for a financial year beginning in 2029, 6.6%; ( h ) for a financial year beginning in 2030, 6.2%; ( i ) for a financial year beginning in 2031, 5.8%; ( j ) for a financial year beginning in 2032, 5.4%; and ( k ) for a financial year beginning after 2032, 5.0%', "附表二第 2 段：按财年起始年")
# ---- domestic flows, by the statutes (范围.md 口径 2)
p("cn.domestic.dividend_exempt", "CN", "DIVIDEND", "condition", "qualifying_dividends_between_resident_companies_exempt", 1, "bool", "cn.law.eit#26", "2008-01-01",
  "符合条件的居民企业之间的股息、红利等权益性投资收益", "第二十六条(二)；条件见实施条例第八十三条：直接投资")
p("cn.domestic.dividend_listed_months", "CN", "DIVIDEND", "condition", "listed_shares_held_at_least_months_for_exemption", 12, "months", "cn.reg.eit#83", "2008-01-01",
  "不包括连续持有居民企业公开发行并上市流通的股票不足12个月取得的投资收益", "")
p("cn.tp.domestic_same_burden_no_adjustment", "CN", "ALL", "condition", "no_tp_adjustment_between_domestic_related_parties_with_same_burden", 1, "bool", "cn.sta.2017-06#38", "2017-05-01",
  "实际税负相同的境内关联方之间的交易，只要该交易没有直接或者间接导致国家总体税收收入的减少，原则上不作特别纳税调整", "独立交易上限只用于跨境流")
p("hk.domestic.dividend_excluded", "HK", "DIVIDEND", "condition", "dividend_from_chargeable_corporation_excluded", 1, "bool", "hk.cap112.en#s26", "",
  "a dividend from a corporation which is chargeable to tax under this Part shall not be included in", "s26(a)")
# ---- GST reverse charge: the cost is the unrecoverable share (s19, s20)
p("sg.gst.recovery_ratio_basis", "SG", "ALL", "condition", "input_tax_credit_by_recovery_ratio", 1, "bool", "sg.gsta1993.s14#s14", "2020-01-01",
  "credit for the full amount of the recipient’s input tax under sections 19 and 20", "反向征收的销项税按 s19/s20 的可抵扣比例作进项抵扣，净成本 = 9% × (1 − 比例)")
# ---- royalty versus service (国税函〔2009〕507号); only tax due under the treaty is creditable
p("cn.treaty.service_not_royalty", "CN", "SERVICE_FEE", "condition", "service_using_know_how_without_licensing_not_royalty", 1, "bool", "cn.gsh.2009-507#i4", "2009-10-01",
  "如果服务提供方提供服务过程中使用了某些专门知识和技术，但并不转让或许可这些技术，则此类服务不属于特许权使用费范围", "第四条；成果属特许权定义且提供方保有所有权的除外")
p("cn.treaty.professional_services_business_profits", "CN", "SERVICE_FEE", "condition", "professional_services_are_business_profits", 1, "bool", "cn.gsh.2009-507#i6", "2009-10-01",
  "专门从事工程、管理、咨询等专业服务的机构或个人提供的相关服务所取得的款项", "第六条(三)：为劳务所得，适用营业利润条款")
p("cn.ftc.not_due_under_treaty_not_creditable", "CN", "ALL", "condition", "tax_not_due_under_treaty_not_creditable", 1, "bool", "cn.cs.2009-125#i4", "2010-01-01",
  "按照税收协定规定不应征收的境外所得税税款", "第四条(二)：多扣的税不抵免，走来源地退税")
p("sg.ftc.tax_payable_under_arrangements", "SG", "ALL", "condition", "credit_for_tax_payable_under_the_arrangements", 1, "bool", "sg.ita1947.full#s50", "",
  "tax payable in respect of any income in the territory with the government of which the arrangements are made is to be allowed as a credit", "s50(1)：抵免以按协定应缴的税为限")
p("sg.wht.service_outside_sg_excluded", "SG", "SERVICE_FEE", "condition", "management_fee_performed_outside_sg_not_deemed", 1, "bool", "sg.ita1947.full#s12", "",
  "the management or assistance in the management of any trade, business or profession, where such management or assistance is performed outside Singapore for or on behalf of a person resident in Singapore or a permanent establishment in Singapore by a non‑resident person who",
  "s12(7A)(b)：境外履行且无新加坡业务/常设机构的非居民，不视同新加坡来源")
p("cn-sg.pe.service_days", SG, "SERVICE_FEE", "condition", "service_pe_days_in_12_months", 183, "days", "treaty.cn-sg.2007.p2.zh#1", "2010-01-01",
  "取消第三款第（二）项中“六个月”的规定，用“一百八十 三天”代替", "第二议定书第一条：劳务型常设机构门槛 183 天")
p("cn-hk.pe.service_days", HK, "SERVICE_FEE", "condition", "service_pe_days_in_12_months", 183, "days", "treaty.cn-hk.2006.p2.zh#3", "2008-06-11",
  "取消《安排》第五条第三款（二）项中“六个月”的规定， 用“一百八十三天”代替", "第二议定书第三条：劳务型常设机构门槛 183 天")
p("cn-sg.pe.business_profits_residence_only", SG, "SERVICE_FEE", "condition", "business_profits_taxed_at_source_only_through_pe", 1, "bool", "treaty.cn-sg.2007.zh#7.1", "2008-01-01",
  "缔约国一方企业的利润应仅在该缔约国征税，但该企业 通过设在缔约国另一方的常设机构在该缔约国另一方进行营业 的除外", "第7(1)条：无常设机构则来源国不征营业利润")
p("cn-hk.pe.business_profits_residence_only", HK, "SERVICE_FEE", "condition", "business_profits_taxed_at_source_only_through_pe", 1, "bool", "treaty.cn-hk.2006.zh#7.1", "2007-01-01",
  "一方企业的利润应仅在该一方征税，但该企业通过设在另一 方的常设机构在该另一方进行营业的除外", "第7(1)条")
p("cn.service.deemed_profit_min", "CN", "SERVICE_FEE", "rate", "deemed_profit_rate_management_min", 30, "%", "cn.gsf.2010-19#5", "2010-02-20",
  "从事管理服务的，利润率为30%-50%", "管理服务核定利润率下限")
p("cn.service.deemed_profit_max", "CN", "SERVICE_FEE", "rate", "deemed_profit_rate_management_max", 50, "%", "cn.gsf.2010-19#5", "2010-02-20",
  "从事管理服务的，利润率为30%-50%", "管理服务核定利润率上限")
p("cn.service.deemed_profit_other_min", "CN", "SERVICE_FEE", "rate", "deemed_profit_rate_other_min", 15, "%", "cn.gsf.2010-19#5", "2010-02-20",
  "从事其他劳务或劳务以外经营活动的，利润率不低于15%", "其他劳务核定利润率下限")
p("cn.service.deemed_basis", "CN", "SERVICE_FEE", "condition", "deemed_income_equals_revenue_times_profit_rate", 1, "bool", "cn.gsf.2010-19#4", "2010-02-20",
  "应纳税所得额=收入总额×经税务机关核定的利润率", "按收入总额核定")
p("cn.service.source_where_performed", "CN", "SERVICE_FEE", "condition", "service_income_sourced_where_performed", 1, "bool", "cn.reg.eit#7", "2008-01-01",
  "提供劳务所得，按照劳务发生地确定", "第7条(二)：劳务所得来源地为劳务发生地")
p("sg.wht.service_fee", "SG", "SERVICE_FEE", "condition", "management_fees_deemed_sg_source", 1, "bool", "sg.ita1947.full#s12", "",
  "any payment for the management or assistance in the management of any trade", "第12(7)(c)条：管理费视为新加坡来源；经第45A条按第45条扣缴")
p("sg.wht.s45a_applies", "SG", "SERVICE_FEE", "procedure", "s45_applies_to_s12_7_payments", 1, "bool", "sg.ita1947.full#s45A", "",
  "Section 45(1) to (8) applies in relation to the payment of any income referred to in section 12(6) or (7)", "第45A(1)条")
# ---- liquidation and capital reduction: a distribution splits into a dividend part and a disposal part
p("cn.liquidation.split", "CN", "LIQUIDATION", "condition", "liquidation_proceeds_split_dividend_then_gain", 1, "bool", "cn.cs.2009-60#i5", "2008-01-01",
  "其中相当于被清算企业累计未分配利润和累计盈余公积中按该股东所占股份比例计算的部分，应确认为股息所得；剩余资产减除股息所得后的余额，超过或低于股东投资成本的部分，应确认为股东的投资转让所得或损失",
  "清算分配：先股息（累计未分配利润和盈余公积按比例），余额减成本为转让所得")
p("cn.capital_reduction.split", "CN", "CAPITAL_REDUCTION", "condition", "capital_reduction_split_return_dividend_gain", 1, "bool", "cn.sta.2011-34#i5", "2011-07-01",
  "相当于初始出资的部分，应确认为投资收回；相当于被投资企业累计未分配利润和累计盈余公积按减少实收资本比例计算的部分，应确认为股息所得；其余部分确认为投资资产转让所得",
  "减资：初始出资为收回，累计利润按比例为股息，其余为转让所得")

XC = {
    "cn.reinvest.credit_rate": "cn.sta.2025-18.interp：解读与公告一致，10% 或更低协定税率二选一",
    "sg.wht.late_penalty_monthly_cap": "S45 计算器 2026-10-06：逾期十九个月，罚款 200 = 5% + 封顶 15%，一致，标签 sg_s45.12",
    "sg.dtr.cor_due_prior_years": "S45 计算器 2026-10-06：2025 年的付款在 2026 年查询，提示提交后 3 个月内，标签 sg_s45.12、13",
    "sg.time.excluded_days": "S45 计算器 2026-10-06：周日顺延见标签 sg_s45.09；顺延途中的公众假期 17 May 2027 被排除，见标签 sg_s45.11",
    "sg.dtr.cor_due": "S45 计算器 2026-10-06：2026 年的付款提示 31 Mar 2027，2027 年的付款提示 31 Mar 2028，一致，标签 sg_s45.01、11",
    "cn-sg.int.cap_other": "S45 计算器 2026-10-06：10.00%，一致，标签 sg_s45.01；cn.gsf.2010-75#11 第二款解释：其他情况下利息的征税税率为10%，一致",
    "cn-sg.int.cap_bank": "S45 计算器 2026-10-06：7.00%，一致，标签 sg_s45.02；cn.gsf.2010-75#11 第二款解释：受益所有人为银行或金融机构情况下 7%，一致",
    "cn-sg.roy.cap": "S45 计算器 2026-10-06：10.00%，一致，标签 sg_s45.04；cn.gsf.2010-75#12 第二款解释：设定最高税率为10%，一致",
    "cn-sg.roy.equipment_base": "中英文议定书第三条与国税发〔2010〕75号第十二条解释一致：按总额 60% 确定税基；其后的第二、第三议定书和多边公约均未改动。S45 计算器 2026-10-06 只显示名义税率 10.00%，标签 sg_s45.05",
    "sg.wht.interest": "S45 计算器 2026-10-06：无协定税率 15.00%，一致，标签 sg_s45.01、06",
    "sg.wht.royalty": "S45 计算器 2026-10-06：无协定税率 10.00%，一致，标签 sg_s45.04、07",
    "sg.wht.rate_fallback": "S45 计算器 2026-10-06：经固定营业场所取得时 17.00%，一致，标签 sg_s45.08",
    "hk-sg.no_comprehensive_dta": "S45 计算器 2026-10-06：香港的协定税率为 Not Applicable，一致，标签 sg_s45.06、07",
    "sg.wht.late_penalty": "S45 计算器 2026-10-06：罚款按协定税率下的税额计，标签 sg_s45.09",
    "sg.wht.filing_due": "S45 计算器 2026-10-06：15 Mar 2026 为周日，显示 16 Mar 2026，与释义法第50条一致，标签 sg_s45.09；税务局页面示例写名义日期 15 Jun 2025，标签 sg_iras_ex.01",
    "sg.wht.late_penalty_monthly_starts_after_days": "S45 计算器 2026-10-06：附加罚款 5 个整月，标签 sg_s45.09；税务局页面示例：2 个整月合计 490，标签 sg_iras_ex.02；均一致",
}
for r in R:
    if r["param_id"] in XC:
        r["cross_check"] = XC[r["param_id"]]

with (ROOT / "params.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(R)
print("params written:", len(R))
