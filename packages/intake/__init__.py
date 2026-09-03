"""Natural-language case intake for L0: description -> candidate fact card.

The LLM may only *propose* facts (confirmation_status=ai_candidate); the
fact dictionary is the vocabulary contract, and anything outside it is
rejected. Deterministic judgement stays in the rule engine.
"""

from packages.intake.extraction import (
    ExtractionError,
    ExtractionResult,
    extract_facts,
    validate_candidates,
)
from packages.intake.prompting import build_system_prompt, build_user_prompt, field_catalog

__all__ = [
    "ExtractionError",
    "ExtractionResult",
    "build_system_prompt",
    "build_user_prompt",
    "extract_facts",
    "field_catalog",
    "validate_candidates",
]
