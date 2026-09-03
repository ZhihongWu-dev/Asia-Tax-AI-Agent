"""Research report rendering for L0 evaluation runs.

Reports are rebuilt from persisted execution records (evaluation_runs +
evaluation_results + knowledge metadata). Rendering is pure and
deterministic: the same database state always reproduces the same report.
The research watermark is hard-coded and cannot be switched off.
"""

from packages.reporting.renderer import (
    NODE_LABELS_ZH,
    OUTPUT_LABELS_ZH,
    RESEARCH_WATERMARK,
    TERMINAL_LABELS_ZH,
    NodeRow,
    ReportInput,
    render_markdown,
)

__all__ = [
    "NODE_LABELS_ZH",
    "OUTPUT_LABELS_ZH",
    "RESEARCH_WATERMARK",
    "TERMINAL_LABELS_ZH",
    "NodeRow",
    "ReportInput",
    "render_markdown",
]
