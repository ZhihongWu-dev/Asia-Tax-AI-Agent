"""Check that the database, CSVs, decisions and engine are a compatible handoff."""
import argparse
import ast
import csv
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from tax_graph.params import Params
from tax_graph.rules.compile import compile_rules, param_refs
from tax_graph.rules.spec import SPEC


def rows(path):
    csv.field_size_limit(10 ** 9)
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def compact(text):
    return re.sub(r"\s+", "", text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-params", type=Path)
    parser.add_argument("--previous-clauses", type=Path)
    args = parser.parse_args()
    params = Params()
    compiled = compile_rules(SPEC, params)
    references = sorted({pid for rule in SPEC for pid in param_refs(rule)})
    con = sqlite3.connect("file:" + (ROOT / "official.sqlite").as_posix() + "?mode=ro", uri=True)
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    assert integrity == "ok", integrity
    db_params = {row[0] for row in con.execute("SELECT param_id FROM param")}
    assert db_params == set(params.rows), "Database and params.csv differ"
    columns = [row[1] for row in con.execute("PRAGMA table_info(param)")]
    for record in con.execute("SELECT * FROM param"):
        row = dict(zip(columns, record))
        assert row == params.rows[row["param_id"]], row["param_id"]
    clauses = {cid: text for cid, text in con.execute("SELECT cite_id, text FROM clause")}
    csv_clauses = {row["cite_id"]: row["text"] for row in rows(ROOT / "clauses.csv")}
    assert clauses == csv_clauses, "Database and clauses.csv differ"
    decisions = rows(ROOT / "decisions.csv")
    db_decisions = list(con.execute("SELECT id, seq, statement, cite_id, quote, used_in FROM decision ORDER BY id, seq"))
    expected = sorted((row["id"], int(row["seq"]), row["statement"], row["cite_id"], row["quote"], row["used_in"]) for row in decisions)
    assert db_decisions == expected, "Database and decisions.csv differ"
    for row in decisions:
        assert row["quote"] and compact(row["quote"]) in compact(clauses.get(row["cite_id"], "")), row
    required = {"D%02d" % number for number in range(14, 32)}
    assert required <= {row["id"] for row in decisions}, "Missing D14-D31 decisions"
    code_clauses = set()
    for file in (ROOT.parent / "tax_graph").rglob("*.py"):
        if file.name.startswith("check_") or "validation" in file.parts:
            continue
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if re.fullmatch(r"[a-z][a-z0-9.-]+#[A-Za-z0-9()._-]+", node.value):
                    code_clauses.add(node.value)
    referenced_clauses = sorted(code_clauses | {source for rule in compiled for source in rule.sources if "#" in source})
    assert set(referenced_clauses) <= set(clauses), "Missing engine clause references"
    result = {
        "integrity_check": integrity, "rules": len(compiled), "documents": con.execute("SELECT COUNT(*) FROM doc").fetchone()[0],
        "clauses": len(clauses), "parameters": len(params.rows), "referenced_parameters": len(references),
        "referenced_clauses": len(referenced_clauses),
        "missing_parameters": [], "missing_clauses": [], "decisions": len({row["id"] for row in decisions}),
        "decision_quote_rows_checked": len(decisions), "required_decisions": sorted(required),
        "csv_database_consistent": True,
    }
    if args.previous_params:
        prior = {row["param_id"] for row in rows(args.previous_params)}
        result["previous_missing_parameters"] = sorted(set(references) - prior)
    if args.previous_clauses:
        prior = {row["cite_id"] for row in rows(args.previous_clauses)}
        result["previous_missing_clauses"] = sorted(set(referenced_clauses) - prior)
    (ROOT / "handoff_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# official 配套资料核对", "", "由 `python official/tools/audit_handoff.py` 核对当前资料库和引擎。", "",
             "- 数据库完整性：`ok`。", "- 参数、条款、口径 CSV 与数据库内容一致。",
             "- %d 条规则编译通过；缺少参数 0，缺少法条引用 0。" % len(compiled),
             "- D14–D31 均有记录，全部口径引语在所引条款中逐字找到（忽略空白）。", "",
             "## D14–D31 的原文依据", "", "完整陈述、原文引语及使用位置见 [decisions.csv](decisions.csv)。", "",
             "| 口径 | 引文锚点数 | 依据原件 |", "|---|---:|---|"]
    if args.previous_params and args.previous_clauses:
        lines[4:4] = ["- 对照此前上传版本：原先缺少的 %d 个参数、%d 个法条引用均已补齐。" % (
            len(result["previous_missing_parameters"]), len(result["previous_missing_clauses"]))]
    documents = {doc_id: path for doc_id, path in con.execute("SELECT id, file FROM doc")}
    for did in sorted(required):
        entries = [row for row in decisions if row["id"] == did]
        paths = sorted({documents[row["cite_id"].split("#")[0]] for row in entries})
        links = ", ".join("[%s](%s)" % (Path(path).name, path) for path in paths)
        lines.append("| %s | %d | %s |" % (did, len(entries), links))
    lines += ["", "废止或替代关系保留在 [removed.csv](removed.csv)、[superseded.csv](superseded.csv) 和 [repealed_stubs.csv](repealed_stubs.csv)，适用局限见 [currency.csv](currency.csv)。本次沿用来源记录，没有另行编写法律口径。",
              "", "构建报告见 [STATUS.md](STATUS.md) 和 [INDEX.md](INDEX.md)，详细核对结果见 [handoff_audit.json](handoff_audit.json)。",
              "口径属于项目登记的法律解释，本核对验证证据链和代码配套关系，不代表外部税务专家审核。"]
    (ROOT / "HANDOFF.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    con.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
