"""Singapore s45 withholding on payments to a non-resident company, and the CN–SG treaty on top (规则层.md §7 step 1).
Treaty rule ids end in "@sg": the same treaty parameter also serves the Mainland-source direction (spec_cn).

Structure only: every number is a param_id resolved by compile.py. General rules are unconditional; exceptions
carry the condition and name what they override (default-logic style, 规则层.md §3).
"""
from .model import (ALL, ALWAYS, And, Discretion, Effect, Leaf, Mount, Not, Or, RuleObj, Scope, ge, gt, is_false, is_in, is_true, le)

SG, CN, HK = "SG", "CN", "HK"
DIVIDEND, INTEREST, ROYALTY, SHARE_TRANSFER = "DIVIDEND", "INTEREST", "ROYALTY", "SHARE_TRANSFER"
SERVICE_FEE = "SERVICE_FEE"
IP_TRANSFER = "IP_TRANSFER"
WITHHELD = (INTEREST, ROYALTY, SERVICE_FEE)                       # s45 / s45A income
NON_RESIDENT = Leaf("payee_in_source_jur", is_false, on="payee")


def dom(income):
    return Scope(SG, None, income)


def treaty(income):
    return Scope(SG, CN, income)


def inbound(income, source=ALL):
    return Scope(source, SG, income, side="residence")


TREATY_RULES = ("cn-sg.int.cap_bank@sg", "cn-sg.int.cap_other@sg", "cn-sg.int.government_exempt@sg",
                "cn-sg.roy.cap@sg", "cn-sg.roy.equipment_base@sg", "cn-sg.pe.no_pe@sg")
COR_RULES = ("sg.dtr.cor", "sg.dtr.cor_prior_years")

