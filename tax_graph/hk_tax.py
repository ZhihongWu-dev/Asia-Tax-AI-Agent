"""Hong Kong profits tax on one flow: outbound royalties, onshore equity gains, and FSIE on inbound income.

A presentation over flow_tax (规则层.md): the Hong Kong item's effective rate under both bounds, after any foreign
tax credit (s50 / s50AAA), in percent of the gross amount; None when Hong Kong charges nothing.
"""
from .flow_tax import FlowTax, flow_tax

HK, CN, SG = "HK", "CN", "SG"


def hk_tax(payer_loc, payee_loc, income, facts, on=None, amount=None, params=None, ticks=None, target_loc=None) -> FlowTax:
    return flow_tax(payer_loc, payee_loc, income, facts, HK, on=on, amount=amount, params=params, ticks=ticks, target_loc=target_loc)
