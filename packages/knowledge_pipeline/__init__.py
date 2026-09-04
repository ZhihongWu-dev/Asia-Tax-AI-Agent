"""L0 knowledge pipeline (Iteration 2): fetch -> snapshot -> segment -> units.

Official sources are immutable once snapshotted; every legal unit is
hash-pinned and locatable. Content drift (hash change) is recorded, never
silently absorbed.
"""

from packages.knowledge_pipeline.segment import (
    UnitDraft,
    segment_cap112,
    segment_html,
    segment_pdf,
)

__all__ = ["UnitDraft", "segment_cap112", "segment_html", "segment_pdf"]
