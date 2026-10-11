"""Run the shipped engine checks and samples without accessing the source project."""
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent
MODULES = (
    "rules", "check_engine", "check_fields", "check_extract", "check_scope",
    "check_entity", "check_cn_wht", "check_flow_tax", "check_hk_tax", "check_sg_s45",
)


def run(name, args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    text = result.stdout.decode("utf-8", "replace")
    (DEST / (name + ".log")).write_text(text, encoding="utf-8")
    return {"name": name, "command": "python " + " ".join(args),
            "exit_code": result.returncode, "log": name + ".log"}


def main():
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda name: run(name, ["-m", "tax_graph." + name]), MODULES))
    for name, case, table in (
        ("meridian", "meridian.json", False),
        ("meridian_table", "meridian.json", True),
        ("hk_sample", "hk_holding_services.synthetic.json", True),
    ):
        args = ["-m", "tax_graph.run", "tax_graph/examples/" + case,
                "--out-dir", "tax_graph/examples/results"]
        if table:
            args.append("--table")
        results.append(run(name, args))
    (DEST / "results.json").write_text(json.dumps(
        {"python": sys.version.split()[0], "results": results}, indent=2), encoding="utf-8")
    for result in results:
        print(result["name"], "PASS" if result["exit_code"] == 0 else "FAIL")
    return int(any(result["exit_code"] for result in results))


if __name__ == "__main__":
    sys.exit(main())
