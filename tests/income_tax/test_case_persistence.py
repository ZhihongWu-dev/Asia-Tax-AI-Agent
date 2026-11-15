import pytest
from packages.chat.store import ChatStore, CaseNotFound, RevisionConflict
from packages.chat.income_tax import save_case
from packages.contracts.income_tax import IncomeTaxCase


def inputs(amount="100"):
    return IncomeTaxCase(subject="company", jurisdiction="cn", period_start="2026-01-01", period_end="2026-12-31", currency="CNY", residency="resident", incomes=[dict(category="business", source_jurisdiction="cn", gross_amount=amount, description="Sales")])


def test_owner_revision_and_replay(tmp_path):
    store=ChatStore("sqlite:///" + str(tmp_path / "cases.sqlite"))
    doc=store.create("alice")
    with pytest.raises(CaseNotFound): save_case(store, "bob", doc["id"], 0, "one", inputs())
    saved=save_case(store, "alice", doc["id"], 0, "one", inputs())
    assert saved["revision"] == 1
    assert saved["income_tax_status"] == "needs_information"
    assert save_case(store, "alice", doc["id"], 0, "one", inputs())["revision"] == 1
    with pytest.raises(ValueError, match="request_payload_conflict"):
        save_case(store, "alice", doc["id"], 1, "one", inputs("200"))
    with pytest.raises(RevisionConflict): save_case(store, "alice", doc["id"], 0, "two", inputs())
    reopened=ChatStore("sqlite:///" + str(tmp_path / "cases.sqlite"))
    assert reopened.get("alice", doc["id"])["income_tax"]["incomes"][0]["gross_amount"] == "100"


def test_amendment_invalidates_result_preserves_dividend_facts(tmp_path):
    store=ChatStore("sqlite:///" + str(tmp_path / "cases.sqlite"));doc=store.create("alice")
    save_case(store,"alice",doc["id"],0,"one",inputs())
    doc=store.get("alice",doc["id"]);doc["income_tax_result"]={"amount":"5"};doc["facts"]={"existing":"unchanged"};store.save("alice",doc,1)
    save_case(store,"alice",doc["id"],2,"two",inputs("200"))
    doc=store.get("alice",doc["id"])
    assert "income_tax_result" not in doc
    assert doc["facts"] == {"existing":"unchanged"}
    assert doc["income_tax_history"][0]["inputs"]["incomes"][0]["gross_amount"] == "100"
