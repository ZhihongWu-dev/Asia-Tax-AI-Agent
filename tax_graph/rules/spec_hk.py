"""Hong Kong (规则层.md §7 step 3). Three families, all under Cap. 112:

  outbound   royalties paid by a Hong Kong payer are deemed trading receipts (s15(1)(b)) taxed on a deemed profit (s21A),
             and the Arrangement caps them for a Mainland recipient; dividends and interest to a non-resident with no
             Hong Kong business bear no charge, so no rule exists for them (a CHARGE that is absent is a tax of zero)
  inbound    specified foreign-sourced income received in Hong Kong by an MNE entity is charged (s15I) unless an
             exception applies: economic substance (s15K), IP nexus (s15L), participation (s15M/15N)
  onshore    equity disposal gains sourced in Hong Kong: charged on the gain unless capital (s14) or within the
             tax certainty scheme (Sch 17K)
Structure only; every number is a param_id.
"""
from .model import (ALL, ALWAYS, And, Discretion, Effect, Leaf, Not, Or, RuleObj, Scope, ge, gt, is_false, is_in, is_true, le)

HK, CN, SG = "HK", "CN", "SG"
DIVIDEND, INTEREST, ROYALTY, SHARE_TRANSFER = "DIVIDEND", "INTEREST", "ROYALTY", "SHARE_TRANSFER"
SERVICE_FEE = "SERVICE_FEE"
IP_TRANSFER = "IP_TRANSFER"
FSIE_INCOME = (DIVIDEND, INTEREST, ROYALTY, SHARE_TRANSFER)        # s15H "specified foreign-sourced income"
NON_RESIDENT = Leaf("payee_in_source_jur", is_false, on="payee")


def out(income, residence=None):
    return Scope(HK, residence, income)


def inbound(income):
    return Scope(ALL, HK, income, side="residence")


SUBSTANCE = Or(Leaf("substance_ruled_adequate", is_true, on="payee"),          # an advance ruling binds (s88A, Sch 10)
               Discretion("adequate_substance", cites=("hk.cap112.en#s15K",)))
SUBSTANCE_COND = Or(And(Leaf("pure_equity_holding", is_true, "hk.fsie.substance_pure_holding", on="payee"),
                        Leaf("registration_filing_compliant", is_true, on="payee"), SUBSTANCE),
                    And(Leaf("pure_equity_holding", is_false, "hk.fsie.substance_non_pure_holding", on="payee"), SUBSTANCE))
PARTICIPATION_COND = And(
    Leaf("hk_resident_or_pe", is_true, "hk.fsie.participation_resident_or_pe", on="payee"),
    Leaf("ratio", ge, "hk.fsie.participation_ratio_min"),
    Leaf("holding_months", ge, "hk.fsie.participation_months_min"),
    Or(Leaf("foreign_taxed", is_true, "hk.fsie.participation_subject_to_tax"),
       Leaf("underlying_profits_taxed", is_true, "hk.fsie.participation_headline_rate_basis")),
    Leaf("foreign_headline_rate", ge, "hk.fsie.reference_rate"),
    Leaf("deductible_at_payer", is_false, "hk.fsie.participation_anti_hybrid"),
    Discretion("no_main_purpose_of_tax_benefit", cites=("hk.cap112.en#s15N",)))

HK_S45 = And(Leaf("associated_ratio", ge, "hk.stamp.associated_ratio"), Leaf("stamp_relief_claimed", is_true),
             Leaf("clawback_event_within_2y", is_false, "hk.stamp.clawback_years"))


