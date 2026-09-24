"""FastAPI application for the L0 research prototype.

Endpoints:
- ``GET  /health``       readiness probe (no credentials in the response);
- ``GET  /api/meta``     what the local knowledge base and model currently hold;
- ``GET  /api/samples``  synthetic English demo cases;
- ``POST /api/analyze``  run one case through intake -> chain -> citations.

Local research use only. L0 governance (PRD s.3.3, decision D-002): only
synthetic data may reach the model, so /api/analyze requires the caller to
confirm the case is fictional. Nothing here produces a tax conclusion.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from packages.contracts.enums import JUDGEMENT_CHAIN
from packages.intake.extraction import ExtractionError
from packages.knowledge_loader import parser as knowledge_parser
from packages.model_adapter.client import ModelError, get_model_config
from packages.persistence.config import get_settings
from packages.persistence.db import session_scope
from packages.persistence.models import LegalUnit, RuleNode, RuleSet, Source
from packages.rule_engine.runner import EVALUATED_NODES, GATE_NODE

SAMPLES_PATH = Path(__file__).resolve().parent / "demo_cases_en.json"
MAX_CASE_CHARS = 4000

app = FastAPI(title="Asia Tax AI Agent — HK FSIE L0", version="0.2.1")


@app.get("/health")
def health() -> dict[str, str]:
    database = make_url(get_settings().database_url).render_as_string(hide_password=True)
    return {"status": "ok", "release_level": "L0", "database": database}


@lru_cache
def _samples() -> dict[str, Any]:
    return json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))


def _sample_ids() -> set[str]:
    return {case["id"] for case in _samples()["cases"]}


@app.get("/api/samples")
def samples() -> dict[str, Any]:
    return _samples()


def _latest_rule_set(session) -> RuleSet | None:
    return session.execute(
        select(RuleSet).where(RuleSet.jurisdiction == "HK", RuleSet.package == "fsie")
        .order_by(RuleSet.id.desc()).limit(1)
    ).scalar_one_or_none()


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    manifest = knowledge_parser._read_json(knowledge_parser.FSIE_DIR / "source_manifest.json")
    model = get_model_config()
    try:
        with session_scope() as session:
            rule_set = _latest_rule_set(session)
            # Only nodes this engine can evaluate count; the gate is not a step.
            loaded_nodes = (
                session.execute(select(RuleNode.node).where(RuleNode.rule_set_id == rule_set.id)).scalars().all()
                if rule_set
                else []
            )
            parsed_sources = session.scalar(
                select(func.count()).select_from(Source).where(Source.parse_status == "parsed")
            )
            legal_units = session.scalar(select(func.count()).select_from(LegalUnit))
            rule_set_version = rule_set.version if rule_set else None
            rule_set_status = (rule_set.professional_validation_status or "unverified") if rule_set else None
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {type(exc).__name__}") from exc

    implemented = {n for n in loaded_nodes if n in EVALUATED_NODES and n != GATE_NODE}
    return {
        "release_level": "L0",
        "jurisdiction": "HK",
        "package": "fsie",
        "rule_set_version": rule_set_version,
        "rule_set_status": rule_set_status,
        "chain_nodes_total": len([k for k, v in JUDGEMENT_CHAIN.items() if v > 0]),
        "chain_nodes_implemented": len(implemented),
        "sources_registered": len(manifest["sources"]),
        "sources_parsed": parsed_sources or 0,
        "legal_units": legal_units or 0,
        "legal_coverage_cutoff": manifest.get("legal_coverage_cutoff"),
        "model": model.model_name if model.is_configured else None,
    }


CaseText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=MAX_CASE_CHARS)]


class AnalyzeRequest(BaseModel):
    text: CaseText
    confirm_synthetic: bool = False
    sample_id: str | None = None


def _preflight() -> None:
    """Fail before the model call if the database or rule set is missing, so a
    broken setup never spends a model call."""
    try:
        with session_scope() as session:
            rule_set = _latest_rule_set(session)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {type(exc).__name__}") from exc
    if rule_set is None:
        raise HTTPException(status_code=503, detail="no HK/fsie rule set loaded; run make load")


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    if not request.confirm_synthetic:
        raise HTTPException(
            status_code=400,
            detail="L0 accepts fictional (synthetic) cases only. Confirm the case contains no real client data.",
        )
    if not get_model_config().is_configured:
        raise HTTPException(status_code=503, detail="model adapter not configured (.env)")
    _preflight()

    from packages.intake.service import analyze_case  # heavy imports only when used

    # Only known preset ids become case ids; anything else falls back to a
    # content hash, so arbitrary client strings never reach the database.
    case_id = f"WEB-{request.sample_id}" if request.sample_id in _sample_ids() else None
    try:
        result = analyze_case(request.text, case_id)
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=f"extraction rejected by the fact dictionary: {exc}") from exc
    except ModelError as exc:
        raise HTTPException(status_code=502, detail=f"model call failed: {exc}") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"database error: {type(exc).__name__}") from exc
    except SystemExit as exc:  # raised when no rule set has been loaded
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    result.pop("report_markdown", None)
    result.pop("raw_facts", None)
    return result
