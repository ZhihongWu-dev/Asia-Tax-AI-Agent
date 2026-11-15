from copy import deepcopy
import pytest
from scripts.reconcile_legacy_library import reconcile


def test_preserves_tax_observations_and_updates_only_identifiers():
    row = dict(param_id="sg.final.old", scope="sg", slot="final", name="cit_rate",
               value="17", subject="company", effective_from="2020-01-01",
               cite_id="law#all", quote="tax rate is 17 percent", superseded_by="sg.final.old")
    original = deepcopy(row)
    result, _, report = reconcile([row], [], [dict(doc_id="law", cite_id="law#s1", text="The tax rate is 17 percent.")])
    assert row == original
    assert result[0]["param_id"].startswith("sg.final.cit_rate.legacy_")
    assert result[0]["superseded_by"] == result[0]["param_id"]
    assert result[0]["cite_id"] == "law#s1"
    for key in ("value", "subject", "effective_from", "quote", "name"):
        assert result[0][key] == original[key]
    again, _, second = reconcile(result, [], [dict(doc_id="law", cite_id="law#s1", text="The tax rate is 17 percent.")])
    assert again == result and not second["parameter_renames"]


@pytest.mark.parametrize("clauses", [
    [dict(doc_id="other", cite_id="other#s1", text="same quote")],
    [dict(doc_id="law", cite_id="law#s1", text="same quote"), dict(doc_id="law", cite_id="law#s2", text="same quote")],
    [dict(doc_id="law", cite_id="law#s1", text="different quote")],
])
def test_ambiguous_missing_or_other_document_quote_never_rebinds(clauses):
    source = [dict(id="decision", cite_id="law#all", quote="same quote")]
    _, result, report = reconcile([], source, clauses)
    assert result == source
    assert len(report["unresolved_citations"]) == 1
    assert not report["exact_quote_rebindings"]