SPEC = [
    # ---- no charge on dividends or interest paid to a non-resident with no Hong Kong business: s14 reaches only profits of a
    #      business carried on in Hong Kong (a declaration, so the coverage matrix can tell "nothing" from "not written")
    RuleObj("hk.nocharge.outbound", out((DIVIDEND, INTEREST)), Effect.NOCHARGE, None, cond=NON_RESIDENT, uses=("hk.nocharge.scope",)),

    # ---- services: profits of a non-resident are charged only when the work is done in Hong Kong (s14; whether the
    #      profits arise here is a judgement), on the profit in the fee; a Mainland resident below the PE threshold is exempt
    RuleObj("hk.service.charge", out(SERVICE_FEE), Effect.CHARGE, "hk.profits.rate_corp",
            cond=And(NON_RESIDENT, Leaf("service_performed_in_source", is_true, "hk.nocharge.scope"),
                     Discretion("profits_arise_in_hk", cites=("hk.cap112.en#s14",))),
            uses=("hk.profits.charge_scope", "hk.profits.rate_entity")),
    RuleObj("hk.service.base", out(SERVICE_FEE), Effect.BASE, None, uses=("hk.nocharge.scope",)),
    RuleObj("hk.nocharge.service_offshore", out(SERVICE_FEE), Effect.NOCHARGE, None,
            cond=And(NON_RESIDENT, Leaf("service_performed_in_source", is_false, "hk.nocharge.scope"))),
    RuleObj("cn-hk.pe.no_pe@hk", out(SERVICE_FEE, CN), Effect.EXEMPT, None,
            cond=And(Leaf("residence_cert", is_true, on="payee"), Leaf("fixed_place_in_hk", is_false, on="payee"),
                     Leaf("service_days_12m", le, "cn-hk.pe.service_days")),
            uses=("cn-hk.pe.business_profits_residence_only",)),

    # ---- outbound royalties: deemed trading receipt, deemed profit 30% (100% from an associate), payer deducts
    RuleObj("hk.royalty.deemed", out(ROYALTY), Effect.CHARGE, "hk.profits.rate_corp",
            cond=And(Leaf("payee_in_source_jur", is_false, on="payee"), Or(Leaf("ip_used_in_hk", is_true, "hk.royalty.deemed_use_in_hk"),
                            Leaf("royalty_deductible_in_hk", is_true, "hk.royalty.deemed_use_outside_hk_deductible"))),
            uses=("hk.royalty.payer_chargeable", "hk.royalty.payer_must_deduct", "hk.royalty.deemed_film_use_in_hk")),
    RuleObj("hk.royalty.deemed_profit", out(ROYALTY), Effect.BASE, "hk.royalty.deemed_profit"),
    RuleObj("hk.royalty.deemed_profit_associate", out(ROYALTY), Effect.BASE, "hk.royalty.deemed_profit_associate",
            cond=And(Leaf("payee_is_associate", is_true, on="payee"),
                     Not(Leaf("ip_never_owned_by_hk_business", is_true, "hk.royalty.associate_carve_out"))),
            overrides=frozenset({"hk.royalty.deemed_profit"})),
    RuleObj("cn-hk.roy.cap@hk", out(ROYALTY, CN), Effect.RATE_CAP, "cn-hk.roy.cap",
            cond=And(Leaf("residence_cert", is_true, on="payee"),
                     Discretion("beneficial_owner", cites=("treaty.cn-hk.2006.zh#12.2",)))),
    RuleObj("cn-hk.ppt@hk", out(ALL, CN), Effect.DENY, "cn-hk.ppt",
            cond=Discretion("ppt", cites=("treaty.cn-hk.2006.p5.zh#6",)), overrides=frozenset({"cn-hk.roy.cap@hk", "cn-hk.pe.no_pe@hk"})),

    # ---- stamp duty on a transfer of Hong Kong stock: every person effecting the sale or purchase makes a contract note
    #      (s19(1)), each stamped at 0.1% of the consideration (First Schedule head 2(1)); a levy, not income tax
    # SDO s45: no duty between associated bodies corporate (90%) when the Collector is shown the relief's conditions —
    #   claimed, the consideration from within the association, no ceasing to be associated within 2 years (口径 D18)
    #      (shares a liquidation or capital reduction cancels are neither sold nor transferred: no note, 口径 D19)
    RuleObj("hk.stamp.seller", out(SHARE_TRANSFER), Effect.STAMP, "hk.stamp.stock_rate", bearer="payee",
            cond=And(Leaf("shares_cancelled", is_false, "hk.stamp.contract_note_each_party"), Not(HK_S45)),
            uses=("hk.stamp.contract_note_each_party",)),
    RuleObj("hk.stamp.buyer", out(SHARE_TRANSFER), Effect.STAMP, "hk.stamp.stock_rate", bearer="payer",
            cond=And(Leaf("shares_cancelled", is_false, "hk.stamp.contract_note_each_party"), Not(HK_S45)),
            uses=("hk.stamp.contract_note_each_party",)),

    # ---- the payer's deduction (s16(1)); whether an outgoing was incurred in producing chargeable profits is a judgement
    # s16(2): interest is deductible only if the lender is a financial institution (d) or the interest is chargeable
    # to Hong Kong profits tax in the lender's hands (c); the other limbs (utilities, qualifying instruments) are not
    # structures this model places
    RuleObj("hk.deduct.interest", out(INTEREST), Effect.DEDUCTION, "hk.profits.rate_corp",
            cond=And(Discretion("incurred_in_production_of_profits", cites=("hk.cap112.en#s16",), on="payer"),
                     Or(Leaf("payee_is_financial_institution", is_true, "hk.deduct.interest_cond_fi", on="payee"),
                        Leaf("lender_interest_taxable_in_hk", is_true, "hk.deduct.interest_cond_lender_taxable", on="payee"))),
            uses=("hk.deduct.general", "hk.profits.rate_entity")),
    RuleObj("hk.deduct.service_fee", out(SERVICE_FEE), Effect.DEDUCTION, "hk.profits.rate_corp",
            cond=Discretion("incurred_in_production_of_profits", cites=("hk.cap112.en#s16",), on="payer"),
            uses=("hk.deduct.general", "hk.profits.rate_entity")),
    RuleObj("hk.deduct.royalty", out(ROYALTY), Effect.DEDUCTION, "hk.profits.rate_corp",
            cond=Leaf("royalty_deductible_in_hk", is_true, "hk.deduct.general"), uses=("hk.profits.rate_entity",)),
    RuleObj("hk.tp.deduction_cap", out((INTEREST, ROYALTY, SERVICE_FEE)), Effect.DEDUCT_BASE, None, cond=NON_RESIDENT,
            uses=("hk.tp.arms_length",)),
    # s58C: a group entity above any two of the Schedule 17I thresholds keeps master and local files, 9 months after year end
    RuleObj("hk.tp.local_file", out((INTEREST, ROYALTY, SERVICE_FEE)), Effect.DEADLINE, "hk.tp.local_file_months",
            cond=And(Leaf("payee_is_related", is_true, on="payee"), Leaf("is_mne_member", is_true, on="payer"),
                     Leaf("hk_tp_small_entity", is_false, "hk.tp.threshold_revenue", on="payer")),
            uses=("hk.tp.threshold_assets", "hk.tp.threshold_employees")),

    # ---- inbound, Hong Kong-sourced: s14 charges profits arising in or derived from Hong Kong whatever their payer's
    #      jurisdiction; where interest (provision of credit) or a royalty (place of use) arises is a judgement. When it is
    #      Hong Kong-sourced the FSIE regime below is beside the point, so this charge overrides it.
    RuleObj("hk.onshore.charge", inbound((INTEREST, ROYALTY)), Effect.CHARGE, "hk.profits.rate_corp",
            cond=And(NON_RESIDENT, Discretion("income_sourced_in_hk", cites=("hk.cap112.en#s14",))),
            overrides=frozenset({"hk.fsie.charge", "hk.fsie.substance.interest", "hk.fsie.ip_nexus"}),
            uses=("hk.profits.charge_scope", "hk.profits.rate_entity")),

    # ---- inbound: FSIE charge on specified foreign-sourced income received in Hong Kong by an MNE entity
    RuleObj("hk.fsie.charge", inbound(FSIE_INCOME), Effect.CHARGE, "hk.profits.rate_corp",
            cond=And(Leaf("payee_in_source_jur", is_false, on="payee"), Leaf("is_mne_member", is_true, "hk.fsie.mne_entity_only", on="payee"),
                     Leaf("receipt_kind", is_in, "hk.fsie.receipt_kinds")),
            uses=("hk.fsie.covered_income", "hk.fsie.received_in_hk_trigger", "hk.fsie.remittance_is_receipt",
                  "hk.fsie.commencement", "hk.profits.charge_scope", "hk.profits.rate_entity")),
    RuleObj("hk.fsie.gain.base", inbound(SHARE_TRANSFER), Effect.BASE, None, uses=("hk.fsie.gain_not_capital",)),
    RuleObj("hk.fsie.ip_nexus", inbound(ROYALTY), Effect.BASE, None,
            uses=("hk.fsie.ip_nexus_exception", "hk.fsie.nexus_uplift", "hk.fsie.nexus_cap")),
    *[RuleObj("hk.fsie.substance.%s" % inc.lower(), inbound(inc), Effect.EXEMPT, None, cond=SUBSTANCE_COND,
              uses=("hk.fsie.substance_exception_income",)) for inc in (DIVIDEND, INTEREST, SHARE_TRANSFER)],
    *[RuleObj("hk.fsie.participation.%s" % inc.lower(), inbound(inc), Effect.EXEMPT, None, cond=PARTICIPATION_COND,
              uses=("hk.fsie.participation_main_purpose",)) for inc in (DIVIDEND, SHARE_TRANSFER)],
    # intragroup transfer: no gain or loss if seller and buyer are associated and both chargeable; undone if within
    # 2 years either ceases to be chargeable or they cease to be associated (s15OA, s15OB)
    RuleObj("hk.fsie.intragroup_relief", inbound(SHARE_TRANSFER), Effect.EXEMPT, None,
            cond=And(Leaf("intragroup_transfer", is_true, "hk.fsie.intragroup_relief"),
                     Leaf("acquirer_chargeable_in_hk", is_true),
                     Leaf("clawback_event_within_2y", is_false, "hk.fsie.intragroup_clawback_years")),
            uses=("hk.fsie.intragroup_assoc_ratio_min",)),

    # ---- 口径 D22: the IP transfer step. A non-resident selling IP to a Hong Kong buyer carries on no business here (s14);
    #      the buyer, its associate, deducts nothing (s16EC(2)). A Hong Kong seller: the proceeds above the expenditure
    #      still unallowed, up to the deductions allowed, are a trading receipt sourced here (s16E(3), s16EB(2)); a gain
    #      arising offshore and received here is an IP disposal gain charged under FSIE (s15I — not capital even if it so
    #      arises), less the excepted portion of a qualifying IP's gain (s15L, Sch 17FC); a gain arising here is charged
    #      only if not capital (s14). Where the gain arises, and whether it is capital, are judgements.
    RuleObj("hk.nocharge.ip_purchase", out(IP_TRANSFER), Effect.NOCHARGE, None, cond=NON_RESIDENT,
            uses=("hk.nocharge.scope", "hk.ip.purchase_from_associate_no_deduction")),
    RuleObj("hk.ip.recapture", inbound(IP_TRANSFER), Effect.CHARGE, "hk.profits.rate_corp",
            uses=("hk.ip.clawback", "hk.ip.clawback_specified", "hk.profits.rate_entity")),
    RuleObj("hk.ip.fsie", inbound(IP_TRANSFER), Effect.CHARGE, "hk.profits.rate_corp",
            cond=And(NON_RESIDENT, Leaf("is_mne_member", is_true, "hk.fsie.mne_entity_only", on="payee"),
                     Leaf("receipt_kind", is_in, "hk.fsie.receipt_kinds"),
                     Not(Discretion("ip_gain_sourced_in_hk", cites=("hk.cap112.en#s14",), on="flow"))),
            overrides=frozenset({"hk.ip.recapture"}),
            uses=("hk.fsie.ip_disposal_gain", "hk.fsie.ip_disposal_not_capital", "hk.fsie.qualifying_ip_kinds",
                  "hk.fsie.nexus_uplift", "hk.fsie.nexus_cap", "hk.ip.clawback", "hk.profits.rate_entity")),
    RuleObj("hk.ip.onshore", inbound(IP_TRANSFER), Effect.CHARGE, "hk.profits.rate_corp",
            cond=And(Discretion("ip_gain_sourced_in_hk", cites=("hk.cap112.en#s14",), on="flow"),
                     Not(Discretion("ip_held_as_capital_asset", cites=("hk.cap112.en#s14",), on="flow"))),
            overrides=frozenset({"hk.ip.recapture", "hk.ip.fsie"}),
            uses=("hk.profits.charge_scope", "hk.profits.rate_entity")),

    # ---- foreign tax credit on FSIE income: under the Arrangement for Mainland tax (s50), unilaterally for Singapore tax (s50AAA)
    RuleObj("hk.ftc.dta", Scope(CN, HK, ALL, side="residence"), Effect.CREDIT, None,
            cond=Leaf("hk_resident_or_pe", is_true, on="payee"), uses=("hk.ftc.credit_limit",)),
    RuleObj("hk.ftc.unilateral", Scope(SG, HK, ALL, side="residence"), Effect.CREDIT, None,
            cond=Leaf("hk_resident_or_pe", is_true, on="payee"),
            uses=("hk.ftc.unilateral_no_dta", "hk.ftc.unilateral_fsie_only", "hk.ftc.credit_limit")),

    # ---- domestic remedies: objection within 1 month of the assessment (s64), appeal within 1 month of the determination (s66)
    # ---- domestic flows: a Hong Kong company's interest, royalty or fee from a Hong Kong payer is charged under s14 when the
    #      profits arise here (a judgement); a dividend from a chargeable corporation is excluded (s26(a))
    RuleObj("hk.domestic.charge", Scope(HK, HK, (INTEREST, ROYALTY, SERVICE_FEE), side="residence"), Effect.CHARGE, "hk.profits.rate_corp",
            cond=And(Leaf("payee_in_source_jur", is_true, on="payee"), Discretion("profits_arise_in_hk", cites=("hk.cap112.en#s14",))),
            uses=("hk.profits.charge_scope", "hk.profits.rate_entity")),
    RuleObj("hk.domestic.dividend", Scope(HK, HK, DIVIDEND, side="residence"), Effect.NOCHARGE, None,
            cond=Leaf("payee_in_source_jur", is_true, on="payee"), uses=("hk.domestic.dividend_excluded",)),

    # ---- a Hong Kong company's service income: charged on the profit when the work is done in Hong Kong, otherwise
    #      offshore and outside s14 (FSIE does not list service income)
    RuleObj("hk.service.charge_resident", inbound(SERVICE_FEE), Effect.CHARGE, "hk.profits.rate_corp",
            cond=And(NON_RESIDENT, Leaf("service_performed_in_residence", is_true, "hk.nocharge.scope"),
                     Discretion("profits_arise_in_hk", cites=("hk.cap112.en#s14",))),
            uses=("hk.profits.charge_scope", "hk.profits.rate_entity")),
    RuleObj("hk.service.base_resident", inbound(SERVICE_FEE), Effect.BASE, None, cond=NON_RESIDENT,   # a domestic fee has
            uses=("hk.nocharge.scope",)),                                                                   # hk.service.base
    RuleObj("hk.nocharge.service_offshore_resident", inbound(SERVICE_FEE), Effect.NOCHARGE, None,
            cond=And(NON_RESIDENT, Leaf("service_performed_in_residence", is_false, "hk.nocharge.scope"))),
    # ---- Pillar Two (范围.md 9): for a group at or above EUR 750 million, the Hong Kong minimum top-up tax charges the
    #      minimum rate times the shortfall share of the entity's excess profit (the engine's pseudo-flow)
    RuleObj("hk.p2.topup", Scope(HK, HK, "TOPUP", side="residence"), Effect.CHARGE, "p2.minimum_rate",
            cond=And(Leaf("group_revenue_eur", ge, "p2.revenue_threshold", on="payee"), Leaf("p2_iir", is_false, "p2.qualified_iir_hk")),
            uses=("hk.p2.hkmtt",)),
    #      口径 D20: the IIR top-up tax (s26AE(2), (6); Sch 60 Art 2.1-2.3) — a Hong Kong parent that applies the IIR pays
    #      its allocable share of a low-taxed entity's top-up abroad (the engine's iir: pseudo-flow, the parent's own)
    RuleObj("hk.p2.iir", Scope(HK, HK, "TOPUP", side="residence"), Effect.CHARGE, "p2.minimum_rate",
            cond=And(Leaf("group_revenue_eur", ge, "p2.revenue_threshold", on="payee"), Leaf("p2_iir", is_true, "p2.qualified_iir_hk")),
            overrides=frozenset({"hk.p2.topup"}), uses=("hk.p2.iir_payable_from", "p2.qualified_iir_sg")),
    RuleObj("hk.p2.base", Scope(HK, HK, "TOPUP", side="residence"), Effect.BASE, None,
            uses=("p2.minimum_rate", "p2.sbie_payroll_rate", "p2.sbie_tangible_rate", "p2.sbie_payroll_transition", "p2.sbie_tangible_transition")),
    RuleObj("hk.objection", Scope(ALL, HK, ALL, side="residence"), Effect.DEADLINE, "hk.objection.months"),
    RuleObj("hk.objection.source", out(ALL), Effect.DEADLINE, "hk.objection.months"),
    RuleObj("hk.appeal", Scope(ALL, HK, ALL, side="residence"), Effect.DEADLINE, "hk.appeal.months"),

    # ---- onshore equity disposal gains: charge on the gain; capital assets excluded; tax certainty scheme
    RuleObj("hk.gain.charge", out(SHARE_TRANSFER), Effect.CHARGE, "hk.profits.rate_corp", uses=("hk.profits.charge_scope", "hk.profits.rate_entity")),
    RuleObj("hk.gain.base", out(SHARE_TRANSFER), Effect.BASE, None),
    RuleObj("hk.gain.capital", out(SHARE_TRANSFER), Effect.EXEMPT, None,
            cond=Discretion("capital_asset", cites=("hk.cap112.en#s14",)), uses=("hk.gain.capital_asset_excluded",)),
    RuleObj("hk.onshore_gain.certainty", out(SHARE_TRANSFER), Effect.EXEMPT, None,
            cond=And(Leaf("ratio", ge, "hk.onshore_gain.ratio_min"),
                     Leaf("holding_months", ge, "hk.onshore_gain.holding_months_min"),
                     Leaf("held_as_trading_stock", is_false, "hk.onshore_gain.trading_stock_disregarded"),
                     Leaf("sch17k_elected", is_true, "hk.onshore_gain.election_required", on="payee"))),
]
