"""Singapore YA 2026 arithmetic on an already established chargeable-income basis.

This module is not a gross-income-to-return workflow. Residency, source,
exemptions, deductions, losses and credit entitlement must be established by
country intake/rules before these functions are used in a user-facing result.
Amounts returned are exact before assessment rounding and prepaid taxes.
"""
from decimal import Decimal, localcontext
import json
from pathlib import Path
from .arithmetic import Band, ZERO, amount, marginal_tax

POLICY_VERSION = "sg-ya2026-2026-11-16"
CORPORATE_SOURCE = "https://www.iras.gov.sg/quick-links/tax-rates/corporate-income-tax-rates"
PERSONAL_SOURCE = "https://www.iras.gov.sg/taxes/individual-income-tax/basics-of-individual-income-tax/tax-residency-and-tax-rates/individual-income-tax-rates"
SOURCE_MANIFEST = json.loads(Path(__file__).with_name("sg_ya2026_sources.json").read_text(encoding="utf-8"))
SOURCE_BY_URL = {item["url"]: item for item in SOURCE_MANIFEST["sources"]}
COMPANY_BASIS_SOURCES = json.loads(Path(__file__).with_name(
    'sg_company_basis_sources.json').read_text(encoding='utf-8'))['sources']
PERSONAL_BANDS = tuple(Band(None if upper is None else Decimal(upper), Decimal(rate)) for upper, rate in (
    ("20000", "0"), ("30000", ".02"), ("40000", ".035"), ("80000", ".07"),
    ("120000", ".115"), ("160000", ".15"), ("200000", ".18"), ("240000", ".19"),
    ("280000", ".195"), ("320000", ".20"), ("500000", ".22"), ("1000000", ".23"),
    (None, ".24")))


def reconcile_company_basis(case, *, normal_chargeable_income):
    """Check established usable amounts before PTE/SUTE, without classifying losses.

    Saved deductions include verified exclusions and usable tax deductions,
    including capital allowances/donations, but not the separately saved prior
    trade-loss deduction. Their statutory ordering/eligibility is established
    in the supporting computation; an excess here is not a carryforward award.
    """
    with localcontext() as context:
        context.prec = 40
        total = sum((item.gross_amount for item in case.incomes), ZERO)
        net = total - case.claimed_deductions - case.carried_losses
        base = max(ZERO, net)
        if normal_chargeable_income != base:
            raise ValueError('Singapore company chargeable income must reconcile to saved income, established deductions/exclusions and prior-loss deduction before exemption')
        return dict(total_income=total, established_deductions_and_exclusions=case.claimed_deductions,
            established_prior_loss_deduction=case.carried_losses,
            net_before_zero_floor=net, chargeable_income_before_exemption=base,
            scope='Established usable amounts only; does not determine ordering, eligibility or unutilised capital allowances, losses or donations')


def check_year(year):
    if type(year) is not int or year != 2026:
        raise ValueError("This policy is verified only for YA 2026")


def resident_individual_tax(chargeable_income, *, assessment_year):
    check_year(assessment_year)
    base = amount(chargeable_income)
    tax, bands = marginal_tax(base, PERSONAL_BANDS)
    return {"policy_version": POLICY_VERSION, "assessment_year": assessment_year,
            "currency": "SGD", "chargeable_income": base, "gross_tax": tax,
            "bands": bands, "source_url": PERSONAL_SOURCE, "source": dict(SOURCE_BY_URL[PERSONAL_SOURCE]),
            "stage": "resident_rate_schedule_before_credits_and_assessment_rounding"}


def company_tax(normal_chargeable_income, *, assessment_year, exemption_scheme,
                startup_eligibility_confirmed, cash_grant_eligible, allowed_tax_setoff):
    """Normal-rate income only; caller must separately route concessionary-rate income.

The explicit scheme and eligibility inputs cannot be inferred from a company name.
allowed_tax_setoff is the legally allowable credit, not raw foreign tax paid.
Cash grant is reported separately and is not subtracted again from tax payable.
"""
    check_year(assessment_year)
    if exemption_scheme not in ("partial", "startup", "none"):
        raise ValueError("Unknown exemption scheme")
    if type(cash_grant_eligible) is not bool or type(startup_eligibility_confirmed) is not bool:
        raise ValueError("Eligibility must be explicitly confirmed")
    if exemption_scheme == "startup" and not startup_eligibility_confirmed:
        raise ValueError("Start-up scheme requires confirmed eligibility")
    base, credit = amount(normal_chargeable_income), amount(allowed_tax_setoff)
    with localcontext() as context:
        context.prec = 40
        exemption = ZERO
        if exemption_scheme == "partial":
            exemption = min(base, Decimal("10000")) * Decimal(".75")
            exemption += min(max(ZERO, base - Decimal("10000")), Decimal("190000")) * Decimal(".50")
        elif exemption_scheme == "startup":
            exemption = min(base, Decimal("100000")) * Decimal(".75")
            exemption += min(max(ZERO, base - Decimal("100000")), Decimal("100000")) * Decimal(".50")
        taxable = base - exemption
        gross_tax = taxable * Decimal(".17")
        if credit > gross_tax:
            raise ValueError("Allowed tax set-off cannot exceed gross tax")
        before_rebate = gross_tax - credit
        grant = Decimal("2000") if cash_grant_eligible else ZERO
        rebate = max(ZERO, min(before_rebate * Decimal(".50"), Decimal("40000")) - grant)
        return {"policy_version": POLICY_VERSION, "assessment_year": assessment_year, "currency": "SGD",
                "normal_chargeable_income": base, "exemption_scheme": exemption_scheme,
                "exempt_amount": exemption, "taxable_after_exemption": taxable,
                "gross_tax": gross_tax, "allowed_tax_setoff": credit, "tax_before_rebate": before_rebate,
                "cit_rebate": rebate, "cash_grant_separate": grant, "net_tax": before_rebate - rebate,
                "source_url": CORPORATE_SOURCE, "source": dict(SOURCE_BY_URL[CORPORATE_SOURCE]), "stage": "normal_rate_tax_before_prepayments_and_assessment_rounding"}
