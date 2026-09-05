"""DS-06 seeding: required master data present, idempotent, secret-free."""

from __future__ import annotations

from packages.persistence.settings import L0_SETTINGS, seed_system_settings


class FakeSession:
    def __init__(self):
        self.added = []
        self._rows = {}

    def execute(self, stmt):
        class _R:
            def scalar_one_or_none(self_inner):
                return None
        return _R()

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        pass


def test_seed_writes_all_required_keys():
    session = FakeSession()
    n = seed_system_settings(session)
    assert n == len(L0_SETTINGS)
    keys = {s.key for s in session.added}
    for required in ("release_level", "legal_coverage_cutoff", "research_watermark_required", "professional_validation"):
        assert required in keys


def test_l0_envelope_values():
    assert L0_SETTINGS["release_level"][0] == "L0"
    assert L0_SETTINGS["research_watermark_required"][0] is True
    assert L0_SETTINGS["professional_validation"][0]["validator_enforced"] is True
