from decimal import Decimal, localcontext
import pytest
from packages.income_tax.arithmetic import Band, marginal_tax
from packages.income_tax.singapore import company_tax, resident_individual_tax, PERSONAL_BANDS


@pytest.mark.parametrize("base,expected", [
    ("0", "0"), ("20000", "0"), ("30000", "200"), ("40000", "550"),
    ("80000", "3350"), ("120000", "7950"), ("160000", "13950"),
    ("200000", "21150"), ("240000", "28750"), ("280000", "36550"),
    ("320000", "44550"), ("500000", "84150"), ("1000000", "199150"),
    ("1100000", "223150"),
])
def test_resident_schedule_matches_iras_published_cumulative_tax(base, expected):
    result = resident_individual_tax(base, assessment_year=2026)
    assert result["gross_tax"] == Decimal(expected)
    assert sum(band.taxable for band in result["bands"]) == Decimal(base)


def test_every_threshold_uses_next_marginal_rate_without_a_tax_cliff():
    for index, band in enumerate(PERSONAL_BANDS[:-1]):
        tax = resident_individual_tax(band.upper, assessment_year=2026)["gross_tax"]
        above = resident_individual_tax(band.upper + Decimal(".01"), assessment_year=2026)["gross_tax"]
        below = resident_individual_tax(band.upper - Decimal(".01"), assessment_year=2026)["gross_tax"]
        assert above - tax == Decimal(".01") * PERSONAL_BANDS[index + 1].rate
        assert tax - below == Decimal(".01") * band.rate


@pytest.mark.parametrize("base,setoff,grant,rebate,net", [
    ("75000", "750", False, "6000", "6000"),
    ("17500", "0", True, "0", "2975"),
    ("297500", "175", True, "23200", "27200"),
    ("1000000", "0", True, "38000", "132000"),
    ("0", "0", True, "0", "0"),
])
def test_company_iras_examples_and_rebate_cap(base, setoff, grant, rebate, net):
    result = company_tax(base, assessment_year=2026, exemption_scheme="none",
                         startup_eligibility_confirmed=False, cash_grant_eligible=grant,
                         allowed_tax_setoff=setoff)
    assert result["cit_rebate"] == Decimal(rebate)
    assert result["net_tax"] == Decimal(net)
    assert result["cash_grant_separate"] == (Decimal("2000") if grant else 0)


@pytest.mark.parametrize("scheme,base,exempt", [
    ("partial", "10000", "7500"), ("partial", "200000", "102500"),
    ("partial", "300000", "102500"), ("startup", "100000", "75000"),
    ("startup", "200000", "125000"), ("startup", "300000", "125000"),
])
def test_exemption_bands_and_caps(scheme, base, exempt):
    result = company_tax(base, assessment_year=2026, exemption_scheme=scheme,
                         startup_eligibility_confirmed=True, cash_grant_eligible=False,
                         allowed_tax_setoff="0")
    assert result["exempt_amount"] == Decimal(exempt)


@pytest.mark.parametrize("invalid", ["NaN", "Infinity", "-1", "1e19", 0.1, True, "0.0000001", "not money", None])
def test_invalid_money_never_becomes_a_tax_result(invalid):
    with pytest.raises(ValueError):
        resident_individual_tax(invalid, assessment_year=2026)


def test_no_unverified_year_or_startup_eligibility():
    with pytest.raises(ValueError, match="YA 2026"):
        resident_individual_tax("100000", assessment_year=2027)
    with pytest.raises(ValueError, match="confirmed eligibility"):
        company_tax("100000", assessment_year=2026, exemption_scheme="startup",
                    startup_eligibility_confirmed=False, cash_grant_eligible=False, allowed_tax_setoff="0")
    with pytest.raises(ValueError, match="cannot exceed"):
        company_tax("100", assessment_year=2026, exemption_scheme="none",
                    startup_eligibility_confirmed=False, cash_grant_eligible=False, allowed_tax_setoff="18")


def test_decimal_context_cannot_change_arithmetic():
    with localcontext() as context:
        context.prec = 5
        result = resident_individual_tax("1100000.01", assessment_year=2026)
    assert result["gross_tax"] == Decimal("223150.0024")


def test_malformed_schedule_rejected_even_for_zero_income():
    with pytest.raises(ValueError):
        marginal_tax("0", [Band(Decimal("100"), Decimal(".1"))])
    with pytest.raises(ValueError):
        marginal_tax("0", [Band(Decimal("100"), Decimal(".1")), Band(Decimal("50"), Decimal(".2")), Band(None, Decimal(".3"))])


def test_policy_sources_resolve_to_registered_unchanged_official_snapshots():
    import csv
    import hashlib
    from pathlib import Path
    from packages.income_tax.singapore import SOURCE_MANIFEST, POLICY_VERSION
    root = Path(__file__).resolve().parents[2] / "database"
    with (root / "doc.csv").open(encoding="utf-8-sig", newline="") as stream:
        docs = {row["id"]: row for row in csv.DictReader(stream)}
    assert SOURCE_MANIFEST["policy_version"] == POLICY_VERSION
    assert SOURCE_MANIFEST["assessment_year"] == 2026
    for source in SOURCE_MANIFEST["sources"]:
        record = docs[source["doc_id"]]
        assert record["url"] == source["url"]
        assert record["sha256"] == source["sha256"]
        assert hashlib.sha256((root / record["file"]).read_bytes()).hexdigest() == source["sha256"]