SPEC = [
    # ---- domestic charge, s43(3)/(3A) collected under s45 / s45A
    RuleObj("sg.wht.interest", dom(INTEREST), Effect.CHARGE, "sg.wht.interest", cond=Leaf("payee_in_source_jur", is_false, on="payee"), uses=("sg.wht.interest_non_resident",)),
    RuleObj("sg.wht.royalty", dom(ROYALTY), Effect.CHARGE, "sg.wht.royalty", cond=Leaf("payee_in_source_jur", is_false, on="payee"), uses=("sg.wht.royalty_non_resident",)),
    RuleObj("sg.wht.equipment_rent", dom(ROYALTY), Effect.CHARGE, "sg.wht.movable_property_rent",
            cond=And(Leaf("payee_in_source_jur", is_false, on="payee"), Leaf("is_equipment_lease", is_true)), overrides=frozenset({"sg.wht.royalty"})),
    # exception: income of the payee's fixed place in Singapore is taxed at the prevailing rate; no treaty cap, no certificate
    RuleObj("sg.wht.fixed_place", dom(WITHHELD), Effect.CHARGE, "sg.wht.rate_fallback",
            cond=And(Leaf("payee_in_source_jur", is_false, on="payee"), Leaf("fixed_place_in_sg", is_true, on="payee")),
            overrides=frozenset({"sg.wht.interest", "sg.wht.royalty", "sg.wht.equipment_rent", "sg.wht.service_fee"} | set(TREATY_RULES) | set(COR_RULES))),

    # ---- management / service fees to a non-resident are Singapore income (s12(7)(c)) withheld under s45A at the
    #      prevailing rate, unless the work is done wholly outside Singapore by a non-resident without a Singapore business (s12(7A))
    RuleObj("sg.wht.service_fee", dom(SERVICE_FEE), Effect.CHARGE, "sg.wht.rate_fallback",
            cond=And(NON_RESIDENT, Leaf("service_performed_in_source", is_true, "sg.wht.service_outside_sg_excluded")),
            uses=("sg.wht.service_fee", "sg.wht.s45a_applies")),
    RuleObj("cn-sg.pe.no_pe@sg", treaty(SERVICE_FEE), Effect.EXEMPT, None,
            cond=And(Leaf("residence_cert", is_true, on="payee"), Leaf("fixed_place_in_sg", is_false, on="payee"),
                     Leaf("service_days_12m", le, "cn-sg.pe.service_days")),
            uses=("cn-sg.pe.business_profits_residence_only",)),

    # ---- stamp duty: a transfer of shares is stamped at 0.2% of the consideration, paid by the transferee (First Schedule
    #      Art 3(c), Third Schedule Art 2(a)); an outside buyer's duty is its own
    # SDA s15(1)(b) with the 2014 Rules: no ad valorem duty between associated permitted entities (75% of voting capital,
    #   more than half the votes), claimed, kept associated and the asset kept for 2 years (rule 7(1)(a), (b)) (口径 D18, D19)
    #   shares a liquidation or capital reduction cancels pass by no conveyance on sale (口径 D19)
    RuleObj("sg.stamp.buyer", dom(SHARE_TRANSFER), Effect.STAMP, "sg.stamp.share_rate", bearer="payer",
            cond=And(Leaf("shares_cancelled", is_false, "sg.stamp.share_rate"),
                     Not(And(Leaf("associated_ratio", ge, "sg.stamp.associated_capital_min"), Leaf("stamp_relief_claimed", is_true),
                         Leaf("clawback_event_within_2y", is_false, "sg.stamp.clawback_years"),
                         Leaf("asset_disposed_within_2y", is_false, "sg.stamp.clawback_years")))),
            uses=("sg.stamp.transferee_pays",)),

    # ---- GST reverse charge: a Singapore business that cannot recover all its input tax accounts for 9% on services and
    #      IP bought from abroad (s14, s16); a fully taxable business is outside the charge
    RuleObj("sg.gst.reverse_charge", dom((SERVICE_FEE, ROYALTY, IP_TRANSFER)), Effect.VAT, "sg.gst.rate", bearer="payer",
            cond=And(NON_RESIDENT, Leaf("gst_input_fully_recoverable", is_false, "sg.gst.reverse_charge", on="payer")),
            uses=("sg.gst.recovery_ratio_basis",)),

    # ---- Pillar Two (MEMTA 2024): for a group at or above EUR 750 million, the domestic top-up tax charges the minimum rate
    #      times the shortfall share of the entity's excess profit (the engine's pseudo-flow)
    RuleObj("sg.p2.topup", Scope(SG, SG, "TOPUP", side="residence"), Effect.CHARGE, "sg.p2.minimum_rate",
            cond=And(Leaf("group_revenue_eur", ge, "sg.p2.revenue_threshold", on="payee"), Leaf("p2_iir", is_false, "p2.qualified_iir_sg")),
            uses=("sg.p2.dtt",)),
    #      口径 D20: the MTT (Part 2, ss 11-15) — a Singapore responsible member pays the top-up tax of its relevant
    #      entities abroad (the engine's iir: pseudo-flow, the parent's own)
    RuleObj("sg.p2.mtt", Scope(SG, SG, "TOPUP", side="residence"), Effect.CHARGE, "sg.p2.minimum_rate",
            cond=And(Leaf("group_revenue_eur", ge, "sg.p2.revenue_threshold", on="payee"), Leaf("p2_iir", is_true, "p2.qualified_iir_sg")),
            overrides=frozenset({"sg.p2.topup"}), uses=("sg.p2.mtt_chargeable_entity", "p2.qualified_iir_hk")),
    RuleObj("sg.p2.base", Scope(SG, SG, "TOPUP", side="residence"), Effect.BASE, None, uses=("sg.p2.minimum_rate",)),

    # ---- domestic flows: income accruing in Singapore to a Singapore company is charged (s10(1)); dividends are exempt
    #      under the declaration below
    RuleObj("sg.domestic.charge", Scope(SG, SG, (INTEREST, ROYALTY, SERVICE_FEE), side="residence"), Effect.CHARGE, "sg.corp.rate",
            cond=Leaf("payee_in_source_jur", is_true, on="payee"), uses=("sg.charge.basis", "sg.corp.rate_entity")),

    # ---- a Singapore company's service income from abroad: charged on the profit in the fee, under s10(1) for the work done
    #      here or s10(25) when the rest is received here; replaces the gross FSIE charge for this income
    RuleObj("sg.service.charge", inbound(SERVICE_FEE), Effect.CHARGE, "sg.corp.rate",
            cond=And(NON_RESIDENT, Or(Leaf("service_performed_in_residence", is_true, "sg.charge.basis"),
                                      Leaf("receipt_kind", is_in, "sg.fsie.receipt_kinds"))),
            overrides=frozenset({"sg.fsie.charge"}), uses=("sg.charge.basis", "sg.corp.rate_entity")),
    RuleObj("sg.service.base", inbound(SERVICE_FEE), Effect.BASE, None, uses=("sg.charge.basis",)),

    # ---- 口径 D22: the IP transfer step. An outright purchase is no payment "for the use of or the right to use" (s12(7)):
    #      nothing is deemed sourced here, nothing withheld; the buyer writes the price down over the 5 years it may elect
    #      (s19B(1AA), (1AB)) — none for rights from a related party that had Singapore deductions for creating them (10A),
    #      none for rights acquired after the basis period for YA 2028 (10)(aa). A Singapore seller: the proceeds above the
    #      expenditure still unallowed, up to the allowances made, are charged (s19B(4), (5)); the rest is capital unless
    #      judged otherwise (s10(1)); the IP sits where its owner resides (s10L(15)(k)), so s10L does not reach it.
    RuleObj("sg.nocharge.ip_purchase", dom(IP_TRANSFER), Effect.NOCHARGE, None, cond=NON_RESIDENT, uses=("sg.ip.purchase_not_use",)),
    RuleObj("sg.ip.wda", dom(IP_TRANSFER), Effect.DEDUCTION, "sg.corp.rate",
            cond=Leaf("seller_had_sg_creation_deductions", is_false, "sg.ip.wda_regime"),
            uses=("sg.ip.wda_related_party_denial", "sg.ip.assignee_undertaking", "sg.corp.rate_entity")),
    RuleObj("sg.ip.wda.horizon", dom(IP_TRANSFER), Effect.DEDUCT_BASE, None, uses=("sg.ip.wda_years",)),
    RuleObj("sg.ip.recapture", inbound(IP_TRANSFER), Effect.CHARGE, "sg.corp.rate", overrides=frozenset({"sg.fsie.charge"}),
            uses=("sg.ip.balancing_charge", "sg.ip.charge_after_period", "sg.ip.owner_situs", "sg.corp.rate_entity")),
    RuleObj("sg.ip.revenue", inbound(IP_TRANSFER), Effect.CHARGE, "sg.corp.rate",
            cond=Not(Discretion("ip_held_as_capital_asset", cites=("sg.ita1947.full#s10",), on="flow")),
            overrides=frozenset({"sg.ip.recapture", "sg.fsie.charge"}), uses=("sg.charge.basis", "sg.corp.rate_entity")),

    # ---- dividends of a Singapore company are exempt in the recipient's hands (one-tier, s13(1)(za)): a declaration
    RuleObj("sg.nocharge.dividend", dom(DIVIDEND), Effect.NOCHARGE, None, uses=("sg.nocharge.dividend",)),

    # ---- gains: no tax on capital; a gain is Singapore income for a Singapore company, or for a non-resident only through
    #      a Singapore business (s10(1)); either way s13W exempts a >= 20% holding kept >= 24 months
    RuleObj("sg.gain.charge", dom(SHARE_TRANSFER), Effect.CHARGE, "sg.corp.rate",
            cond=Or(Leaf("payee_in_source_jur", is_true, on="payee"), Leaf("fixed_place_in_sg", is_true, on="payee")),
            uses=("sg.charge.basis", "sg.corp.rate_entity")),
    RuleObj("sg.gain.base", dom(SHARE_TRANSFER), Effect.BASE, None, uses=("sg.charge.basis",)),
    RuleObj("sg.gain.capital", dom(SHARE_TRANSFER), Effect.EXEMPT, None,
            cond=Discretion("gain_is_capital_in_nature", cites=("sg.ita1947.full#s10",))),
    RuleObj("sg.gain.s13w", dom(SHARE_TRANSFER), Effect.EXEMPT, None,
            cond=And(Leaf("ratio", ge, "sg.s13w.ratio_min"), Leaf("holding_months", ge, "sg.s13w.holding_months_min"))),

    # ---- the payer's deduction (s14(1)); "wholly and exclusively in the production of the income" is a judgement
    # s14(1)(a): interest is deductible when the borrowed capital is employed in acquiring the income (not, say, shares
    # whose dividends are exempt); whether an outgoing was wholly and exclusively incurred is a judgement
    RuleObj("sg.deduct.interest", dom(INTEREST), Effect.DEDUCTION, "sg.corp.rate",
            cond=And(Discretion("incurred_in_production_of_income", cites=("sg.ita1947.full#s14",), on="payer"),
                     Leaf("loan_purpose_income_producing", is_true, "sg.deduct.interest_capital_employed", on="payer")),
            uses=("sg.deduct.general", "sg.corp.rate_entity")),
    *[RuleObj("sg.deduct.%s" % inc.lower(), dom(inc), Effect.DEDUCTION, "sg.corp.rate",
              cond=Discretion("incurred_in_production_of_income", cites=("sg.ita1947.full#s14",), on="payer"),
              uses=("sg.deduct.general", "sg.corp.rate_entity")) for inc in (ROYALTY, SERVICE_FEE)],
    RuleObj("sg.tp.deduction_cap", dom((INTEREST, ROYALTY, SERVICE_FEE)), Effect.DEDUCT_BASE, None, cond=NON_RESIDENT,
            uses=("sg.tp.arms_length",)),
    # s34F: documentation when gross revenue exceeds $10m, by the time of the return; s34E: 5% surcharge on an adjustment
    RuleObj("sg.tp.documentation", dom((INTEREST, ROYALTY, SERVICE_FEE)), Effect.DEADLINE, "sg.tp.documentation_due",
            cond=And(Leaf("payee_is_related", is_true, on="payee"), Leaf("gross_revenue", gt, "sg.tp.documentation_revenue_min", on="payer")),
            uses=("sg.corp.return_due",)),
    RuleObj("sg.tp.surcharge", dom((INTEREST, ROYALTY, SERVICE_FEE)), Effect.PENALTY, "sg.tp.surcharge_rate",
            cond=Leaf("payee_is_related", is_true, on="payee")),

    # ---- CN–SG agreement: caps and the equipment-rent base; min() makes the two interest caps compatible
    RuleObj("cn-sg.int.cap_bank@sg", treaty(INTEREST), Effect.RATE_CAP, "cn-sg.int.cap_bank",
            cond=Leaf("payee_is_financial_institution", is_true, on="payee")),
    RuleObj("cn-sg.int.cap_other@sg", treaty(INTEREST), Effect.RATE_CAP, "cn-sg.int.cap_other"),
    RuleObj("cn-sg.int.government_exempt@sg", treaty(INTEREST), Effect.EXEMPT, "cn-sg.int.government_exempt",
            cond=And(Leaf("payee_is_government", is_true, on="payee"),
                     Leaf("government_exempt_condition_met", is_true, "cn-sg.int.government_exempt_condition", on="payee"))),
    RuleObj("cn-sg.roy.cap@sg", treaty(ROYALTY), Effect.RATE_CAP, "cn-sg.roy.cap"),
    RuleObj("cn-sg.roy.equipment_base@sg", treaty(ROYALTY), Effect.BASE, "cn-sg.roy.equipment_base",
            cond=Leaf("is_equipment_lease", is_true)),
    # principal purpose test (MLI Art 7(1) as synthesised into the agreement): denies every treaty benefit above
    RuleObj("cn-sg.ppt@sg", Scope(SG, CN, ALL), Effect.DENY, "cn-sg.ppt",
            cond=Discretion("ppt", cites=("treaty.cn-sg.2007.mli.zh#27",)), overrides=frozenset(TREATY_RULES)),

    # ---- procedure: filing deadline (statute, then IRAS practice), penalty, certificate of residence
    RuleObj("sg.wht.due", dom(WITHHELD), Effect.DEADLINE, "sg.wht.filing_due",           # only what s45 withholds
            uses=("sg.time.excluded_days", "sg.time.act_on_excluded_day", "sg.holiday.sunday_substitute")),
    RuleObj("sg.wht.due_practice", dom(WITHHELD), Effect.DEADLINE, "observed:sg.wht.due_date_saturday_rolls",
            uses=("sg.wht.comptroller_may_allow_other_period", "sg.wht.penalty_runs_from_allowed_date")),
    RuleObj("sg.wht.penalty", dom(WITHHELD), Effect.PENALTY, "sg.wht.late_penalty",
            uses=("sg.wht.late_penalty_monthly", "sg.wht.late_penalty_monthly_cap",
                  "sg.wht.late_penalty_monthly_starts_after_days")),
    RuleObj("sg.dtr.cor", treaty(ALL), Effect.DEADLINE, "sg.dtr.cor_due",
            cond=Leaf("claim_is_for_prior_year", is_false)),
    RuleObj("sg.dtr.cor_prior_years", treaty(ALL), Effect.DEADLINE, "sg.dtr.cor_due_prior_years",
            cond=Leaf("claim_is_for_prior_year", is_true)),

    # ---- 口径 D24, receiving side, Singapore-sourced: interest or a royalty a Singapore company derives from a lending or licensing
    #      business carried on here is income accruing in or derived from Singapore (s10(1)), charged whether or not it
    #      is remitted; where it arises is a judgement — when it is Singapore-sourced the remittance rules are beside the point
    RuleObj("sg.onshore.charge", inbound((INTEREST, ROYALTY)), Effect.CHARGE, "sg.corp.rate",
            cond=And(NON_RESIDENT, Discretion("income_sourced_in_sg", cites=("sg.ita1947.full#s10",))),
            overrides=frozenset({"sg.fsie.charge"}), uses=("sg.charge.basis", "sg.corp.rate_entity")),
    # ---- receiving side: foreign income is charged when received in Singapore (s10(1), (25)); foreign dividends
    #      are exempt under s13(8) if taxed abroad at a headline rate of at least 15% and the Comptroller is satisfied
    RuleObj("sg.fsie.charge", inbound(ALL), Effect.CHARGE, "sg.corp.rate",
            cond=And(Leaf("payee_in_source_jur", is_false, on="payee"), Leaf("receipt_kind", is_in, "sg.fsie.receipt_kinds")),
            uses=("sg.charge.basis", "sg.foreign_income.remittance_is_receipt", "sg.fsie.recipient", "sg.corp.rate_entity")),
    RuleObj("sg.fsie.exempt", inbound(DIVIDEND), Effect.EXEMPT, None,
            cond=And(Leaf("foreign_taxed", is_true, "sg.fsie.subject_to_tax"),
                     Leaf("foreign_headline_rate", ge, "sg.fsie.headline_rate_min"),
                     Discretion("exemption_beneficial", cites=("sg.ita1947.full#s13",))),
            uses=("sg.fsie.beneficial", "sg.fsie.ministerial_order")),
    # s10L: a foreign disposal gain received in Singapore is income unless the seller has adequate economic substance
    RuleObj("sg.s10l.gain", inbound(SHARE_TRANSFER), Effect.EXEMPT, None,
            cond=Or(Leaf("is_relevant_group_entity", is_false, "sg.s10l.relevant_group_entity", on="payee"),
                    Leaf("is_excluded_entity", is_true, "sg.s10l.excluded_entity", on="payee"),
                    Discretion("adequate_substance", cites=("sg.ita1947.full#s10L",))),
            uses=("sg.s10l.received_in_sg_trigger", "sg.s10l.substance_pure_holding", "sg.s10l.substance_non_pure_holding",
                  "sg.s10l.share_situs")),
    RuleObj("sg.fsie.gain.base", inbound(SHARE_TRANSFER), Effect.BASE, None),
    # foreign tax credit: under the Agreement for Mainland tax (s50), unilaterally for Hong Kong tax (s50A)
    RuleObj("sg.ftc.dta", inbound(ALL, CN), Effect.CREDIT, None, uses=("sg.ftc.credit_limit", "sg.ftc.tax_payable_under_arrangements")),
    RuleObj("sg.ftc.unilateral", inbound(ALL, HK), Effect.CREDIT, None,
            uses=("sg.ftc.unilateral", "sg.ftc.unilateral_income", "sg.ftc.credit_limit")),
    # domestic remedy: a company objects within 2 months of the notice of assessment (s76(3)(a))
    RuleObj("sg.objection", inbound(ALL), Effect.DEADLINE, "sg.objection.months_company"),
    RuleObj("sg.objection.source", dom(ALL), Effect.DEADLINE, "sg.objection.months_company"),
    # s50C: on election, one pooled credit for the year over the qualifying foreign income instead of item by item
    RuleObj("sg.ftc.pooling", Scope(ALL, SG, ALL, mount=Mount.ENTITY, side="residence"), Effect.CREDIT, None,
            cond=And(Leaf("ftc_pooling_election", is_true, "sg.ftc.pooling_election", on="payee"),
                     Leaf("foreign_taxed", is_true, "sg.ftc.pooling_foreign_tax_paid"),
                     Leaf("foreign_headline_rate", ge, "sg.ftc.pooling_headline_rate_min")),
            uses=("sg.ftc.pooling_sg_tax_not_nil",)),
]
