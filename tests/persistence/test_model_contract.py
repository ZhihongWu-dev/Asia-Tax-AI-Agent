"""The ORM model must stay a faithful translation of the shared contract."""

from __future__ import annotations

import re

from sqlalchemy import CheckConstraint

from packages.contracts.enums import (
    JUDGEMENT_CHAIN,
    CaseStatus,
    CaseTerminalState,
    FactConfirmationStatus,
    NodeOutputStatus,
    ProfessionalValidationStatus,
    values,
)
from packages.persistence import models  # noqa: F401  (registers tables on Base)
from packages.persistence.base import Base

EXPECTED_TABLES = {
    "organizations",
    "cases",
    "facts",
    "fact_versions",
    "rule_sets",
    "rule_nodes",
    "rule_executions",
    "evaluation_cases",
    "evaluation_runs",
    "evaluation_results",
    "audit_events",
    "sources",
    "legal_units",
}

# Knowledge definitions are global; everything else that runs a case is tenant-scoped.
BUSINESS_TABLES_WITH_ORG = {
    "cases",
    "facts",
    "fact_versions",
    "rule_executions",
    "evaluation_runs",
    "evaluation_results",
}
GLOBAL_TABLES_WITHOUT_ORG = {
    "organizations",
    "rule_sets",
    "rule_nodes",
    "evaluation_cases",
    "audit_events",  # organization_id intentionally nullable
    "sources",  # knowledge layer is global
    "legal_units",
}

EXPECTED_CHECK_VALUES = {
    "ck_rule_node_node": set(JUDGEMENT_CHAIN),
    "ck_rule_exec_node": set(JUDGEMENT_CHAIN),
    "ck_eval_result_node": set(JUDGEMENT_CHAIN),
    "ck_rule_node_status": values(ProfessionalValidationStatus),
    "ck_evaluation_case_state": values(CaseTerminalState),
    "ck_eval_run_state": values(CaseTerminalState),
    "ck_case_status": values(CaseStatus),
    "ck_fact_confirmation": values(FactConfirmationStatus),
    "ck_fact_version_confirmation": values(FactConfirmationStatus),
    "ck_rule_exec_output": values(NodeOutputStatus),
    "ck_eval_result_output": values(NodeOutputStatus),
}


def _in_values(constraint: CheckConstraint) -> set[str]:
    match = re.search(r"IN \((.*)\)", str(constraint.sqltext))
    assert match, f"unexpected check expression: {constraint.sqltext}"
    return set(re.findall(r"'([^']*)'", match.group(1)))


def test_exactly_the_first_slice_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_business_tables_carry_organization_id():
    for table_name in BUSINESS_TABLES_WITH_ORG:
        assert "organization_id" in Base.metadata.tables[table_name].columns
    for table_name in GLOBAL_TABLES_WITHOUT_ORG - {"audit_events"}:
        assert "organization_id" not in Base.metadata.tables[table_name].columns


def test_every_enum_check_matches_the_contract_and_none_is_missing():
    seen: set[str] = set()
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if not isinstance(constraint, CheckConstraint):
                continue
            if constraint.name in EXPECTED_CHECK_VALUES:
                seen.add(constraint.name)
                assert _in_values(constraint) == EXPECTED_CHECK_VALUES[constraint.name], (
                    f"CHECK {constraint.name} drifted from its contract enum"
                )
    assert seen == set(EXPECTED_CHECK_VALUES), f"missing CHECK constraints: {set(EXPECTED_CHECK_VALUES) - seen}"
