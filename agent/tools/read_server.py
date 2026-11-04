#!/usr/bin/env python
"""tax-read: the retrieval service over the law library, a run's products and a case file (agent/retrieval_spec.en.md §10).

  python agent/tools/read_server.py --root cases --db database --rule rule --agent front|analysis|review|polish

One process per identity: the identity decides what may be read (agent/tools/access.py, shared with the guard hook), and
the process lives as long as one agent session, which is the scope of the session de-duplication. Returns are verbatim and
carry no scores. Python 3.11; depends on the `mcp` package (2.x).
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import read_core as RC  # noqa: E402

INSTRUCTIONS = ("Reading and retrieval for the case agents: map a case instead of globbing it; search the law, the products and the case "
                "file with several questions in one call; list a kind of record; get one record or clause verbatim; expand along edges; "
                "ground a quote. The ids returned are the refs of the sources table. Text is verbatim; there are no scores.")


def build_server(root, db, rule, agent):
    from mcp.server.mcpserver import MCPServer
    r = RC.Reader(agent, cases_root=root, db_root=db, rule_root=rule)
    s = MCPServer("tax-read-%s" % agent, version=RC.SERVER_VERSION, instructions=INSTRUCTIONS)

    @s.tool(name="map")
    def map_tool(case_id: str) -> dict:
        """The folders and files of a case you may read, each with a one-line meaning; the current round and run; counts of the
        product records; the parsing status of each document; the library's size. Use it instead of Glob."""
        return r.map(case_id)

    @s.tool(name="search")
    def search_tool(queries: list[str], scope: str = "all", filters: dict | None = None, k: int = 8, max_chars: int = RC.BUDGET, full: bool = False) -> dict:
        """Search with several questions at once. scope: law (provisions, treaties, guidance), products (the run's computed records),
        case (facts, sources, dialogue, notes, document pages), or all. filters: case_id, run_id (default the current run), and
        jur, as_of (YYYY-MM-DD, the law in force that day), lang, doc, type, cand, branch, point, scenario, slot, page.
        Hits carry an id (cite it as the ref), the verbatim fragment (law) or a compact card (records), the channels that found it
        and its rank; a hit already returned in this session comes back as its id only unless full=true."""
        return r.search(queries, scope, filters or {}, k, max_chars, full)

    @s.tool(name="list")
    def list_tool(kind: str, filters: dict | None = None, k: int = 20, cursor: int = 0) -> dict:
        """Cards of one kind of record, paged with cursor. Library: params (jur, slot, subject), absences (jur, slot), treaties
        (jur, jur_b), jurisdictions, blocked, decisions, docs. Products (case_id or run_id): structures, branches, hops, cells,
        rules, points, scenarios, open_items, requirements, transfers, exposures, penalties, past_payments, gaps, brief, diff,
        input. Case file (case_id): facts, sources, dialogue, answers, notes, documents, pages, handoff, to_collect, constraints."""
        return r.list(kind, filters or {}, k, cursor)

    @s.tool(name="get")
    def get_tool(id: str, offset: int = 0, max_chars: int = RC.GET_PAGE) -> dict:
        """One item verbatim, paged by offset: a clause (cite_id such as treaty.cn-hk.2006.zh#10.2, or a unit cite_id@n), a record
        (<run_id>:<type>:<key> or <case_id>:<type>:<key>), param:<id> (with its history), doc:<id>, decision:<id>, rule:<id>,
        or file:<case_id>/<path> for a text file of the case."""
        return r.get(id, offset, max_chars)

    @s.tool(name="expand")
    def expand_tool(id: str, kinds: list[str] | None = None, depth: int = 1, k: int = 20) -> dict:
        """The neighbours of a clause or a record along explicit edges, grouped by kind: for a clause contains / in, cites /
        cited_by, same_provision, co_cited, rule_cites, param_cites; for a record branch, hop, cell, rule, cites, delta,
        requirement, transfer, first_if_favourable, first_if_unfavourable, blocks, source, page (and of_<kind> backwards)."""
        return r.expand(id, kinds, depth, k)

    @s.tool(name="ground")
    def ground_tool(id: str, quote: str) -> dict:
        """Whether a quote occurs in the clause, record or page `id`: match exact (whitespace ignored) or none; for an OCR page
        approximate with the matched span, for review to judge."""
        return r.ground(id, quote)

    @s.tool(name="pack")
    def pack_tool(case_id: str, node: str) -> dict:
        """The prefetch pack of a node (analysis, review_draft, review_final, review_intake, front): its path and item ids.
        The orchestrator writes it before the node starts; call this to rebuild it."""
        return r.pack(case_id, node)

    @s.tool(name="cite_check")
    def cite_check_tool(case_id: str, run_id: str, target: str = "draft") -> dict:
        """Provenance of a report (target draft or polished): sources rows whose ref does not resolve, and figures of the body
        that no source row's fragment states."""
        return r.cite_check(case_id, run_id, target)

    return s


def main():
    import os
    for k, v in (("TQDM_DISABLE", "1"), ("TRANSFORMERS_VERBOSITY", "error"), ("TOKENIZERS_PARALLELISM", "false"), ("HF_HUB_OFFLINE", "1")):
        os.environ.setdefault(k, v)                              # stdout carries the protocol: no progress bars, no chatter
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="cases")
    ap.add_argument("--db", default="database")
    ap.add_argument("--rule", default="rule")
    ap.add_argument("--agent", required=True, choices=RC.access.AGENTS)
    a = ap.parse_args()
    build_server(Path(a.root), Path(a.db), Path(a.rule), a.agent).run(transport="stdio")


if __name__ == "__main__":
    main()
