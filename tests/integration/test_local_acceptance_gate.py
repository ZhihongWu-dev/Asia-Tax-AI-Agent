"""Prevent the local integration command from accepting a partially evidenced report."""
import pytest
from scripts.check_combined_local import checks_pass


@pytest.mark.parametrize('change', [
    {'missing_domain_citations': 1}, {'missing_domain_citations': 308},
    {'report_frozen': False}, {'fsie_locators': 20}, {'reload': False},
])
def test_report_with_failed_acceptance_check_is_rejected(change):
    checks = dict(report_frozen=True, fsie_locators=21,
                  missing_domain_citations=0, reload=True)
    assert checks_pass(checks)
    checks.update(change)
    assert not checks_pass(checks)


def test_missing_citation_check_is_not_treated_as_zero():
    assert not checks_pass(dict(report_frozen=True, fsie_locators=21, reload=True))
